import time
import gradio as gr
from typing	import Optional

# SD Webui Modules
from modules import ui

# Extension Library
from library import local
from library import logger
from library import civitai
from library import sd_webui
from library import download
from library import utilities
from library.settings import Settings

# Logger
LOGGER = logger.configure()

def model_list(types: Optional[list[str]]= None):
	''' Returns a list of models of the specified types '''

	# Default to all types
	if types is None:
		types = [type.name_hr for type in civitai.Model.Type]

	# Get the models
	models: list[local.Model] = []
	for type_hr in types:
		type = civitai.Model.Type[type_hr.upper()]
		models.extend(local.Model.by_type(type))
	return models

def scan_status(types: Optional[list[str]]= None):
	missing_scan = 0

	# Count models with missing scan
	for model in model_list(types):
		if not model.has_scan:
			missing_scan += 1

	# Generate Scan text
	text = 'Scan 1 Model' if missing_scan == 1 else f'Scan {missing_scan} Models'
	if missing_scan == 0: text = 'Update Scans'
	color = 'primary' if missing_scan > 0 else 'secondary'
	return gr.update(interactive= types is None or len(types) > 0, value= text, variant= color)

def nsfw_previews_status(types: Optional[list[str]]= None):
	nsfw_previews = 0

	# Count the NSFW previews
	for model in model_list(types):
		if model.has_nsfw_preview:
			nsfw_previews += 1

	# Remove NSFW Previews text
	text = 'Remove 1 NSFW Preview' if nsfw_previews == 1 else f'Remove {nsfw_previews} NSFW Previews'
	return gr.update(interactive= True, visible= nsfw_previews > 0, value= text if nsfw_previews > 0 else 'IDLE')

def missing_previews_status(types: Optional[list[str]]= None):
	missing_previews = 0

	# Count the missing previews
	for model in model_list(types):
		if model.has_missing_preview:
			missing_previews += 1

	# Remove NSFW Previews text
	text = 'Fix 1 Missing Preview' if missing_previews == 1 else f'Fix {missing_previews} Missing Previews'
	return gr.update(interactive= True, visible= missing_previews > 0, value= text if missing_previews > 0 else 'IDLE')

def vae_symlinks_status(types: Optional[list[str]]= None):
	count = 0

	# Count the symlinks
	for model in model_list(types):
		if Settings.create_vae_symlinks():
			if model.vae_model is not None and not model.has_vae_symlink:
				count += 1
		else:
			if model.has_vae_symlink:
				count += 1

	# Fix VAE Symlinks text
	if Settings.create_vae_symlinks():
		text = 'Fix 1 Missing VAE Symlink' if count == 1 else f'Fix {count} Missing VAE Symlinks'
	else:
		text = 'Remove 1 VAE Symlink' if count == 1 else f'Remove {count} VAE Symlinks'
	return gr.update(visible= count > 0, value= text)

def markdown_status(types: Optional[list[str]]= None):
	missing_markdown = 0

	# Count models with missing markdown
	for model in model_list(types):
		if not model.has_markdown:
			missing_markdown += 1

	# Generate Markdown text
	text = 'Generate 1 Missing Markdown File' if missing_markdown == 1 else f'Generate {missing_markdown} Missing Markdown Files'
	if missing_markdown == 0: text = 'Regenerate Markdown Files'
	return gr.update(interactive= types is None or len(types) > 0, value= text)

def download_images_status(types: Optional[list[str]]= None):
	missing_images = 0

	# Count the missing images
	for model in model_list(types):
		missing_images += len(model.missing_images)

	# Download Images text
	text = 'Download 1 Missing Image' if missing_images == 1 else f'Download {missing_images} Missing Images'
	return gr.update(interactive= True, visible= missing_images > 0, value= text)

def download_vaes_status(types: Optional[list[str]]= None):
	missing_vaes = 0

	# Cannot download VAEs if there is any model with missing scan
	for model in model_list(types):
		if not model.has_scan:
			return gr.update(visible= False)

	# Count the missing vaes
	for model in model_list(types):
		if model.vae_missing:
			missing_vaes += 1

	# Download VAEs text
	text = 'Download 1 Missing VAE' if missing_vaes == 1 else f'Download {missing_vaes} Missing VAEs'
	return gr.update(interactive= True, visible= missing_vaes > 0, value= text)

def run_scan(types: list[str], scan_text: str):

	# Scan or update the model scans
	for model in model_list(types):
		if 'Update' not in scan_text:
			if not model.has_scan:
				yield \
				(
					gr.update(interactive= False, value= f'Scanning model {model.name}...'),
					*run_model_type_change(types)[1:]
				)
				model.scan()
		else:
			yield \
			(
				gr.update(interactive= False, value= f'Updating scan for {model.name}...'),
				*run_model_type_change(types)[1:]
			)
			model.scan(True)

	yield run_model_type_change(types)

def run_model_type_change(types: list[str]):
	return \
	(
		scan_status(types),
		nsfw_previews_status(types),
		missing_previews_status(types),
		vae_symlinks_status(types),
		markdown_status(types),
		download_images_status(types),
		download_vaes_status(types)
	)

def run_refresh(types: list[str]):
	local.clear_cache()
	utilities.clear_json_cache()
	sd_webui.model.reload_all_filenames()
	return run_model_type_change(types)

