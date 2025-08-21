import * as utils from "./utils.js";
import * as chat from "./chat.js";
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
                    if (xhr.responseJSON && xhr.responseJSON.error) {
                        errorMessage = xhr.responseJSON.error;
                    }
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
                    renderImageError("An error occurred while generating the image.");
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
    addEventListenerToElement("prompt", "input", updateCharacterCount);
    // Grid buttons
    addEventListenerToElement("firstGrid", "click", firstGrid);
    addEventListenerToElement("previousGrid", "click", previousGrid);
    addEventListenerToElement("nextGrid", "click", nextGrid);
    addEventListenerToElement("lastGrid", "click", lastGrid);
    // Chat buttons
    addEventListenerToElement("send-chat", "click", sendChatMessage);
    // Grid Modal Buttons
    addEventListenerToElement("grid-image-close", "click", closeGridModal);
    addEventListenerToElement("grid-prev", "click", previousGridImage);
    addEventListenerToElement("grid-next", "click", nextGridImage);
    addEventListenerToElement("advanced-toggle", "click", toggleShowAdvanced);
    addEventListenerToElement("advanced-generate-grid", "change", toggleAdvancedInput);
    addEventListener("keydown", keyDownEvent);
    document.getElementById("generationTab").click();
    // Character prompt event listeners
    addEventListenerToElement("add-character-btn", "click", addCharacterPrompt);
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
 * Highlights differences between base and processed text by finding and highlighting
 * only the parts that actually changed (like __color__ -> violet).
 */
function highlightTextDifferences(baseText, processedText) {
    // Use a more sophisticated approach to find dynamic prompt replacements
    // This handles cases like "1.5::__color__" -> "1.5::violet" where only "violet" should be highlighted
    let result = processedText;
    // Find all dynamic prompt patterns in the base text (like __color__, __style__, etc.)
    const dynamicPromptPattern = /__([^_]+)__/g;
    const matches = [...baseText.matchAll(dynamicPromptPattern)];
    for (const match of matches) {
        const fullPlaceholder = match[0]; // e.g., "__color__"
        const placeholderName = match[1]; // e.g., "color"
        // Find where this placeholder appears in the base text
        const baseIndex = match.index;
        // Get the context around the placeholder to find the corresponding part in processed text
        const beforePlaceholder = baseText.substring(0, baseIndex);
        const afterPlaceholder = baseText.substring(baseIndex + fullPlaceholder.length);
        // Find the corresponding position in the processed text
        const beforeIndex = beforePlaceholder.length;
        let afterIndex = processedText.length;
        if (afterPlaceholder.length > 0) {
            const afterStart = processedText.indexOf(afterPlaceholder, beforeIndex);
            if (afterStart !== -1) {
                afterIndex = afterStart;
            }
        }
        // Extract the replacement value from the processed text
        const replacementValue = processedText.substring(beforeIndex, afterIndex);
        // Only highlight if the replacement is different and not empty
        if (replacementValue && replacementValue !== fullPlaceholder) {
            const highlightedReplacement = `<span class="diff-highlight">${escapeHtml(replacementValue)}</span>`;
            result = result.substring(0, beforeIndex) + highlightedReplacement + result.substring(afterIndex);
        }
    }
    // If no dynamic prompts were found, fall back to basic word comparison for other changes
    if (matches.length === 0 && baseText !== processedText) {
        // Simple fallback: highlight the entire processed text if it's completely different
        result = `<span class="diff-highlight">${escapeHtml(processedText)}</span>`;
    }
    return result;
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
        // Create (or update) the "Copy Prompt" button.
        let copyPromptButton = document.getElementById("copy-prompt-btn");
        if (!copyPromptButton) {
            copyPromptButton = document.createElement("button");
            copyPromptButton.id = "copy-prompt-btn";
            copyPromptButton.textContent = "Copy Prompt";
            metadataDiv.appendChild(copyPromptButton);
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
        chatHistory.appendChild(div);
    }
    else {
        var lastChildDiv = chatHistory.lastChild;
        lastChildDiv.innerHTML = utils.unescapeHTML(html);
    }
    chatHistory.scrollTop = chatHistory.scrollHeight; // Scroll to bottom
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
