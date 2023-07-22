import shutil
from pathlib import Path
from typing import Optional, Any, cast

# SD Webui Modules
from modules import ui

# Extension Library
from library import paths
from library import logger
from library import civitai
from library import download
from library import sd_webui
from library import utilities
from library.settings import Settings
from library.utilities import Filename

# Logger
LOGGER = logger.configure()

# Model Cache
MODEL_CACHE: dict[str, 'Model'] = {}

def clear_cache():
	''' Clear the model cache '''
	MODEL_CACHE.clear()
	LOGGER.debug('Cleared Model Cache')

def load_scans() -> dict[str, Any]:
	''' Load dictionary of model scans from storage '''
	return utilities.load_json(paths.SCANNED_FILE, {})

def save_scans(scans: dict[str, Any]):
	''' Save dictionary of model scans to storage '''
	utilities.store_json(paths.SCANNED_FILE, scans)

def refresh_markdown():
	''' Refresh markdown files for all installed models '''

	for type in civitai.Model.Type:
		for filename in sd_webui.model.filenames(type):
			Model.get(type, filename).generate_markdown()
	LOGGER.info('Refreshed all markdown files')

def purge_scans():
	''' Purge stored scans from models that are no longer installed '''

	# Get scans
	scans = load_scans()

	# Get installed models
	installed = []
	for type in civitai.Model.Type:
		for filename in sd_webui.model.filenames(type):
			installed.append(f'{type.name}/{filename.full}')

	# Get non installed models
	non_installed = []
	for key in scans:
		if key not in installed:
			non_installed.append(key)

	# Remove scans of non installed models
	for key in non_installed:
		del scans[key]
		LOGGER.info(f'Removed scan of non installed model [{key}]')

	# Save updated scans
	if len(non_installed) > 0:
		save_scans(scans)

