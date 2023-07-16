import gradio as gr
from typing	import Optional

# SD Webui Modules
from modules import ui

# Extension Library
from library import local
from library import logger
from library import civitai
from library import sd_webui
from library import utilities
from library.settings import Settings

# Logger
LOGGER = logger.configure()

def scan_status(types: Optional[list[str]]= None):
	missing_scan = 0

	# Default to all types
	if types is None:
		types = [type.name_hr for type in civitai.Model.Type]

	# Count models with missing scan
	for type_hr in types:
		type = civitai.Model.Type[type_hr.upper()]
		for model in local.Model.by_type(type):
			if not model.has_scan:
				missing_scan += 1

	# Generate Scan text
	text = 'Scan 1 Model' if missing_scan == 1 else f'Scan {missing_scan} Models'
	if missing_scan == 0: text = 'Update Scans'
	color = 'primary' if missing_scan > 0 else 'secondary'
	return gr.update(interactive= len(types) > 0, value= text, variant= color)

def nsfw_previews_status(types: Optional[list[str]]= None):
	nsfw_previews = 0

	# Default to all types
	if types is None:
		types = [type.name_hr for type in civitai.Model.Type]

	# Count the NSFW previews
	for type_hr in types:
		type = civitai.Model.Type[type_hr.upper()]
		for model in local.Model.by_type(type):
			if model.has_nsfw_preview:
				nsfw_previews += 1

	# Remove NSFW Previews text
	text = 'Remove 1 NSFW Preview' if nsfw_previews == 1 else f'Remove {nsfw_previews} NSFW Previews'
	return gr.update(visible= nsfw_previews > 0, value= text)

def missing_previews_status(types: Optional[list[str]]= None):
	missing_previews = 0

	# Default to all types
	if types is None:
		types = [type.name_hr for type in civitai.Model.Type]

	# Count the missing previews
	for type_hr in types:
		type = civitai.Model.Type[type_hr.upper()]
		for model in local.Model.by_type(type):
			if model.has_missing_preview:
				missing_previews += 1

	# Remove NSFW Previews text
	text = 'Fix 1 Missing Preview' if missing_previews == 1 else f'Fix {missing_previews} Missing Previews'
	return gr.update(visible= missing_previews > 0, value= text)

def vae_symlinks_status(types: Optional[list[str]]= None):
	count = 0

	# Default to all types
	if types is None:
		types = [type.name_hr for type in civitai.Model.Type]

	# Count the symlinks
	for type_hr in types:
		type = civitai.Model.Type[type_hr.upper()]
		for model in local.Model.by_type(type):
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

	# Default to all types
	if types is None:
		types = [type.name_hr for type in civitai.Model.Type]

	# Count models with missing markdown
	for type_hr in types:
		type = civitai.Model.Type[type_hr.upper()]
		for model in local.Model.by_type(type):
			if not model.has_markdown:
				missing_markdown += 1

	# Generate Markdown text
	text = 'Generate 1 Missing Markdown File' if missing_markdown == 1 else f'Generate {missing_markdown} Missing Markdown Files'
	if missing_markdown == 0: text = 'Regenerate Markdown Files'
	return gr.update(interactive= len(types) > 0, value= text)

def download_images_status(types: Optional[list[str]]= None):
	missing_images = 0

	# Default to all types
	if types is None:
		types = [type.name_hr for type in civitai.Model.Type]

	# Count the missing images
	for type_hr in types:
		type = civitai.Model.Type[type_hr.upper()]
		for model in local.Model.by_type(type):
			missing_images += len(model.missing_images)

	# Download Images text
	text = 'Download 1 Missing Image' if missing_images == 1 else f'Download {missing_images} Missing Images'
	return gr.update(visible= missing_images > 0, value= text)

def download_vaes_status(types: Optional[list[str]]= None):
	missing_vaes = 0

	# Default to all types
	if types is None:
		types = [type.name_hr for type in civitai.Model.Type]

	# Count the missing vaes
	for type_hr in types:
		type = civitai.Model.Type[type_hr.upper()]
		for model in local.Model.by_type(type):
			if model.vae_missing:
				missing_vaes += 1

	# Download VAEs text
	text = 'Download 1 Missing VAE' if missing_vaes == 1 else f'Download {missing_vaes} Missing VAEs'
	return gr.update(visible= missing_vaes > 0, value= text)

def run_scan(types: list[str], scan_text: str):
	for type_hr in types:
		type = civitai.Model.Type[type_hr.upper()]
		for model in local.Model.by_type(type):
			if 'Update' not in scan_text:
				if not model.has_scan:
					model.scan()
			else:
				model.scan(True)
	return run_model_type_change(types, 'Scan Complete')

