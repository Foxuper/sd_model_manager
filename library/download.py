import re
import tempfile
import requests
import threading
from tqdm import tqdm
from enum import Enum
from pathlib import Path
from collections import deque

# Extension Library
from library import paths
from library import logger
from library import civitai
from library import sd_webui
from library import utilities
from library.utilities import Filename

# Logger
LOGGER = logger.configure()

class File:
	''' File entity used for downloading files '''

	class Status(Enum):
		INVALID     = 'Invalid'
		QUEUED      = 'Queued'
		DOWNLOADING = 'Downloading'
		COMPLETE    = 'Complete'
		FAILED      = 'Failed'

	@property
	def file(self):
		''' The full path to the file '''
		return self.directory / self.filename.full

	@property
	def exists(self):
		''' Whether the file exists or not '''
		return self.file.exists()

	@property
	def complete(self):
		''' Whether the file is complete or not '''
		return self.status == File.Status.COMPLETE

	@property
	def mean_speed(self):
		''' Mean download speed in bytes per second '''
		return sum(self.speed) / len(self.speed) if len(self.speed) > 0 else 0

	@property
	def speed_hr(self):
		''' Download speed in human readable format e.g. 1.2 MB/s '''
		return f'{utilities.format_size_hr(self.mean_speed / 1024)}/s'

	@property
	def estimated_time_hr(self):
		''' Estimated time remaining in human readable format e.g. 1:32 min '''

		if self.estimated_time == 0:
			return '-'
		return utilities.format_time_hr(self.estimated_time)

	@property
	def percentage_hr(self):
		''' Download percentage in human readable format e.g. 50% '''

		if self.file_size == 0 or self.downloaded == 0:
			return '100%' if self.complete else '0%'
		return f'{self.downloaded / self.file_size * 100:.2f}%'

	@property
	def progress_hr(self):
		''' Download progress in human readable format e.g. 1.2 MB / 2.5 MB '''

		if self.file_size == 0:
			return '-'
		downloaded = utilities.format_size_hr(self.downloaded / 1024)
		file_size = utilities.format_size_hr(self.file_size / 1024)
		return f'{downloaded} / {file_size}'

	def __init__(self, url: str, type: civitai.Model.Type, filename: Filename):
		LOGGER.debug(f'Initializing downloader for: {url}')

		# Get the download directory
		if filename.extension == '.png':
			directory = paths.IMAGES_DIR
		else:
			directory = paths.default_directory(type.name)

		# File info
		self.temp_file: Path | None = None
		self.response: requests.Response
		self.status = File.Status.INVALID
		self.file_size: int = 0

		# Basic info
		self.url = url
		self.type = type
		self.directory = directory
		self.filename = filename

		# Download info
		self.downloaded: int = 0
		self.estimated_time: float = 0
		self.speed: deque[float] = deque(maxlen= 10)

		# Make the request
		try:
			self.response = requests.get(url, stream= True)
			if not self.response.ok:
				raise Exception(f'HTTP status code [{self.response.status_code}]')
		except Exception as e:
			LOGGER.error(f'The download request failed: {e}'); return

		# Get header info
		content_type = self.response.headers.get('Content-Type', '')
		disposition = self.response.headers.get('Content-Disposition', '')
		self.file_size = int(self.response.headers.get('Content-Length', 0))

		# If the file is an image, extract the file extension from the content type
		if 'image' in content_type:
			search = re.search(r'image\/([\w]+)', content_type)
			extension = f'.{search.group(1)}' if search is not None else None

		# Otherwise, extract the file extension from the content disposition
		else:
			search = re.search(r'filename="([\w.]+)"', disposition)
			extension = Filename(search.group(1)).extension if search is not None else None

		# Prefer the header file extension over the provided filename extension
		extension = filename.extension if extension is None else extension
		self.filename = filename.with_extension(extension)

		# Find a unique file name if the file is not an image
		if not directory.samefile(paths.IMAGES_DIR):

			# Initialize new filename and index
			new_filename = self.filename
			index = 1

			# Find a new name if there is a name conflict
			while new_filename.name in sd_webui.model.names(type):
				new_filename = self.filename.with_index(index, '_')
				index += 1
			self.filename = new_filename

		# Assert the file does not already exist
		if self.file.exists():
			LOGGER.error(f'File already exists: {self.file}'); return

		# Mark as queued
		self.status = File.Status.QUEUED

	@classmethod
	def from_civitai_file(cls, type: civitai.Model.Type, file: civitai.File):
		return cls(file.downloadUrl, type, Filename(file.name))

	@classmethod
	def from_civitai_image(cls, type: civitai.Model.Type, image: civitai.Image, filename: Filename):
		filename = Filename(f'{type.name}_{filename.name}.png')
		return cls(image.custom_url, type, filename)

	def remove_file(self):
		''' Remove the file from the system if it exists '''

		if self.file.exists():
			self.file.unlink()

	def remove_temp_file(self):
		''' Remove the temporary download file from the system if it exists '''

		if self.temp_file is not None and self.temp_file.exists():
			self.temp_file.unlink()

	def download(self, is_running: threading.Event):
		''' Download the file while the running event is set '''

		if not is_running.is_set() or self.status != File.Status.QUEUED:
			return

		# Mark as downloading
		self.status = File.Status.DOWNLOADING

		# Create the progress bar
		progress_bar = tqdm(total= self.file_size, unit= 'iB', unit_scale= True)

		# Change the file name if it already exists
		if self.file.exists():
			self.filename = self.filename.find_nonexistent(self.directory, '_')

		# Create temporary file for writing
		with tempfile.NamedTemporaryFile(dir= self.directory, delete= False) as temp_file:
			self.temp_file = Path(temp_file.name)

			# Iterate over the response content
			for chunk in self.response.iter_content(1024 * 1024):

				# Stop the download if the running event is cleared
				if not is_running.is_set():
					progress_bar.close()
					self.speed.clear()
					temp_file.close()
					self.temp_file.unlink()
					yield self; return

				# Update the progress bar and write the chunk to the file
				progress_bar.update(len(chunk))
				temp_file.write(chunk)

				# Update download info
				self.downloaded += len(chunk)
				self.speed.append(progress_bar.format_dict['rate'] or 0)
				if self.file_size > 0:
					mean_speed = self.mean_speed if self.mean_speed > 0 else 1
					self.estimated_time = (self.file_size - self.downloaded) / mean_speed

				# Yield the download info
				yield self

		# Check if the download was successful or not
		if self.file_size == 0 or self.downloaded == self.file_size:

			# If the file is an image, convert it to png
			if self.directory.samefile(paths.IMAGES_DIR):
				self.filename = self.filename.with_extension('.png')
				self.temp_file = utilities.image_to_png(self.directory, Filename(self.temp_file.name))

			# Mark as complete
			self.status = File.Status.COMPLETE
			LOGGER.debug(f'Download complete: {self.file}')
		else:

			# Remove the temporary file and mark as failed
			self.temp_file.unlink()
			self.status = File.Status.FAILED
			LOGGER.error(f'Download failed: {self.file}')

		# Rename the temporary file to its final name
		self.temp_file.rename(self.file)

		# Close the progress bar and yield the final download info
		progress_bar.close()
		self.speed.clear()
		yield self