class Model:
	''' An installed model in local storage '''

	def __init__(self, type: civitai.Model.Type, filename: Filename):
		self.model_id: int | None = None
		self.hash: str | None = None
		self.filename = filename
		self.type = type
		self.load_scan()

	def __hash__(self):
		return hash(self.hash)

	def __eq__(self, other: Any):
		if isinstance(other, Model):
			return self.type == other.type and self.filename == other.filename
		return False

	def refresh_cache(self):
		''' Refresh the model cache '''
		MODEL_CACHE[self.key] = self

	def remove_cache(self):
		''' Remove the model from the cache '''

		if self.key in MODEL_CACHE:
			del MODEL_CACHE[self.key]

	@staticmethod
	def get(type: civitai.Model.Type, filename: Filename):
		''' Get a model from cache or instantiate a new one '''

		# Generate model key
		key = f'{type.name}/{filename.full}'

		# Get model from cache
		if key in MODEL_CACHE:
			return MODEL_CACHE[key]

		# Instantiate new model
		model = Model(type, filename)
		MODEL_CACHE[key] = model
		return model

	@classmethod
	def by_type(cls, type: civitai.Model.Type) -> list['Model']:
		''' List installed models of the given type '''

		filenames = sd_webui.model.filenames(type)
		return [cls.get(type, filename) for filename in filenames]

	@classmethod
	def all(cls):
		''' List all installed models '''
		return [model for type in civitai.Model.Type for model in cls.by_type(type)]

	@property
	def key(self):
		''' Scan key for the model '''
		return f'{self.type.name}/{self.filename.full}'

	@property
	def image_key(self):
		''' Base image key for the model '''
		return f'{self.type.name}_{self.filename.name}'

	@property
	def name(self):
		''' Name of the model '''
		return self.filename.name

	@property
	def autov2(self):
		''' AutoV2 hash of the model '''
		return self.hash[:10] if self.hash is not None else ''

	@property
	def size_hr(self):
		''' Human readable size of the model '''
		return sd_webui.model.size_hr(self.type, self.filename)

	@property
	def in_civitai(self):
		''' Whether the model is in Civitai '''
		return self.model_id is not None

	@property
	def type_mismatch(self):
		''' Whether the installed model type is different from the Civitai model type '''
		return self.type != self.civitai_model.type if self.in_civitai else False

	@property
	def file(self):
		''' Path to the installed model file '''
		return cast(Path, sd_webui.model.file(self.type, self.filename))

	@property
	def json_file(self):
		''' Path to the Civitai model JSON file '''
		return paths.DATABASE_DIR / f'{self.model_id}.json'

	@property
	def preview_file(self):
		''' Path to the preview image file '''
		return paths.default_directory(self.type.name) / f'{self.name}.preview.png'

	@property
	def markdown_file(self):
		''' Path to the markdown information file '''
		return paths.default_directory(self.type.name) / f'{self.name}.md'

	@property
	def image_files(self) -> list[Path]:
		''' Paths to the Civitai model image files '''

		if not self.in_civitai:
			return []
		filename = Filename(self.image_key + '.png')
		image_count = len(self.civitai_version.images)
		return [paths.IMAGES_DIR / filename.with_index(i).full for i in range(image_count)]

	@property
	def missing_images(self) -> list[Path]:
		''' Paths to missing Civitai model image files '''
		return [file for file in self.image_files if not file.exists()]

	@property
	def vae_symlink_file(self):
		''' Path to the VAE symlink file if the related VAE model is installed '''

		# Get VAE model
		vae_model = self.vae_model

		# Generate the symlink filename
		if vae_model is None:
			filename = f'{self.filename.name}.vae.null'
		else:
			filename = f'{self.filename.name}.vae{vae_model.file.suffix}'

		# Return the symlink file path
		return paths.default_directory(self.type.name) / filename

	@property
	def all_images(self):
		''' Paths to all model images '''

		images = [file for file in paths.IMAGES_DIR.glob(f'{self.image_key}.*')]
		images.sort(key= lambda file: cast(int, Filename(file.name).get_index()))
		return images

	@property
	def all_safe_images(self):
		''' Paths to all model images that not marked as NSFW '''

		# Return all images if NSFW images are not hidden
		if not Settings.hide_nsfw_images():
			return self.all_images

		# Return only safe images
		safe_images: list[Path] = []
		for image in self.all_images:
			index = cast(int, Filename(image).get_index())
			if index < 1000 and self.has_scan:
				civitai_image = self.civitai_version.images[index]
				if not civitai_image.is_safe:
					continue
			safe_images.append(image)

		return safe_images

	@property
	def downloaded_images(self):
		''' Paths to the Civitai model image files that are downloaded '''
		return [image for image in self.image_files if image.exists()]

	@property
	def preview_index(self):
		''' Index of the current preview image '''

		if not self.has_preview:
			return None
		for image in self.all_images:
			if image.samefile(self.preview_file):
				return Filename(image.name).get_index()
		return None

	@property
	def civitai_model(self) -> civitai.Model:
		''' Get Civitai model '''

		if self.has_json:
			return civitai.Model.load_raw_json(self.json_file)
		raise ValueError(f'Model "{self.filename.full}" is not in Civitai')

	@property
	def civitai_version(self) -> civitai.Version:
		''' Get Civitai model version '''

		for version in self.civitai_model.versions:
			for file in version.files:
				if file.hash == self.hash:
					return version
		raise ValueError(f'Could not find Civitai model version for "{self.filename.full}"')

	@property
	def civitai_file(self) -> civitai.File:
		''' Get Civitai model file '''

		for file in self.civitai_version.files:
			if file.hash == self.hash:
				return file
		raise ValueError(f'Could not find Civitai model file for "{self.filename.full}"')

	@property
	def civitai_vae_file(self):
		''' Returns the Civitai VAE file if the version includes one '''
		return self.civitai_version.vae_file if self.in_civitai else None

	@property
	def vae_missing(self):
		''' Whether the Civitai model version includes a VAE file but it is not installed '''
		return self.civitai_vae_file is not None and self.vae_model is None

	@property
	def has_scan(self):
		''' Whether the model has a stored scan '''
		return self.key in load_scans()

	@property
	def has_json(self):
		''' Whether the model has an existing Civitai JSON file '''
		return self.in_civitai and self.json_file.exists()

	@property
	def has_preview(self):
		''' Whether the model has an existing preview image file '''
		return self.preview_file.exists()

	@property
	def has_markdown(self):
		''' Whether the model has an existing markdown information file '''
		return self.markdown_file.exists()

	@property
	def has_vae_symlink(self):
		''' Whether the model has an existing VAE symlink file '''
		return self.vae_symlink_file.exists()

	@property
	def has_nsfw_preview(self):
		''' Whether the model has an existing NSFW preview image file '''

		if not self.has_preview:
			return False
		return not utilities.path_in_list(self.preview_file, self.all_safe_images)

	@property
	def has_missing_preview(self):
		''' Whether the model can have a preview image but it is missing '''
		return not self.has_preview and len(self.all_safe_images) > 0

	@property
	def is_primary(self):
		''' Whether the Civitai file is marked as primary '''
		return self.civitai_file.primary if self.in_civitai else True

	@property
	def is_vae(self):
		''' Whether the Civitai file is marked as an optional VAE file '''
		return self.civitai_file.is_vae if self.in_civitai else self.type == civitai.Model.Type.VAE

	@property
	def is_latest(self):
		''' Whether the installed model belongs to its latest Civitai version '''

		if not self.in_civitai:
			return True
		return self.civitai_version.id == self.civitai_model.versions[0].id

	@property
	def is_updatable(self):
		''' Whether the installed has a newer version in Civitai '''

		if not self.in_civitai:
			return False
		return not any([model.is_latest and not model.is_vae for model in self.installed_by_model])

	@property
	def installed_by_model(self) -> list['Model']:
		''' List of installed models belonging to the same Civitai model '''

		if not self.in_civitai:
			return []
		model_hashes: list[str] = []

		# Finds the hashes of all files belonging to the Civitai model
		for version in self.civitai_model.versions:
			for file in version.files:
				model_hashes.append(file.hash)

		# Keeps only the installed models with matching hashes
		return [model for model in self.all() if model.hash in model_hashes]

	@property
	def installed_by_version(self) -> list['Model']:
		''' List of installed models belonging to the same Civitai model version '''

		if not self.in_civitai:
			return []
		version_hashes: list[str] = []

		# Finds the hashes of all files belonging to the Civitai model version
		for file in self.civitai_version.files:
			version_hashes.append(file.hash)

		# Keeps only the installed models with matching hashes
		return [model for model in self.all() if model.hash in version_hashes]

	@property
	def tags(self):
		''' Tags of the installed model '''

		if not self.in_civitai:
			return []
		return cast(list[str], self.civitai_model.tags)

	@property
	def trigger_words(self):
		''' Trigger words of the installed model '''

		if self.type == civitai.Model.Type.EMBEDDING:
			return [self.name]
		return self.civitai_version.trainedWords if self.in_civitai else []

	@property
	def vae_model(self):
		''' Get included Civitai VAE model if it is installed '''

		# Skip if the Civitai version does not include a VAE
		vae_file = self.civitai_vae_file
		if vae_file is None: return None

		# Search for installed model with matching hash
		for model in self.installed_by_version:
			if model.hash == vae_file.hash:
				return model
		return None

	@property
	def included_by(self) -> list['Model']:
		''' List of installed models that include this model as an optional VAE '''

		# Skip if model is not a VAE
		if self.type != civitai.Model.Type.VAE:
			return []

		# Search for installed models with matching VAE hash
		models: list[Model] = []
		for model in self.all():
			vae_file = model.civitai_vae_file
			if vae_file is not None and vae_file.hash == self.hash:
				models.append(model)
		return models

	def scan(self, update= False):
		''' Performs a full scan of the model for information or missing JSON file '''

		LOGGER.info(f'Scanning model {self.name}...')

		# Scan local Civitai database
		if not self.has_scan:
			self.scan_database()

		# Scan Civitai repository, trigger if JSON file is missing
		if not self.has_scan or (self.in_civitai and not self.has_json) or update:
			self.scan_civitai()

		# Assert VAE file matches model type
		self.assert_vae_type()

		# Regenerate markdown for related models
		self.regenerate_related()

	def scan_database(self):
		''' Scan local Civitai database for model information '''

		# Get model hash if not set
		if self.hash is None:
			self.hash = sd_webui.model.hash(self.type, self.filename)

		# Try to find matching file hash
		for json_file in list(paths.DATABASE_DIR.glob('*.json')):
			model = civitai.Model.load_raw_json(json_file)
			for version in model.versions:
				for file in version.files:

					# The scan is saved only if the hash matches
					if file.hash == self.hash:
						self.model_id = model.id
						self.save_scan()
						return

	def scan_civitai(self):
		''' Scan Civitai API for model information '''

		# Get model hash if not set
		if self.hash is None:
			self.hash = sd_webui.model.hash(self.type, self.filename)

		# Request model version if model ID is not set
		if self.model_id is None:
			civitai_version = civitai.Version.request_by_hash(self.hash)
			if civitai_version is None: self.save_scan(); return

			# Set model ID and save scan
			self.model_id = civitai_version.modelId
			self.save_scan()

		# Request model
		civitai_model = civitai.Model.request(self.model_id)
		if civitai_model is None: return

		# Store Civitai database file
		civitai_model.store_raw_json(self.json_file)

	def load_scan(self):
		''' Load model scan from storage '''

		try:
			# Only set model ID and hash if its scan exists
			model = load_scans()[self.key]
			self.model_id = model['model_id']
			self.hash = model['hash']
		except:
			self.model_id = None
			self.hash = None

	def save_scan(self):
		''' Save model scan to storage '''

		scans = load_scans()

		# Get model hash
		if self.hash is None:
			self.hash = sd_webui.model.hash(self.type, self.filename)

		# Set model ID and hash
		scans[self.key] = \
		{
			'model_id': self.model_id,
			'hash': self.hash
		}

		# Save updated scans and refresh cache
		save_scans(scans)
		self.refresh_cache()

	def assert_vae_type(self):
		''' Remove Civitai model ID for VAE models if there is a type mismatch '''

		if self.in_civitai and self.is_vae and self.type != self.civitai_model.type:
			LOGGER.warning(f'Model "{self.filename.full}" has a type mismatch with Civitai')
			self.model_id = None
			self.save_scan()

	def link_vae(self):
		''' Create a symlink to the required VAE file if it exists '''

		# Skip if related VAE model is not installed
		vae_model = self.vae_model
		if vae_model is None: return

		# Get VAE symlink file
		vae_symlink = self.vae_symlink_file

		# Remove existing VAE symlink
		if vae_symlink.exists() or vae_symlink.is_symlink():
			vae_symlink.unlink()

		# Create symlink to VAE file
		vae_symlink.symlink_to(vae_model.file)

		# Refresh filenames
		sd_webui.model.reload_filenames(self.type)
		sd_webui.model.reload_filenames(civitai.Model.Type.VAE)
		LOGGER.info(f'Linked VAE model "{vae_model.name}" to "{self.name}"')

	def set_preview(self, image: Path):
		''' Set a preview image for the model '''

		# Remove existing preview
		if self.has_preview or self.preview_file.is_symlink():
			self.preview_file.unlink()

		# Create symlink to image
		self.preview_file.symlink_to(image)
		LOGGER.info(f'Set preview for model "{self.filename.full}"')

	def image_by_index(self, index: Optional[int]= None):
		'''
			Retrieve a model image by its index
			- If index is None, the first available image is returned
			- If there are no images or the index is not found, None is returned
		'''

		for image in self.all_safe_images:
			if index is None or index == Filename(image).get_index():
				return image
		return None

	def select_preview(self, index: Optional[int]= None):
		''' Select an image to use as a preview for the model '''

		image = self.image_by_index(index)
		if image is not None: self.set_preview(image)

	def add_custom_image(self, image_path: Path, replace_preview= False):
		''' Add a custom image to the model '''

		# Custom images have an index of 1000 or higher
		index = 1000
		for image in self.all_images:
			image_index = cast(int, Filename(image).get_index())
			if image_index < 1000:
				continue
			if index == image_index:
				index += 1
			else:
				break

		# Copy image to images directory
		filename = Filename(self.image_key + image_path.suffix).with_index(index)
		image_file = paths.IMAGES_DIR / filename.full
		png_image_file = image_file.with_suffix('.png')
		shutil.copy(image_path, image_file)

		# Convert image to PNG
		utilities.image_to_png(paths.IMAGES_DIR, filename)

		# Set image as preview if there is no preview
		if not self.has_preview or replace_preview:
			self.set_preview(png_image_file)

		LOGGER.info(f'Added custom image "{png_image_file.name}"')

	def remove_image(self, index: int):
		''' Remove a model image by its index '''

		image = self.image_by_index(index)
		if image is not None:
			if self.has_preview and image.samefile(self.preview_file):
				self.preview_file.unlink()
				image.unlink()
				self.select_preview()
			else:
				image.unlink()

	def image_file_entities(self):
		''' Get all missing Civitai model images as entities for the download manager '''

		files = []
		for image in self.missing_images:

			# Get corresponding Civitai image
			image_filename = Filename(image)
			index = cast(int, image_filename.get_index())
			civitai_image = self.civitai_version.images[index]

			# Generate file entity
			files.append(download.File(civitai_image.custom_url, self.type, image_filename))
		return files

	def vae_file_entity(self):
		''' Get the missing Civitai VAE model file as an entity for the download manager '''

		# Skip if model is not missing its VAE
		if not self.vae_missing:
			return None

		# Get VAE file and convert to entity
		file = cast(civitai.File, self.civitai_vae_file)
		return download.File.from_civitai_file(civitai.Model.Type.VAE, file)

	def latest_file_entity(self):
		''' Get the latest Civitai version file as an entity for the download manager '''

		# Skip if model is up to date
		if not self.is_updatable:
			return None

		# Get latest version and convert to entity
		latest_version = self.civitai_model.latest_version
		file = cast(civitai.File, latest_version.primary_file)
		return download.File.from_civitai_file(self.type, file)

	@staticmethod
	def handle_download(type: civitai.Model.Type, filename: Filename, images: list[Path]= []):
		''' Download Civitai model file to a directory '''

		# Reload filenames and scan the downloaded model
		sd_webui.model.reload_filenames(type)
		model = Model.get(type, filename)
		model.scan()

		# Assert the image filenames match the model name
		for image in images:
			index = Filename(image).get_index()
			image_filename = Filename(model.image_key + image.suffix)
			image.rename(image.parent / image_filename.with_index(index).full)

		# Set preview image to the first available image
		model.select_preview()

		# Return model
		return model

	def regenerate_related(self, include_self= True):
		''' Regenerate markdown for models related to this model '''

		# Regenerate markdown and link VAE for self
		if include_self:
			self.generate_markdown()
			self.link_vae()

		# Regenerate markdown for all installed models belonging to the Civitai parent model
		for model in self.installed_by_model:
			if self == model: continue
			model.generate_markdown()

		# Regenerate markdown and link VAE for models that include this model
		for model in self.included_by:
			model.generate_markdown()
			model.link_vae()

	def reset_name(self):
		''' Reset the installed model name to the default Civitai filename '''

		if not self.in_civitai: return
		self.rename(Filename(self.civitai_file.name).name)

	def rename(self, new_name: str):
		''' Rename installed model '''

		# Filter out invalid names
		if new_name == '':
			LOGGER.warning('The new model name cannot be empty'); return
		if new_name == self.name:
			LOGGER.warning('The new model name is the same as the current name'); return
		if new_name in sd_webui.model.names(self.type):
			LOGGER.warning(f'The new model name "{new_name}" already exists'); return
		if self.filename.with_name(new_name).name != new_name:
			LOGGER.warning('The new model name cannot contain a prefix or extension'); return

		# Generate new filename
		new_filename = self.filename.with_name(new_name)
		LOGGER.info(f'Renaming model "{self.filename.full}" to "{new_filename.full}"')

		# Rename model
		self.rename_file(new_filename)
		self.rename_scan(new_filename)
		self.rename_images(new_filename)
		self.rename_markdown(new_filename)
		self.rename_vae_symlink(new_filename)
		self.filename = new_filename

		# Regenerate markdown for models that include this model
		self.regenerate_related()

		# Refresh model cache
		self.refresh_cache()

	def rename_file(self, new_filename: Filename):
		''' Rename model file for the installed model '''

		self.file.rename(self.file.parent / new_filename.full)
		sd_webui.model.reload_filenames(self.type)
		LOGGER.debug(f'Renamed model file to "{new_filename.full}"')

	def rename_scan(self, new_filename: Filename):
		''' Rename scan information key for the installed model '''

		if self.has_scan:
			new_key = f'{self.type.name}/{new_filename.full}'
			scans = load_scans()
			scans[new_key] = scans.pop(self.key)
			save_scans(scans)
			LOGGER.debug(f'Renamed scan information key to "{new_key}"')

	def rename_images(self, new_filename: Filename):
		''' Rename all images for the installed model '''

		# Get current preview image index
		index = self.preview_index

		# Generate new image name
		new_name = f'{self.type.name}_{new_filename.name}'

		# Delete preview image if it exists
		if self.has_preview:
			self.preview_file.unlink()

		# Rename all model images
		for image in self.all_images:
			file = utilities.rename_file(image, new_name, indexed= True)
			LOGGER.debug(f'Renamed image file to "{file.name}"')

		# Set preview image to the renamed image
		if index is not None:
			model = Model(self.type, new_filename)
			model.select_preview(index)
			LOGGER.debug(f'Renamed preview image to "{model.preview_file.name}"')

	def rename_markdown(self, new_filename: Filename):
		''' Rename markdown file for the installed model '''

		if self.has_markdown:
			file = utilities.rename_file(self.markdown_file, new_filename.name)
			LOGGER.debug(f'Renamed markdown file to "{file.name}"')

	def rename_vae_symlink(self, new_filename: Filename):
		''' Rename VAE symlink for the installed model '''

		if self.has_vae_symlink:
			file = utilities.rename_file(self.vae_symlink_file, new_filename.name)
			LOGGER.debug(f'Renamed VAE symlink to "{file.name}"')

	def delete(self):
		''' Delete installed model '''

		# Unlink VAE from models that include this model
		for model in self.included_by:
			model.delete_vae_symlink()

		# Delete model files
		self.delete_model_file()
		self.delete_scan()
		self.delete_images()
		self.delete_markdown()
		self.delete_vae_symlink()

		# Regenerate markdown for models that include this model
		self.regenerate_related(False)

		# Remove model from cache
		self.remove_cache()

	def delete_model_file(self):
		''' Delete model file for the installed model '''

		self.file.unlink()
		LOGGER.debug(f'Deleted model file for "{self.filename.full}"')

		# Reload filenames
		sd_webui.model.reload_filenames(self.type)

	def delete_scan(self):
		''' Delete scan information for the installed model '''

		if self.has_scan:
			scans = load_scans()
			del scans[self.key]
			save_scans(scans)
			LOGGER.debug(f'Deleted scan information for "{self.filename.full}"')

	def delete_images(self):
		''' Delete image files for the installed model '''

		# Remove preview image
		if self.has_preview or self.preview_file.is_symlink():
			self.preview_file.unlink()
			LOGGER.debug(f'Deleted preview symlink "{self.preview_file.name}"')

		# Remove all non-preview images
		for image in self.all_images:
			image.unlink()
			LOGGER.debug(f'Deleted image file "{image.name}"')

	def delete_markdown(self):
		''' Delete markdown information file for the installed model '''

		if self.has_markdown:
			self.markdown_file.unlink()
			LOGGER.debug(f'Deleted markdown file "{self.markdown_file.name}"')

	def delete_vae_symlink(self):
		''' Remove the symlink to the required VAE file if it exists '''

		if self.has_vae_symlink or self.vae_symlink_file.is_symlink():
			self.vae_symlink_file.unlink()
			LOGGER.info(f'Removed VAE symlink "{self.vae_symlink_file.name}"')

	def generate_markdown(self):
		'''
			Generate markdown information for the installed model
			- Overwrites existing markdown file with current information
		'''

		self.markdown_file.write_text(self.build_markdown(), encoding= 'utf-8')
		LOGGER.info(f'Generated markdown file "{self.markdown_file.name}"')

	def build_versions_markdown(self):
		versions: list[str] = []

		# Get current version and installed version ids
		current_version = self.civitai_version
		installed_ids = [m.civitai_version.id for m in self.installed_by_model if m.in_civitai]

		# Iterate through versions
		for version in self.civitai_model.versions:

			# Only show installed versions if configured
			if not Settings.all_versions_in_md() and version.id not in installed_ids:
				continue

			# Get unicode symbols for installed and current versions
			installed = ui.save_style_symbol if version.id in installed_ids else ''
			current = ui.restore_progress_symbol if version.id == current_version.id else ''

			# Generate markdown row for version
			versions.append(f'- **{version.full_name}** {installed}{current}')

		# Join versions
		return '\n'.join([f'{version}' for version in versions])

	def build_markdown(self):
		if not self.in_civitai:

			# Get markdown template
			markdown = paths.LOCAL_MD_FILE.read_text(encoding= 'utf-8')

			# Fill model info
			markdown = markdown.replace('{NAME}', self.name)

			# Fill file info
			markdown = markdown.replace('{LOCAL_FILE}', self.file.name)
			markdown = markdown.replace('{AUTOV2}', self.autov2)
			markdown = markdown.replace('{SIZE}', self.size_hr)

		else:

			# Get markdown template
			markdown = paths.REMOTE_MD_FILE.read_text(encoding= 'utf-8')

			# Fill model info
			markdown = markdown.replace('{NAME}', self.civitai_model.name)
			markdown = markdown.replace('{URL}', self.civitai_version.url)

			# Fill tags
			markdown = markdown.replace('{TAGS}', ', '.join([f'`{tag}`' for tag in self.tags]))

			# Fill version info
			markdown = markdown.replace('{VERSIONS}', self.build_versions_markdown())

			# Fill file info
			markdown = markdown.replace('{LOCAL_FILE}', self.file.name)
			markdown = markdown.replace('{REMOTE_FILE}', self.civitai_file.name)
			markdown = markdown.replace('{AUTOV2}', self.civitai_file.autov2)
			markdown = markdown.replace('{TYPE}', self.civitai_file.type_hr)
			markdown = markdown.replace('{SIZE}', self.civitai_file.size_hr)

		# Generated fields
		vae_local_file = self.vae_model.file.name if self.vae_model is not None else '`NOT INSTALLED`'
		included_by_md = '\n'.join([f'- {model.filename.full}' for model in self.included_by])
		trigger_words_md = '\n'.join([f'- {word}' for word in self.trigger_words])

		# Fill VAE info
		if self.civitai_vae_file is not None:
			markdown += paths.VAE_MD_FILE.read_text(encoding= 'utf-8')
			markdown = markdown.replace('{VAE_LOCAL_FILE}', vae_local_file)
			markdown = markdown.replace('{VAE_REMOTE_FILE}', self.civitai_vae_file.name)
			markdown = markdown.replace('{VAE_AUTOV2}', self.civitai_vae_file.autov2)

		# Fill included by
		if included_by_md != '':
			markdown += paths.LIST_MD_FILE.read_text(encoding= 'utf-8')
			markdown = markdown.replace('{LIST_TITLE}', 'Included by')
			markdown = markdown.replace('{LIST_CONTENT}', included_by_md)

		# Fill trigger words
		if trigger_words_md != '':
			markdown += paths.LIST_MD_FILE.read_text(encoding= 'utf-8')
			markdown = markdown.replace('{LIST_TITLE}', 'Trigger words')
			markdown = markdown.replace('{LIST_CONTENT}', trigger_words_md)

		return markdown

	@staticmethod
	def table_header():
		''' Get table header '''
		return ['File', 'Version', 'AutoV2', 'Size', 'Status']

	def to_table_row(self):
		'''
			Convert model info to table row
			- The 'tags' field is included only for searching purposes
		'''

		file = self.file.name
		version = 'Local'
		autov2 = self.autov2
		size = self.size_hr
		status = 'Not Scanned'
		tags = ','.join(self.tags)

		# Version
		if self.in_civitai:
			version = self.civitai_version.full_name

		# Status
		if self.has_scan:
			status = 'Scanned'
		if self.in_civitai:
			status = 'Latest'
		if self.is_updatable:
			status = 'Outdated'
		elif not self.is_latest:
			status = 'Previous'
		if len(self.included_by) > 0:
			status += ' I'
		elif self.civitai_vae_file is not None:
			status += ' -V' if self.vae_missing else ' +V'

		# Return table row
		return [file, version, autov2, size, status, tags]