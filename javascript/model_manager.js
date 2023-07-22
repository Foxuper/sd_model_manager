let EXTENSION_TAB_BUTTON = null;
var ResourceType;
(function (ResourceType) {
    ResourceType["CHECKPOINT"] = "checkpoint";
    ResourceType["EMBEDDING"] = "embedding";
    ResourceType["HYPERNETWORK"] = "hypernetwork";
    ResourceType["LORA"] = "lora";
    ResourceType["LYCORIS"] = "lycoris";
    ResourceType["VAE"] = "vae";
})(ResourceType || (ResourceType = {}));
var ExtraTabs;
(function (ExtraTabs) {
    ExtraTabs["TEXT_TO_IMAGE"] = "txt2img";
    ExtraTabs["IMAGE_TO_IMAGE"] = "img2img";
})(ExtraTabs || (ExtraTabs = {}));
function resourceTypeFromId(id) {
    if (id.includes('checkpoints'))
        return ResourceType.CHECKPOINT;
    if (id.includes('textual_inversion'))
        return ResourceType.EMBEDDING;
    if (id.includes('hypernetworks'))
        return ResourceType.HYPERNETWORK;
    if (id.includes('lora'))
        return ResourceType.LORA;
    if (id.includes('lycoris'))
        return ResourceType.LYCORIS;
    if (id.includes('vae'))
        return ResourceType.VAE;
}
/** Get an element from the gradio app via a query selector */
function getElement(query) { return gradioApp().querySelector(query); }
/** Get many elements from the gradio app via a query selector */
function getElements(query) { return gradioApp().querySelectorAll(query); }
/** Triggers a button click after a delay */
function triggerButton(button_id, delay = 0) {
    const button = getElement(button_id);
    setTimeout(() => button.click(), delay);
}
/** Assigns an action to a button if it doesn't have one already */
function assignButtonAction(button_id, action) {
    const button = getElement(button_id);
    if (button.onclick != null)
        return;
    button.onclick = action;
}
/** Executes a callback when the value of a button or textarea changes */
function waitForValueChange(component_id, text, action, delay = 200) {
    const element = getElement(component_id);
    const interval = setInterval(function () {
        if (element.innerText == text || element.value == text) {
            action();
            clearInterval(interval);
        }
    }, delay);
}
/** Assigns an action to a button that will trigger when the value changes */
function assignWaitForValueChange(component_id, text, action, delay = 200) { assignButtonAction(component_id, () => waitForValueChange(component_id, text, action, delay)); }
/** Refreshes one of the model tabs */
function refreshTab(type, delay = 0) { triggerButton(`#sd_mm_refresh_${type.valueOf()}`, delay); }
/** Refreshes all the model tabs */
function refreshAllTabs(delay = 0, except = null) {
    for (const key of Object.keys(ResourceType)) {
        if (ResourceType[key] == except)
            continue;
        refreshTab(ResourceType[key], delay);
    }
}
/** Refreshes the home tab menu */
function refreshHomeMenu(delay = 0) { triggerButton('#sd_mm_refresh_button', delay); }
/** Shows the global download manager */
function showDownloadManager() {
    getElement('#sd_mm_download_manager').style.display = 'block';
    refreshHomeMenu();
}
/** Hides the global download manager */
function hideDownloadManager() {
    getElement('#sd_mm_download_manager').style.display = 'none';
    triggerButton('#sd_mm_download_refresh', 500);
    refreshHomeMenu();
}
/** Handles events when a download button is clicked */
function handleDownloadButton(download_button_id) {
    // Shows the download manager when the download starts
    assignWaitForValueChange(download_button_id, 'Downloading...', function () {
        showDownloadManager();
        triggerButton('#sd_mm_download_manager_start');
        // Hides the download manager when the download finishes
        waitForValueChange(download_button_id, 'Download Complete', function () {
            hideDownloadManager();
            refreshAllTabs(500);
        });
    });
}
/** Handles the download images button on the model tabs */
function handleTabDownloadImagesButton(type) { handleDownloadButton(`#sd_mm_download_images_${type.valueOf()}`); }
/** Handles the download vaes button on the model tabs */
function handleTabDownloadVaeButton(type) { handleDownloadButton(`#sd_mm_download_vae_${type.valueOf()}`); }
/** Handles the download latest button on the model tabs */
function handleTabDownloadLatestButton(type) { handleDownloadButton(`#sd_mm_download_latest_${type.valueOf()}`); }
/** Handles the delete model button on the model tabs */
function handleTabDeleteModelButton(type) {
    assignButtonAction(`#sd_mm_delete_${type.valueOf()}`, function () {
        // Refresh the tabs and the home menu when the delete is finished
        waitForValueChange(`#sd_mm_search_${type.valueOf()} textarea`, '', function () {
            refreshAllTabs(0, type);
            refreshHomeMenu();
            triggerButton('#sd_mm_download_refresh');
        });
    });
}
/** Find the extension tab button and save it in a global variable */
function findExtensionTabButton() {
    const buttons = getElements('#tabs .tab-nav button');
    // Find the extension tab button
    for (const button of buttons) {
        if (button.innerText == 'Model Manager') {
            EXTENSION_TAB_BUTTON = button;
            break;
        }
    }
}
/** Add an onclick event to the rows of a dataframe that will trigger a search */
function addSearchTriggerToDataframe(type) {
    // Get the search input
    const search_input = getElement(`#sd_mm_search_${type.valueOf()} textarea`);
    // Get the rows of the dataframe
    const dataframe_rows = getElements(`#sd_mm_dataframe_${type.valueOf()} tbody tr`);
    // Iterate over the rows of the dataframe
    for (const row of dataframe_rows) {
        // Get the filename of the row (first column)
        const filename = row.querySelector('span');
        // Skip if the row already has an onclick event
        if (row.onclick != null)
            continue;
        // Add onclick event to the row
        row.onclick = function () {
            // Modify the search input and trigger the search
            search_input.value = filename.innerHTML;
            search_input.dispatchEvent(new Event('input'));
        };
    }
}
/** Add a button that links to the resource page for each model card */
function addResourceToModelCards(type) {
    // Get the model cards
    const type_class = `${type.valueOf()}_extra_tabs`;
    const model_cards = getElements(`#${type_class} .card .actions .additional`);
    // Iterate over the model cards
    for (const card of model_cards) {
        // Skip if the card already has an action
        if (card.getAttribute('action-added') == 'true')
            continue;
        card.setAttribute('action-added', 'true');
        // Get the card element and its parent
        const card_div = card.parentElement.parentElement;
        const parent_div = card_div.parentElement;
        const actions_ul = card.querySelector('ul');
        // Get the model name and type
        const model_name = card_div.getAttribute('data-sort-name');
        const model_type = resourceTypeFromId(parent_div.id).valueOf();
        // Override the replace preview button
        const replace_action = `onclick="sdmmReplacePreview(event, '${model_type}', '${model_name}')"`;
        actions_ul.innerHTML = `<a href="#" title="Use generated image as preview" ${replace_action}></a>`;
        // Create the link to the resource page
        const resource_action = `onclick="sdmmGoToResource(event, '${model_type}', '${model_name}')"`;
        actions_ul.innerHTML += `<a href="#" title="Go to resource" class="resource" ${resource_action}></a>`;
    }
}
/** Replace the preview image of a model with the generated image */
function sdmmReplacePreview(event, model_type, model_name) {
    // Prevent the default action of the click event
    event.stopPropagation();
    event.preventDefault();
    // Get current tab
    let current_tab = get_uiCurrentTab().innerText.trim();
    // Get the gallery element
    const gallery = getElements(`#${current_tab}_gallery button > img`);
    if (gallery.length == 0)
        return;
    // Get the selected gallery index
    let index = selected_gallery_index();
    if (index == -1)
        index = 0;
    // Create query string and encode it
    const type = model_type.toUpperCase();
    const filename = encodeURIComponent(model_name);
    const image_path = encodeURIComponent(gallery[index].src.split('/file=')[1]);
    const query_string = `?type=${type}&filename=${filename}&image=${image_path}`;
    // Send the request and refresh the thumbnails
    fetch(origin + `/sd-mm/add-image/${query_string}`, { method: 'POST' });
    getElement(`#${current_tab}_extra_refresh`).click();
    // Refresh the tab and home menu
    refreshTab(ResourceType[type]);
    refreshHomeMenu();
}
/** Open the resource page when clicking on the resource action button */
function sdmmGoToResource(event, model_type, model_name) {
    // Prevent the default action of the click event
    event.stopPropagation();
    event.preventDefault();
    // Get the search input
    const search_input = getElement(`#sd_mm_search_${model_type} textarea`);
    // Get all the tab buttons
    const nav_div = getElement('#tab_sd_model_manager .tab-nav');
    const tab_buttons = nav_div.querySelectorAll('button');
    for (const button of tab_buttons) {
        if (button.innerText.trim().toLowerCase() == model_type.toLowerCase()) {
            // Select the model tab
            button.click();
            // Clear the search input if it is not empty
            if (search_input.value != '') {
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
function sdmmZoomImage(event) {
    // Get the image that was clicked and create an overlay div
    const image = event.target;
    // Create the overlay div
    const overlay = document.createElement('div');
    overlay.onclick = overlay.remove;
    overlay.id = 'sd-mm-full-screen-overlay';
    // Set the image as the background of the overlay div
    overlay.innerHTML = `<img src="${image.src}">`;
    // Append the overlay div to the body
    document.body.appendChild(overlay);
}
/** Splits an image information string into a list of fields */
function split_info(info) {
    const fields = [];
    // Split the info string into lines
    const lines = info.split('<br>');
    // Add the prompt field
    fields.push({ name: 'Prompt', value: '' });
    // Iterate over the lines
    for (const line of lines) {
        for (const field of line.split(',')) {
            // Trim and skip empty fields
            const trimmed_field = field.trim();
            if (trimmed_field == '')
                continue;
            // Try to parse the field name and value
            const match = trimmed_field.match(/^([\w ]+): ([^,]+)/);
            if (match) {
                // If the regex matched, then the field is valid
                const name = match[1].trim();
                const value = match[2].trim();
                fields.push({ name, value });
            }
            else {
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
function build_info_html(info) {
    let field_count = 0;
    // Get the fields from the info string
    const fields = split_info(info);
    // Build the html container for the info
    let html = '<div class="sd-mm-model-info-container">\n';
    // Function to close last row
    function close_row() {
        if (field_count > 0) {
            html += '    </div>\n';
            field_count = 0;
        }
    }
    // Iterate over the fields
    for (const field of fields) {
        const is_normal_field = !field.name.match(/(^| )prompt/i);
        // Close row when there is more than one field
        if (field_count > 1)
            close_row();
        // Only normal fields are added to the row
        if (is_normal_field) {
            if (field_count == 0)
                html += '<div class="row">\n';
            html += '    <div class="field">\n';
            field_count++;
        }
        // Prompt fields are added to a vertical field
        else {
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
function sdmmShowInfo(info) {
    // Create the overlay div
    const overlay = document.createElement('div');
    overlay.onclick = overlay.remove;
    overlay.id = 'sd-mm-full-screen-overlay';
    // Build the html for the image info
    overlay.innerHTML = build_info_html(info);
    // Avoid closing the overlay when clicking on the info container
    const info_container = overlay.querySelector('.sd-mm-model-info-container');
    info_container.onclick = (event) => { event.preventDefault(); event.stopPropagation(); };
    // Append the overlay div to the body
    document.body.appendChild(overlay);
}
/** API call to set the preview image of a model */
function sdmmSetPreview(type, filename, index) {
    // Create query string and encode it
    filename = encodeURIComponent(filename);
    const query_string = `?type=${type}&filename=${filename}&index=${index}`;
    // Send the request and refresh the tab
    fetch(origin + `/sd-mm/set-preview${query_string}`, { method: 'POST' });
    refreshTab(ResourceType[type]);
    refreshHomeMenu(500);
}
/** API call to delete an image of a model */
function sdmmDeleteImage(type, filename, index) {
    // Create query string and encode it
    filename = encodeURIComponent(filename);
    const query_string = `?type=${type}&filename=${filename}&index=${index}`;
    // Send the request and refresh the tab
    fetch(origin + `/sd-mm/delete-image/${query_string}`, { method: 'POST' });
    refreshTab(ResourceType[type]);
    refreshHomeMenu(500);
}
/** Send the image to the txt2img tab */
function sdmmSendToTxt2Img(type, filename, index) {
    // Get the request and info textboxes
    const request_input = getElement('#sd_mm_txt2img_request textarea');
    const info_textbox = getElement('#sd_mm_txt2img_info textarea');
    // Set the request input value and trigger the input event
    request_input.value = `${type}/${filename}/${index}`;
    request_input.dispatchEvent(new Event('input'));
    // The info textbox will be filled when the request is done
    const interval = setInterval(function () {
        if (info_textbox.value != '') {
            // Trigger the send button and clear the info textbox
            triggerButton('#sd_mm_txt2img_send');
            info_textbox.value = '';
            clearInterval(interval);
        }
    }, 200);
}
/** Trigger the image input to add an image */
function sdmmTriggerImageInput(type) {
    // Get the image input
    const image_input = getElement(`#sd_mm_image_input_${type.toLowerCase()} input`);
    // Clear the input after selecting an image
    image_input.addEventListener('change', function () {
        // Delay the click event to make sure the image is submitted
        setTimeout(() => triggerButton(`#sd_mm_image_input_${type.toLowerCase()} button`), 500);
    });
    // Click the image input
    image_input.click();
}
onUiLoaded(function () {
    // Home tab button events
    assignWaitForValueChange('#sd_mm_scan_models_button', 'Update Scans', refreshAllTabs);
    assignWaitForValueChange('#sd_mm_remove_nsfw_previews_button', 'IDLE', refreshAllTabs);
    assignWaitForValueChange('#sd_mm_fix_missing_previews_button', 'IDLE', refreshAllTabs);
    assignWaitForValueChange('#sd_mm_generate_markdown_button', 'Regenerate Markdown Files', refreshAllTabs);
    handleDownloadButton('#sd_mm_download_images_button');
    handleDownloadButton('#sd_mm_download_vaes_button');
    handleDownloadButton('#sd_mm_download_model_button');
    // Download manager button events
    assignButtonAction('#sd_mm_download_manager_stop', hideDownloadManager);
    // Model tabs button events
    for (const key of Object.keys(ResourceType)) {
        handleTabDownloadImagesButton(ResourceType[key]);
        handleTabDownloadVaeButton(ResourceType[key]);
        handleTabDownloadLatestButton(ResourceType[key]);
        handleTabDeleteModelButton(ResourceType[key]);
    }
    refreshAllTabs(500);
});
onAfterUiUpdate(function () {
    findExtensionTabButton();
    for (const key of Object.keys(ResourceType))
        addSearchTriggerToDataframe(ResourceType[key]);
    for (const key of Object.keys(ExtraTabs))
        addResourceToModelCards(ExtraTabs[key]);
});
