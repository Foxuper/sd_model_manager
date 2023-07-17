from pathlib import Path
from fastapi import FastAPI

# Extension Library
from library import sd_webui
from library import local
from library import logger
from library import civitai
from library.utilities import Filename

# Logger
LOGGER = logger.configure()

def initialize_api(app: FastAPI):

	@app.post('/sd-mm/set-preview/')
	async def set_preview(type: str, filename: str, index: int):
		''' Sets the preview image for the given model '''

		LOGGER.debug(f"API -> set_preview: {type}, {filename}, {index}")
		model = local.Model.get(civitai.Model.Type[type], Filename(filename))
		model.select_preview(index)

	@app.post('/sd-mm/delete-image/')
	async def delete_image(type: str, filename: str, index: int):
		''' Deletes the image at the given index for the given model '''

		LOGGER.debug(f"API -> delete_image: {type}, {filename}, {index}")
		model = local.Model.get(civitai.Model.Type[type], Filename(filename))
		model.remove_image(index)

	@app.post('/sd-mm/add-image/')
	async def add_image(type: str, filename: str, image: str):
		''' Adds the image to the given model '''

		LOGGER.debug(f"API -> add_image: {type}, {filename}, {image}")
		model_type = civitai.Model.Type[type]

		for model_filename in sd_webui.model.filenames(model_type):
			if model_filename.full.lower() == filename.lower():
				model = local.Model.get(model_type, model_filename)
				model.add_custom_image(Path(image), True)
				break