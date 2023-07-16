declare function gradioApp(): Document;
declare function onUiLoaded(callback: () => void): void;
declare function onAfterUiUpdate(callback: () => void): void;

let EXTENSION_TAB_BUTTON: HTMLButtonElement = null;

enum ResourceType
{
	CHECKPOINT,
	EMBEDDING,
	HYPERNETWORK,
	LORA,
	LYCORIS,
	VAE
}

enum ExtraTabs
{
	TEXT_TO_IMAGE,
	IMAGE_TO_IMAGE
}

function resourceTypeFromId(id: string): ResourceType
{
	if (id.includes('checkpoints'))       return ResourceType.CHECKPOINT;
	if (id.includes('textual_inversion')) return ResourceType.EMBEDDING;
	if (id.includes('hypernetworks'))     return ResourceType.HYPERNETWORK;
	if (id.includes('lora'))              return ResourceType.LORA;
	if (id.includes('lycoris'))           return ResourceType.LYCORIS;
	if (id.includes('vae'))               return ResourceType.VAE;
}

function getExtraTabsClass(type: ExtraTabs): string
{
	if (type == ExtraTabs.TEXT_TO_IMAGE)  return 'txt2img_extra_tabs';
	if (type == ExtraTabs.IMAGE_TO_IMAGE) return 'img2img_extra_tabs';
}

/** Refresh the embedding model list */
function clickEmbeddingReloadButton()
{
	// Get the refresh button of the embedding tab
	const refresh_embedding_button: HTMLButtonElement =
		gradioApp().querySelector('#sd_mm_refresh_embedding');

	// Click the refresh button after 500ms
	setTimeout(() => refresh_embedding_button.click(), 500);
}

/** Handles the main download button on the home tab */
function handleHomeDownloadButton()
{
	// Find the download button
	const download_button: HTMLButtonElement =
		gradioApp().querySelector('#sd-mm-download-model');
	if (download_button == null) return;

	// Skip if the button already has an onclick event
	if (download_button.onclick != null) return;

	// Add an onclick event to the download button
	download_button.onclick = () =>
	{
		// Get the model type textbox
		const model_type: HTMLTextAreaElement =
			gradioApp().querySelector('#sd-mm-model-type textarea');
		if (model_type == null) return;

		// Get the global refresh button
		const main_refresh_button: HTMLButtonElement =
			gradioApp().querySelector('#sd-mm-refresh-button');
		if (main_refresh_button == null) return;

		// Get the refresh button of the model type
		const refresh_button: HTMLButtonElement =
			gradioApp().querySelector(`#sd_mm_refresh_${model_type.value}`);
		if (refresh_button == null) return;

		// Disable the download button
		download_button.disabled = true;

		// Trigger the model refresh button when the download is done
		const interval = setInterval(() =>
		{
			if (download_button.innerText != 'Download')
			{
				main_refresh_button.click();
				refresh_button.click();
				clearInterval(interval);
			}
		}
		, 100);
	};
}

/** Find the extension tab button and save it in a global variable */
function findExtensionTabButton()
{
	// Get the tab buttons
	const buttons: NodeListOf<HTMLButtonElement> =
		gradioApp().querySelectorAll('#tabs .tab-nav button');
	if (buttons == null) return;

	// Find the extension tab button
	for (const button of buttons)
	{
		if (button.innerText == 'Model Manager')
		{
			EXTENSION_TAB_BUTTON = button;
			break;
		}
	}
}

/** Add an onclick event to the rows of a dataframe that will trigger a search */
function addSearchTriggerToDataframe(type: ResourceType)
{
	// Get the search input
	const search_input: HTMLTextAreaElement =
		gradioApp().querySelector(`#sd_mm_search_${String(ResourceType[type]).toLowerCase()} textarea`);
	if (search_input == null) return;

	// Get the rows of the dataframe
	const dataframe_rows: NodeListOf<HTMLTableRowElement> =
		gradioApp().querySelectorAll(`#sd_mm_dataframe_${String(ResourceType[type]).toLowerCase()} tbody tr`);
	if (dataframe_rows == null) return;

	// Iterate over the rows of the dataframe
	for (const row of dataframe_rows)
	{
		// Get the filename of the row (first column)
		const filename = row.querySelector('span');
		if (filename == null) continue;

		// Skip if the row already has an onclick event
		if (row.onclick != null) continue;

		// Add onclick event to the row
		row.onclick = function ()
		{
			// Modify the search input and trigger the search
			search_input.value = filename.innerHTML;
			search_input.dispatchEvent(new Event('input'));
		}
	}
}

/** Add a button that links to the resource page for each model card */
function addResourceToModelCards(type: ExtraTabs)
{
	// Get the model cards
	const type_class = getExtraTabsClass(type);
	const model_cards = gradioApp().querySelectorAll(`#${type_class} .card .actions .additional`);
	if (model_cards == null) return;

	// Iterate over the model cards
	for (const card of model_cards)
	{
		// Skip if the card already has an action
		if (card.getAttribute('action-added') == 'true') continue;
		card.setAttribute('action-added', 'true');

		// Get the card element and its parent
		const card_div = card.parentElement.parentElement;
		const parent_div = card_div.parentElement;

		// Get the model name and type
		const model_name = card_div.getAttribute('data-sort-name');
		const model_type = String(ResourceType[resourceTypeFromId(parent_div.id)]).toLowerCase();

		// Create the link to the resource page
		const resource_link = document.createElement('ul');
		const action = `onclick="sdmmOnCardClick(event, '${model_type}', '${model_name}')"`;
		resource_link.innerHTML = `<a href="#" title="Go to resource" class="resource" ${action}>go to resource</a>`;
		card.append(resource_link);

		// Another <ul> element for correct margin on card mode
		card.append(document.createElement('ul'));
	}
}

