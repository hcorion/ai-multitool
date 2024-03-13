"use strict";
var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
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
        generationTab: "Generation",
        gridViewTab: "GridView",
        chatTab: "Chat",
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
function loadImages(page) {
    $.getJSON(`/get-images/${page}`, (data) => {
        const grid = $(".image-grid");
        grid.empty(); // Clear existing images
        data.forEach((image) => {
            const aspectRatioBox = $("<div>").addClass("aspect-ratio-box");
            const imgElement = $("<img>").attr("src", image).attr("id", "gridImage");
            imgElement.on("click", openGridModal);
            aspectRatioBox.append(imgElement);
            grid.append(aspectRatioBox);
        });
        document.getElementsByTagName;
        document.getElementById("gridPageNum").textContent = `Page ${page}/${totalPages}`;
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
    var _a;
    const filePath = evt.currentTarget.src;
    document.getElementById("grid-image-modal").style.display = "block";
    const thumbFileName = filePath.split("/").pop();
    const pathDir = filePath.slice(0, -((_a = thumbFileName === null || thumbFileName === void 0 ? void 0 : thumbFileName.length) !== null && _a !== void 0 ? _a : 0));
    const fileName = thumbFileName === null || thumbFileName === void 0 ? void 0 : thumbFileName.slice(0, -".thumb.jpg".length).concat(".png");
    document.getElementById("grid-modal-image").src = pathDir + fileName;
    $.getJSON("/get-image-metadata/" + fileName, function (metadata) {
        var metadataDiv = document.getElementById("grid-info-panel");
        metadataDiv.innerHTML = ""; // Clear previous metadata
        for (var key in metadata) {
            // <div class="info-item"><span>Prompt:</span><span id="prompt-value"></span></div>
            var infoItem = document.createElement("div");
            infoItem.className = "info-item";
            infoItem.textContent = key + ":";
            metadataDiv.appendChild(infoItem);
            var infoValue = document.createElement("div");
            infoValue.className = "prompt-value";
            infoValue.textContent = metadata[key];
            metadataDiv.appendChild(infoValue);
        }
    });
}
function closeGenModal() {
    document.getElementById("image-modal").style.display = "none";
}
function closeGridModal() {
    document.getElementById("grid-image-modal").style.display = "none";
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
    $.ajax({
        type: "GET",
        url: "/chat?thread_id=" + encodeURIComponent(conversationId),
        contentType: "application/json",
        scriptCharset: "utf-8",
        success: (response) => {
            let chatData = JSON.parse(response);
            chatInput.value = ""; // Clear input field
            refreshChatMessages(chatData.messages);
            currentThreadId = chatData.threadId;
        },
        error: (error) => {
            console.error("Error:", error);
        },
    });
}
function fetchWithStreaming(url, data, processChunk) {
    return __awaiter(this, void 0, void 0, function* () {
        try {
            const response = yield fetch(url, {
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
                    const { value, done } = yield reader.read();
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
    });
}
// "queued", "in_progress", "requires_action", "cancelling", "cancelled", "failed", "completed", "expired"
let prettyStatuses = {
    queued: "in queue",
    in_progress: "in progress...",
    requires_action: "processing action...",
};
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
    if (!userMessage)
        return;
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
        if (chatData.status) {
            chatStatusText.textContent =
                chatData.status in prettyStatuses ? prettyStatuses[chatData.status] : chatData.status;
            return;
        }
        refreshChatMessages(chatData.messages);
        chatInput.value = ""; // Clear input field
        currentThreadId = chatData.threadId;
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
        // Refresh the conversation list
        refreshConversationList();
        chatStatusText.textContent = "Awaiting input...";
        sendChatButton.disabled = false;
    });
}
showdown.extension("highlight", function () {
    return [
        {
            type: "output",
            filter: function (text, converter, options) {
                var left = "<pre><code\\b[^>]*>", right = "</code></pre>", flags = "g";
                var replacement = function (_wholeMatch, match, left, right) {
                    var lang = (left.match(/class=\"([^ \"]+)/) || [])[1];
                    left = left.slice(0, 18) + "hljs " + left.slice(18);
                    if (lang) {
                        left = left.slice(0, 18) + "hljs " + left.slice(18);
                        if (hljs.getLanguage(lang)) {
                            console.log("got language");
                            return left + hljs.highlight(lang, match).value + right;
                        }
                        else {
                            return left + hljs.highlightAuto(match).value + right;
                        }
                    }
                    else {
                        left = left.slice(0, 10) + ' class="hljs" ' + left.slice(10);
                        return left + hljs.highlightAuto(match).value + right;
                    }
                };
                return showdown.helper.replaceRecursiveRegExp(text, replacement, left, right, flags);
            },
        },
    ];
});
function refreshChatMessages(messages) {
    const chatHistory = document.getElementById("chat-history");
    chatHistory.innerHTML = "";
    // Display AI response in chat history
    messages.forEach((message) => {
        var converter = new showdown.Converter({
            strikethrough: true,
            smoothLivePreview: true,
            tasklists: true,
            extensions: ["highlight"],
        }), text = message.text, html = converter.makeHtml(text);
        chatHistory.innerHTML += `<div class="ai-message">${html}</div>`;
    });
    chatHistory.scrollTop = chatHistory.scrollHeight; // Scroll to bottom
}
