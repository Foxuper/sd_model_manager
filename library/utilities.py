import re
import sys
import time
import json
import hashlib
import requests
from PIL import Image
from pathlib import Path
from typing import Optional, Any
from PIL.PngImagePlugin import PngInfo
from modules.images import read_info_from_image

# Extension Library
import library.logger as logger

# Logger
LOGGER = logger.configure()

# JSON Cache
JSON_CACHE: dict[Path, Any] = {}

class Hashable:
	''' Hashable object that can be used in a set '''
	hash: str

	def __hash__(self):
		return hash(self.hash)

	def __eq__(self, other: Any):
		if isinstance(other, Hashable):
			return self.hash == other.hash
		return False

class Filename:
	''' Represents the final part of a path composed of a name, prefix and extension '''

	def __init__(self, filename: str | Path):
		self._filename = Path(filename).name

	def __str__(self):
		return self.full

	def __repr__(self):
		return f'Filename({self.full})'

	def __eq__(self, other: Any):
		if isinstance(other, Filename):
			return self.full == other.full
		return False

	@property
	def full(self):
		''' Returns all components of the filename joined together '''
		return self._filename

	@property
	def name(self):
		''' Returns the name component of the filename '''

		search = re.search(r'^(.*?)(\.[^\d]|\.[^.]*$|$)', self.full)
		return str(search.group(1)) if search is not None else ''

	@property
	def prefix(self):
		''' Returns the prefix component of the filename '''

		search = re.search(r'(\.[^\d].*)\.', self.full)
		return str(search.group(1)) if search is not None else ''

	@property
	def extension(self):
		''' Returns the extension of the filename '''

		search = re.search(r'(\.[^.]*)$', self.full)
		return str(search.group(1)) if search is not None else ''

	def with_name(self, name: str):
		''' Returns a new filename with the given name component '''
		return Filename(f'{name}{self.prefix}{self.extension}')

	def with_prefix(self, prefix: str):
		''' Returns a new filename with the given prefix component '''
		return Filename(f'{self.name}{prefix}{self.extension}')

	def with_extension(self, extension: str):
		''' Returns a new filename with the given extension component '''
		return Filename(f'{self.name}{self.prefix}{extension}')

	def with_index(self, index: int | None, separator= '.'):
		''' Returns a new filename with the given index component '''

		if index is None: return Filename(self.full)
		return self.with_name(f'{self.name}{separator}{index}')

	def get_index(self, separator= '.'):
		''' Returns the index component of the filename if it exists '''

		search = re.search(rf'\{separator}(\d+)$', self.name)
		return int(search.group(1)) if search is not None else None

	def find_nonexistent(self, directory: Path, separator= '.'):
		''' Returns a new filename with the next available index component in the given directory '''

		file = directory / self.full
		while file.exists():
			index = Filename(file).get_index(separator)
			if index is None:
				file = directory / self.with_index(0, separator).full
			else:
				file = directory / self.with_index(index + 1, separator).full
		return Filename(file)

def file_size_kb(file: Path):
	''' Returns the size of a file in KB '''
	return file.stat().st_size / 1024

def truncate(string: str, length: int):
	''' Truncates a string to a given length '''
	return (string[:length] + '...') if len(string) > length else string

def file_sha256(file: Path, chunk_size= 1 << 22):
	''' Calculates the SHA256 hash of a file '''

	LOGGER.info(f'Calculating SHA256 hash of "{file.name}"')
	sha256_hash = hashlib.sha256()
	with file.open('rb') as file_handle:
		for chunk in iter(lambda: file_handle.read(chunk_size), b''):
			sha256_hash.update(chunk)
	return sha256_hash.hexdigest().upper()

def rename_file(file: Path, new_name: str, indexed= False):
	''' Renames a file '''

	filename = Filename(file)
	index = filename.get_index()
	filename = filename.with_name(new_name)
	if indexed: filename = filename.with_index(index)
	return file.rename(file.parent / filename.full)

def clear_json_cache():
	''' Clear JSON file cache '''

	global JSON_CACHE; JSON_CACHE = {}
	LOGGER.debug('Cleared JSON file cache')

def store_json(file: Path, data: Any):
	''' Stores data in a JSON file '''

	with file.open('w') as file_handle:
		json.dump(data, file_handle, indent= 4)
		JSON_CACHE[file] = data

def load_json(file: Path, default: Any= None):
	''' Loads data from a JSON file '''

	# Return default value if file does not exist
	if not file.exists():
		return default

	# Load JSON file if not cached
	elif file not in JSON_CACHE:
		with file.open('r') as file_handle:
			JSON_CACHE[file] = json.load(file_handle)

	# Return cached JSON file
	return JSON_CACHE[file]

def get_related_files(directories: list[Path], extensions: list[str], filename: Filename):
	''' Returns a list of files that have a matching name component in a list of directories '''

	related_files: list[Path] = []
	for directory in directories:
		for related_file in directory.glob(f'{filename.name}.*'):
			if related_file.suffix in extensions and not related_file.is_symlink():
				related_files.append(related_file)
	related_files.sort()
	return related_files

def path_in_list(path: Path, paths: list[Path]):
	''' Returns True if a path exists in a list of paths '''

	# Resolve all paths
	path = path.resolve()
	paths = [p.resolve() for p in paths]

	# Compare paths
	for p in paths:
		if path.samefile(p):
			return True
	return False