/** Open the resource page when clicking on a model card */
function sdmmOnCardClick(event: Event, model_type: string, model_name: string)
{
	// Prevent the default action of the click event
	event.stopPropagation();
	event.preventDefault();

	// Get the search input
	const search_input: HTMLTextAreaElement =
		gradioApp().querySelector(`#sd_mm_search_${model_type} textarea`);
	if (search_input == null) return;

	// Get all the tab buttons
	const nav_div = gradioApp().querySelector('#tab_sd_model_manager .tab-nav');
	const tab_buttons: NodeListOf<HTMLButtonElement> = nav_div.querySelectorAll('button');

	for (const button of tab_buttons)
	{
		if (button.innerText.trim().toLowerCase() == model_type.toLowerCase())
		{
			// Select the model tab
			button.click();

			// Trigger the search
			search_input.value = model_name;
			search_input.dispatchEvent(new Event('input'));

			// Select the extension tab
			setTimeout(() => EXTENSION_TAB_BUTTON.click(), 200);
			break;
		}
	}
}

/** Creates a full screen overlay that contains the image that was clicked */
function sdmmZoomImage(event: Event)
{
	// Get the image that was clicked and create an overlay div
	const image = event.target as HTMLImageElement;

	// Create the overlay div
	const overlay = document.createElement('div');
	overlay.onclick = () => overlay.remove();
	overlay.id = 'sd-mm-full-screen-overlay';

	// Set the image as the background of the overlay div
	overlay.innerHTML = `<img src="${image.src}">`;

	// Append the overlay div to the body
	document.body.appendChild(overlay);
}

/** API call to set the preview image of a model */
function sdmmSetPreview(type: string, filename: string, index: number)
{
	// Create query string and encode it
	filename = encodeURIComponent(filename);
	const query_string = `?type=${type}&filename=${filename}&index=${index}`;

	// Send the request
	fetch(origin + `/sd-mm/set-preview${query_string}`, { method: 'POST' });

	// Get the refresh button
	const refresh_button: HTMLButtonElement =
		gradioApp().querySelector(`#sd_mm_refresh_${type.toLowerCase()}`);
	if (refresh_button == null) return;

	// Trigger the refresh button
	refresh_button.click();
}

/** API call to delete an image of a model */
function sdmmDeleteImage(type: string, filename: string, index: number)
{
	// Create query string and encode it
	filename = encodeURIComponent(filename);
	const query_string = `?type=${type}&filename=${filename}&index=${index}`;

	// Send the request
	fetch(origin + `/sd-mm/delete-image/${query_string}`, { method: 'POST' });

	// Get the refresh button
	const refresh_button: HTMLButtonElement =
		gradioApp().querySelector(`#sd_mm_refresh_${type.toLowerCase()}`);
	if (refresh_button == null) return;

	// Trigger the refresh button
	refresh_button.click();
}

/** Send the image to the txt2img tab */
function sdmmSendToTxt2Img(type: string, filename: string, index: number)
{
	// Get the request input
	const request_input: HTMLTextAreaElement =
		gradioApp().querySelector('#sd_mm_txt2img_request textarea');
	if (request_input == null) return;

	// Get the send button
	const send_button: HTMLButtonElement =
		gradioApp().querySelector('#sd_mm_txt2img_send');
	if (send_button == null) return;

	// Get the info textbox
	const info_textbox: HTMLTextAreaElement =
		gradioApp().querySelector('#sd_mm_txt2img_info textarea');
	if (info_textbox == null) return;

	// Set the request input value and trigger the input event
	request_input.value = `${type}/${filename}/${index}`;
	request_input.dispatchEvent(new Event('input'));

	// The info textbox will be filled when the request is done
	const interval = setInterval(() =>
	{
		if (info_textbox.value != '')
		{
			// Trigger the send button and clear the info textbox
			send_button.click();
			info_textbox.value = '';
			clearInterval(interval);
		}
	}
	, 100);
}

/** Trigger the image input to add an image */
function sdmmTriggerImageInput(type: string)
{
	// Get the image input
	const image_input: HTMLInputElement =
		gradioApp().querySelector(`#sd_mm_image_input_${type.toLowerCase()} input`);
	if (image_input == null) return;
	console.log(image_input);

	// Clear the input after selecting an image
	image_input.addEventListener('change', () =>
	{
		// Delay the click event to make sure the image is submitted
		setTimeout(() =>
		{
			// Get the clear input button
				const clear_button: HTMLButtonElement =
				gradioApp().querySelector(`#sd_mm_image_input_${type.toLowerCase()} button`);
			if (clear_button == null) return;

			// Trigger the clear button
			clear_button.click();
		},
		500);
	});

	// Click the image input
	image_input.click();
}

onUiLoaded(function()
{
	clickEmbeddingReloadButton();
	handleHomeDownloadButton();
});

onAfterUiUpdate(function()
{
	findExtensionTabButton();
	Object.keys(ResourceType).forEach(key => addSearchTriggerToDataframe(ResourceType[key]));
	Object.keys(ExtraTabs).forEach(key => addResourceToModelCards(ExtraTabs[key]));
});