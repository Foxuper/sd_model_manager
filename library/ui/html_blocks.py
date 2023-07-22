import time
import urllib.parse
from PIL import Image
from typing	import cast
from pathlib import Path

# Extension Library
from library import paths
from library import local
from library import download
from library import utilities
from library.utilities import Filename

def create_image(model: local.Model, image_path: Path):
	''' Creates HTML code for an image card with action buttons '''

	# Get image path relative to SD web UI root and escape special URL characters
	relative_path = image_path.relative_to(paths.ROOT_DIR)
	url_path = urllib.parse.quote(str(relative_path), safe= '/:\\')

	# Check if the image has parameters and if it is the preview
	has_parameters = utilities.image_has_parameters(image_path)
	is_preview = model.has_preview and image_path.samefile(model.preview_file)

	# Get model information and image index
	type = model.type.name
	filename = model.filename.full
	index = cast(int, Filename(image_path).get_index())

	# Add cache time to user defined images to avoid caching issues
	cache_time = time.time() if index >= 1000 else 0

	# Create HTML code
	html  = f'<div class="sd-mm-image">\n'
	html += f'    <img src="file={url_path}?c={cache_time}" onclick="sdmmZoomImage(event)" />\n'
	html += f'    <div class="sd-mm-actions">\n'

	# Preview icon
	if is_preview:
		html += f'    <div class="sd-mm-action sd-mm-preview" title="This is the preview"></div>\n'

	# Set as preview button
	else:
		html += f'    <div class="sd-mm-action sd-mm-star" title="Set as preview"\n'
		html += f'        onclick="sdmmSetPreview(\'{type}\', \'{filename}\', {index})"></div>\n'

	if has_parameters:
		info: str = Image.open(image_path).info['parameters']

		# Make info string safe for HTML
		info = info.replace('"', '&quot;').replace("'", '&#39;')
		info = info.replace('\r\n', '<br>').replace('\r', '<br>').replace('\n', '<br>')

		# Send to PNG Info button
		html += f'    <div class="sd-mm-action sd-mm-send-to" title="Send to txt2img"\n'
		html += f'        onclick="sdmmSendToTxt2Img(\'{type}\', \'{filename}\', {index})"></div>\n'

		# Show info button
		html += f'    <div class="sd-mm-action sd-mm-info" title="Show info"\n'
		html += f'        onclick="sdmmShowInfo(\'{info}\')"></div>\n'

	# Delete image button
	html += f'        <div class="sd-mm-action sd-mm-delete" title="Delete"\n'
	html += f'            onclick="sdmmDeleteImage(\'{type}\', \'{filename}\', {index})"></div>\n'

	html += f'    </div>\n'
	html += f'</div>\n'
	return html

def create_gallery(model: local.Model):
	''' Creates HTML code for a gallery of images '''

	# Get all downloaded images of the model
	images = model.all_safe_images

	# Show gallery title if there are no images
	if len(images) == 0:
		return '<h3>Images</h3>\n'

	# Create HTML for gallery
	html  = f'<div class="sd-mm-gallery">\n'
	html += f'	<div class="sd-mm-actions">\n'
	html += f'		<div class="sd-mm-action sd-mm-add" title="Add Image"\n'
	html += f'			onclick="sdmmTriggerImageInput(\'{model.type.name}\')"></div>\n'
	html += f'	</div>\n'

	# Create HTML code for each image
	for image in images:
		html += create_image(model, image)

	html += f'</div>\n'
	return html

def create_file(file: download.File):
	''' Creates HTML code for a file in the download manager '''

	html =  f'<tr>\n'
	html += f'    <td class="filename">\n'
	html += f'        <div class="filename-container">{file.filename.full}</div>\n'
	html += f'    </td>\n'
	html += f'    <td class="status">{file.status.value}</td>\n'
	html += f'    <td class="progress-bar">\n'
	html += f'        <div class="bar-container">\n'
	html += f'            <div class="bar" style="width: {file.percentage_hr}"></div>\n'
	html += f'            <div class="percentage">{file.percentage_hr}</div>\n'
	html += f'        </div>\n'
	html += f'    </div>\n'
	html += f'    <td class="info">{file.speed_hr}</td>\n'
	html += f'    <td class="info">{file.progress_hr}</td>\n'
	html += f'    <td class="info">{file.estimated_time_hr}</td>\n'
	html += f'</tr>\n'
	return html

def create_manager(files: list[download.File]):
	''' Creates HTML code for the download manager '''

	html = '<table class="sd-mm-download-manager">\n'
	for file in files:
		html += create_file(file)
	html += '</table>\n'
	return html