import gradio as gr
from pathlib import Path
from typing	import Literal
from tempfile import _TemporaryFileWrapper

# SD Webui Modules
from modules import ui

# Extension Library
from library import local
from library import logger
from library import civitai
from library.ui import html
from library import sd_webui
from library import utilities
from library.utilities import Filename

# Logger
LOGGER = logger.configure()

class SearchBar:
	''' Search bar component for the model tab '''

	input:   gr.Textbox
	mode:    gr.Radio
	clear:   gr.Button
	refresh: gr.Button
	table:   gr.Dataframe

	def __init__(self, type: civitai.Model.Type):
		with gr.Column():
			with gr.Row():

				# Search input
				self.input = gr.Textbox(label= 'Search', elem_id= f'sd_mm_search_{type.name.lower()}')

				# Search mode selector
				with gr.Column(elem_classes= 'sd-mm-fitted-column'):
					self.mode = gr.Radio(['and', 'or'], label= 'Search Mode', value= lambda: 'and')

				# Clear and refresh buttons
				with gr.Column(elem_classes= 'sd-mm-fitted-column'):
					self.clear = gr.Button('Clear Search')
				with gr.Column(elem_classes= 'sd-mm-fitted-column'):
					self.refresh = gr.Button(ui.refresh_symbol, elem_id= f'sd_mm_refresh_{type.name.lower()}')

			# Model table
			table = [row[:-1] for row in get_model_table(type)]
			self.table = gr.Dataframe(table, headers= local.Model.table_header(), elem_id= f'sd_mm_dataframe_{type.name.lower()}')

class Gallery:
	''' Gallery component for the model tab '''

	html: gr.HTML
	add:  gr.Button

	def __init__(self):
		with gr.Box(elem_classes= 'sd-mm-padded-box'):
			with gr.Column():

				# Gallery HTML element
				self.html = gr.HTML(elem_classes= 'sd-mm-gallery-html')

				# Gallery buttons
				self.add = gr.Button('Add Image').style(full_width= False)

class Markdown:
	''' Markdown component for the model tab '''

	content:  gr.Markdown
	generate: gr.Button

	def __init__(self):
		with gr.Box(elem_classes= 'sd-mm-padded-box'):
			with gr.Column():

				# Markdown content element
				self.content = gr.Markdown()

				# Markdown buttons
				self.generate = gr.Button('Generate').style(full_width= False)

class ModelNameEditor:
	''' Model name editor component for the model tab '''

	input: gr.Textbox
	save:  gr.Button
	reset: gr.Button

	def __init__(self):
		with gr.Box(elem_classes= 'sd-mm-padded-box'):
			with gr.Column():
				gr.Markdown('### Name')
				with gr.Row():

					# Model name input
					self.input = gr.Textbox(show_label= False, interactive= True)

					# Save and reset buttons
					self.save  = gr.Button('Save').style(full_width= False)
					self.reset = gr.Button('Default').style(full_width= False)

class CivitaiActions:
	''' Civitai actions component for the model tab '''

	scan:            gr.Button
	update_scan:     gr.Button
	download_vae:    gr.Button
	download_images: gr.Button
	download_latest: gr.Button

	def __init__(self):
		with gr.Box(elem_classes= 'sd-mm-padded-box'):
			with gr.Column():
				gr.Markdown('### Civitai')
				with gr.Row():

					# Civitai buttons
					self.scan            = gr.Button('Scan', variant= 'primary')
					self.update_scan     = gr.Button('Update Scan')
					self.download_vae	 = gr.Button('Download VAE')
					self.download_images = gr.Button('Download Images')
					self.download_latest = gr.Button('Download Latest')

class ModelActions:
	''' Model actions component for the model tab '''

	delete: gr.Button

	def __init__(self):
		with gr.Box(elem_classes= 'sd-mm-padded-box'):
			with gr.Column():
				gr.Markdown('### Model')
				with gr.Row():

					# Model buttons
					self.delete = gr.Button('Delete', variant= 'stop')

def get_model_table(type: civitai.Model.Type):
	''' Get a table with all the models of a given type '''

	# Convert models to table rows
	model_list = [model.to_table_row() for model in local.Model.by_type(type)]

	# Return empty row if no models
	if len(model_list) == 0:
		return [[''] * len(local.Model.table_header())]

	# Return sorted table by model filename
	return sorted(model_list, key= lambda model: model[0].lower())

def get_component_status(model: local.Model):
	''' Get the visibility and content of all components '''

	all_images = len(model.all_safe_images)
	missing_images = len(model.missing_images)
	downloaded_images = len(model.downloaded_images)

	# Markdown content text
	if model.has_markdown:
		markdown_content = model.markdown_file.read_text(encoding= 'utf-8')
	else:
		markdown_content = '### Markdown'

	# Markdown generate text
	if not model.has_markdown:
		markdown_generate = 'Generate'
	else:
		markdown_generate = 'Regenerate'

	# Civitai download images text
	if downloaded_images == 0:
		download_images = 'Download Images'
	elif missing_images == 1:
		download_images = 'Download 1 Missing Image'
	else:
		download_images = f'Download {missing_images} Missing Images'

	return \
	{
		# Model options view
		'view': gr.update(visible= model.filename.full != ''),

		# Gallery component
		'gallery.html': gr.update(value= html.create_gallery(model)),
		'gallery.add': gr.update(visible= all_images == 0),

		# Markdown component
		'markdown.content': gr.update(value= markdown_content),
		'markdown.generate': gr.update(value= markdown_generate),

		# Model name component
		'model_name.input': gr.update(value= model.name),
		'model_name.reset': gr.update(visible= model.in_civitai),

		# Civitai buttons
		'civitai.scan':            gr.update(visible= not model.has_scan),
		'civitai.update_scan':     gr.update(visible= model.has_scan),
		'civitai.download_vae':    gr.update(visible= model.vae_missing),
		'civitai.download_images': gr.update(visible= missing_images > 0, value= download_images),
		'civitai.download_latest': gr.update(visible= model.is_updatable)
	}

