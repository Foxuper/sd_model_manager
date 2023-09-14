import re
import json
import hashlib
from PIL import Image
from typing import Any
from pathlib import Path
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

		search = re.findall(rf'{re.escape(separator)}(\d+)', self.name)
		return int(search[-1]) if len(search) > 0 else None

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
		return f'{kilobytes:.0f} KB' if kilobytes.is_integer() else f'{kilobytes:.0f} KB'
	elif kilobytes < 1024 * 1024:
		megabytes = kilobytes / 1024
		return f'{megabytes:.0f} MB' if megabytes.is_integer() else f'{megabytes:.2f} MB'
	else:
		gigabytes = kilobytes / (1024 * 1024)
		return f'{gigabytes:.0f} GB' if gigabytes.is_integer() else f'{gigabytes:.2f} GB'

def format_time_hr(seconds: float):
	''' Formats a time in seconds to a human readable string '''

	if seconds < 60:
		return f'{seconds:.1f} sec'
	elif seconds < 60 * 60:
		minutes = seconds / 60
		seconds = seconds % 60
		return f'{minutes:.0f}:{seconds:02.0f} min'
	else:
		hours = seconds / (60 * 60)
		minutes = (seconds % (60 * 60)) / 60
		return f'{hours:.0f}:{minutes:02.0f} hr'

def image_has_parameters(image_file: Path):
	''' Returns true if an image has parameters '''

	image = Image.open(image_file)
	return 'parameters' in image.info

def image_to_png(directory: Path, filename: Filename):
	''' Converts an image to PNG '''

	# Skip if image is already a PNG
	if filename.extension == '.png':
		return directory / filename.full

	# Get image paths
	image_file = directory / filename.full
	png_image_file = image_file.with_suffix('.png')
	LOGGER.debug(f'Converting image "{image_file}" to PNG')

	# Read metadata from original image and save it to PNG
	with Image.open(image_file) as image:
		try:
			info = PngInfo()
			exif = read_info_from_image(image)[0]
			info.add_text('parameters', exif)
			image.save(png_image_file, pnginfo= info)

		# Save image without metadata if it fails
		except:
			LOGGER.debug(f'Failed to read metadata from image "{filename.full}"')
			image.save(png_image_file)

	# Delete original image
	image_file.unlink()
	return png_image_file