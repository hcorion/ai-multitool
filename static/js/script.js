import * as utils from "./utils.js";
import * as chat from "./chat.js";
document.addEventListener("DOMContentLoaded", () => {
    $("#loading-spinner").hide();
    $("#prompt-form").on("submit", (event) => {
        event.preventDefault();
        const formData = $("#prompt-form").serialize();
        $("#loading-spinner").show();
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
        });
    });
    // Image gen elements
    addEventListenerToElement("provider", "change", providerChanged);
    addEventListenerToElement("model", "change", modelButtonChanged);
    // Assigning event listeners
    addEventListenerToElement("generationTab", "click", handleTabClick);
    addEventListenerToElement("gridViewTab", "click", handleTabClick);
    addEventListenerToElement("chatTab", "click", handleTabClick);
    addEventListenerToElement("style", "input", updateStyleDescription);
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
        document.getElementById("size").selectedIndex = 0;
    }
    else if ((selection.value == "stabilityai")) {
        $(".openai").hide();
        $(".novelai").hide();
        $(".stabilityai").show();
        modelChanged(selection.value);
    }
    else if ((selection.value == "novelai")) {
        $(".openai").hide();
        $(".stabilityai").hide();
        $(".novelai").show();
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
function updateStyleDescription() {
    const styleInput = document.getElementById("style");
    const currentStyle = styleInput.value;
    const styleDescriptionDisplay = document.getElementById("styleDescription");
    if (currentStyle === "vivid") {
        styleDescriptionDisplay.textContent =
            "(Vivid causes the model to lean towards generating hyper-real and dramatic images)";
    }
    else if (currentStyle === "natural") {
        styleDescriptionDisplay.textContent =
            "(Natural causes the model to produce more natural, less hyper-real looking images)";
    }
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
        // Display each metadata key–value pair.
        for (const key in metadata) {
            const infoItem = document.createElement("div");
            infoItem.className = "info-item";
            infoItem.textContent = key + ":";
            metadataDiv.appendChild(infoItem);
            const infoValue = document.createElement("div");
            infoValue.className = "prompt-value";
            infoValue.textContent = metadata[key];
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
        chatName = allConversations[currentThreadId].chat_name;
    }
    while (!chatName) {
        chatName = prompt("Please title this conversation (max 30 chars):", "Conversation");
        if (chatName.length > 30) {
            chatName = "";
        }
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
