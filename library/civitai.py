import re
import time
import requests
from enum import Enum
from pathlib import Path
from pydantic import BaseModel
from typing import Optional, Any

# Extension Library
from library import logger
from library import utilities
from library.settings import Settings
from library.utilities import Filename

# Logger
LOGGER = logger.configure()

# Model dictionary of json data
MODEL_JSON_DATA: dict[int, dict] = {}

class Api(Enum):
	''' Civitai API endpoints'''

	# Web
	WEB_MODELS = 'https://civitai.com/models'

	# API
	GET_MODEL_BY_ID     = 'https://civitai.com/api/v1/models'
	GET_VERSION_BY_ID   = 'https://civitai.com/api/v1/model-versions'
	GET_VERSION_BY_HASH = 'https://civitai.com/api/v1/model-versions/by-hash'

	def with_value(self, value: str | int):
		''' Returns the endpoint with the given value appended '''
		return f'{self.value}/{value}'

	def request(self, value: str | int):
		''' Sends a request to the endpoint with the given value appended '''

		request = requests.get(self.with_value(value))
		return self.handle_response(request)

	@classmethod
	def handle_response(cls, response: requests.Response):
		''' Handles a json response from the Civitai API '''

		LOGGER.debug(f'Handling response [{response.status_code}]')
		json: dict[str, Any] | None = None

		if response.ok:
			try:
				json = response.json()
			except Exception as e:
				LOGGER.error('Failed to parse json response')
				LOGGER.error(e)
		else:
			if response.status_code == 404:
				LOGGER.debug('Requested resource not found')
			else:
				LOGGER.error(f'Request failed [{response.status_code}]')
				LOGGER.error(response.text)

		LOGGER.debug(f'Waiting {Settings.request_delay()} seconds to avoid rate limiting')
		time.sleep(Settings.request_delay())
		return json

class Image(BaseModel):
	''' Civitai model image retrieved from the API '''

	class Nsfw(Enum):
		NONE   = 'None'
		SOFT   = 'Soft'
		MATURE = 'Mature'
		X      = 'X'

	# Image properties
	url: str
	nsfw: Nsfw
	hash: str

	@property
	def is_safe(self):
		''' Wether the image is safe to view '''
		return self.nsfw == Image.Nsfw.NONE

	@property
	def raw_url(self):
		''' The raw url of the image (without width limit) '''
		return re.sub(r'\/width=\d+', '', self.url)

	def download(self, directory: Path, filename: Filename):
		''' Downloads the image to the specified path '''
		return utilities.download_file(self.raw_url, directory, filename)

class File(BaseModel):
	''' Civitai model file retrieved from the API '''

	class Type(Enum):
		MODEL         = 'Model'
		VAE           = 'VAE'
		CONFIG        = 'Config'
		NEGATIVE      = 'Negative'
		PRUNED_MODEL  = 'Pruned Model'
		TRAINING_DATA = 'Training Data'

	class Metadata(BaseModel):
		class Fp(Enum):
			FP16 = 'fp16'
			FP32 = 'fp32'

		class Size(Enum):
			FULL   = 'full'
			PRUNED = 'pruned'

		class Format(Enum):
			SAFETENSOR   = 'SafeTensor'
			PICKLETENSOR = 'PickleTensor'
			OTHER        = 'Other'

		fp:     Fp     | None
		size:   Size   | None
		format: Format | None

	class Hashes(BaseModel):
		AutoV1: str = ''
		AutoV2: str = ''
		SHA256: str = ''
		CRC32:  str = ''
		BLAKE3: str = ''

	# File properties
	name:        str
	id:          int
	sizeKB:      float
	type:        Type
	metadata:    Metadata
	hashes:      Hashes
	downloadUrl: str
	primary:     bool = False

	@property
	def full_name(self):
		''' Full name of the file '''
		return f'{self.name} [{self.id}]'

	@property
	def hash(self):
		''' Hash of the file (SHA256) '''
		return self.hashes.SHA256

	@property
	def autov2(self):
		''' AutoV2 hash of the file '''
		return self.hashes.AutoV2

	@property
	def size_hr(self):
		''' Size of the file in human readable format '''
		return utilities.format_size_hr(self.sizeKB)

	@property
	def is_vae(self):
		''' Wether the file is a VAE and also not primary '''
		return self.type == self.Type.VAE and not self.primary

	@property
	def type_hr(self):
		''' File type in human readable format '''

		fields = []
		if self.metadata.size   is not None: fields.append(self.metadata.size.name.capitalize())
		if self.metadata.fp     is not None: fields.append(self.metadata.fp.value)
		if self.metadata.format is not None: fields.append(self.metadata.format.value)
		return ' '.join(fields)

	def download(self, directory: Path, filename: Optional[Filename]= None):
		''' Downloads the file to the specified path '''

		if filename is None: filename = Filename(self.name)
		return utilities.download_file(self.downloadUrl, directory, filename)

