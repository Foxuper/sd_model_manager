declare function gradioApp(): Document;
declare function onUiLoaded(callback: () => void): void;
declare function onAfterUiUpdate(callback: () => void): void;
declare function get_uiCurrentTab(): HTMLButtonElement;
declare function selected_gallery_index(): number;

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

	// Skip if the button already has an onclick event
	if (download_button.onclick != null) return;

	// Add an onclick event to the download button
	download_button.onclick = () =>
	{
		// Get the model type textbox
		const model_type: HTMLTextAreaElement =
			gradioApp().querySelector('#sd-mm-model-type textarea');

		// Get the global refresh button
		const main_refresh_button: HTMLButtonElement =
			gradioApp().querySelector('#sd-mm-refresh-button');

		// Get the refresh button of the model type
		const refresh_button: HTMLButtonElement =
			gradioApp().querySelector(`#sd_mm_refresh_${model_type.value}`);

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

	// Get the rows of the dataframe
	const dataframe_rows: NodeListOf<HTMLTableRowElement> =
		gradioApp().querySelectorAll(`#sd_mm_dataframe_${String(ResourceType[type]).toLowerCase()} tbody tr`);

	// Iterate over the rows of the dataframe
	for (const row of dataframe_rows)
	{
		// Get the filename of the row (first column)
		const filename = row.querySelector('span');

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

	// Iterate over the model cards
	for (const card of model_cards)
	{
		// Skip if the card already has an action
		if (card.getAttribute('action-added') == 'true') continue;
		card.setAttribute('action-added', 'true');

		// Get the card element and its parent
		const card_div = card.parentElement.parentElement;
		const parent_div = card_div.parentElement;
		const actions_ul = card.querySelector('ul');

		// Get the model name and type
		const model_name = card_div.getAttribute('data-sort-name');
		const model_type = String(ResourceType[resourceTypeFromId(parent_div.id)]).toLowerCase();

		// Override the replace preview button
		const replace_action = `onclick="sdmmAddImage(event, '${model_type}', '${model_name}')"`;
		actions_ul.innerHTML = `<a href="#" title="Use generated image as preview" ${replace_action}></a>`;

		// Create the link to the resource page
		const resource_action = `onclick="sdmmGoToResource(event, '${model_type}', '${model_name}')"`;
		actions_ul.innerHTML += `<a href="#" title="Go to resource" class="resource" ${resource_action}></a>`;
	}
}

function sdmmAddImage(event: Event, model_type: string, model_name: string)
{
	// Prevent the default action of the click event
	event.stopPropagation();
	event.preventDefault();

	// Get current tab
	let current_tab = get_uiCurrentTab().innerText.trim();

	// Get the gallery element
	const gallery: NodeListOf<HTMLImageElement> =
		gradioApp().querySelectorAll(`#${current_tab}_gallery button > img`);
	if (gallery.length == 0) return;

	// Get the selected gallery index
	let index = selected_gallery_index();
	if (index == -1) index = 0;

	// Create query string and encode it
	const type = model_type.toUpperCase();
	const filename = encodeURIComponent(model_name);
	const image_path = encodeURIComponent(gallery[index].src.split('/file=')[1]);
	const query_string = `?type=${type}&filename=${filename}&image=${image_path}`;

	// Send the request
	fetch(origin + `/sd-mm/add-image/${query_string}`, { method: 'POST' });

	// Get the refresh button
	const refresh_button: HTMLButtonElement =
		gradioApp().querySelector(`#${current_tab}_extra_refresh`);

	// Trigger the refresh button
	refresh_button.click();
}

/** Open the resource page when clicking on the resource action button */
function sdmmGoToResource(event: Event, model_type: string, model_name: string)
{
	// Prevent the default action of the click event
	event.stopPropagation();
	event.preventDefault();

	// Get the search input
	const search_input: HTMLTextAreaElement =
		gradioApp().querySelector(`#sd_mm_search_${model_type} textarea`);

	// Get all the tab buttons
	const nav_div = gradioApp().querySelector('#tab_sd_model_manager .tab-nav');
	const tab_buttons: NodeListOf<HTMLButtonElement> = nav_div.querySelectorAll('button');

	for (const button of tab_buttons)
	{
		if (button.innerText.trim().toLowerCase() == model_type.toLowerCase())
		{
			// Select the model tab
			button.click();

			// Clear the search input if it is not empty
			if (search_input.value != '')
			{
				search_input.value = '';
				search_input.dispatchEvent(new Event('input'));
			}

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

/** Splits an image information string into a list of fields */
function split_info(info: string)
{
	const fields: {name: string, value: string}[] = [];

	// Split the info string into lines
	const lines = info.split('<br>');

	// Add the prompt field
	fields.push({name: 'Prompt', value: ''});

	// Iterate over the lines
	for (const line of lines)
	{
		for (const field of line.split(','))
		{
			// Trim and skip empty fields
			const trimmed_field = field.trim();
			if (trimmed_field == '') continue;

			// Try to parse the field name and value
			const match = trimmed_field.match(/^([\w ]+): ([^,]+)/);

			if (match)
			{
				// If the regex matched, then the field is valid
				const name = match[1].trim();
				const value = match[2].trim();
				fields.push({name, value});
			}
			else
			{
				// The field is not valid, so append it to the last field
				const comma = (fields[0].value == '') ? '' : ', ';
				fields[fields.length - 1].value += `${comma}${trimmed_field}`;
			}
		}
	}

	// Escape chevrons in the field values
	for (const field of fields)
		field.value = field.value.replace(/</g, '&lt;').replace(/>/g, '&gt;');

	return fields;
}

/** Builds the html view for the image info */
function build_info_html(info: string)
{
	let field_count = 0;

	// Get the fields from the info string
	const fields = split_info(info);

	// Build the html container for the info
	let html = '<div class="sd-mm-model-info-container">\n';

	// Function to close last row
	function close_row()
	{
		if (field_count > 0)
		{
			html += '    </div>\n';
			field_count = 0;
		}
	}

	// Iterate over the fields
	for (const field of fields)
	{
		const is_normal_field = !field.name.match(/(^| )prompt/i);

		// Close row when there is more than one field
		if (field_count > 1)
			close_row();

		// Only normal fields are added to the row
		if (is_normal_field)
		{
			if (field_count == 0)
				html += '<div class="row">\n';
			html += '    <div class="field">\n';
			field_count++;
		}
		// Prompt fields are added to a vertical field
		else
		{
			close_row();
			html += '    <div class="vertical-field">\n';
		}

		// Add the field name and value
		html += `            <div class="name">${field.name}</div>\n`;
		html += `            <div class="value">${field.value}</div>\n`;
		html += '        </div>\n';
	}

	close_row();
	html += '</div>\n';
	return html;
}

/** Creates a full screen overlay that contains the image information */
function sdmmShowInfo(info: string)
{
	// Create the overlay div
	const overlay = document.createElement('div');
	overlay.onclick = () => overlay.remove();
	overlay.id = 'sd-mm-full-screen-overlay';

	// Build the html for the image info
	overlay.innerHTML = build_info_html(info);

	// Avoid closing the overlay when clicking on the info container
	const info_container: HTMLDivElement
		= overlay.querySelector('.sd-mm-model-info-container');
	info_container.onclick = (event) => { event.preventDefault(); event.stopPropagation(); };

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

	// Trigger the refresh button
	refresh_button.click();
}

/** Send the image to the txt2img tab */
function sdmmSendToTxt2Img(type: string, filename: string, index: number)
{
	// Get the request input
	const request_input: HTMLTextAreaElement =
		gradioApp().querySelector('#sd_mm_txt2img_request textarea');

	// Get the send button
	const send_button: HTMLButtonElement =
		gradioApp().querySelector('#sd_mm_txt2img_send');

	// Get the info textbox
	const info_textbox: HTMLTextAreaElement =
		gradioApp().querySelector('#sd_mm_txt2img_info textarea');

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

	// Clear the input after selecting an image
	image_input.addEventListener('change', () =>
	{
		// Delay the click event to make sure the image is submitted
		setTimeout(() =>
		{
			// Get the clear input button
			const clear_button: HTMLButtonElement =
				gradioApp().querySelector(`#sd_mm_image_input_${type.toLowerCase()} button`);

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