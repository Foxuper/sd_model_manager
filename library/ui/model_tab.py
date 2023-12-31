import time
import gradio as gr
from pathlib import Path
from typing	import Literal, cast
from tempfile import _TemporaryFileWrapper

# SD Webui Modules
from modules import ui

# Extension Library
from library import local
from library import logger
from library import civitai
from library import sd_webui
from library import download
from library.settings import Settings
from library.utilities import Filename

# Extension UI
from library.ui import html_blocks

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
				self.add = gr.Button('Add Image', scale= 0)

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
				self.generate = gr.Button('Generate', scale= 0)

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
					self.save  = gr.Button('Save', scale= 0)
					self.reset = gr.Button('Default', scale= 0)

class CivitaiActions:
	''' Civitai actions component for the model tab '''

	scan:            gr.Button
	update_scan:     gr.Button
	download_images: gr.Button
	download_vae:    gr.Button
	download_latest: gr.Button

	def __init__(self, model: local.Model):
		with gr.Box(elem_classes= 'sd-mm-padded-box'):
			with gr.Column():
				gr.Markdown('### Civitai')
				with gr.Row():
					type = model.type.name.lower()

					def images_status():
						return get_component_status(model)['civitai.download_images']
					def vae_status():
						return get_component_status(model)['civitai.download_vae']
					def latest_status():
						return get_component_status(model)['civitai.download_latest']

					# Civitai buttons
					self.scan            = gr.Button('Scan', variant= 'primary')
					self.update_scan     = gr.Button('Update Scan')
					self.download_images = gr.Button(images_status, elem_id= f'sd_mm_download_images_{type}')
					self.download_vae	 = gr.Button(vae_status, elem_id= f'sd_mm_download_vae_{type}')
					self.download_latest = gr.Button(latest_status, elem_id= f'sd_mm_download_latest_{type}')

class ModelActions:
	''' Model actions component for the model tab '''

	delete: gr.Button

	def __init__(self, type: civitai.Model.Type):
		with gr.Box(elem_classes= 'sd-mm-padded-box'):
			with gr.Column():
				gr.Markdown('### Model')
				with gr.Row():

					# Model buttons
					self.delete = gr.Button('Delete', variant= 'stop', elem_id= f'sd_mm_delete_{type.name.lower()}')

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
		'gallery.html': gr.update(value= html_blocks.create_gallery(model)),
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
		'civitai.download_images': gr.update(interactive= True, visible= missing_images > 0, value= download_images),
		'civitai.download_vae':    gr.update(interactive= True, visible= model.vae_missing, value= 'Download VAE'),
		'civitai.download_latest': gr.update(interactive= True, visible= model.is_updatable, value= 'Download Latest')
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
	filename = Filename(table[0][0] if len(table) == 1 and len(filter) > 0 else '')
	model = local.Model.get(model.type, filename)
	status = get_component_status(model)

	return model, table, *status.values()

def run_add_images(model_state: local.Model, images: list[_TemporaryFileWrapper]):
	for image in images:
		model_state.add_custom_image(Path(image.name))
	return run_filter_table(model_state, model_state.filename.full)

def run_search_refresh(model: local.Model, filter: str):
	local.clear_cache()
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

def run_civitai_download_images(model: local.Model):
	yield gr.update(interactive= False, value= 'Initializing...')

	# Get download manager instance
	download_manager = download.DownloadManager.instance()
	image_entities: list[download.File] = []

	# Create image entities and enqueue them
	for image in model.image_file_entities():
		download_manager.enqueue(image)
		image_entities.append(image)

	# Start the download manager
	download_manager.start()

	# Wait for the download to finish
	while download_manager.running:
		yield gr.update(interactive= False, value= 'Downloading...')
		time.sleep(0.2)

	# Fix missing previews
	if model.has_missing_preview:
		model.select_preview()

	# Yield final status
	if download_manager.all_complete:
		yield gr.update(interactive= False, value= 'Download Complete')
	else:
		yield get_component_status(model)['civitai.download_images']

def run_civitai_download_vae(model: local.Model):
	yield gr.update(interactive= False, value= 'Initializing...')

	# Get download manager instance
	download_manager = download.DownloadManager.instance()

	# Create VAE entity and enqueue it
	vae_entity = cast(download.File, model.vae_file_entity())
	download_manager.enqueue(vae_entity)

	# Start the download manager
	download_manager.start()

	# Wait for the download to finish
	while download_manager.running:
		yield gr.update(interactive= False, value= 'Downloading...')
		time.sleep(0.2)

	# Handle the downloaded VAEs
	if vae_entity.complete:
		local.Model.handle_download(civitai.Model.Type.VAE, vae_entity.filename)

	# Yield final status
	if download_manager.all_complete:
		yield gr.update(interactive= False, value= 'Download Complete')
	else:
		yield get_component_status(model)['civitai.download_vae']

def run_civitai_download_latest(model: local.Model):
	yield gr.update(interactive= False, value= 'Initializing...')

	# Get download manager instance
	download_manager = download.DownloadManager.instance()
	image_entities: list[download.File] = []

	# Create latest model version file entity and enqueue it
	latest_entity = cast(download.File, model.latest_file_entity())
	download_manager.enqueue(latest_entity)

	# Do not download images if the model entity is invalid
	if latest_entity.status == download.File.Status.INVALID:
		yield get_component_status(model)['civitai.download_latest']
		return

	# Create image entities and enqueue if auto image download is enabled
	if Settings.auto_image_download():
		version = model.civitai_model.latest_version
		for index, image in enumerate(version.images):
			filename = latest_entity.filename.with_index(index)
			image_entity = download.File.from_civitai_image(model.type, image, filename)
			download_manager.enqueue(image_entity)
			image_entities.append(image_entity)

	# Start the download manager
	download_manager.start()

	# Wait for the download to finish
	while download_manager.running:
		yield gr.update(interactive= False, value= 'Downloading...')
		time.sleep(0.2)

	# Remove image entities if main download is not complete
	if not latest_entity.complete:
		for image_entity in image_entities:
			image_entity.remove_file()

	# Handle the downloaded model and images
	else:
		images = [image.file for image in image_entities if image.complete]
		local.Model.handle_download(model.type, latest_entity.filename, images)

	# Yield final status
	if download_manager.all_complete:
		yield gr.update(interactive= False, value= 'Download Complete')
	else:
		yield get_component_status(model)['civitai.download_latest']

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
						civitai = CivitaiActions(model_state.value)
					model = ModelActions(type)

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
			civitai.download_images,
			civitai.download_vae,
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
		civitai.download_images.click(run_civitai_download_images, [model_state], civitai.download_images)
		civitai.download_vae.click(run_civitai_download_vae, [model_state], civitai.download_vae)
		civitai.download_latest.click(run_civitai_download_latest, [model_state], civitai.download_latest)

		# Model
		model.delete.click(run_model_delete, [model_state], [search.input])