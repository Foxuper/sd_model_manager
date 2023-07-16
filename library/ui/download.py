import gradio as gr

# Extension Library
from library import paths
from library import local
from library import civitai

def download_message(file_downloaded: bool):
	if file_downloaded:
		return 'File Already Downloaded'
	else:
		return 'Download'

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

	return \
	(
		model,
		gr.update(value= name),
		gr.update(value= type),
		gr.update(choices= versions, value= versions[0])
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
		gr.update(
			variant= 'primary' if not file_downloaded else 'secondary',
			value= download_message(file_downloaded),
			interactive= not file_downloaded,
			visible= file is not None
		)
	)

def run_download_file(model: civitai.Model, file: civitai.File):
	filename = file.download(paths.default_directory(model.type.name))

	# Handle the download
	if filename is not None:
		downloaded_model = local.Model.get(model.type, filename)
		downloaded_model.handle_download(model.type, filename)

	# Download button
	return gr.update(
		variant= 'primary' if filename is None else 'secondary',
		value= download_message(file is not None),
		interactive= filename is None
	)

def component():
	''' Civitai model download component '''

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
					search = gr.Button('Search', variant= 'primary')

			# Name, Type and Version
			with gr.Row():
				name = gr.Textbox(label= 'Name', interactive= False)
				with gr.Column(elem_classes= 'sd-mm-fitted-column'):
					type = gr.Textbox(label= 'Type', interactive= False, elem_id= 'sd-mm-model-type')
				version = gr.Dropdown(label= 'Version')

			# File, File Type and File Size
			with gr.Row():
				file = gr.Dropdown(label= 'File')
				with gr.Column(elem_classes= 'sd-mm-fitted-column'):
					file_type = gr.Textbox(label= 'Type', interactive= False)
				with gr.Column(elem_classes= 'sd-mm-fitted-column'):
					file_size = gr.Textbox(label= 'Size', interactive= False)

			# Download button
			download = gr.Button('Download', variant= 'primary', visible= False, elem_id= 'sd-mm-download-model')

	# Events
	search.click(run_search_model, [url_or_id], [model_state, name, type, version])
	version.change(run_select_version, [model_state, version], [version_state, file])
	file.change(run_select_file, [version_state, file], [file_state, file_type, file_size, download])
	download.click(run_download_file, [model_state, file_state], [download])