class DownloadManager:
	''' Download manager for downloading files in the background '''

	_instance = None
	_lock = threading.Lock()

	def __init__(self):
		self._running = threading.Event()
		self._thread: threading.Thread
		self.files: list[File] = []

	@classmethod
	def instance(cls):
		''' Returns the singleton instance of the download manager '''
		with cls._lock:
			if cls._instance is None:
				cls._instance = cls()
		cls._instance._clear()
		return cls._instance

	@property
	def running(self):
		''' whether the download manager is running or not '''
		return self._running.is_set()

	@property
	def all_complete(self):
		''' Whether all files are complete or not '''
		return all(file.complete for file in self.files)

	@property
	def incomplete_files(self):
		''' Returns all files that are not complete '''
		return [file for file in self.files if not file.complete]

	def enqueue(self, file: File):
		''' Enqueues a file to be downloaded if it is not already '''

		for existing_file in self.files:
			if existing_file.url == file.url:
				LOGGER.debug(f'File [{file.filename.full}] already in download queue')
				return

		LOGGER.debug(f'Enqueuing file: {file.filename.full}')
		self.files.append(file)

	def start(self):
		''' Starts the download manager '''

		if self.running:
			LOGGER.debug('Download manager is already running')
			return

		self._thread = threading.Thread \
		(
			target= self._download_thread,
			daemon= True
		)

		self._running.set()
		self._thread.start()
		LOGGER.debug('Download manager started')

	def stop(self):
		''' Stops the download manager '''

		if not self.running:
			LOGGER.debug('Download manager is not running')
			return

		# Stop the download thread
		self._running.clear()
		self._thread.join()
		self._clear()
		LOGGER.debug('Download manager stopped')

	def _clear(self):
		''' Clears the download queue '''

		# Only clear the queue if the download manager is not running
		if not self.running:
			self.files.clear()

	def _download_thread(self):
		''' The download thread '''

		try:
			for index, file in enumerate(self.files):
				for current_file in file.download(self._running):
					if not self.running:
						break
					self.files[index] = current_file

		except Exception as e:
			for file in self.incomplete_files:
				file.remove_temp_file()
				file.status = File.Status.FAILED
			LOGGER.error(f'Download thread failed: {e}')

		# Mark as stopped
		self._running.clear()
		LOGGER.debug('Download thread stopped')