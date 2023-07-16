import gradio as gr
from PIL import Image
from typing	import cast
from pathlib import Path

# SD Webui Modules
from modules.extras import run_pnginfo
import modules.generation_parameters_copypaste as parameters_copypaste

# Extension Library
from library import local
from library import civitai
from library.utilities import Filename

def run_txt2img(request: str):
	'''
		Converts a text request into its corresponding image metadata and image object
		- `request`: The request string, in the format of `type/filename/index`
		- `returns`: A tuple of the image metadata and image object
		- The request is filled through JS to trigger this function
	'''

	type, filename, index = request.split('/')

	# Get the image
	model = local.Model.get(civitai.Model.Type[type], Filename(filename))
	image_file = cast(Path, model.image_by_index(int(index)))
	image = Image.open(image_file)

	# Resize the image to load faster, only the metadata is needed
	image.thumbnail((1, 1), Image.Resampling.NEAREST)

	# Return the info and image
	return run_pnginfo(image)[1], image

def component():
	'''
		Hidden component that allows to send an image to the txt2img tab
		- `triggers`:
			- The request string is filled through JS
			- The action is triggered with JS through the send button
		- `actions`:
			- The image is sent to the txt2img tab
	'''

	with gr.Column(visible= False):
		request = gr.Textbox(elem_id= 'sd_mm_txt2img_request')
		send = gr.Button(elem_id= 'sd_mm_txt2img_send')
		info = gr.Textbox(elem_id= 'sd_mm_txt2img_info')
		image = gr.Image()

		# Link the button to the txt2img paste button
		parameters_copypaste.register_paste_params_button \
		(
			parameters_copypaste.ParamBinding \
			(
				tabname= 'txt2img',
				paste_button= send,
				source_text_component= info,
				source_image_component= image
			)
		)

		# Fill the info and image through the request text
		request.change(run_txt2img, [request], [info, image])