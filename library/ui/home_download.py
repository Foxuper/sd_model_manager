import time
import gradio as gr
from typing import Optional

# SD Webui Modules
from modules import ui

# Extension Library
from library import local
from library import civitai
from library import download
from library.settings import Settings

def download_state(file: Optional[civitai.File] = None, file_downloaded = False, text = ''):
	custom_text = (text != '')

	# Button text
	if text == '':
		if file_downloaded:
			text = 'File Already Downloaded'
		else:
			text = 'Download'

	return gr.update \
	(
		variant= 'primary' if not file_downloaded else 'secondary', value= text,
		interactive= not file_downloaded and not custom_text,
		visible= file is not None or custom_text
	)

def run_search_model(url_or_id: str):
	model = civitai.Model.request_by_mixed(url_or_id)

	if model is not None:
		name = model.name
		type = model.type.name.lower()
		versions = [version.full_name for version in model.versions]
	else:
		name = ''
		type = ''
		versions = ['']

	# Simulate version and file selection to extract download button state
	select_version = run_select_version(model, versions[0])
	select_file = run_select_file(select_version[0], select_version[1]['value'])

	return \
	(
		model,
		gr.update(value= name),
		gr.update(value= type),
		gr.update(choices= versions, value= versions[0]),

		# Download button
		select_file[3],
	)

def run_clear_search():
	return \
	(
		# URL / ID
		gr.update(value= ''),

		# Model, Name, Type and Version
		None,
		gr.update(value= ''),
		gr.update(value= ''),
		gr.update(choices= [''], value= ''),

		# Download button
		download_state()
	)

def run_select_file(version: civitai.Version | None, full_name: str):
	file_downloaded = False

	if version is not None:
		file = next(f for f in version.files if f.full_name == full_name)
		type = file.type_hr
		size = file.size_hr

		# Search for existing file
		for model in local.Model.all():
			if model.hash == file.hash:
				file_downloaded = True
				break
	else:
		file = None
		type = ''
		size = ''

	return \
	(
		file,
		gr.update(value= type),
		gr.update(value= size),

		# Download button
		download_state(file, file_downloaded)
	)

def run_select_version(model: civitai.Model | None, full_name: str):
	if model is not None:
		version = next(v for v in model.versions if v.full_name == full_name)
		files = [file.full_name for file in version.files if not file.is_vae]
		file = next(f.full_name for f in version.files if f.primary)
	else:
		version = None
		files = []
		file = ''

	return \
	(
		version,
		gr.update(choices= files, value= file)
	)

def run_download_file(model: civitai.Model, version: civitai.Version, file: civitai.File):
	yield download_state(text= 'Initializing...')

	# Get download manager instance
	download_manager = download.DownloadManager.instance()
	image_entities: list[download.File] = []

	# Create model entity and enqueue it
	model_entity = download.File.from_civitai_file(model.type, file)
	download_manager.enqueue(model_entity)

	# Do not download images if the model entity is invalid
	if model_entity.status == download.File.Status.INVALID:
		select_file = run_select_file(version, file.full_name)
		yield select_file[3]; return

	# Create image entities and enqueue if auto image download is enabled
	if Settings.auto_image_download():
		for index, image in enumerate(version.images):
			filename = model_entity.filename.with_index(index)
			image_entity = download.File.from_civitai_image(model.type, image, filename)
			download_manager.enqueue(image_entity)
			image_entities.append(image_entity)

	# Start the download manager
	download_manager.start()

	# Disable download button and yield 'Downloading...' until download is complete
	while download_manager.running:
		yield download_state(text= 'Downloading...')
		time.sleep(0.2)

	# Remove image entities if main download is not complete
	if not model_entity.complete:
		for image_entity in image_entities:
			image_entity.remove_file()

	# Handle the downloaded model and images
	else:
		images = [image.file for image in image_entities if image.complete]
		local.Model.handle_download(model.type, model_entity.filename, images)

	# Yield final status
	if download_manager.all_complete:
		yield download_state(text= 'Download Complete')
	else:
		yield download_state(text= 'Stopped / Failed')

def component():
	''' Home tab Civitai model download component '''

	# State elements
	model_state = gr.State(None)
	version_state = gr.State(None)
	file_state = gr.State(None)

	with gr.Box(elem_classes= f'sd-mm-padded-box'):
		with gr.Column():
			gr.Markdown('### Download Civitai Model')

			# Search bar
			with gr.Row():
				url_or_id = gr.Textbox(label= 'Model URL / ID', placeholder= 'https://civitai.com/models/...')
				with gr.Column(elem_classes= 'sd-mm-fitted-column'):
					search = gr.Button('Search', variant= 'primary', elem_id= 'sd_mm_download_search')
				with gr.Column(elem_classes= 'sd-mm-fitted-column'):
					clear = gr.Button('Clear Search', variant= 'secondary')
				with gr.Column(elem_classes= 'sd-mm-fitted-column'):
					refresh = gr.Button(ui.refresh_symbol, elem_id= 'sd_mm_download_refresh')

			# Name, Type and Version
			with gr.Row():
				name = gr.Textbox(label= 'Name', interactive= False)
				with gr.Column(elem_classes= 'sd-mm-fitted-column'):
					type = gr.Textbox(label= 'Type', interactive= False)
				version = gr.Dropdown(label= 'Version')

			# File, File Type and File Size
			with gr.Row():
				file = gr.Dropdown(label= 'File')
				with gr.Column(elem_classes= 'sd-mm-fitted-column'):
					file_type = gr.Textbox(label= 'Type', interactive= False)
				with gr.Column(elem_classes= 'sd-mm-fitted-column'):
					file_size = gr.Textbox(label= 'Size', interactive= False)

			# Download button
			download = gr.Button('Download', variant= 'primary', visible= False, elem_id= 'sd_mm_download_model_button')

	# Events
	search.click(run_search_model, [url_or_id], [model_state, name, type, version, download])
	clear.click(run_clear_search, outputs= [url_or_id, model_state, name, type, version, download])
	refresh.click(run_select_file, [version_state, file], [file_state, file_type, file_size, download])
	version.change(run_select_version, [model_state, version], [version_state, file])
	file.change(run_select_file, [version_state, file], [file_state, file_type, file_size, download])
	download.click(run_download_file, [model_state, version_state, file_state], [download])