def run_remove_nsfw_previews(types: list[str]):
	models = model_list(types)
	for model in models:
		if model.has_nsfw_preview:
			yield gr.update(interactive= False, value= f'Removing NSFW Preview for {model.name}...')
			model.preview_file.unlink()
			model.select_preview()
	yield nsfw_previews_status(types)

def run_fix_missing_previews(types: list[str]):
	for model in model_list(types):
		if model.has_missing_preview:
			yield gr.update(interactive= False, value= f'Fixing Missing Preview for {model.name}...')
			model.select_preview()
	yield missing_previews_status(types)

def run_fix_vae_symlinks(types: list[str]):
	for model in model_list(types):
		if Settings.create_vae_symlinks():
			if model.vae_model is not None and not model.has_vae_symlink:
				yield gr.update(interactive= False, value= f'Creating VAE Symlink for {model.name}...')
				model.link_vae()
		else:
			if model.has_vae_symlink:
				yield gr.update(interactive= False, value= f'Removing VAE Symlink for {model.name}...')
				model.vae_symlink_file.unlink()
	yield vae_symlinks_status(types)

def run_generate_markdown(types: list[str]):
	models = model_list(types)
	for index, model in enumerate(models):
		yield gr.update(interactive= False, value= f'Generating Markdown {index + 1} / {len(models)}')
		model.generate_markdown()
	yield markdown_status(types)

def run_civitai_download_images(types: list[str]):
	yield gr.update(interactive= False, value= 'Initializing...')

	# Get download manager instance
	download_manager = download.DownloadManager.instance()
	image_entities: list[download.File] = []

	# Create image entities and enqueue them
	for model in model_list(types):
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
	for model in model_list(types):
		if model.has_missing_preview:
			model.select_preview()

	# Yield final status
	if download_manager.all_complete:
		yield gr.update(interactive= False, value= 'Download Complete')
	else:
		yield download_images_status(types)

def run_civitai_download_vaes(types: list[str]):
	yield gr.update(interactive= False, value= 'Initializing...')

	# Get download manager instance
	download_manager = download.DownloadManager.instance()
	vae_entities: list[download.File] = []

	# Create VAE entities and enqueue them
	for model in model_list(types):
		vae = model.vae_file_entity()
		if vae is not None:
			download_manager.enqueue(vae)
			vae_entities.append(vae)

	# Start the download manager
	download_manager.start()

	# Wait for the download to finish
	while download_manager.running:
		yield gr.update(interactive= False, value= 'Downloading...')
		time.sleep(0.2)

	# Handle the downloaded VAEs
	for vae_entity in vae_entities:
		if vae_entity.complete:
			local.Model.handle_download(civitai.Model.Type.VAE, vae_entity.filename)

	# Yield final status
	if download_manager.all_complete:
		yield gr.update(interactive= False, value= 'Download Complete')
	else:
		yield download_vaes_status(types)

def component(model_types: list[civitai.Model.Type]):
	''' Home tab menu component '''

	type_names = [type.name_hr for type in model_types]

	with gr.Box(elem_classes= f'sd-mm-padded-box'):
		with gr.Column():
			with gr.Row():

				# Model Manager title
				gr.HTML('<br><h1>Model Manager<h1>')

				# Model type selection and refresh button
				with gr.Column(elem_classes= 'sd-mm-fitted-column'):
					types = gr.CheckboxGroup(type_names, value=type_names, label= 'Model Type', interactive= True)
				with gr.Column(elem_classes= 'sd-mm-fitted-column'):
					refresh = gr.Button(ui.refresh_symbol, elem_id= 'sd_mm_refresh_button')

			# Model actions
			with gr.Row():
				scan = gr.Button(scan_status, variant= 'primary', elem_id= 'sd_mm_scan_models_button')
				remove_nsfw_previews = gr.Button(nsfw_previews_status, elem_id= 'sd_mm_remove_nsfw_previews_button')
				fix_missing_previews = gr.Button(missing_previews_status, elem_id= 'sd_mm_fix_missing_previews_button')
				fix_vae_symlinks = gr.Button(vae_symlinks_status)
				generate_markdown = gr.Button(markdown_status, elem_id= 'sd_mm_generate_markdown_button')
				download_images = gr.Button(download_images_status, elem_id= 'sd_mm_download_images_button')
				download_vaes = gr.Button(download_vaes_status, elem_id= 'sd_mm_download_vaes_button')

	type_change_outputs: list[gr.components.Component] = \
	[
		scan,
		remove_nsfw_previews,
		fix_missing_previews,
		fix_vae_symlinks,
		generate_markdown,
		download_images,
		download_vaes
	]

	# Events
	scan.click(run_scan, [types, scan], type_change_outputs)
	types.change(run_model_type_change, [types], type_change_outputs)
	refresh.click(run_refresh, [types], type_change_outputs)
	remove_nsfw_previews.click(run_remove_nsfw_previews, [types], [remove_nsfw_previews])
	fix_missing_previews.click(run_fix_missing_previews, [types], [fix_missing_previews])
	fix_vae_symlinks.click(run_fix_vae_symlinks, [types], [fix_vae_symlinks])
	generate_markdown.click(run_generate_markdown, [types], [generate_markdown])
	download_images.click(run_civitai_download_images, [types], [download_images])
	download_vaes.click(run_civitai_download_vaes, [types], [download_vaes])