import gradio as gr
import gradio.routes

# SD Webui Modules
from modules import script_callbacks

# Extension Library
from library import api
from library import local
from library import logger
from library import civitai
from library import sd_webui
from library import settings
from library import utilities

# Extension UI
from library.ui import home_menu
from library.ui import home_download
from library.ui import model_tab
from library.ui import download_manager
from library.ui import send_to_txt2img

# Logger
LOGGER = logger.configure()

# Import Extensions
BUILTIN_LORA_EXTENSION = sd_webui.extension.lora_builtin.import_extension()
LYCORIS_EXTENSION = sd_webui.extension.lycoris.import_extension()

def all_model_types():
	''' Returns all available model types '''

	types = [type for type in civitai.Model.Type]
	if BUILTIN_LORA_EXTENSION is None: types.remove(civitai.Model.Type.LORA)
	if LYCORIS_EXTENSION is None:      types.remove(civitai.Model.Type.LYCORIS)
	return types

# Tab Interface
def on_ui_tabs():
	with gr.Blocks(analytics_enabled= False) as ui_component:

		# Home tab
		with gr.Tab('Home'):
			with gr.Column():
				home_menu.component(all_model_types())
				home_download.component()

		# Model tabs
		for type in all_model_types():
			model_tab.component(type)

		# Download manager
		download_manager.component()
		send_to_txt2img.component()

	return [(ui_component, settings.EXTENSION_NAME, settings.EXTENSION_ID)]

# Initialize
def on_app_started(blocks: gr.Blocks, app: gradio.routes.App):
	sd_webui.model.directory.create_default()
	sd_webui.model.reload_all_filenames()
	utilities.clear_json_cache()
	local.clear_cache()
	local.purge_scans()
	api.initialize_api(app)

# Register extension settings
script_callbacks.on_ui_settings(settings.on_ui_settings)

# Register extension tab interface
script_callbacks.on_ui_tabs(on_ui_tabs)

# Register extension app started
script_callbacks.on_app_started(on_app_started)