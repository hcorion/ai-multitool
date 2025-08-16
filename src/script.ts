import * as utils from "./utils.js";
import * as chat from "./chat.js";

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

    document.getElementById("generationTab")!.click();

    // Just refresh the image gen provider
    providerChanged();
});

function keyDownEvent(evt: KeyboardEvent) {
    if (evt.code == "ArrowRight") {
        nextGridImage();
    } else if (evt.code == "ArrowLeft") {
        previousGridImage();
    }
}

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
        (document.getElementById("size") as HTMLSelectElement).selectedIndex = 0;
    } else if ((selection.value == "stabilityai")) {
        $(".openai").hide();
        $(".novelai").hide();
        $(".stabilityai").show();
        modelChanged(selection.value);
    } else if ((selection.value == "novelai")) {
        $(".openai").hide();
        $(".stabilityai").hide();
        $(".novelai").show();
        // This is ugly, but index #3 is where the novelai size options start
        (document.getElementById("size") as HTMLSelectElement).selectedIndex = 3;
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
    if (provider == "stabilityai") {
        const selection = document.getElementById("model") as HTMLSelectElement;
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
        throw new Error(`modelChanged called with unsupported provider ${provider}`);
    }

}

function updateCharacterCount(): void {
    const promptInput = document.getElementById("prompt") as HTMLInputElement;
    const charCount: number = promptInput.value.length;
    const charCountDisplay = document.getElementById("charCount") as HTMLDivElement;
    charCountDisplay.textContent = `${charCount} / 4000`;
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
        if (currentPage <= 1) {
            currentGridImageIndex = 0;
            return;
        }
        previousGrid()
        currentGridImageIndex = gridImages.length - 1;
    } else if (currentGridImageIndex >= gridImages.length) {
        if (currentPage >= totalPages) {
            currentGridImageIndex = gridImages.length - 1;
            return;
        }
        nextGrid()
        currentGridImageIndex = 0;
    }
    const newImgElement = gridImages.get(currentGridImageIndex) as HTMLImageElement;
    const filePath = newImgElement.src;
    const thumbFileName = filePath.split("/").pop();
    const pathDir = filePath.slice(0, -(thumbFileName?.length ?? 0));
    // This works with .thumb.png as well since we just trim the length regardless of the contents
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
            
            // Add special styling for character prompts
            if (key.match(/^Character \d+ (Prompt|Negative)$/)) {
                infoItem.classList.add("character-prompt-item");
            }
            
            infoItem.textContent = key + ":";
            metadataDiv.appendChild(infoItem);

            const infoValue = document.createElement("div");
            infoValue.className = "prompt-value";
            
            // Add special styling for character prompt values
            if (key.match(/^Character \d+ (Prompt|Negative)$/)) {
                infoValue.classList.add("character-prompt-value");
            }
            
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
            const promptTextarea = document.getElementById("prompt") as HTMLTextAreaElement;
            const negativePromptTextarea = document.getElementById("negative_prompt") as HTMLTextAreaElement;
            // Try various key cases in case the keys are not lowercase.
            const promptText = metadata["Prompt"];
            const negativePromptText = metadata["Negative Prompt"] || "";
            promptTextarea.value = promptText;
            negativePromptTextarea.value = negativePromptText;
            
            // Handle character prompt metadata if present
            // Extract character prompts from metadata and populate character interface when available
            const characterPrompts: Array<{positive: string, negative: string}> = [];
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
                (window as any).pendingCharacterPrompts = characterPrompts;
                console.log("Character prompts found in metadata:", characterPrompts);
            }
            
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

function toggleShowAdvanced(event: Event): void {
    console.log("show advanced")
    const advancedDropdown = document.getElementById("advanced-dropdown") as HTMLElement;
    // Toggle visibility based on current state.
    if (advancedDropdown.style.display === "none") {
        advancedDropdown.style.display = "block";
    } else {
        advancedDropdown.style.display = "none";
        // Also reset the custom input toggle and hide its container when closing.
        const inputToggle = document.getElementById("advanced-generate-grid") as HTMLInputElement;
        if (inputToggle) {
            inputToggle.checked = false;
        }
        const inputContainer = document.querySelector(".advanced-input-container") as HTMLElement;
        if (inputContainer) {
            inputContainer.style.display = "none";
        }
    }
}