def get_directories(paths: list[Path | None]):
	''' Returns a list of unique directories from a list of paths '''

	directories: list[Path] = []
	for path in paths:
		if path is not None and path.is_dir() and not path_in_list(path, directories):
			directories.append(path)
	return directories

def find_file(directories: list[Path], filename: Filename):
	''' Returns the first existing file from a list of directories '''

	for directory in directories:
		file_path = directory / filename.full
		if file_path.exists():
			return file_path
	return None

def format_size_hr(kilobytes: float):
	''' Formats a size in Kylobytes to a human readable string '''

	if kilobytes < 1024:
		return f'{kilobytes:.2f} KB'
	elif kilobytes < 1024 * 1024:
		megabytes = kilobytes / 1024
		return f'{megabytes:.2f} MB'
	else:
		gigabytes = kilobytes / (1024 * 1024)
		return f'{gigabytes:.2f} GB'

def image_has_parameters(image_file: Path):
	''' Returns true if an image has parameters '''

	image = Image.open(image_file)
	return 'parameters' in image.info

def image_to_png(directory: Path, filename: Filename):
	''' Converts an image to PNG '''

	# Skip if image is already a PNG
	if filename.extension == '.png':
		return

	# Get image paths
	image_file = directory / filename.full
	png_image_file = image_file.with_suffix('.png')
	LOGGER.debug(f'Converting image "{image_file}" to PNG')

	# Read metadata from original image and save it to PNG
	image = Image.open(image_file)

	# Attempt to read metadata from image and save it to PNG
	try:
		info = PngInfo()
		exif = read_info_from_image(image)[0]
		info.add_text('parameters', exif)
		image.save(png_image_file, pnginfo= info)
	except:
		LOGGER.debug(f'Failed to read metadata from image "{filename.full}"')
		image.save(png_image_file)

	# Delete original image
	image_file.unlink()

def progress_bar(label: str, speed: str, progress: Optional[float]= None, length= 50):
	''' Prints a progress bar '''

	# Generates the progress bar
	if progress is not None:
		filled_length = int(length * progress)
		bar = '█' * filled_length + '░' * (length - filled_length)
		bar_string = f'{label}: |{bar}| {progress * 100:.1f}%'
	else:
		bar_string = f'{label}'

	# Prints the progress bar and speed
	sys.stdout.write(logger.TerminalColor.BLUE.wrap(bar_string))
	sys.stdout.write(f' - {speed}')

	# Flushes the buffer
	sys.stdout.write('    \r')
	sys.stdout.flush()

def download_file(url: str, directory: Path, filename: Filename, chunk_count= 100):
	'''
		Downloads a file from a URL
		- The header file extension is used over the provided filename extension
		- If the file already exists, generates a new name with an index suffix
		- Returns the name of the downloaded file or None if the download failed
	'''

	LOGGER.info(f'Start download from: {url}')

	# Make the request
	try:
		response = requests.get(url, stream= True)
	except Exception as e:
		LOGGER.error(f'The download request failed: {e}')
		return None

	# Get content type
	try:
		content_type = response.headers['Content-Type']
	except:
		content_type = ''

	# The file is an image
	if 'image' in content_type:
		file_size = None

		# Parse file extension from content type
		search = re.search(r'image\/([\w]+)', content_type)
		extension = f'.{search.group(1)}' if search is not None else None
	else:
		# Get file info from header
		try:
			file_size = int(response.headers['Content-Length'])
			file_disposition = response.headers['Content-Disposition']
		except:
			LOGGER.error(f'Failed to get file info from header: {response.headers}')
			return None

		# Parse file name from disposition
		search = re.search(r'filename="([\w.]+)"', file_disposition)
		extension = Filename(search.group(1)).extension if search is not None else None

	# Get the file extension
	extension = filename.extension if extension is None else extension

	# Find a unique file name and get the file path
	filename = filename.with_extension(extension).find_nonexistent(directory, '')
	LOGGER.debug(f'Download file name: {filename.full}')
	file = directory / filename.full

	# Generate power of 2 chunk size
	chunk_size = file_size // chunk_count if file_size is not None else 1 << 10
	chunk_size = 2 ** (chunk_size >> 1).bit_length()
	LOGGER.debug(f'Download chunk size: {chunk_size / 1024} KB')

	# Download file
	try:
		downloaded_size = 0
		download_start = time.perf_counter()

		with file.open('wb') as f:
			for chunk in response.iter_content(chunk_size):
				downloaded_size += len(chunk)
				f.write(chunk)
				f.flush()

				# Calculate time difference
				current_time = time.perf_counter()
				time_delta = current_time - download_start
				current_time = download_start

				# Download speed
				download_speed = downloaded_size / time_delta
				formatted_speed = f'{download_speed / 1024 / 1024:.2f} MB/s'

				# Progress bar
				progress = None if file_size is None else downloaded_size / file_size
				progress_bar('> Downloading', formatted_speed, progress)

			# Flush progress bar
			sys.stdout.write('\n')
			sys.stdout.flush()

			# Verify file size
			if file_size is None or downloaded_size == file_size:
				LOGGER.info(f'Download complete')
				size_error = False
			else:
				size_error = True

		# Delete file if size mismatch
		if size_error:
			LOGGER.error(f'Download failed: File size mismatch')
			if file.exists(): file.unlink()
			return None

		# Return filename on success
		return filename

	except Exception as e:
		LOGGER.error(f'Download failed: {e}')
		return None