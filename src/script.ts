import * as utils from "./utils.js";

document.addEventListener("DOMContentLoaded", () => {
    $("#loading-spinner").hide();
    $("#prompt-form").on("submit", (event: JQuery.SubmitEvent) => {
        event.preventDefault();
        const formData: string = $("#prompt-form").serialize();

        $("#loading-spinner").show();

        $.ajax({
            type: "POST",
            url: "/",
            data: formData,
            success: (response: string) => {
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

    document.getElementById("generationTab")!.click();

    // Just refresh the image gen provider
    providerChanged();
});

// Function to add an event listener to an element
function addEventListenerToElement(elementId: string, eventType: string, handler: (evt: Event) => void) {
    const element = document.getElementById(elementId);
    if (element) {
        element.addEventListener(eventType, handler);
    } else {
        console.warn(`Element with ID '${elementId}' not found.`);
    }
}

type TabId = "generationTab" | "gridViewTab" | "chatTab";

// Event Handlers
function handleTabClick(evt: Event) {
    const element = evt.target as HTMLElement;
    const elementId = element.id as TabId;

    const tabMap: Record<TabId, string> = {
        generationTab: "Generation",
        gridViewTab: "GridView",
        chatTab: "Chat",
    };

    if (tabMap[elementId]) {
        openTab(evt as MouseEvent, tabMap[elementId]);
    }
}

function providerChanged() {
    const selection = document.getElementById("provider") as HTMLSelectElement;
    if (selection.value == "openai") {
        $(".stabilityai").hide();
        $(".novelai").hide();
        $(".openai").show();
    } else if ((selection.value == "stabilityai")) {
        $(".openai").hide();
        $(".novelai").hide();
        $(".stabilityai").show();
        modelChanged(selection.value);
    } else if ((selection.value == "novelai")) {
        $(".openai").hide();
        $(".stabilityai").hide();
        $(".novelai").show();
        modelChanged(selection.value);
    } else {
        throw new Error(`Tried to switch to unsupported provider ${selection}`);
    }
}

function modelButtonChanged() {
    const provider = document.getElementById("provider") as HTMLSelectElement;
    modelChanged(provider.value)
}

function modelChanged(provider: string) {
    const selection = document.getElementById("model") as HTMLSelectElement;
    if (provider == "stabilityai") {
        if (selection && !selection.hidden) {
            if (selection.value == "sd3-turbo") {
                $(".negativeprompt").hide();
            } else if ((selection.value = "sd3")) {
                $(".negativeprompt").show();
            } else {
                throw new Error(`Tried to switch to unsupported SD3 model ${selection}`);
            }
        }
    } else if (provider == "novelai") {
        $(".negativeprompt").show();
    } else if (provider == "openai") {
        $(".negativeprompt").hide();
    } else {
        throw new Error(`modelChanged called with unsupported provider ${selection}`);
    }

}

function updateCharacterCount(): void {
    const promptInput = document.getElementById("prompt") as HTMLInputElement;
    const charCount: number = promptInput.value.length;
    const charCountDisplay = document.getElementById("charCount") as HTMLDivElement;
    charCountDisplay.textContent = `${charCount} / 4000`;
}

function updateStyleDescription(): void {
    const styleInput = document.getElementById("style") as HTMLSelectElement;
    const currentStyle: string = styleInput.value;
    const styleDescriptionDisplay = document.getElementById("styleDescription") as HTMLDivElement;

    if (currentStyle === "vivid") {
        styleDescriptionDisplay.textContent =
            "(Vivid causes the model to lean towards generating hyper-real and dramatic images)";
    } else if (currentStyle === "natural") {
        styleDescriptionDisplay.textContent =
            "(Natural causes the model to produce more natural, less hyper-real looking images)";
    }
}

function openTab(evt: MouseEvent, tabName: string): void {
    const tabcontent = Array.from(document.getElementsByClassName("tabcontent") as HTMLCollectionOf<HTMLElement>);
    tabcontent.forEach((element) => (element.style.display = "none"));

    const tablinks = Array.from(document.getElementsByClassName("tablinks") as HTMLCollectionOf<HTMLElement>);
    tablinks.forEach((element) => (element.className = element.className.replace(" active", "")));

    const tab = document.getElementById(tabName) as HTMLElement;
    tab.style.display = "block";
    (evt.currentTarget as HTMLElement).className += " active";

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

let currentPage: number = 1;
let totalPages: number = -1;

function gridTabLoaded(): void {
    $.get("/get-total-pages", (data: string) => {
        totalPages = parseInt(data, 10);
        loadImages(currentPage);
    });
}

/* global variable to keep track of the current grid image index */
let currentGridImageIndex: number = 0;

function loadImages(page: number): void {
    $.getJSON(`/get-images/${page}`, (data: string[]) => {
        const grid = $(".image-grid");
        grid.empty(); // Clear existing images

        // For each image in “data”, attach an index so we can navigate later.
        data.forEach((image: string, index: number) => {
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

function firstGrid(): void {
    currentPage = 1;
    loadImages(currentPage);
}

function nextGrid(): void {
    if (currentPage < totalPages) {
        currentPage += 1;
        loadImages(currentPage);
    }
}

function previousGrid(): void {
    if (currentPage > 1) {
        currentPage -= 1;
        loadImages(currentPage);
    }
}

function lastGrid(): void {
    currentPage = totalPages;
    loadImages(currentPage);
}

function openGenModal(evt: Event): void {
    const src = (evt.currentTarget as HTMLImageElement).src;
    document.getElementById("image-modal")!.style.display = "block";
    (document.getElementById("modal-image") as HTMLImageElement).src = src;

    document.getElementById("image-modal")!.addEventListener("wheel", (event: WheelEvent) => {
        event.preventDefault(); // Prevent background scrolling when the modal is open
    });

    document.getElementById("modal-image")!.addEventListener("wheel", (event: WheelEvent) => {
        const img = event.target as HTMLImageElement;
        const scaleIncrement: number = 0.1;
        const currentScale = img.style.transform.match(/scale\(([^)]+)\)/);

        let scale: number = currentScale ? parseFloat(currentScale[1]) : 1;

        if (event.deltaY < 0) {
            scale += scaleIncrement; // Zoom in
        } else {
            scale -= scaleIncrement; // Zoom out
        }

        scale = Math.max(1, Math.min(scale, 5)); // Adjust min and max scale as needed
        img.style.transform = `scale(${scale})`;
    });
}

function openGridModal(evt: Event): void {
    // Get the clicked image and determine its index
    const clickedImg = evt.currentTarget as HTMLImageElement;
    const indexAttr = clickedImg.getAttribute("data-index");
    currentGridImageIndex = indexAttr ? parseInt(indexAttr, 10) : 0;
    updateGridModalImage();
    $("#grid-image-modal").show();
}

function updateGridModalImage(): void {
    // Get the list of grid images from the current grid DOM.
    const gridImages = $(".image-grid img");
    if (gridImages.length === 0) {
        console.warn("No grid images found.");
        return;
    }
    // Wrap-around logic.
    if (currentGridImageIndex < 0) {
        currentGridImageIndex = gridImages.length - 1;
    } else if (currentGridImageIndex >= gridImages.length) {
        currentGridImageIndex = 0;
    }
    const newImgElement = gridImages.get(currentGridImageIndex) as HTMLImageElement;
    const filePath = newImgElement.src;
    const thumbFileName = filePath.split("/").pop();
    const pathDir = filePath.slice(0, -(thumbFileName?.length ?? 0));
    const fileName = thumbFileName?.slice(0, -".thumb.jpg".length).concat(".png");

    // Update the modal image.
    (document.getElementById("grid-modal-image") as HTMLImageElement).src = pathDir + fileName;

    // Fetch and update the metadata.
    $.getJSON("/get-image-metadata/" + fileName, function (metadata) {
        const metadataDiv = document.getElementById("grid-info-panel") as HTMLElement;
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
        let copyPromptButton = document.getElementById("copy-prompt-btn") as HTMLButtonElement;
        if (!copyPromptButton) {
            copyPromptButton = document.createElement("button");
            copyPromptButton.id = "copy-prompt-btn";
            copyPromptButton.textContent = "Copy Prompt";
            metadataDiv.appendChild(copyPromptButton);
        }

        // Add listener (or rebind) for the copy action.
        copyPromptButton.onclick = () => {
            console.log("Metadata received:", metadata);
            const promptTextarea = document.getElementById("prompt") as HTMLTextAreaElement;
            const negativePromptTextarea = document.getElementById("negative_prompt") as HTMLTextAreaElement;
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

function previousGridImage(): void {
    currentGridImageIndex -= 1;
    updateGridModalImage();
}

function nextGridImage(): void {
    currentGridImageIndex += 1;
    updateGridModalImage();
}

function closeGridModal(): void {
    $("#grid-image-modal").hide();
}

function closeGenModal(): void {
    document.getElementById("image-modal")!.style.display = "none";
}

//////////////////////
////   Chat tab   ////
//////////////////////

type ThreadData = {
    id: string;
    created_at: number;
    metadata: { [key: string]: string };
    object: string;
};

type ConversationData = {
    data: ThreadData;
    chat_name: string;
    last_update: number;
};

let allConversations: { [key: string]: ConversationData } = {};
var currentThreadId: string = "";

function chatTabLoaded(): void {
    refreshConversationList();
}

function refreshConversationList(): void {
    const conversationsList = document.getElementById("conversations-list") as HTMLDivElement;

    $.get("/get-all-conversations", (response: string) => {
        console.log("convos pulled");
        let conversations: { [key: string]: ConversationData } = JSON.parse(response);
        allConversations = conversations;
        let children: Node[] = [];
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

function onConversationSelected(this: HTMLDivElement, ev: MouseEvent) {
    let conversationId = this.getAttribute("data-conversation-id") as string;
    console.log(`conversation: ${conversationId}`);
    const chatInput = document.getElementById("chat-input") as HTMLTextAreaElement;

    $.ajax({
        type: "GET",
        url: "/chat?thread_id=" + encodeURIComponent(conversationId),
        contentType: "application/json",
        scriptCharset: "utf-8",
        success: (response: string) => {
            let chatData: MessageHistory = JSON.parse(response);
            chatInput.value = ""; // Clear input field
            refreshChatMessages(chatData.messages);
            currentThreadId = chatData.threadId;
        },
        error: (error) => {
            console.error("Error:", error);
        },
    });
}

type ChatMessage = {
    role: string;
    text: string;
};
type MessageHistory = {
    type: string;
    text: string;
    delta: string;
    snapshot: string;
    threadId: string;
    status: string;
    messages: ChatMessage[];
};

async function fetchWithStreaming(url: string, data: any, processChunk: (chunkData: any) => void) {
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
                if (done) break;
                const chunk = decoder.decode(value, { stream: true });
                resultString += chunk;

                const parts = resultString.split("␆␄");
                resultString = parts.pop() as string; // Handle the rest in the next iteration.

                parts.forEach((part) => {
                    if (part) {
                        try {
                            processChunk(part);
                        } catch (e) {
                            console.error("Error parsing JSON chunk:", e);
                        }
                    }
                });
            }
        } else {
            console.log("Response body is not readable");
        }
    } catch (error) {
        console.error("Fetch error:", error);
    }
}

// "queued", "in_progress", "requires_action", "cancelling", "cancelled", "failed", "completed", "expired"
let prettyStatuses: { [key: string]: string } = {
    queued: "in queue",
    in_progress: "in progress...",
    requires_action: "processing action...",
};

var cachedMessageList: ChatMessage[];
var progressNum = 0;

function sendChatMessage(): void {
    var chatName: string = "";
    if (currentThreadId) {
        chatName = allConversations[currentThreadId].chat_name;
    }
    while (!chatName) {
        chatName = prompt("Please title this conversation (max 30 chars):", "Conversation") as string;
        if (chatName.length > 30) {
            chatName = "";
        }
    }
    const chatInput = document.getElementById("chat-input") as HTMLTextAreaElement;
    const sendChatButton = document.getElementById("send-chat") as HTMLInputElement;
    const chatStatusText = document.getElementById("chat-current-status") as HTMLDivElement;
    const userMessage = chatInput.value.trim();
    if (!userMessage) return;

    // Send the message to the server
    sendChatButton.disabled = true;
    fetchWithStreaming(
        "/chat",
        {
            user_input: userMessage,
            chat_name: chatName,
            thread_id: currentThreadId,
        },
        (chunkData) => {
            console.log("succeess");
            var parsedData = JSON.parse(chunkData);
            // Weird hack to prevent "too stringified" json blobs getting converted to just strings.
            let chatData: MessageHistory = typeof parsedData === "string" ? JSON.parse(parsedData) : parsedData;

            if (chatData.type == "message_list") {
                chatStatusText.textContent = "In queue...";
                currentThreadId = chatData.threadId;
                cachedMessageList = chatData.messages;
                chatInput.value = ""; // Clear input field
                refreshChatMessages(cachedMessageList);
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
            } else if (chatData.type == "text_created") {
                cachedMessageList.push({ role: "assistant", text: "" } as ChatMessage);
                chatStatusText.textContent = "In progress...";
            } else if (chatData.type == "text_delta") {
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
            } else if (chatData.type == "text_done") {
                sendChatButton.disabled = false;
                chatStatusText.textContent = "Awaiting Input...";
                progressNum = 0;
            }
            // TODO: Hook up the tool-based outputs
        },
    );
}

showdown.extension("highlight", function () {
    return [
        {
            type: "output",
            filter: function (text, converter, options) {
                var left = "<pre><code\\b[^>]*>",
                    right = "</code></pre>",
                    flags = "g";
                var replacement = function (_wholeMatch: string, match: string, left: string, right: string) {
                    var lang = (left.match(/class=\"([^ \"]+)/) || [])[1];
                    left = left.slice(0, 18) + "hljs " + left.slice(18);
                    if (lang) {
                        left = left.slice(0, 18) + "hljs " + left.slice(18);
                        if (hljs.getLanguage(lang)) {
                            return left + hljs.highlight(lang, utils.unescapeHTML(match)).value + right;
                        } else {
                            return left + hljs.highlightAuto(utils.unescapeHTML(match)).value + right;
                        }
                    } else {
                        left = left.slice(0, 10) + ' class="hljs" ' + left.slice(10);
                        return left + hljs.highlightAuto(utils.unescapeHTML(match)).value + right;
                    }
                };
                return showdown.helper.replaceRecursiveRegExp(text, replacement, left, right, flags);
            },
        },
    ];
});

function updateMostRecentChatMessage(messages: ChatMessage[]): void {
    const chatHistory = document.getElementById("chat-history") as HTMLDivElement;
    var message = messages[messages.length - 1];
    var converter = new showdown.Converter({
        strikethrough: true,
        smoothLivePreview: true,
        tasklists: true,
        extensions: ["highlight"],
    }),
        text = message.text,
        html = converter.makeHtml(text);
    if (chatHistory.children.length < messages.length) {
        const div = document.createElement("div") as HTMLDivElement;
        div.className = "ai-message";
        div.innerHTML = utils.unescapeHTML(html);
        chatHistory.appendChild(div);
    } else {
        var lastChildDiv = chatHistory.lastChild as HTMLDivElement;
        lastChildDiv.innerHTML = utils.unescapeHTML(html);
    }
    chatHistory.scrollTop = chatHistory.scrollHeight; // Scroll to bottom
}

function refreshChatMessages(messages: ChatMessage[]): void {
    const chatHistory = document.getElementById("chat-history") as HTMLDivElement;
    chatHistory.innerHTML = "";
    // Display AI response in chat history
    messages.forEach((message) => {
        console.log(message.text);
        var converter = new showdown.Converter({
            strikethrough: true,
            smoothLivePreview: true,
            tasklists: true,
            extensions: ["highlight"],
        }),
            text = message.text,
            html = converter.makeHtml(text);
        console.log(html);
        chatHistory.innerHTML += `<div class="ai-message">${utils.unescapeHTML(html)}</div>`;
    });
    chatHistory.scrollTop = chatHistory.scrollHeight; // Scroll to bottom
}
