import sys
import importlib
import importlib.util
from enum import Enum
from typing import Optional, Any, cast

# SD Webui Modules
from modules import shared, sd_models, sd_hijack, sd_vae
from modules.textual_inversion.textual_inversion import Embedding

# Extension Library
from library import paths
from library import logger
from library import civitai
from library import utilities
from library.utilities import Filename

# Logger
LOGGER = logger.configure()

# Extensions
BUILTIN_LORA_EXTENSION: Optional['extension.lora_builtin'] = None
LYCORIS_EXTENSION:      Optional['extension.lycoris']      = None

class extension:
	''' Interface for the SD web UI extensions '''

	class lora_builtin:
		''' Interface for the built-in Lora extension '''

		@staticmethod
		def import_extension():
			global BUILTIN_LORA_EXTENSION
			try:
				sys.path.append(str(paths.ROOT_DIR / 'extensions-builtin' / 'Lora'))
				builtin_lora_extension = importlib.import_module('extensions-builtin.Lora.lora')
				BUILTIN_LORA_EXTENSION = cast(extension.lora_builtin, builtin_lora_extension)
				LOGGER.debug('Built-in Lora extension found')
				return BUILTIN_LORA_EXTENSION
			except Exception as e:
				LOGGER.warning('Built-in Lora extension not found')
				LOGGER.warning(e)
				return None

		class SdVersion(Enum):
			Unknown = 1
			SD1 = 2
			SD2 = 3
			SDXL = 4

		class NetworkOnDisk:
			name: str
			filename: str
			metadata: dict
			is_safetensors: bool
			alias: str
			hash: str
			shorthash: str
			sd_version: 'extension.lora_builtin.SdVersion'

			def detect_version(self) -> 'extension.lora_builtin.SdVersion': ...
			def set_hash(self, v): ...
			def read_hash(self): ...
			def get_alias(self) -> str: ...

		available_loras: dict[str, NetworkOnDisk]

		@staticmethod
		def list_available_loras(): ...

	class lycoris:
		''' Interface for the LyCORIS extension '''

		@staticmethod
		def import_extension():
			global LYCORIS_EXTENSION
			try:
				lycoris_extension = importlib.import_module('extensions.a1111-sd-webui-lycoris.lycoris')
				LYCORIS_EXTENSION = cast(extension.lycoris, lycoris_extension)
				LOGGER.debug('LyCORIS extension found')
				return LYCORIS_EXTENSION
			except:
				LOGGER.warning('LyCORIS extension not found')
				return None

		class LycoOnDisk:
			name: str
			filename: str
			metadata: dict
			ssmd_cover_images: Any

			def __init__(self, name, filename): ...

		available_lycos: dict[str, LycoOnDisk]

		@staticmethod
		def list_available_lycos(): ...

class model:
	''' Interface for the SD web UI models '''

	class directory:
		''' Interface for the SD web UI model directories '''

		@staticmethod
		def create_default():
			''' Create all default model directories if they do not exist '''

			for type in civitai.Model.Type:
				paths.default_directory(type.name).mkdir(parents= True, exist_ok= True)

		@staticmethod
		def list(type: civitai.Model.Type):
			''' List the directories of the given model type '''

			default_directory = paths.default_directory(type.name)
			custom_directory = paths.custom_directory(type.name)
			return utilities.get_directories([default_directory, custom_directory])

	@staticmethod
	def reload_filenames(type: civitai.Model.Type):
		''' Reload the list of filenames for the given model type '''

		if type == civitai.Model.Type.CHECKPOINT:
			sd_models.list_models()
			LOGGER.debug(f'Checkpoint filenames reloaded')

		elif type == civitai.Model.Type.EMBEDDING:
			sd_hijack.model_hijack.embedding_db.load_textual_inversion_embeddings()
			LOGGER.debug(f'Embedding filenames reloaded')

		elif type == civitai.Model.Type.HYPERNETWORK:
			shared.reload_hypernetworks()
			LOGGER.debug(f'Hypernetwork filenames reloaded')

		elif type == civitai.Model.Type.LORA:
			if BUILTIN_LORA_EXTENSION is not None:
				BUILTIN_LORA_EXTENSION.list_available_loras()
				LOGGER.debug(f'Lora filenames reloaded')

		elif type == civitai.Model.Type.LYCORIS:
			if LYCORIS_EXTENSION is not None:
				LYCORIS_EXTENSION.list_available_lycos()
				LOGGER.debug(f'Lyco filenames reloaded')

		elif type == civitai.Model.Type.VAE:
			sd_vae.refresh_vae_list()
			LOGGER.debug(f'VAE filenames reloaded')

		else:
			LOGGER.error(f'Unknown model type: {type}')

	@staticmethod
	def reload_all_filenames():
		''' Reload the list of filenames for all model types '''

		for type in civitai.Model.Type:
			model.reload_filenames(type)

	@staticmethod
	def filenames(type: civitai.Model.Type) -> list[Filename]:
		''' List the installed model filenames for the given model type '''

		if type == civitai.Model.Type.CHECKPOINT:
			checkpoints: dict[str, sd_models.CheckpointInfo] = sd_models.checkpoints_list
			filenames = [Filename(value.name) for value in checkpoints.values()]

		elif type == civitai.Model.Type.EMBEDDING:
			embeddings: dict[str, Embedding] = sd_hijack.model_hijack.embedding_db.word_embeddings
			filenames = [Filename(cast(str, value.filename)) for value in embeddings.values()]

		elif type == civitai.Model.Type.HYPERNETWORK:
			hypernetworks: dict[str, str] = shared.hypernetworks
			filenames = [Filename(filename) for filename in hypernetworks.values()]

		elif type == civitai.Model.Type.LORA:
			if BUILTIN_LORA_EXTENSION is None: return []
			loras = BUILTIN_LORA_EXTENSION.available_loras
			filenames = [Filename(value.filename) for value in loras.values()]

		elif type == civitai.Model.Type.LYCORIS:
			if LYCORIS_EXTENSION is None: return []
			lycos = LYCORIS_EXTENSION.available_lycos
			filenames = [Filename(value.filename) for value in lycos.values()]

		elif type == civitai.Model.Type.VAE:
			vaes: dict[str, str] = sd_vae.vae_dict
			filenames = [Filename(filename) for filename in vaes.values()]
		else:
			raise ValueError(f'Unknown model type: {type}')

		# Remove non-existent files from the list
		return [filename for filename in filenames if model.file(type, filename) is not None]

	@staticmethod
	def names(type: civitai.Model.Type) -> list[str]:
		''' List the installed model names for the given model type '''

		filenames = model.filenames(type)
		return [filename.name for filename in filenames]

	@staticmethod
	def file(type: civitai.Model.Type, filename: Filename):
		''' Retrieves the file path of a model '''

		directories = model.directory.list(type)
		return utilities.find_file(directories, filename)

	@staticmethod
	def size_kb(type: civitai.Model.Type, filename: Filename):
		''' Retrieves the size in kilobytes of a model '''

		file = utilities.find_file(model.directory.list(type), filename)
		return file.stat().st_size / 1024 if file is not None else 0.0

	@staticmethod
	def size_hr(type: civitai.Model.Type, filename: Filename):
		''' Retrieves the size in human-readable format of a model '''

		size_kb = model.size_kb(type, filename)
		return utilities.format_size_hr(size_kb)

	@staticmethod
	def hash(type: civitai.Model.Type, filename: Filename):
		''' Gets the hash of a model '''

		file = utilities.find_file(model.directory.list(type), filename)
		return utilities.file_sha256(file) if file is not None else ''