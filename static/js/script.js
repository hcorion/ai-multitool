"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const jquery_1 = __importDefault(require("jquery"));
document.addEventListener('DOMContentLoaded', () => {
    (0, jquery_1.default)('#prompt-form').on('submit', (event) => {
        event.preventDefault();
        const formData = (0, jquery_1.default)('#prompt-form').serialize();
        jquery_1.default.ajax({
            type: 'POST',
            url: '/',
            data: formData,
            success: (response) => {
                (0, jquery_1.default)('#result-section').html(response);
            }
        });
    });
});
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
// Set the default open tab (Generation tab)
document.getElementById("defaultOpen").click();
let currentPage = 0;
let totalPages = -1;
function gridTabLoaded() {
    jquery_1.default.get('/get-total-pages', (data) => {
        totalPages = parseInt(data, 10);
        loadImages(currentPage);
    });
}
function loadImages(page) {
    jquery_1.default.getJSON(`/get-images/${page}`, (data) => {
        const grid = (0, jquery_1.default)('.image-grid');
        grid.empty(); // Clear existing images
        data.forEach((image) => {
            const imgElement = (0, jquery_1.default)('<img>').attr('src', image);
            grid.append(imgElement);
        });
        document.getElementById("gridPageNum").textContent = `Page ${page + 1}/${totalPages + 1}`;
    });
}
function nextGrid() {
    currentPage += 1;
    loadImages(currentPage);
}
function previousGrid() {
    if (currentPage > 0) {
        currentPage -= 1;
        loadImages(currentPage);
    }
}
function openModal(src) {
    document.getElementById('image-modal').style.display = "block";
    document.getElementById('modal-image').src = src;
}
function closeModal() {
    document.getElementById('image-modal').style.display = "none";
}
document.getElementById('image-modal').addEventListener('wheel', (event) => {
    event.preventDefault(); // Prevent background scrolling when the modal is open
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