function toggleAdvancedInput(event: Event): void {
    const inputToggle = event.target as HTMLInputElement;
    const inputContainer = document.querySelector(".advanced-input-container") as HTMLElement;
    const advancedOption = document.getElementById("grid-prompt-file") as HTMLInputElement;

    if (inputToggle.checked) {
        inputContainer.style.display = "block";
        advancedOption.disabled = false;
    } else {
        inputContainer.style.display = "none";
        advancedOption.disabled = true;
    }
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

function updateConversationTitle(conversationId: string, newTitle: string): void {
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
        success: (response: any) => {
            if (response.success) {
                console.log("Title updated successfully:", newTitle);
                // Update local conversations cache with the server response
                allConversations = response.conversations;
                // Refresh the conversation list display
                refreshConversationListFromCache();
            } else {
                console.error("Failed to update title:", response.error);
            }
        },
        error: (xhr: JQueryXHR, status: string, error: string) => {
            console.error("Error updating conversation title:", error);
        }
    });
}

function refreshConversationListFromCache(): void {
    /**
     * Refresh the conversation list display using cached conversation data.
     * This is more efficient than making another server request.
     */
    const conversationsList = document.getElementById("conversations-list") as HTMLDivElement;

    let children: Node[] = [];
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

function scheduleConversationTitleRefresh(conversationId: string): void {
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
            $.get("/get-all-conversations", (response: string) => {
                try {
                    let conversations: { [key: string]: ConversationData } = JSON.parse(response);
                    
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
                    
                } catch (error) {
                    console.error("Error parsing conversation list response:", error);
                    // Continue checking despite the error
                    setTimeout(checkForTitleUpdate, checkInterval);
                }
            }).fail((xhr, status, error) => {
                console.error("Error fetching conversation list:", error);
                // Continue checking despite the error
                setTimeout(checkForTitleUpdate, checkInterval);
            });
        } else {
            // Title has already been updated, stop checking
            console.log(`Title already updated for conversation ${conversationId}: ${allConversations[conversationId].chat_name}`);
        }
    };
    
    // Start the first check after a short delay to give the server time to generate the title
    setTimeout(checkForTitleUpdate, 2000); // Wait 2 seconds before first check
}

function onConversationSelected(this: HTMLDivElement, ev: MouseEvent) {
    let conversationId = this.getAttribute("data-conversation-id") as string;
    console.log(`conversation: ${conversationId}`);
    const chatInput = document.getElementById("chat-input") as HTMLTextAreaElement;

    chat.onConversationSelected(conversationId, (chatData: chat.MessageHistory) => {
        chatInput.value = ""; // Clear input field
        chat.refreshChatMessages(chatData.messages);
        currentThreadId = chatData.threadId;
    })
}

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

var cachedMessageList: chat.ChatMessage[];
var progressNum = 0;

function sendChatMessage(): void {
    var chatName: string = "";
    if (currentThreadId) {
        // Use existing conversation title
        chatName = allConversations[currentThreadId].chat_name;
    } else {
        // For new conversations, use a default title (server will generate the actual title)
        chatName = "New Chat";
    }
    const chatInput = document.getElementById("chat-input") as HTMLTextAreaElement;
    const sendChatButton = document.getElementById("send-chat") as HTMLInputElement;
    const chatStatusText = document.getElementById("chat-current-status") as HTMLDivElement;
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
            let chatData: chat.MessageHistory = typeof parsedData === "string" ? JSON.parse(parsedData) : parsedData;

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
            } else if (chatData.type == "text_created") {
                cachedMessageList.push({ role: "assistant", text: "" } as chat.ChatMessage);
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

function updateMostRecentChatMessage(messages: chat.ChatMessage[]): void {
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