def run_filter_table(model: local.Model, filter= '', mode: Literal['and', 'or']= 'and'):
	table = get_model_table(model.type)

	# Split the filter list and remove empty strings
	filters = filter.split(',')
	filters = [filter.strip() for filter in filters if not filter.isspace() and filter != '']

	# Filter the table
	if mode == 'and':
		table = [row for row in table if all(filter.lower() in str(row).lower() for filter in filters)]
	else:
		table = [row for row in table if any(filter.lower() in str(row).lower() for filter in filters)]

	# Remove the 'tags' field from the table
	table = [row[:-1] for row in table]

	# Set table to empty row if no results
	if len(table) == 0:
		table = [[''] * len(local.Model.table_header())]

	# Get filename, model and status
	filename = Filename(table[0][0] if len(table) == 1 else '')
	model = local.Model.get(model.type, filename)
	status = get_component_status(model)

	return model, table, *status.values()

def run_add_images(model_state: local.Model, images: list[_TemporaryFileWrapper]):
	for image in images:
		model_state.add_custom_image(Path(image.name))
	return run_filter_table(model_state, model_state.filename.full)

def run_search_refresh(model: local.Model, filter: str):
	local.clear_cache()
	utilities.clear_json_cache()
	sd_webui.model.reload_filenames(model.type)
	return run_filter_table(model, filter)

def run_markdown_generate(model: local.Model):
	model.generate_markdown()
	status = get_component_status(model)
	return status['markdown.content'], status['markdown.generate']

def run_model_name_save(model: local.Model, new_name: str):
	model.rename(new_name)
	return model.filename.full

def run_model_name_reset(model: local.Model):
	model.reset_name()
	return model.filename.full

def run_civitai_scan(model: local.Model):
	model.scan()
	LOGGER.info(f'Scan complete for "{model.filename.full}"')
	return run_filter_table(model, model.filename.full)

def run_civitai_update_scan(model: local.Model):
	model.scan(True)
	LOGGER.info(f'Updated scan for "{model.filename.full}"')
	return run_filter_table(model, model.filename.full)

def run_civitai_download_vae(model: local.Model):
	vae_model = model.download_vae()
	if vae_model is not None:
		LOGGER.info(f'Downloaded VAE "{vae_model.filename.full}"')
	return run_filter_table(model, model.filename.full)

def run_civitai_download_images(model: local.Model):
	model.download_images()
	return run_filter_table(model, model.filename.full)

def run_civitai_download_latest(model: local.Model):
	latest_model = model.download_latest()
	if latest_model is not None:
		LOGGER.info(f'Downloaded latest version "{latest_model.filename.full}"')
	return run_filter_table(model, model.filename.full)

def run_model_delete(model: local.Model):
	model.delete()
	return ''

def component(type: civitai.Model.Type):
	''' Create a model tab of the specified type '''

	with gr.Tab(type.name_hr, elem_id= f'sd_mm_tab_{type.name.lower()}'):

		# Tab image input element
		image_input = gr.Files(elem_id= f'sd_mm_image_input_{type.name.lower()}',
			file_types= ['.png', '.jpg', '.jpeg', '.webp'], visible= False)

		# State elements
		model_state = gr.State(local.Model.get(type, Filename('')))
		model_type = gr.Textbox(type.name, visible= False)

		# Search bar component
		search = SearchBar(type)

		# Model options view
		with gr.Column(visible= False) as view:
			gallery = Gallery()
			markdown = Markdown()

			# Options accordion
			with gr.Accordion('Options', open= False):
				model_name = ModelNameEditor()
				with gr.Row():
					with gr.Column(scale = 4):
						civitai = CivitaiActions()
					model = ModelActions()

		search_inputs = \
		[
			model_state,
			search.input,
			search.mode
		]

		search_outputs = \
		[
			model_state,
			search.table,

			# Status
			view,
			gallery.html,
			gallery.add,
			markdown.content,
			markdown.generate,
			model_name.input,
			model_name.reset,
			civitai.scan,
			civitai.update_scan,
			civitai.download_vae,
			civitai.download_images,
			civitai.download_latest
		]

		markdown_outputs = \
		[
			markdown.content,
			markdown.generate
		]

		# Image input
		image_input.upload(run_add_images, [model_state, image_input], search_outputs)

		# Search bar
		search.input.change(run_filter_table, search_inputs, search_outputs)
		search.clear.click(lambda: '', outputs= [search.input])
		search.refresh.click(run_search_refresh, [model_state, search.input], search_outputs)

		# Gallery
		gallery.add.click(None, [model_type], _js= f'(type) => sdmmTriggerImageInput(type)')

		# Markdown
		markdown.generate.click(run_markdown_generate, [model_state], markdown_outputs)

		# Name Editor
		model_name.save.click(run_model_name_save, [model_state, model_name.input], [search.input])
		model_name.reset.click(run_model_name_reset, [model_state], [search.input])

		# Civitai
		civitai.scan.click(run_civitai_scan, [model_state], search_outputs)
		civitai.update_scan.click(run_civitai_update_scan, [model_state], search_outputs)
		civitai.download_vae.click(run_civitai_download_vae, [model_state], search_outputs)
		civitai.download_images.click(run_civitai_download_images, [model_state], search_outputs)
		civitai.download_latest.click(run_civitai_download_latest, [model_state], search_outputs)

		# Model
		model.delete.click(run_model_delete, [model_state], [search.input])