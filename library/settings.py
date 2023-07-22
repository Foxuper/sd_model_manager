import gradio as gr
from enum import Enum
from typing import Any

# SD Webui Modules
from modules import shared

# Extension Information
EXTENSION_NAME = 'Model Manager'
EXTENSION_ID   = 'sd_model_manager'

# Default Settings
DEFAULT_DEBUG_MODE          = False
DEFAULT_HIDE_NSFW_IMAGES    = True
DEFAULT_CREATE_VAE_SYMLINKS = True
DEFAULT_ALL_VERSIONS_IN_MD  = True
DEFAULT_IMAGE_WIDTH_LIMIT   = True
DEFAULT_AUTO_IMAGE_DOWNLOAD = True
DEFAULT_REQUEST_DELAY       = 1.0

class Settings(Enum):
	''' Global settings for the extension '''

	DEBUG_MODE          = f'{EXTENSION_ID}_debug_mode'
	HIDE_NSFW_MODELS    = f'{EXTENSION_ID}_hide_nsfw_models'
	HIDE_NSFW_IMAGES    = f'{EXTENSION_ID}_hide_nsfw_images'
	CREATE_VAE_SYMLINKS = f'{EXTENSION_ID}_create_vae_symlinks'
	ALL_VERSIONS_IN_MD  = f'{EXTENSION_ID}_all_versions_in_md'
	IMAGE_WIDTH_LIMIT   = f'{EXTENSION_ID}_image_width_limit'
	AUTO_IMAGE_DOWNLOAD = f'{EXTENSION_ID}_auto_image_download'
	REQUEST_DELAY       = f'{EXTENSION_ID}_request_delay'

	def get(self, default: Any) -> Any:
		''' Returns the value of the setting if it exists, otherwise the default value '''

		if hasattr(shared.opts, self.value):
			attribute = getattr(shared.opts, self.value)
			return attribute if attribute is not None else default
		return default

	@staticmethod
	def get_cmd(option: str, default: Any) -> Any:
		''' Returns the value of the command line option if it exists, otherwise the default value '''

		if hasattr(shared.cmd_opts, option):
			return getattr(shared.cmd_opts, option)
		return default

	@classmethod
	def debug_mode(cls) -> bool:
		return cls.DEBUG_MODE.get(DEFAULT_DEBUG_MODE)

	@classmethod
	def hide_nsfw_images(cls) -> bool:
		return cls.HIDE_NSFW_IMAGES.get(DEFAULT_HIDE_NSFW_IMAGES)

	@classmethod
	def create_vae_symlinks(cls) -> bool:
		return cls.CREATE_VAE_SYMLINKS.get(DEFAULT_CREATE_VAE_SYMLINKS)

	@classmethod
	def all_versions_in_md(cls) -> bool:
		return cls.ALL_VERSIONS_IN_MD.get(DEFAULT_ALL_VERSIONS_IN_MD)

	@classmethod
	def image_width_limit(cls) -> bool:
		return cls.IMAGE_WIDTH_LIMIT.get(DEFAULT_IMAGE_WIDTH_LIMIT)

	@classmethod
	def auto_image_download(cls) -> bool:
		return cls.AUTO_IMAGE_DOWNLOAD.get(DEFAULT_AUTO_IMAGE_DOWNLOAD)

	@classmethod
	def request_delay(cls) -> float:
		return cls.REQUEST_DELAY.get(DEFAULT_REQUEST_DELAY)

def on_ui_settings():
	section = (EXTENSION_ID, EXTENSION_NAME)

	shared.opts.add_option(Settings.DEBUG_MODE.value, shared.OptionInfo(DEFAULT_DEBUG_MODE,
			'Enable debug messages and log file (requires UI reload)',
			gr.Checkbox, section= section))

	shared.opts.add_option(Settings.HIDE_NSFW_IMAGES.value, shared.OptionInfo(DEFAULT_HIDE_NSFW_IMAGES,
			'Hide NSFW model images (does not disable NSFW image generation)',
			gr.Checkbox, section= section))

	shared.opts.add_option(Settings.CREATE_VAE_SYMLINKS.value, shared.OptionInfo(DEFAULT_CREATE_VAE_SYMLINKS,
			'Create VAE symlinks for models with VAEs',
			gr.Checkbox, section= section))

	shared.opts.add_option(Settings.ALL_VERSIONS_IN_MD.value, shared.OptionInfo(DEFAULT_ALL_VERSIONS_IN_MD,
			'Include all model versions in markdown info',
		    gr.Checkbox, section= section))

	shared.opts.add_option(Settings.IMAGE_WIDTH_LIMIT.value, shared.OptionInfo(DEFAULT_IMAGE_WIDTH_LIMIT,
			'When downloading images, use default width limit (450px)',
			gr.Checkbox, section= section))

	shared.opts.add_option(Settings.AUTO_IMAGE_DOWNLOAD.value, shared.OptionInfo(DEFAULT_AUTO_IMAGE_DOWNLOAD,
			'Automatically download included images when downloading models (Except for missing VAEs)',
			gr.Checkbox, section= section))

	shared.opts.add_option(Settings.REQUEST_DELAY.value, shared.OptionInfo(DEFAULT_REQUEST_DELAY,
			'Civitai API request delay (seconds)',
			gr.Slider, {'maximum': 10, 'step': 0.1}, section= section))