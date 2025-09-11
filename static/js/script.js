import * as utils from "./utils.js";
import * as chat from "./chat.js";
import { InpaintingMaskCanvas } from "./inpainting/inpainting-mask-canvas.js";
document.addEventListener("DOMContentLoaded", () => {
    $("#loading-spinner").hide();
    $("#prompt-form").on("submit", (event) => {
        event.preventDefault();
        const formData = $("#prompt-form").serialize();
        $("#loading-spinner").show();
        // Check if we should use the new /image endpoint or legacy / endpoint
        const useNewEndpoint = shouldUseNewImageEndpoint();
        if (useNewEndpoint) {
            // Use new /image endpoint with JSON response
            $.ajax({
                type: "POST",
                url: "/image",
                data: formData,
                dataType: "json",
                success: (response) => {
                    if (response.success) {
                        renderImageResult(response);
                    }
                    else {
                        renderImageError(response.error_message || "Unknown error occurred");
                    }
                    $("#loading-spinner").hide();
                },
                error: (xhr) => {
                    let errorMessage = "An error occurred while generating the image.";
                    // Try to extract detailed error information
                    if (xhr.responseJSON) {
                        if (xhr.responseJSON.error_message) {
                            errorMessage = xhr.responseJSON.error_message;
                        }
                        else if (xhr.responseJSON.error) {
                            errorMessage = xhr.responseJSON.error;
                        }
                        // Add additional error details if available
                        if (xhr.responseJSON.error_type) {
                            errorMessage += ` (${xhr.responseJSON.error_type})`;
                        }
                    }
                    else if (xhr.responseText) {
                        // Try to parse error from response text
                        try {
                            const errorData = JSON.parse(xhr.responseText);
                            if (errorData.error_message) {
                                errorMessage = errorData.error_message;
                            }
                            else if (errorData.error) {
                                errorMessage = errorData.error;
                            }
                        }
                        catch (e) {
                            // If parsing fails, include the raw response text for debugging
                            errorMessage += ` (Status: ${xhr.status}, Response: ${xhr.responseText.substring(0, 200)})`;
                        }
                    }
                    else {
                        errorMessage += ` (HTTP ${xhr.status}: ${xhr.statusText})`;
                    }
                    console.error('Image generation error:', {
                        status: xhr.status,
                        statusText: xhr.statusText,
                        responseJSON: xhr.responseJSON,
                        responseText: xhr.responseText
                    });
                    renderImageError(errorMessage);
                    $("#loading-spinner").hide();
                }
            });
        }
        else {
            // Use legacy / endpoint with HTML response
            $.ajax({
                type: "POST",
                url: "/",
                data: formData,
                success: (response) => {
                    $("#result-section").html(response);
                    addEventListenerToElement("generatedImage", "click", openGenModal);
                    addEventListenerToElement("generatedImageClose", "click", closeGenModal);
                    $("#loading-spinner").hide();
                },
                error: () => {
                    renderImageError("An error occurred while generating the image with legacy endpoint.");
                    $("#loading-spinner").hide();
                }
            });
        }
    });
    // Image gen elements
    addEventListenerToElement("provider", "change", providerChanged);
    addEventListenerToElement("model", "change", modelButtonChanged);
    // Assigning event listeners
    addEventListenerToElement("generationTab", "click", handleTabClick);
    addEventListenerToElement("gridViewTab", "click", handleTabClick);
    addEventListenerToElement("chatTab", "click", handleTabClick);
    addEventListenerToElement("promptsTab", "click", handleTabClick);
    addEventListenerToElement("prompt", "input", updateCharacterCount);
    // Grid buttons
    addEventListenerToElement("firstGrid", "click", firstGrid);
    addEventListenerToElement("previousGrid", "click", previousGrid);
    addEventListenerToElement("nextGrid", "click", nextGrid);
    addEventListenerToElement("lastGrid", "click", lastGrid);
    // Chat buttons
    addEventListenerToElement("send-chat", "click", sendChatMessage);
    // Reasoning modal buttons
    addEventListenerToElement("reasoning-modal-close", "click", hideReasoningModalFromScript);
    // Grid Modal Buttons
    addEventListenerToElement("grid-image-close", "click", closeGridModal);
    // Inpainting buttons
    addEventListenerToElement("clear-inpainting-btn", "click", clearInpaintingMode);
    addEventListenerToElement("grid-prev", "click", previousGridImage);
    addEventListenerToElement("grid-next", "click", nextGridImage);
    addEventListenerToElement("advanced-toggle", "click", toggleShowAdvanced);
    // Add keyboard and click-outside handlers for reasoning modal
    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape") {
            const modal = document.getElementById("reasoning-modal");
            if (modal && modal.style.display === "block") {
                hideReasoningModalFromScript();
            }
        }
    });
    // Click outside modal to close
    document.addEventListener("click", (e) => {
        const modal = document.getElementById("reasoning-modal");
        if (modal && modal.style.display === "block" && e.target === modal) {
            hideReasoningModalFromScript();
        }
    });
    addEventListenerToElement("advanced-generate-grid", "change", toggleAdvancedInput);
    addEventListener("keydown", keyDownEvent);
    document.getElementById("generationTab").click();
    // Character prompt event listeners
    addEventListenerToElement("add-character-btn", "click", addCharacterPrompt);
    // Prompt Files modal event listeners
    addEventListenerToElement("create-prompt-file-btn", "click", () => showPromptFileModal("create"));
    addEventListenerToElement("prompt-modal-close", "click", hidePromptFileModal);
    addEventListenerToElement("prompt-file-cancel", "click", hidePromptFileModal);
    addEventListenerToElement("prompt-file-save", "click", savePromptFile);
    // Just refresh the image gen provider
    providerChanged();
});
function keyDownEvent(evt) {
    if (evt.code == "ArrowRight") {
        nextGridImage();
    }
    else if (evt.code == "ArrowLeft") {
        previousGridImage();
    }
}
// Helper functions for new image API
function shouldUseNewImageEndpoint() {
    // For now, always use the new endpoint for basic generation
    // In the future, this could check for advanced features like grid generation
    const advancedGrid = $("#advanced-generate-grid").is(":checked");
    return !advancedGrid; // Use new endpoint unless advanced grid is enabled
}
function renderImageResult(response) {
    // Extract character prompts from metadata
    let characterPromptsHtml = '';
    if (response.metadata) {
        const characterPrompts = [];
        for (const [key, value] of Object.entries(response.metadata)) {
            // Look for processed character prompt metadata (revised prompts)
            const match = key.match(/^Character (\d+) Processed Prompt$/);
            if (match && value && typeof value === 'string') {
                characterPrompts.push(value);
            }
        }
        if (characterPrompts.length > 0) {
            characterPromptsHtml = `<p><strong>Character Prompts:</strong> ${characterPrompts.join(', ')}</p>`;
        }
    }
    const resultHtml = `
        <div class="result-container">
            <div class="image-container">
                <img id="generatedImage" src="${response.image_path}" alt="Generated Image" class="generated-image">
            </div>
            <div class="result-info">
                <h3>Generated Image</h3>
                ${response.revised_prompt ? `<p><strong>Revised Prompt:</strong> ${response.revised_prompt}</p>` : ''}
                ${characterPromptsHtml}
                <p><strong>Provider:</strong> ${response.provider}</p>
                <p><strong>Operation:</strong> ${response.operation}</p>
                <p><strong>Image Name:</strong> ${response.image_name}</p>
                
                <div class="image-actions" style="margin-top: 15px;">
                    <button id="editMaskBtn" class="edit-mask-btn">
                        🎨 Edit Mask for Inpainting
                    </button>
                </div>
            </div>
        </div>
            <div id="image-modal" style="display:none" class="modal">
            <span id="generatedImageClose" class="close">&times;</span>
            <img class="modal-content" id="modal-image">
        </div>
    `;
    $("#result-section").html(resultHtml);
    // Add event listeners for the new elements
    addEventListenerToElement("generatedImage", "click", openGenModal);
    addEventListenerToElement("generatedImageClose", "click", closeGenModal);
    // Add event listener for inpaint button with prompt extraction
    const editMaskBtn = document.getElementById("editMaskBtn");
    if (editMaskBtn) {
        editMaskBtn.addEventListener("click", () => {
            // Extract prompts from the response metadata
            const { prompt, negativePrompt, characterPrompts } = extractPromptsFromMetadata(response.metadata || {});
            // Open inpainting mask canvas with prompts
            if (response.image_path) {
                openInpaintingMaskCanvas(response.image_path, prompt, negativePrompt, characterPrompts);
            }
        });
    }
}
function renderImageError(errorMessage) {
    const errorHtml = `
        <div class="error-dialog">
            <span class="error-icon">&#9888;</span>
            <span class="error-text">${errorMessage}</span>
        </div>
    `;
    $("#result-section").html(errorHtml);
}
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
        generationTab: "Generation",
        gridViewTab: "GridView",
        chatTab: "Chat",
        promptsTab: "PromptFiles",
    };
    if (tabMap[elementId]) {
        openTab(evt, tabMap[elementId]);
    }
}
function providerChanged() {
    const selection = document.getElementById("provider");
    if (selection.value == "openai") {
        $(".stabilityai").hide();
        $(".novelai").hide();
        $(".openai").show();
        hideCharacterPromptInterface();
        document.getElementById("size").selectedIndex = 0;
    }
    else if ((selection.value == "stabilityai")) {
        $(".openai").hide();
        $(".novelai").hide();
        $(".stabilityai").show();
        hideCharacterPromptInterface();
        modelChanged(selection.value);
    }
    else if ((selection.value == "novelai")) {
        $(".openai").hide();
        $(".stabilityai").hide();
        $(".novelai").show();
        showCharacterPromptInterface();
        // This is ugly, but index #3 is where the novelai size options start
        document.getElementById("size").selectedIndex = 3;
        modelChanged(selection.value);
    }
    else {
        throw new Error(`Tried to switch to unsupported provider ${selection}`);
    }
}
function modelButtonChanged() {
    const provider = document.getElementById("provider");
    modelChanged(provider.value);
}
function modelChanged(provider) {
    if (provider == "stabilityai") {
        const selection = document.getElementById("model");
        if (selection && !selection.hidden) {
            if (selection.value == "sd3-turbo") {
                $(".negativeprompt").hide();
            }
            else if ((selection.value = "sd3")) {
                $(".negativeprompt").show();
            }
            else {
                throw new Error(`Tried to switch to unsupported SD3 model ${selection}`);
            }
        }
    }
    else if (provider == "novelai") {
        $(".negativeprompt").show();
    }
    else if (provider == "openai") {
        $(".negativeprompt").hide();
    }
    else {
        throw new Error(`modelChanged called with unsupported provider ${provider}`);
    }
}
function updateCharacterCount() {
    const promptInput = document.getElementById("prompt");
    const charCount = promptInput.value.length;
    const charCountDisplay = document.getElementById("charCount");
    charCountDisplay.textContent = `${charCount} / 4000`;
}
function openTab(evt, tabName) {
    const tabcontent = Array.from(document.getElementsByClassName("tabcontent"));
    tabcontent.forEach((element) => (element.style.display = "none"));
    const tablinks = Array.from(document.getElementsByClassName("tablinks"));
    tablinks.forEach((element) => (element.className = element.className.replace(" active", "")));
    const tab = document.getElementById(tabName);
    tab.style.display = "block";
    evt.currentTarget.className += " active";
    switch (tabName) {
        case "GridView":
            gridTabLoaded();
            break;
        case "Chat":
            chatTabLoaded();
            break;
        case "PromptFiles":
            promptFilesTabLoaded();
            break;
        default:
            break;
    }
    if (tabName === "") {
    }
}
let currentPage = 1;
let totalPages = -1;
function gridTabLoaded() {
    $.get("/get-total-pages", (data) => {
        totalPages = parseInt(data, 10);
        loadImages(currentPage);
    });
}
/* global variable to keep track of the current grid image index */
let currentGridImageIndex = 0;
function loadImages(page) {
    $.getJSON(`/get-images/${page}`, (data) => {
        const grid = $(".image-grid");
        grid.empty(); // Clear existing images
        // For each image in “data”, attach an index so we can navigate later.
        data.forEach((image, index) => {
            const aspectRatioBox = $("<div>").addClass("aspect-ratio-box");
            const imgElement = $("<img>")
                .attr("src", image)
                .attr("id", "gridImage")
                .attr("data-index", index.toString());
            imgElement.on("click", openGridModal);
            aspectRatioBox.append(imgElement);
            grid.append(aspectRatioBox);
        });
        $("#gridPageNum").text(`Page ${page}/${totalPages}`);
    });
}
function firstGrid() {
    currentPage = 1;
    loadImages(currentPage);
}
function nextGrid() {
    if (currentPage < totalPages) {
        currentPage += 1;
        loadImages(currentPage);
    }
}
function previousGrid() {
    if (currentPage > 1) {
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
    document.getElementById("image-modal").style.display = "block";
    document.getElementById("modal-image").src = src;
    document.getElementById("image-modal").addEventListener("wheel", (event) => {
        event.preventDefault(); // Prevent background scrolling when the modal is open
    });
    document.getElementById("modal-image").addEventListener("wheel", (event) => {
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
    // Get the clicked image and determine its index
    const clickedImg = evt.currentTarget;
    const indexAttr = clickedImg.getAttribute("data-index");
    currentGridImageIndex = indexAttr ? parseInt(indexAttr, 10) : 0;
    updateGridModalImage();
    $("#grid-image-modal").show();
}
/**
 * Returns processedText with <span class="highlight">...</span> wrapped around tokens
 * that differ from baseText. Uses word-level LCS and prefers earlier matches on ties
 * to avoid mis-highlighting repeated words. Adjacent changed tokens (and separators
 * between them) are merged into a single highlight span.
 */
function highlightTextDifferences(baseText, processedText) {
    const WORD_RE = hasUnicodePropertyEscapes()
        ? /[\p{L}\p{N}_]+/gu
        : /[A-Za-z0-9_]+/g;
    const baseWords = extractWords(baseText, WORD_RE);
    const processedWords = extractWords(processedText, WORD_RE);
    // Indices in processedWords that are kept (unchanged)
    const keptProcessedIdx = lcsKeepIndicesPreferLeft(baseWords, processedWords);
    const OPEN = '<span class="diff-highlight">';
    const CLOSE = '</span>';
    let result = '';
    let lastIndex = 0;
    let processedWordIdx = 0;
    let inHighlight = false;
    for (const m of matchAll(processedText, WORD_RE)) {
        const start = m.index;
        const end = start + m[0].length;
        const sep = processedText.slice(lastIndex, start);
        const isKept = keptProcessedIdx.has(processedWordIdx);
        if (inHighlight) {
            if (isKept) {
                // Close current highlight; separator belongs outside; then the kept token
                result += CLOSE;
                inHighlight = false;
                result += sep + m[0];
            }
            else {
                // Continue the same highlight; separator goes inside to merge adjacent changes
                result += sep + m[0];
            }
        }
        else {
            if (isKept) {
                result += sep + m[0];
            }
            else {
                // Start a new highlight span
                result += sep + OPEN + m[0];
                inHighlight = true;
            }
        }
        processedWordIdx++;
        lastIndex = end;
    }
    if (inHighlight)
        result += CLOSE;
    if (lastIndex < processedText.length)
        result += processedText.slice(lastIndex);
    return result;
    // ----- helpers -----
    function extractWords(text, re) {
        const words = [];
        for (const m of matchAll(text, re))
            words.push(m[0]);
        return words;
    }
    function hasUnicodePropertyEscapes() {
        try {
            new RegExp('\\p{L}', 'u');
            return true;
        }
        catch {
            return false;
        }
    }
    // Iterates matches like String.prototype.matchAll
    function* matchAll(text, re) {
        const flags = re.flags.includes('g') ? re.flags : re.flags + 'g';
        const rx = new RegExp(re.source, flags);
        let m;
        while ((m = rx.exec(text)) !== null) {
            yield m;
            if (m[0].length === 0)
                rx.lastIndex++;
        }
    }
    /**
     * LCS backtracking that prefers moving LEFT on ties, i.e., it keeps earlier
     * indices in the processed sequence. This avoids matching the later duplicate
     * (e.g., the "example" inside a replacement) over the earlier unchanged one.
     */
    function lcsKeepIndicesPreferLeft(a, b) {
        const n = a.length, m = b.length;
        const dp = Array.from({ length: n + 1 }, () => new Array(m + 1).fill(0));
        for (let i = 1; i <= n; i++) {
            for (let j = 1; j <= m; j++) {
                if (a[i - 1] === b[j - 1]) {
                    dp[i][j] = dp[i - 1][j - 1] + 1;
                }
                else {
                    const up = dp[i - 1][j];
                    const left = dp[i][j - 1];
                    dp[i][j] = up > left ? up : left; // just max; tie handled in backtrack
                }
            }
        }
        const kept = new Set();
        let i = n, j = m;
        while (i > 0 && j > 0) {
            if (a[i - 1] === b[j - 1]) {
                kept.add(j - 1);
                i--;
                j--;
            }
            else if (dp[i - 1][j] > dp[i][j - 1]) {
                // Prefer LEFT when equal => choose UP only when strictly better
                i--;
            }
            else {
                j--;
            }
        }
        return kept;
    }
}
/**
 * Escapes HTML special characters to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
function updateGridModalImage() {
    // Get the list of grid images from the current grid DOM.
    const gridImages = $(".image-grid img");
    if (gridImages.length === 0) {
        console.warn("No grid images found.");
        return;
    }
    // Wrap-around logic.
    if (currentGridImageIndex < 0) {
        if (currentPage <= 1) {
            currentGridImageIndex = 0;
            return;
        }
        previousGrid();
        currentGridImageIndex = gridImages.length - 1;
    }
    else if (currentGridImageIndex >= gridImages.length) {
        if (currentPage >= totalPages) {
            currentGridImageIndex = gridImages.length - 1;
            return;
        }
        nextGrid();
        currentGridImageIndex = 0;
    }
    const newImgElement = gridImages.get(currentGridImageIndex);
    const filePath = newImgElement.src;
    const thumbFileName = filePath.split("/").pop();
    const pathDir = filePath.slice(0, -(thumbFileName?.length ?? 0));
    // This works with .thumb.png as well since we just trim the length regardless of the contents
    const fileName = thumbFileName?.slice(0, -".thumb.jpg".length).concat(".png");
    // Update the modal image.
    document.getElementById("grid-modal-image").src = pathDir + fileName;
    // Fetch and update the metadata.
    $.getJSON("/get-image-metadata/" + fileName, function (metadata) {
        const metadataDiv = document.getElementById("grid-info-panel");
        metadataDiv.innerHTML = ""; // Clear previous metadata
        // Process character prompts and main prompts to determine what to display
        const processedMetadata = {};
        const characterPromptData = {};
        const mainPromptData = {};
        // First pass: identify character prompts and compare base vs processed
        for (const key in metadata) {
            const characterMatch = key.match(/^Character (\d+) (Prompt|Negative)$/);
            const processedMatch = key.match(/^Character (\d+) Processed (Prompt|Negative)$/);
            const mainPromptMatch = key.match(/^(Prompt|Negative Prompt)$/);
            const processedMainMatch = key.match(/^Revised (Prompt|Negative Prompt)$/);
            if (characterMatch) {
                const charNum = characterMatch[1];
                const promptType = characterMatch[2];
                const baseKey = `Character ${charNum} ${promptType}`;
                const processedKey = `Character ${charNum} Processed ${promptType}`;
                const baseValue = metadata[baseKey] || "";
                const processedValue = metadata[processedKey] || "";
                // If both exist, compare them
                if (baseValue && processedValue) {
                    const isDifferent = baseValue !== processedValue;
                    characterPromptData[baseKey] = {
                        base: baseValue,
                        processed: processedValue,
                        isDifferent: isDifferent
                    };
                    if (isDifferent) {
                        // Show both base and processed with different styling
                        processedMetadata[baseKey] = baseValue;
                        processedMetadata[processedKey] = processedValue;
                    }
                    else {
                        // Show only the base prompt
                        processedMetadata[baseKey] = baseValue;
                    }
                }
                else if (baseValue) {
                    // Only base exists
                    processedMetadata[baseKey] = baseValue;
                }
                else if (processedValue) {
                    // Only processed exists (shouldn't happen, but handle it)
                    processedMetadata[processedKey] = processedValue;
                }
            }
            else if (mainPromptMatch) {
                // Handle main prompts (Prompt, Negative Prompt)
                const promptType = mainPromptMatch[1];
                const baseKey = promptType;
                const processedKey = `Revised ${promptType}`;
                const baseValue = metadata[baseKey] || "";
                const processedValue = metadata[processedKey] || "";
                // If both exist, compare them
                if (baseValue && processedValue) {
                    const isDifferent = baseValue !== processedValue;
                    mainPromptData[baseKey] = {
                        base: baseValue,
                        processed: processedValue,
                        isDifferent: isDifferent
                    };
                    if (isDifferent) {
                        // Show both base and processed with different styling
                        processedMetadata[baseKey] = baseValue;
                        processedMetadata[processedKey] = processedValue;
                    }
                    else {
                        // Show only the base prompt
                        processedMetadata[baseKey] = baseValue;
                    }
                }
                else if (baseValue) {
                    // Only base exists
                    processedMetadata[baseKey] = baseValue;
                }
                else if (processedValue) {
                    // Only processed exists (shouldn't happen, but handle it)
                    processedMetadata[processedKey] = processedValue;
                }
            }
            else if (!processedMatch && !processedMainMatch) {
                // Non-prompt metadata, add as-is
                processedMetadata[key] = metadata[key];
            }
            // Skip processed prompts in this pass as they're handled above
        }
        // Display each metadata key–value pair.
        for (const key in processedMetadata) {
            const infoItem = document.createElement("div");
            infoItem.className = "info-item";
            // Add special styling for character prompts
            if (key.match(/^Character \d+ (Prompt|Negative|Processed Prompt|Processed Negative)$/)) {
                infoItem.classList.add("character-prompt-item");
            }
            infoItem.textContent = key + ":";
            metadataDiv.appendChild(infoItem);
            const infoValue = document.createElement("div");
            infoValue.className = "prompt-value";
            // Add special styling for character prompt values
            if (key.match(/^Character \d+ (Prompt|Negative|Processed Prompt|Processed Negative)$/)) {
                infoValue.classList.add("character-prompt-value");
                // Add additional styling for processed prompts when they differ from base
                if (key.match(/^Character \d+ Processed (Prompt|Negative)$/)) {
                    infoValue.classList.add("processed-prompt-value");
                    // Find the corresponding base prompt to highlight differences
                    const baseKey = key.replace(" Processed ", " ");
                    const basePromptData = characterPromptData[baseKey];
                    if (basePromptData && basePromptData.isDifferent) {
                        // Use diff highlighting for processed prompts
                        infoValue.innerHTML = highlightTextDifferences(basePromptData.base, basePromptData.processed);
                    }
                    else {
                        infoValue.textContent = processedMetadata[key];
                    }
                }
                else {
                    infoValue.textContent = processedMetadata[key];
                }
            }
            else if (key.match(/^Revised (Prompt|Negative Prompt)$/)) {
                // Handle main revised prompts
                infoValue.classList.add("character-prompt-value", "processed-prompt-value");
                // Find the corresponding base prompt to highlight differences
                const baseKey = key.replace("Revised ", "");
                const basePromptData = mainPromptData[baseKey];
                if (basePromptData && basePromptData.isDifferent) {
                    // Use diff highlighting for processed main prompts
                    infoValue.innerHTML = highlightTextDifferences(basePromptData.base, basePromptData.processed);
                }
                else {
                    infoValue.textContent = processedMetadata[key];
                }
            }
            else {
                infoValue.textContent = processedMetadata[key];
            }
            metadataDiv.appendChild(infoValue);
        }
        // Create button container for better layout
        let buttonContainer = document.getElementById("modal-button-container");
        if (!buttonContainer) {
            buttonContainer = document.createElement("div");
            buttonContainer.id = "modal-button-container";
            buttonContainer.className = "modal-button-container";
            metadataDiv.appendChild(buttonContainer);
        }
        // Create (or update) the "Copy Prompt" button.
        let copyPromptButton = document.getElementById("copy-prompt-btn");
        if (!copyPromptButton) {
            copyPromptButton = document.createElement("button");
            copyPromptButton.id = "copy-prompt-btn";
            copyPromptButton.textContent = "Copy Prompt";
            buttonContainer.appendChild(copyPromptButton);
        }
        // Create (or update) the "Inpaint" button.
        let inpaintButton = document.getElementById("inpaint-btn");
        if (!inpaintButton) {
            inpaintButton = document.createElement("button");
            inpaintButton.id = "inpaint-btn";
            inpaintButton.textContent = "Inpaint";
            inpaintButton.className = "inpaint-button";
            buttonContainer.appendChild(inpaintButton);
        }
        // Add listener (or rebind) for the copy action.
        copyPromptButton.onclick = () => {
            const promptTextarea = document.getElementById("prompt");
            const negativePromptTextarea = document.getElementById("negative_prompt");
            // Try various key cases in case the keys are not lowercase.
            const promptText = metadata["Prompt"];
            const negativePromptText = metadata["Negative Prompt"] || "";
            promptTextarea.value = promptText;
            negativePromptTextarea.value = negativePromptText;
            // Handle character prompt metadata if present
            // Extract character prompts from metadata and populate character interface when available
            const characterPrompts = [];
            for (const key in metadata) {
                const characterMatch = key.match(/^Character (\d+) Prompt$/);
                if (characterMatch) {
                    const charNum = parseInt(characterMatch[1]);
                    const negativeKey = `Character ${charNum} Negative`;
                    characterPrompts[charNum - 1] = {
                        positive: metadata[key],
                        negative: metadata[negativeKey] || ""
                    };
                }
            }
            // Store character prompts for when character interface becomes available
            // This will be used by the character prompt interface implementation
            if (characterPrompts.length > 0) {
                window.pendingCharacterPrompts = characterPrompts;
                console.log("Character prompts found in metadata:", characterPrompts);
                // If NovelAI is currently selected, populate immediately
                const provider = document.getElementById("provider");
                if (provider && provider.value === "novelai") {
                    populateCharacterPrompts(characterPrompts);
                    delete window.pendingCharacterPrompts;
                }
            }
            // Switch to the Generation tab.
            document.getElementById("generationTab")?.click();
        };
        // Add listener for the inpaint action.
        inpaintButton.onclick = () => {
            // Get the current image URL from the modal
            const modalImage = document.getElementById("grid-modal-image");
            const imageUrl = modalImage.src;
            // Extract prompts from the current metadata
            const { prompt, negativePrompt, characterPrompts } = extractPromptsFromMetadata(metadata);
            // Close the grid modal
            closeGridModal();
            // Open the inpainting mask canvas with the current image and prompts
            openInpaintingMaskCanvas(imageUrl, prompt, negativePrompt, characterPrompts);
        };
    });
}
function previousGridImage() {
    currentGridImageIndex -= 1;
    updateGridModalImage();
}
function nextGridImage() {
    currentGridImageIndex += 1;
    updateGridModalImage();
}
function closeGridModal() {
    $("#grid-image-modal").hide();
}
function closeGenModal() {
    document.getElementById("image-modal").style.display = "none";
}
/**
 * Opens the inpainting mask canvas for the given image
 * @param imageUrl - URL of the image to edit
 */
async function openInpaintingMaskCanvas(imageUrl, originalPrompt, originalNegativePrompt, originalCharacterPrompts) {
    const canvas = new InpaintingMaskCanvas({
        imageUrl: imageUrl,
        containerElement: document.body,
        onMaskComplete: async (maskDataUrl, maskFileId) => {
            console.log('Mask completed:', maskDataUrl);
            try {
                // Save the mask to the server and set up inpainting
                await setupInpaintingMode(imageUrl, maskDataUrl, maskFileId, originalPrompt, originalNegativePrompt, originalCharacterPrompts);
            }
            catch (error) {
                console.error('Failed to setup inpainting mode:', error);
                alert('Failed to setup inpainting mode. Please try again.');
            }
        },
        onCancel: () => {
            console.log('Mask editing cancelled');
        }
    });
    try {
        await canvas.show();
    }
    catch (error) {
        console.error('Failed to open inpainting mask canvas:', error);
    }
}
/**
 * Set up inpainting mode with the provided base image and mask
 */
async function setupInpaintingMode(baseImageUrl, maskDataUrl, maskFileId, originalPrompt, originalNegativePrompt, originalCharacterPrompts) {
    try {
        // Save the mask to the server
        const maskPath = await saveMaskToServer(maskDataUrl);
        // Extract the base image path from the URL
        const baseImagePath = extractImagePathFromUrl(baseImageUrl);
        // Show the inpainting section
        showInpaintingSection(baseImageUrl, maskDataUrl, baseImagePath, maskPath);
        // Copy original prompts to the form if provided
        if (originalPrompt) {
            copyPromptToForm(originalPrompt, originalNegativePrompt, originalCharacterPrompts);
        }
        // Switch to the generation tab if not already there
        const generationTab = document.getElementById('generationTab');
        if (generationTab) {
            generationTab.click();
        }
        // Scroll to the inpainting section
        const inpaintingSection = document.getElementById('inpainting-section');
        if (inpaintingSection) {
            inpaintingSection.scrollIntoView({ behavior: 'smooth' });
        }
        console.log('Inpainting mode setup complete');
    }
    catch (error) {
        console.error('Error setting up inpainting mode:', error);
        throw error;
    }
}
/**
 * Save mask data URL to server and return the server path
 */
async function saveMaskToServer(maskDataUrl) {
    try {
        console.log('Saving mask to server, data URL length:', maskDataUrl.length);
        const formData = new FormData();
        // Convert data URL to blob
        const response = await fetch(maskDataUrl);
        if (!response.ok) {
            throw new Error(`Failed to convert data URL to blob: ${response.status} ${response.statusText}`);
        }
        const blob = await response.blob();
        console.log('Converted to blob, size:', blob.size, 'type:', blob.type);
        formData.append('mask', blob, 'mask.png');
        const saveResponse = await fetch('/save-mask', {
            method: 'POST',
            body: formData
        });
        console.log('Save response status:', saveResponse.status, saveResponse.statusText);
        if (!saveResponse.ok) {
            const errorText = await saveResponse.text();
            console.error('Save mask error response:', errorText);
            throw new Error(`Failed to save mask to server: ${saveResponse.status} ${saveResponse.statusText} - ${errorText}`);
        }
        const result = await saveResponse.json();
        console.log('Mask saved successfully:', result);
        if (!result.success) {
            throw new Error(result.error || 'Unknown error saving mask');
        }
        return result.mask_path;
    }
    catch (error) {
        console.error('Error in saveMaskToServer:', error);
        throw error;
    }
}
/**
 * Extract image path from full URL
 */
function extractImagePathFromUrl(imageUrl) {
    // Extract the path part from URLs like /static/images/username/image.png
    const url = new URL(imageUrl, window.location.origin);
    // Remove leading slash to make it relative for Flask
    return url.pathname.startsWith('/') ? url.pathname.substring(1) : url.pathname;
}
/**
 * Show the inpainting section and populate it with image and mask data
 */
function showInpaintingSection(baseImageUrl, maskDataUrl, baseImagePath, maskPath) {
    const inpaintingSection = document.getElementById('inpainting-section');
    const imageNameSpan = document.getElementById('inpainting-image-name');
    const maskStatusSpan = document.getElementById('inpainting-mask-status');
    const basePreview = document.getElementById('inpainting-base-preview');
    const maskPreview = document.getElementById('inpainting-mask-preview');
    const baseImageInput = document.getElementById('inpainting-base-image');
    const maskPathInput = document.getElementById('inpainting-mask-path');
    const operationInput = document.getElementById('inpainting-operation');
    const submitBtn = document.getElementById('generate-submit-btn');
    if (inpaintingSection) {
        inpaintingSection.style.display = 'block';
    }
    if (imageNameSpan) {
        const imageName = baseImagePath.split('/').pop() || 'Unknown';
        imageNameSpan.textContent = imageName;
    }
    if (maskStatusSpan) {
        maskStatusSpan.textContent = 'Mask created successfully';
    }
    if (basePreview) {
        basePreview.src = baseImageUrl;
        basePreview.style.display = 'block';
    }
    if (maskPreview) {
        maskPreview.src = maskDataUrl;
        maskPreview.style.display = 'block';
    }
    if (baseImageInput) {
        baseImageInput.value = baseImagePath;
    }
    if (maskPathInput) {
        maskPathInput.value = maskPath;
    }
    if (operationInput) {
        operationInput.value = 'inpaint';
    }
    if (submitBtn) {
        submitBtn.value = 'Generate Inpainting';
        submitBtn.classList.add('inpainting-mode');
    }
}
/**
 * Extract prompts from image metadata for inpainting
 */
function extractPromptsFromMetadata(metadata) {
    let prompt;
    let negativePrompt;
    const characterPrompts = [];
    // Priority order for main prompt extraction:
    // 1. Original "Prompt" (user's input)
    // 2. "Revised Prompt" (AI-processed version)
    if (metadata['Prompt']) {
        prompt = metadata['Prompt'];
    }
    else if (metadata['Revised Prompt']) {
        prompt = metadata['Revised Prompt'];
    }
    // Priority order for main negative prompt:
    // 1. Original "Negative Prompt" (user's input)  
    // 2. "Revised Negative Prompt" (AI-processed version)
    if (metadata['Negative Prompt']) {
        negativePrompt = metadata['Negative Prompt'];
    }
    else if (metadata['Revised Negative Prompt']) {
        negativePrompt = metadata['Revised Negative Prompt'];
    }
    // Extract character prompts (NovelAI specific)
    const characterMap = {};
    for (const key in metadata) {
        // Look for character prompts: "Character 1 Prompt", "Character 1 Negative", etc.
        const characterMatch = key.match(/^Character (\d+) (Prompt|Negative)$/);
        const processedMatch = key.match(/^Character (\d+) Processed (Prompt|Negative)$/);
        if (characterMatch) {
            const charNum = parseInt(characterMatch[1]);
            const promptType = characterMatch[2];
            if (!characterMap[charNum]) {
                characterMap[charNum] = { positive: '', negative: '' };
            }
            if (promptType === 'Prompt') {
                characterMap[charNum].positive = metadata[key] || '';
            }
            else if (promptType === 'Negative') {
                characterMap[charNum].negative = metadata[key] || '';
            }
        }
        else if (processedMatch) {
            // If no original character prompt exists, use processed version as fallback
            const charNum = parseInt(processedMatch[1]);
            const promptType = processedMatch[2];
            const originalKey = `Character ${charNum} ${promptType}`;
            if (!metadata[originalKey]) {
                if (!characterMap[charNum]) {
                    characterMap[charNum] = { positive: '', negative: '' };
                }
                if (promptType === 'Prompt') {
                    characterMap[charNum].positive = metadata[key] || '';
                }
                else if (promptType === 'Negative') {
                    characterMap[charNum].negative = metadata[key] || '';
                }
            }
        }
    }
    // Convert character map to array (sorted by character number)
    const characterNumbers = Object.keys(characterMap).map(num => parseInt(num)).sort((a, b) => a - b);
    for (const charNum of characterNumbers) {
        characterPrompts.push(characterMap[charNum]);
    }
    console.log('Extracted prompts from metadata:', { prompt, negativePrompt, characterPrompts });
    return { prompt, negativePrompt, characterPrompts };
}
/**
 * Copy prompts to the generation form
 */
function copyPromptToForm(prompt, negativePrompt, characterPrompts) {
    const promptTextarea = document.getElementById('prompt');
    const negativePromptTextarea = document.getElementById('negative_prompt');
    if (promptTextarea && prompt) {
        promptTextarea.value = prompt;
        // Trigger input event to update character count
        promptTextarea.dispatchEvent(new Event('input'));
    }
    if (negativePromptTextarea && negativePrompt) {
        negativePromptTextarea.value = negativePrompt;
        // Trigger input event if there's a character count for negative prompt
        negativePromptTextarea.dispatchEvent(new Event('input'));
    }
    // Handle character prompts if provided
    if (characterPrompts && characterPrompts.length > 0) {
        // Check if NovelAI is selected (character prompts are NovelAI-specific)
        const providerSelect = document.getElementById('provider');
        if (providerSelect && providerSelect.value === 'novelai') {
            // Show character prompt interface if not already visible
            showCharacterPromptInterface();
            // Populate character prompts
            populateCharacterPrompts(characterPrompts);
        }
        else {
            // Store character prompts for later use if user switches to NovelAI
            window.pendingCharacterPrompts = characterPrompts;
            console.log('Character prompts stored for when NovelAI is selected:', characterPrompts);
        }
    }
    console.log('Copied prompts to form:', { prompt, negativePrompt, characterPrompts });
}
/**
 * Clear inpainting mode and return to normal generation
 */
function clearInpaintingMode() {
    const inpaintingSection = document.getElementById('inpainting-section');
    const baseImageInput = document.getElementById('inpainting-base-image');
    const maskPathInput = document.getElementById('inpainting-mask-path');
    const operationInput = document.getElementById('inpainting-operation');
    const submitBtn = document.getElementById('generate-submit-btn');
    if (inpaintingSection) {
        inpaintingSection.style.display = 'none';
    }
    if (baseImageInput) {
        baseImageInput.value = '';
    }
    if (maskPathInput) {
        maskPathInput.value = '';
    }
    if (operationInput) {
        operationInput.value = '';
    }
    if (submitBtn) {
        submitBtn.value = 'Generate Image';
        submitBtn.classList.remove('inpainting-mode');
    }
}
// Make the functions globally available
window.openInpaintingMaskCanvas = openInpaintingMaskCanvas;
window.clearInpaintingMode = clearInpaintingMode;
function toggleShowAdvanced(event) {
    console.log("show advanced");
    const advancedDropdown = document.getElementById("advanced-dropdown");
    // Toggle visibility based on current state.
    if (advancedDropdown.style.display === "none") {
        advancedDropdown.style.display = "block";
    }
    else {
        advancedDropdown.style.display = "none";
        // Also reset the custom input toggle and hide its container when closing.
        const inputToggle = document.getElementById("advanced-generate-grid");
        if (inputToggle) {
            inputToggle.checked = false;
        }
        const inputContainer = document.querySelector(".advanced-input-container");
        if (inputContainer) {
            inputContainer.style.display = "none";
        }
    }
}
function toggleAdvancedInput(event) {
    const inputToggle = event.target;
    const inputContainer = document.querySelector(".advanced-input-container");
    const advancedOption = document.getElementById("grid-prompt-file");
    if (inputToggle.checked) {
        inputContainer.style.display = "block";
        advancedOption.disabled = false;
    }
    else {
        inputContainer.style.display = "none";
        advancedOption.disabled = true;
    }
}
let allConversations = {};
var currentThreadId = "";
function chatTabLoaded() {
    refreshConversationList();
}
function refreshConversationList() {
    const conversationsList = document.getElementById("conversations-list");
    $.get("/get-all-conversations", (response) => {
        console.log("convos pulled");
        let conversations = JSON.parse(response);
        allConversations = conversations;
        let children = [];
        for (let key in conversations) {
            let value = conversations[key];
            var convoItem = document.createElement("div");
            convoItem.className = "conversation-item";
            let creationDate = new Date(value.data.created_at * 1000);
            console.log(`date: ${value.data.created_at}`);
            convoItem.textContent = `${value.chat_name}\n${creationDate.toDateString()}`;
            convoItem.setAttribute("data-conversation-id", key);
            convoItem.addEventListener("click", onConversationSelected);
            conversationsList.appendChild(convoItem);
            children.unshift(convoItem);
        }
        conversationsList.replaceChildren(...children);
    });
}
function updateConversationTitle(conversationId, newTitle) {
    /**
     * Update a conversation title on the server and refresh the conversation list.
     */
    $.ajax({
        type: "POST",
        url: "/update-conversation-title",
        contentType: "application/json",
        data: JSON.stringify({
            conversation_id: conversationId,
            title: newTitle
        }),
        success: (response) => {
            if (response.success) {
                console.log("Title updated successfully:", newTitle);
                // Update local conversations cache with the server response
                allConversations = response.conversations;
                // Refresh the conversation list display
                refreshConversationListFromCache();
            }
            else {
                console.error("Failed to update title:", response.error);
            }
        },
        error: (xhr, status, error) => {
            console.error("Error updating conversation title:", error);
        }
    });
}
function refreshConversationListFromCache() {
    /**
     * Refresh the conversation list display using cached conversation data.
     * This is more efficient than making another server request.
     */
    const conversationsList = document.getElementById("conversations-list");
    let children = [];
    for (let key in allConversations) {
        let value = allConversations[key];
        var convoItem = document.createElement("div");
        convoItem.className = "conversation-item";
        let creationDate = new Date(value.data.created_at * 1000);
        convoItem.textContent = `${value.chat_name}\n${creationDate.toDateString()}`;
        convoItem.setAttribute("data-conversation-id", key);
        convoItem.addEventListener("click", onConversationSelected);
        conversationsList.appendChild(convoItem);
        children.unshift(convoItem);
    }
    conversationsList.replaceChildren(...children);
}
function scheduleConversationTitleRefresh(conversationId) {
    /**
     * Schedule periodic checks for AI-generated title updates for new conversations.
     * This polls the server to see if the title has been updated from "New Chat" to an AI-generated title.
     */
    let attempts = 0;
    const maxAttempts = 10; // Check for up to 30 seconds (3s * 10)
    const checkInterval = 3000; // Check every 3 seconds
    const checkForTitleUpdate = () => {
        attempts++;
        // Stop checking after max attempts or if conversation no longer exists
        if (attempts > maxAttempts || !allConversations[conversationId]) {
            console.log(`Stopped checking for title update for conversation ${conversationId}`);
            return;
        }
        // Check if the title is still "New Chat" (meaning it hasn't been updated yet)
        if (allConversations[conversationId].chat_name === "New Chat") {
            console.log(`Checking for title update for conversation ${conversationId} (attempt ${attempts})`);
            // Refresh the conversation list to get updated titles
            $.get("/get-all-conversations", (response) => {
                try {
                    let conversations = JSON.parse(response);
                    // Check if this conversation's title has been updated
                    if (conversations[conversationId] && conversations[conversationId].chat_name !== "New Chat") {
                        console.log(`Title updated for conversation ${conversationId}: ${conversations[conversationId].chat_name}`);
                        // Update local cache
                        allConversations = conversations;
                        // Refresh the conversation list display
                        refreshConversationListFromCache();
                        // Stop checking since we found the update
                        return;
                    }
                    // Schedule next check if title hasn't been updated yet
                    setTimeout(checkForTitleUpdate, checkInterval);
                }
                catch (error) {
                    console.error("Error parsing conversation list response:", error);
                    // Continue checking despite the error
                    setTimeout(checkForTitleUpdate, checkInterval);
                }
            }).fail((xhr, status, error) => {
                console.error("Error fetching conversation list:", error);
                // Continue checking despite the error
                setTimeout(checkForTitleUpdate, checkInterval);
            });
        }
        else {
            // Title has already been updated, stop checking
            console.log(`Title already updated for conversation ${conversationId}: ${allConversations[conversationId].chat_name}`);
        }
    };
    // Start the first check after a short delay to give the server time to generate the title
    setTimeout(checkForTitleUpdate, 2000); // Wait 2 seconds before first check
}
function onConversationSelected(ev) {
    let conversationId = this.getAttribute("data-conversation-id");
    console.log(`conversation: ${conversationId}`);
    const chatInput = document.getElementById("chat-input");
    chat.onConversationSelected(conversationId, (chatData) => {
        chatInput.value = ""; // Clear input field
        chat.refreshChatMessages(chatData.messages);
        currentThreadId = chatData.threadId;
        // Expose currentThreadId to window for reasoning modal access
        window.currentThreadId = currentThreadId;
    });
}
async function fetchWithStreaming(url, data, processChunk) {
    try {
        const response = await fetch(url, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify(data),
        });
        if (response.body) {
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let resultString = "";
            while (true) {
                const { value, done } = await reader.read();
                if (done)
                    break;
                const chunk = decoder.decode(value, { stream: true });
                resultString += chunk;
                const parts = resultString.split("␆␄");
                resultString = parts.pop(); // Handle the rest in the next iteration.
                parts.forEach((part) => {
                    if (part) {
                        try {
                            processChunk(part);
                        }
                        catch (e) {
                            console.error("Error parsing JSON chunk:", e);
                        }
                    }
                });
            }
        }
        else {
            console.log("Response body is not readable");
        }
    }
    catch (error) {
        console.error("Fetch error:", error);
    }
}
// "queued", "in_progress", "requires_action", "cancelling", "cancelled", "failed", "completed", "expired"
let prettyStatuses = {
    queued: "in queue",
    in_progress: "in progress...",
    requires_action: "processing action...",
};
var cachedMessageList;
var progressNum = 0;
function sendChatMessage() {
    var chatName = "";
    if (currentThreadId) {
        // Use existing conversation title
        chatName = allConversations[currentThreadId].chat_name;
    }
    else {
        // For new conversations, use a default title (server will generate the actual title)
        chatName = "New Chat";
    }
    const chatInput = document.getElementById("chat-input");
    const sendChatButton = document.getElementById("send-chat");
    const chatStatusText = document.getElementById("chat-current-status");
    const userMessage = chatInput.value.trim();
    if (!userMessage) {
        // If now user message, then copy the url for sharing
        if (currentThreadId) {
            const shareUrl = `${document.baseURI}/share?id=${currentThreadId}`;
            utils.copyToClipboard(shareUrl);
            console.log(shareUrl);
        }
        return;
    }
    // Send the message to the server
    sendChatButton.disabled = true;
    fetchWithStreaming("/chat", {
        user_input: userMessage,
        chat_name: chatName,
        thread_id: currentThreadId,
    }, (chunkData) => {
        console.log("succeess");
        var parsedData = JSON.parse(chunkData);
        // Weird hack to prevent "too stringified" json blobs getting converted to just strings.
        let chatData = typeof parsedData === "string" ? JSON.parse(parsedData) : parsedData;
        if (chatData.type == "message_list") {
            chatStatusText.textContent = "In queue...";
            currentThreadId = chatData.threadId;
            // Expose currentThreadId to window for reasoning modal access
            window.currentThreadId = currentThreadId;
            cachedMessageList = chatData.messages;
            chatInput.value = ""; // Clear input field
            chat.refreshChatMessages(cachedMessageList);
            // Just populate it with dummy data so that we have data in case the refresh takes too long
            let currentTimeEpoch = new Date(Date.now()).getUTCSeconds();
            const isNewConversation = !allConversations[chatData.threadId];
            allConversations[chatData.threadId] = {
                data: {
                    id: chatData.threadId,
                    created_at: new Date(Date.now()).getUTCSeconds(),
                    metadata: {},
                    object: "thread",
                },
                chat_name: chatName,
                last_update: currentTimeEpoch,
            };
            // For new conversations, set up title refresh to catch AI-generated titles
            if (isNewConversation && chatName === "New Chat") {
                scheduleConversationTitleRefresh(chatData.threadId);
            }
        }
        else if (chatData.type == "text_created") {
            cachedMessageList.push({ role: "assistant", text: "" });
            chatStatusText.textContent = "In progress...";
        }
        else if (chatData.type == "text_delta") {
            cachedMessageList[cachedMessageList.length - 1].text += chatData.delta;
            updateMostRecentChatMessage(cachedMessageList);
            switch (progressNum) {
                case 0:
                    chatStatusText.textContent = "In progress.";
                    break;
                case 1:
                    chatStatusText.textContent = "In progress..";
                    break;
                case 2:
                    chatStatusText.textContent = "In progress...";
                    break;
                default:
                    break;
            }
            progressNum += 1;
            if (progressNum > 3) {
                progressNum = 0;
            }
        }
        else if (chatData.type == "text_done") {
            sendChatButton.disabled = false;
            chatStatusText.textContent = "Awaiting Input...";
            progressNum = 0;
        }
        // TODO: Hook up the tool-based outputs
    });
}
function updateMostRecentChatMessage(messages) {
    const chatHistory = document.getElementById("chat-history");
    var message = messages[messages.length - 1];
    var converter = new showdown.Converter({
        strikethrough: true,
        smoothLivePreview: true,
        tasklists: true,
        extensions: ["highlight"],
    }), text = message.text, html = converter.makeHtml(text);
    if (chatHistory.children.length < messages.length) {
        const div = document.createElement("div");
        div.className = "ai-message";
        div.innerHTML = utils.unescapeHTML(html);
        // Add reasoning button for assistant messages
        if (message.role === "assistant") {
            addReasoningButtonToMessage(div, messages.length - 1);
        }
        chatHistory.appendChild(div);
    }
    else {
        var lastChildDiv = chatHistory.lastChild;
        lastChildDiv.innerHTML = utils.unescapeHTML(html);
        // Re-add reasoning button if it's an assistant message and doesn't already have one
        if (message.role === "assistant" && !lastChildDiv.querySelector('.reasoning-button')) {
            addReasoningButtonToMessage(lastChildDiv, messages.length - 1);
        }
    }
    chatHistory.scrollTop = chatHistory.scrollHeight; // Scroll to bottom
}
function addReasoningButtonToMessage(messageElement, messageIndex) {
    const reasoningButton = document.createElement("button");
    reasoningButton.className = "reasoning-button";
    reasoningButton.innerHTML = "i";
    reasoningButton.title = "View reasoning";
    reasoningButton.setAttribute("data-message-index", messageIndex.toString());
    reasoningButton.addEventListener("click", (e) => {
        e.preventDefault();
        e.stopPropagation();
        showReasoningModalFromScript(messageIndex);
    });
    messageElement.appendChild(reasoningButton);
}
function showReasoningModalFromScript(messageIndex) {
    // Get current conversation ID
    const conversationId = currentThreadId;
    if (!conversationId) {
        showReasoningErrorFromScript("No conversation selected");
        return;
    }
    // Show modal with loading state
    const modal = document.getElementById("reasoning-modal");
    const content = document.getElementById("reasoning-content");
    const loading = document.getElementById("reasoning-loading");
    const error = document.getElementById("reasoning-error");
    if (!modal || !content || !loading || !error) {
        console.error("Reasoning modal elements not found");
        showReasoningErrorFromScript("Modal interface not available");
        return;
    }
    // Reset modal state
    content.style.display = "none";
    error.style.display = "none";
    loading.style.display = "block";
    modal.style.display = "block";
    // Set up timeout for the request
    const controller = new AbortController();
    const timeoutId = setTimeout(() => {
        controller.abort();
    }, 10000); // 10 second timeout
    // Fetch reasoning data with comprehensive error handling
    fetch(`/chat/reasoning/${conversationId}/${messageIndex}`, {
        signal: controller.signal,
        headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
    })
        .then(response => {
        clearTimeout(timeoutId);
        if (!response.ok) {
            // Handle specific HTTP error codes
            if (response.status === 404) {
                throw new Error("Reasoning data not found for this message");
            }
            else if (response.status === 400) {
                throw new Error("Invalid request - this message may not support reasoning");
            }
            else if (response.status === 401) {
                throw new Error("Authentication required - please refresh the page");
            }
            else if (response.status === 500) {
                throw new Error("Server error - please try again later");
            }
            else {
                throw new Error(`Request failed (${response.status}): ${response.statusText}`);
            }
        }
        return response.json();
    })
        .then(data => {
        loading.style.display = "none";
        // Validate response structure
        if (!data) {
            throw new Error("Empty response received");
        }
        if (data.error) {
            throw new Error(data.message || data.error);
        }
        if (data.reasoning && data.reasoning.complete_summary) {
            displayReasoningDataFromScript(data.reasoning);
            content.style.display = "block";
        }
        else if (data.reasoning && data.reasoning.summary_parts && data.reasoning.summary_parts.length > 0) {
            // Fallback to summary parts if complete summary is not available
            const fallbackData = {
                ...data.reasoning,
                complete_summary: data.reasoning.summary_parts.join('\n\n')
            };
            displayReasoningDataFromScript(fallbackData);
            content.style.display = "block";
        }
        else {
            showReasoningErrorFromScript("No reasoning data available for this message");
        }
    })
        .catch(err => {
        clearTimeout(timeoutId);
        loading.style.display = "none";
        // Handle different types of errors
        if (err.name === 'AbortError') {
            showReasoningErrorFromScript("Request timed out - please try again");
        }
        else if (err.name === 'TypeError' && err.message.includes('fetch')) {
            showReasoningErrorFromScript("Network error - please check your connection");
        }
        else {
            showReasoningErrorFromScript(`Failed to load reasoning data: ${err.message}`);
        }
        console.error("Reasoning modal error:", err);
    });
}
function displayReasoningDataFromScript(reasoningData) {
    const content = document.getElementById("reasoning-content");
    if (!content)
        return;
    try {
        // Validate and sanitize the reasoning data
        const summary = reasoningData.complete_summary || "";
        if (!summary) {
            throw new Error("No reasoning summary available");
        }
        // Escape HTML to prevent XSS
        const escapedSummary = escapeHtml(summary);
        // Format the content with proper line breaks
        const formattedSummary = escapedSummary.replace(/\n/g, '<br>');
        content.innerHTML = `
            <div class="reasoning-summary">
                <h3>AI Reasoning Process</h3>
                <div class="reasoning-text">${formattedSummary}</div>
                ${reasoningData.timestamp ? `<div class="reasoning-timestamp">Generated: ${new Date(reasoningData.timestamp * 1000).toLocaleString()}</div>` : ''}
            </div>
        `;
    }
    catch (error) {
        console.error("Error displaying reasoning data:", error);
        showReasoningErrorFromScript("Failed to display reasoning data");
    }
}
function showReasoningErrorFromScript(message) {
    const error = document.getElementById("reasoning-error");
    if (!error)
        return;
    error.textContent = message;
    error.style.display = "block";
}
function hideReasoningModalFromScript() {
    const modal = document.getElementById("reasoning-modal");
    if (modal) {
        modal.style.display = "none";
    }
}
function showCharacterPromptInterface() {
    const characterSection = document.getElementById("character-prompt-section");
    if (characterSection) {
        characterSection.style.display = "block";
        // Check if there are pending character prompts from copy functionality
        const pendingPrompts = window.pendingCharacterPrompts;
        if (pendingPrompts && Array.isArray(pendingPrompts)) {
            populateCharacterPrompts(pendingPrompts);
            delete window.pendingCharacterPrompts;
        }
    }
}
function hideCharacterPromptInterface() {
    const characterSection = document.getElementById("character-prompt-section");
    if (characterSection) {
        characterSection.style.display = "none";
    }
}
function addCharacterPrompt() {
    const container = document.getElementById("character-prompts-container");
    if (!container)
        return;
    // Get current count to determine the new character's position
    const currentCount = container.querySelectorAll(".character-prompt-item").length;
    const newCharacterNumber = currentCount + 1;
    const characterDiv = document.createElement("div");
    characterDiv.className = "character-prompt-item";
    characterDiv.setAttribute("data-character-index", currentCount.toString());
    characterDiv.innerHTML = `
        <div class="character-item-header">
            <span class="character-label">Character ${newCharacterNumber}</span>
            <div class="character-item-controls">
                <label class="individual-toggle">
                    <input type="checkbox" class="show-negative-toggle" data-character-index="${currentCount}">
                    Show Negative
                </label>
                <button type="button" class="remove-character-btn">Remove</button>
            </div>
        </div>
        
        <div class="character-prompt-group positive-group">
            <div class="character-prompt-label">
                <span>Positive Prompt</span>
                <span class="content-indicator" style="display: none;">Has Content</span>
            </div>
            <textarea 
                name="character_prompts[${currentCount}][positive]" 
                placeholder="Describe this character's appearance and traits..."
                data-prompt-type="positive"
                oninput="updateCharacterContentIndicator(this)"
            ></textarea>
        </div>
        
        <div class="character-prompt-group negative-group" style="display: none;">
            <div class="character-prompt-label">
                <span>Negative Prompt</span>
                <span class="content-indicator" style="display: none;">Has Content</span>
            </div>
            <textarea 
                name="character_prompts[${currentCount}][negative]" 
                placeholder="What to avoid for this character..."
                data-prompt-type="negative"
                oninput="updateCharacterContentIndicator(this)"
            ></textarea>
        </div>
    `;
    // Add event listener for the remove button
    const removeBtn = characterDiv.querySelector(".remove-character-btn");
    if (removeBtn) {
        removeBtn.addEventListener("click", () => {
            characterDiv.remove();
            updateCharacterPromptCount();
            reindexCharacterPrompts();
        });
    }
    // Add event listener for the individual negative prompt toggle
    const negativeToggle = characterDiv.querySelector(".show-negative-toggle");
    if (negativeToggle) {
        negativeToggle.addEventListener("change", (event) => {
            const checkbox = event.target;
            const negativeGroup = characterDiv.querySelector(".negative-group");
            if (negativeGroup) {
                negativeGroup.style.display = checkbox.checked ? "block" : "none";
            }
        });
    }
    container.appendChild(characterDiv);
    updateCharacterPromptCount();
}
function removeCharacterPrompt(characterDiv) {
    characterDiv.remove();
    updateCharacterPromptCount();
    reindexCharacterPrompts();
}
function updateCharacterPromptCount() {
    const container = document.getElementById("character-prompts-container");
    const countElement = document.getElementById("character-count");
    if (container && countElement) {
        const characterItems = container.querySelectorAll(".character-prompt-item");
        const count = characterItems.length;
        countElement.textContent = `${count} character${count !== 1 ? 's' : ''}`;
    }
}
function reindexCharacterPrompts() {
    const container = document.getElementById("character-prompts-container");
    if (!container)
        return;
    const characterItems = container.querySelectorAll(".character-prompt-item");
    characterItems.forEach((item, index) => {
        const characterDiv = item;
        // Update data-character-index attribute
        characterDiv.setAttribute("data-character-index", index.toString());
        // Update character label
        const label = characterDiv.querySelector(".character-label");
        if (label) {
            label.textContent = `Character ${index + 1}`;
        }
        // Update form field names
        const textareas = characterDiv.querySelectorAll("textarea");
        textareas.forEach((textarea) => {
            const promptType = textarea.getAttribute("data-prompt-type");
            textarea.name = `character_prompts[${index}][${promptType}]`;
        });
        // Update negative toggle data-character-index
        const negativeToggle = characterDiv.querySelector(".show-negative-toggle");
        if (negativeToggle) {
            negativeToggle.setAttribute("data-character-index", index.toString());
        }
    });
}
// Positive prompts are always visible, individual negative toggles handle their own visibility
function updateCharacterContentIndicator(textarea) {
    const characterDiv = textarea.closest(".character-prompt-item");
    if (!characterDiv)
        return;
    const promptType = textarea.getAttribute("data-prompt-type");
    const indicator = characterDiv.querySelector(`.${promptType}-group .content-indicator`);
    if (indicator) {
        if (textarea.value.trim().length > 0) {
            indicator.style.display = "inline-block";
        }
        else {
            indicator.style.display = "none";
        }
    }
}
function populateCharacterPrompts(characterPrompts) {
    // Clear existing character prompts
    const container = document.getElementById("character-prompts-container");
    if (container) {
        container.innerHTML = "";
    }
    // Add character prompts from the provided data
    characterPrompts.forEach((promptData) => {
        addCharacterPrompt();
        // Get the last added character prompt and populate it
        const lastCharacterDiv = container?.querySelector(".character-prompt-item:last-child");
        if (lastCharacterDiv) {
            const positiveTextarea = lastCharacterDiv.querySelector('textarea[data-prompt-type="positive"]');
            const negativeTextarea = lastCharacterDiv.querySelector('textarea[data-prompt-type="negative"]');
            if (positiveTextarea) {
                positiveTextarea.value = promptData.positive;
                updateCharacterContentIndicator(positiveTextarea);
            }
            if (negativeTextarea) {
                negativeTextarea.value = promptData.negative;
                updateCharacterContentIndicator(negativeTextarea);
                // If there's negative content, enable the toggle and show the negative group
                if (promptData.negative.trim().length > 0) {
                    const negativeToggle = lastCharacterDiv.querySelector('.show-negative-toggle');
                    const negativeGroup = lastCharacterDiv.querySelector('.negative-group');
                    if (negativeToggle && negativeGroup) {
                        negativeToggle.checked = true;
                        negativeGroup.style.display = "block";
                    }
                }
            }
        }
    });
}
// Make updateCharacterContentIndicator globally accessible for oninput handlers
window.updateCharacterContentIndicator = updateCharacterContentIndicator;
let promptFiles = [];
let currentEditingFile = null;
async function promptFilesTabLoaded() {
    await loadPromptFiles();
}
async function loadPromptFiles() {
    const loadingElement = document.getElementById("prompt-files-loading");
    const contentElement = document.getElementById("prompt-files-content");
    const noFilesElement = document.getElementById("no-prompt-files");
    try {
        loadingElement.style.display = "block";
        contentElement.innerHTML = "";
        noFilesElement.style.display = "none";
        const response = await fetch("/prompt-files");
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        promptFiles = await response.json();
        renderPromptFiles();
    }
    catch (error) {
        console.error("Error loading prompt files:", error);
        contentElement.innerHTML = `<div class="error-message">Error loading prompt files: ${error}</div>`;
    }
    finally {
        loadingElement.style.display = "none";
    }
}
function renderPromptFiles() {
    const contentElement = document.getElementById("prompt-files-content");
    const noFilesElement = document.getElementById("no-prompt-files");
    if (promptFiles.length === 0) {
        noFilesElement.style.display = "block";
        contentElement.innerHTML = "";
        return;
    }
    noFilesElement.style.display = "none";
    const filesHtml = promptFiles.map(file => `
        <div class="prompt-file-item" data-file-name="${escapeHtml(file.name)}">
            <div class="prompt-file-header">
                <h4 class="prompt-file-name">__${escapeHtml(file.name)}__</h4>
                <div class="prompt-file-meta">
                    ${file.content.length} line${file.content.length !== 1 ? 's' : ''} • ${file.size} bytes
                </div>
            </div>
            <div class="prompt-file-preview">
                ${file.content.slice(0, 3).map(line => `<div class="preview-line">${escapeHtml(line)}</div>`).join('')}
                ${file.content.length > 3 ? `<div class="preview-more">... and ${file.content.length - 3} more lines</div>` : ''}
            </div>
            <div class="prompt-file-actions">
                <button class="action-button edit-button" onclick="editPromptFile('${escapeHtml(file.name)}')">Edit</button>
                <button class="action-button delete-button" onclick="deletePromptFile('${escapeHtml(file.name)}')">Delete</button>
            </div>
        </div>
    `).join('');
    contentElement.innerHTML = filesHtml;
}
function showPromptFileModal(mode, fileName) {
    const modal = document.getElementById("prompt-file-modal");
    const title = document.getElementById("prompt-modal-title");
    const nameInput = document.getElementById("prompt-file-name");
    const contentTextarea = document.getElementById("prompt-file-content");
    if (mode === "create") {
        title.textContent = "Create New Prompt File";
        nameInput.value = "";
        contentTextarea.value = "";
        nameInput.disabled = false;
        currentEditingFile = null;
    }
    else if (mode === "edit" && fileName) {
        title.textContent = "Edit Prompt File";
        nameInput.value = fileName;
        nameInput.disabled = true;
        currentEditingFile = fileName;
        const file = promptFiles.find(f => f.name === fileName);
        contentTextarea.value = file ? file.content.join('\n') : "";
    }
    modal.style.display = "flex";
    nameInput.focus();
}
function hidePromptFileModal() {
    const modal = document.getElementById("prompt-file-modal");
    modal.style.display = "none";
    currentEditingFile = null;
}
async function savePromptFile() {
    const nameInput = document.getElementById("prompt-file-name");
    const contentTextarea = document.getElementById("prompt-file-content");
    const fileName = nameInput.value.trim();
    const content = contentTextarea.value;
    if (!fileName) {
        alert("Please enter a file name");
        return;
    }
    if (!/^[a-zA-Z0-9_-]+$/.test(fileName)) {
        alert("File name can only contain letters, numbers, underscores, and hyphens");
        return;
    }
    try {
        const response = await fetch("/prompt-files", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                name: fileName,
                content: content,
            }),
        });
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `HTTP ${response.status}: ${response.statusText}`);
        }
        hidePromptFileModal();
        await loadPromptFiles();
    }
    catch (error) {
        console.error("Error saving prompt file:", error);
        alert(`Error saving file: ${error}`);
    }
}
async function editPromptFile(fileName) {
    showPromptFileModal("edit", fileName);
}
async function deletePromptFile(fileName) {
    if (!confirm(`Are you sure you want to delete the file "${fileName}"?`)) {
        return;
    }
    try {
        const response = await fetch(`/prompt-files/${encodeURIComponent(fileName)}`, {
            method: "DELETE",
        });
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `HTTP ${response.status}: ${response.statusText}`);
        }
        await loadPromptFiles();
    }
    catch (error) {
        console.error("Error deleting prompt file:", error);
        alert(`Error deleting file: ${error}`);
    }
}
// Make prompt file functions globally accessible
window.editPromptFile = editPromptFile;
window.deletePromptFile = deletePromptFile;
window.deletePromptFile = deletePromptFile;