def run_model_type_change(types: list[str], message= ''):
	return \
	(
		scan_status(types),
		nsfw_previews_status(types),
		missing_previews_status(types),
		vae_symlinks_status(types),
		markdown_status(types),
		download_images_status(types),
		download_vaes_status(types),
		message
	)

def run_refresh(types: list[str]):
	local.clear_cache()
	utilities.clear_json_cache()
	sd_webui.model.reload_all_filenames()
	return run_model_type_change(types)

def run_remove_nsfw_previews(types: list[str]):
	for type_hr in types:
		type = civitai.Model.Type[type_hr.upper()]
		for model in local.Model.by_type(type):
			if model.has_nsfw_preview:
				LOGGER.info(f'Removing NSFW Preview for {model.name}')
				model.preview_file.unlink()
				model.select_preview()
	return nsfw_previews_status(types), 'NSFW Previews Removed'

def run_fix_missing_previews(types: list[str]):
	for type_hr in types:
		type = civitai.Model.Type[type_hr.upper()]
		for model in local.Model.by_type(type):
			if model.has_missing_preview:
				model.select_preview()
	return missing_previews_status(types), 'Previews Fixed'

def run_fix_vae_symlinks(types: list[str]):
	for type_hr in types:
		type = civitai.Model.Type[type_hr.upper()]
		for model in local.Model.by_type(type):
			if Settings.create_vae_symlinks():
				if model.vae_model is not None and not model.has_vae_symlink:
					model.link_vae()
			else:
				if model.has_vae_symlink:
					LOGGER.info(f'Removing VAE Symlink for {model.name}')
					model.vae_symlink_file.unlink()
	return vae_symlinks_status(types), 'VAE Symlinks Fixed'

def run_generate_markdown(types: list[str]):
	for type_hr in types:
		type = civitai.Model.Type[type_hr.upper()]
		for model in local.Model.by_type(type):
			model.generate_markdown()
	return markdown_status(types), 'Markdown Generated'

def run_civitai_download_images(types: list[str]):
	for type_hr in types:
		type = civitai.Model.Type[type_hr.upper()]
		for model in local.Model.by_type(type):
			model.download_images()
	return download_images_status(types), 'Images Downloaded'

def run_civitai_download_vaes(types: list[str]):
	for type_hr in types:
		type = civitai.Model.Type[type_hr.upper()]
		for model in local.Model.by_type(type):
			model.download_vae()
	return download_vaes_status(types), 'VAEs Downloaded'

def component(model_types: list[civitai.Model.Type]):
	''' Main menu component '''

	type_names = [type.name_hr for type in model_types]

	with gr.Box(elem_classes= f'sd-mm-padded-box'):
		with gr.Column():
			with gr.Row():
				scan = gr.Button(scan_status, variant= 'primary')
				with gr.Column(elem_classes= 'sd-mm-fitted-column'):
					types = gr.CheckboxGroup(type_names, value=type_names, label= 'Model Type', interactive= True)
				with gr.Column(elem_classes= 'sd-mm-fitted-column'):
					status = gr.Textbox(label= 'Status', interactive= False, elem_id= 'sd-mm-status-textbox')
				with gr.Column(elem_classes= 'sd-mm-fitted-column'):
					refresh = gr.Button(ui.refresh_symbol, elem_id= 'sd-mm-refresh-button')
			with gr.Row():
				remove_nsfw_previews = gr.Button(nsfw_previews_status)
				fix_missing_previews = gr.Button(missing_previews_status)
				fix_vae_symlinks = gr.Button(vae_symlinks_status)
				generate_markdown = gr.Button(markdown_status)
				download_images = gr.Button(download_images_status)
				download_vaes = gr.Button(download_vaes_status)

	type_change_outputs = \
	[
		scan,
		remove_nsfw_previews,
		fix_missing_previews,
		fix_vae_symlinks,
		generate_markdown,
		download_images,
		download_vaes,
		status
	]

	# Events
	scan.click(run_scan, [types, scan], type_change_outputs)
	types.change(run_model_type_change, [types], type_change_outputs)
	refresh.click(run_refresh, [types], type_change_outputs)
	remove_nsfw_previews.click(run_remove_nsfw_previews, [types], [remove_nsfw_previews, status])
	fix_missing_previews.click(run_fix_missing_previews, [types], [fix_missing_previews, status])
	fix_vae_symlinks.click(run_fix_vae_symlinks, [types], [fix_vae_symlinks, status])
	generate_markdown.click(run_generate_markdown, [types], [generate_markdown, status])
	download_vaes.click(run_civitai_download_vaes, [types], [download_vaes, status])
	download_images.click(run_civitai_download_images, [types], [download_images, status])