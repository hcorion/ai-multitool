"use strict";
document.addEventListener('DOMContentLoaded', () => {
    $('#loading-spinner').hide();
    $('#prompt-form').on('submit', (event) => {
        event.preventDefault();
        const formData = $('#prompt-form').serialize();
        $('#loading-spinner').show();
        $.ajax({
            type: 'POST',
            url: '/',
            data: formData,
            success: (response) => {
                $('#result-section').html(response);
                addEventListenerToElement("generatedImage", "click", openGenModal);
                addEventListenerToElement("generatedImageClose", "click", closeGenModal);
                $('#loading-spinner').hide();
            }
        });
    });
    // Assigning event listeners
    addEventListenerToElement("generationTab", "click", handleTabClick);
    addEventListenerToElement("gridViewTab", "click", handleTabClick);
    addEventListenerToElement("style", "input", updateStyleDescription);
    addEventListenerToElement("prompt", "input", updateCharacterCount);
    // Grid buttons
    addEventListenerToElement("firstGrid", "click", firstGrid);
    addEventListenerToElement("previousGrid", "click", previousGrid);
    addEventListenerToElement("nextGrid", "click", nextGrid);
    addEventListenerToElement("lastGrid", "click", lastGrid);
    // Grid Modal Buttons
    addEventListenerToElement("grid-image-close", "click", closeGridModal);
    document.getElementById("generationTab").click();
});
// Function to add an event listener to an element
function addEventListenerToElement(elementId, eventType, handler) {
    const element = document.getElementById(elementId);
    if (element) {
        element.addEventListener(eventType, handler);
    }
    else {
        console.warn(`Element with ID '${elementId}' not found.`);
    }
}
// Event Handlers
function handleTabClick(evt) {
    const element = evt.target;
    const elementId = element.id;
    const tabMap = {
        "generationTab": "Generation",
        "gridViewTab": "GridView"
    };
    if (tabMap[elementId]) {
        openTab(evt, tabMap[elementId]);
    }
}
function updateCharacterCount() {
    const promptInput = document.getElementById("prompt");
    const charCount = promptInput.value.length;
    const charCountDisplay = document.getElementById("charCount");
    charCountDisplay.textContent = `${charCount} / 4000`;
}
function updateStyleDescription() {
    const styleInput = document.getElementById("style");
    const currentStyle = styleInput.value;
    const styleDescriptionDisplay = document.getElementById("styleDescription");
    if (currentStyle === "vivid") {
        styleDescriptionDisplay.textContent = "(Vivid causes the model to lean towards generating hyper-real and dramatic images)";
    }
    else if (currentStyle === "natural") {
        styleDescriptionDisplay.textContent = "(Natural causes the model to produce more natural, less hyper-real looking images)";
    }
}
function openTab(evt, tabName) {
    const tabcontent = Array.from(document.getElementsByClassName("tabcontent"));
    tabcontent.forEach(element => element.style.display = "none");
    const tablinks = Array.from(document.getElementsByClassName("tablinks"));
    tablinks.forEach(element => element.className = element.className.replace(" active", ""));
    const tab = document.getElementById(tabName);
    tab.style.display = "block";
    evt.currentTarget.className += " active";
    if (tabName === "GridView") {
        gridTabLoaded();
    }
}
let currentPage = 0;
let totalPages = -1;
function gridTabLoaded() {
    $.get('/get-total-pages', (data) => {
        totalPages = parseInt(data, 10);
        loadImages(currentPage);
    });
}
function loadImages(page) {
    $.getJSON(`/get-images/${page}`, (data) => {
        const grid = $('.image-grid');
        grid.empty(); // Clear existing images
        data.forEach((image) => {
            const imgElement = $('<img>').attr('src', image).attr('id', "gridImage");
            imgElement.on("click", openGridModal);
            grid.append(imgElement);
        });
        document.getElementsByTagName;
        document.getElementById("gridPageNum").textContent = `Page ${page + 1}/${totalPages + 1}`;
    });
}
function firstGrid() {
    currentPage = 0;
    loadImages(currentPage);
}
function nextGrid() {
    if (currentPage < totalPages) {
        currentPage += 1;
        loadImages(currentPage);
    }
}
function previousGrid() {
    if (currentPage > 0) {
        currentPage -= 1;
        loadImages(currentPage);
    }
}
function lastGrid() {
    currentPage = totalPages;
    loadImages(currentPage);
}
function openGenModal(evt) {
    const src = evt.currentTarget.src;
    document.getElementById('image-modal').style.display = "block";
    document.getElementById('modal-image').src = src;
    document.getElementById('image-modal').addEventListener('wheel', (event) => {
        event.preventDefault(); // Prevent background scrolling when the    modal is open
    });
    document.getElementById('modal-image').addEventListener('wheel', (event) => {
        const img = event.target;
        const scaleIncrement = 0.1;
        const currentScale = img.style.transform.match(/scale\(([^)]+)\)/);
        let scale = currentScale ? parseFloat(currentScale[1]) : 1;
        if (event.deltaY < 0) {
            scale += scaleIncrement; // Zoom in
        }
        else {
            scale -= scaleIncrement; // Zoom out
        }
        scale = Math.max(1, Math.min(scale, 5)); // Adjust min and max scale as needed
        img.style.transform = `scale(${scale})`;
    });
}
function openGridModal(evt) {
    var _a;
    const filePath = evt.currentTarget.src;
    document.getElementById('grid-image-modal').style.display = "block";
    const thumbFileName = filePath.split('/').pop();
    const pathDir = filePath.slice(0, -((_a = thumbFileName === null || thumbFileName === void 0 ? void 0 : thumbFileName.length) !== null && _a !== void 0 ? _a : 0));
    const fileName = thumbFileName === null || thumbFileName === void 0 ? void 0 : thumbFileName.slice(0, -(".thumb.jpg".length)).concat(".png");
    document.getElementById('grid-modal-image').src = pathDir + fileName;
    $.getJSON('/get-image-metadata/' + fileName, function (metadata) {
        var metadataDiv = document.getElementById('grid-info-panel');
        metadataDiv.innerHTML = ''; // Clear previous metadata
        for (var key in metadata) {
            // <div class="info-item"><span>Prompt:</span><span id="prompt-value"></span></div>
            var infoItem = document.createElement('div');
            infoItem.className = "info-item";
            infoItem.textContent = key + ":";
            metadataDiv.appendChild(infoItem);
            var infoValue = document.createElement('div');
            infoValue.className = "prompt-value";
            infoValue.textContent = metadata[key];
            metadataDiv.appendChild(infoValue);
        }
    });
}
function closeGenModal() {
    document.getElementById('image-modal').style.display = "none";
}
function closeGridModal() {
    document.getElementById('grid-image-modal').style.display = "none";
}