class Version(BaseModel):
	''' Civitai model version retrieved from the API '''

	id:           int
	modelId:      int
	name:         str
	trainedWords: list[str]
	model:        Optional['Model'] = None
	files:        list[File]
	images:       list[Image]

	@property
	def full_name(self):
		''' Full name of the model version '''
		return f'{self.name} [{self.id}]'

	@property
	def url(self):
		''' URL to the model version on Civitai '''
		return f'{Api.WEB_MODELS.with_value(self.modelId)}?modelVersionId={self.id}'

	@property
	def primary_file(self):
		''' The primary file of the model version '''
		return next((file for file in self.files if file.primary), None)

	@property
	def vae_file(self):
		''' The optional VAE file of the model version '''
		return next((file for file in self.files if file.is_vae), None)

	@classmethod
	def request(cls, id: str | int):
		''' Requests a model version from Civitai by its ID '''

		LOGGER.debug(f'Requesting model version info from Civitai by id [{id}]')
		json = Api.GET_VERSION_BY_ID.request(id)
		if json is None: return None
		return cls(**json)

	@classmethod
	def request_by_hash(cls, hash: str):
		''' Requests a model version from Civitai by its hash '''

		LOGGER.debug(f'Requesting model version info from Civitai by hash [{hash[:10]}]')
		json = Api.GET_VERSION_BY_HASH.request(hash)
		if json is None: return None
		return cls(**json)

	def download_primary_file(self, directory: Path, filename: Optional[Filename]= None):
		''' Downloads the primary file of the model version to the specified path '''

		if self.primary_file is None:
			LOGGER.error(f'Model version [{self.id}] has no primary file')
			return

		LOGGER.debug(f'Downloading primary file of model version [{self.id}]')
		return self.primary_file.download(directory, filename)

	def download_vae_file(self, directory: Path, filename: Optional[Filename]= None):
		''' Downloads the VAE file of the model version to the specified path '''

		if self.vae_file is None:
			LOGGER.error(f'Model version [{self.id}] has no VAE file')
			return

		LOGGER.debug(f'Downloading VAE file of model version [{self.id}]')
		return self.vae_file.download(directory, filename)

class Model(BaseModel):
	''' Civitai model retrieved from the API '''

	class Type(Enum):
		CHECKPOINT   = 'Checkpoint'
		EMBEDDING    = 'TextualInversion'
		HYPERNETWORK = 'Hypernetwork'
		LORA         = 'LORA'
		LYCORIS      = 'LoCon'
		VAE          = 'VAE'

		@property
		def name_hr(self):
			''' Human readable model type '''
			if self == self.CHECKPOINT:   return 'Checkpoint'
			if self == self.EMBEDDING:    return 'Embedding'
			if self == self.HYPERNETWORK: return 'Hypernetwork'
			if self == self.LORA:         return 'LoRA'
			if self == self.LYCORIS:      return 'LyCORIS'
			if self == self.VAE:          return 'VAE'
			raise NotImplementedError(f'Unknown model type [{self.value}]')

	# Model properties
	id:            Optional[int] = None
	name:          str
	type:          Type
	nsfw:          bool
	tags:          Optional[list[str]] = None
	modelVersions: Optional[list[Version]] = None

	@property
	def versions(self):
		''' List of model versions '''
		return self.modelVersions if self.modelVersions is not None else []

	@property
	def latest_version(self):
		''' The latest model version '''
		return self.versions[0]

	def __init__(self, **data):
		super().__init__(**data)

		# Store raw json response
		if self.id is not None:
			MODEL_JSON_DATA[self.id] = data

	def store_raw_json(self, file_path: Path):
		''' Stores the raw json response to the specified path '''

		if self.id is not None:
			return utilities.store_json(file_path, MODEL_JSON_DATA[self.id])

	@staticmethod
	def load_raw_json(file_path: Path):
		''' Loads a model from the raw json response stored at the specified path '''
		return Model(**utilities.load_json(file_path))

	@classmethod
	def request(cls, id: str | int):
		''' Requests a model from Civitai by its ID '''

		LOGGER.debug(f'Requesting model info from Civitai by id [{id}]')
		json = Api.GET_MODEL_BY_ID.request(id)
		if json is None: return None
		return cls(**json)

	@classmethod
	def request_by_url(cls, url: str):
		''' Requests a model from Civitai by its URL '''

		LOGGER.debug(f'Requesting model info from Civitai by url [{url}]')

		# Parse model ID from URL
		search = re.search(rf'\/models\/(\d+)', url)
		if search is None:
			LOGGER.error(f'Failed to parse model ID from url [{url}]')
			return None

		# Request model by ID
		return cls.request(search.group(1))

	@classmethod
	def request_by_mixed(cls, url_or_id: str):
		''' Requests a model from Civitai by its ID or URL '''

		if url_or_id.isdigit():
			return cls.request(url_or_id)
		else:
			return cls.request_by_url(url_or_id)

# Update forward references
Version.update_forward_refs()