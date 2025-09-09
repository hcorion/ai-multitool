import * as utils from "./utils.js";

export type ChatMessage = {
    role: string;
    text: string;
};
export type MessageHistory = {
    type: string;
    text: string;
    delta: string;
    snapshot: string;
    threadId: string;
    status: string;
    messages: ChatMessage[];
};

export function onConversationSelected(conversationId: string, successCallback: (chatData: MessageHistory) => void): void {
    console.log(`conversation: ${conversationId}`);
    $.ajax({
        type: "GET",
        url: "/chat?thread_id=" + encodeURIComponent(conversationId),
        contentType: "application/json",
        scriptCharset: "utf-8",
        success: (response: string) => {
            let chatData: MessageHistory = JSON.parse(response);
            successCallback(chatData);
        },
        error: (error) => {
            throw new Error(`Error: ${error}`);
        },
    });
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

export function refreshChatMessages(messages: ChatMessage[]): void {
    const chatHistory = document.getElementById("chat-history") as HTMLDivElement;
    chatHistory.innerHTML = "";
    // Display AI response in chat history
    messages.forEach((message, index) => {
        var converter = new showdown.Converter({
            strikethrough: true,
            smoothLivePreview: true,
            tasklists: true,
            tables: true,
            extensions: ["highlight"],
        }),
            text = message.text,
            html = converter.makeHtml(text);
        
        const messageDiv = document.createElement("div");
        messageDiv.className = "ai-message";
        messageDiv.innerHTML = utils.unescapeHTML(html);
        
        // Add reasoning button for assistant messages
        if (message.role === "assistant") {
            addReasoningButton(messageDiv, index);
        }
        
        chatHistory.appendChild(messageDiv);
    });
    chatHistory.scrollTop = chatHistory.scrollHeight; // Scroll to bottom
}

function addReasoningButton(messageElement: HTMLElement, messageIndex: number): void {
    const reasoningButton = document.createElement("button");
    reasoningButton.className = "reasoning-button";
    reasoningButton.innerHTML = "i";
    reasoningButton.title = "View reasoning";
    reasoningButton.setAttribute("data-message-index", messageIndex.toString());
    
    reasoningButton.addEventListener("click", (e) => {
        e.preventDefault();
        e.stopPropagation();
        showReasoningModal(messageIndex);
    });
    
    messageElement.appendChild(reasoningButton);
}

function showReasoningModal(messageIndex: number): void {
    // Get current conversation ID - this should be available globally
    const conversationId = (window as any).currentThreadId;
    if (!conversationId) {
        showReasoningError("No conversation selected");
        return;
    }
    
    // Show modal with loading state
    const modal = document.getElementById("reasoning-modal");
    const content = document.getElementById("reasoning-content");
    const loading = document.getElementById("reasoning-loading");
    const error = document.getElementById("reasoning-error");
    
    if (!modal || !content || !loading || !error) {
        console.error("Reasoning modal elements not found");
        return;
    }
    
    // Reset modal state
    content.style.display = "none";
    error.style.display = "none";
    loading.style.display = "block";
    modal.style.display = "block";
    
    // Fetch reasoning data
    fetch(`/chat/reasoning/${conversationId}/${messageIndex}`)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            return response.json();
        })
        .then(data => {
            loading.style.display = "none";
            if (data.reasoning && data.reasoning.complete_summary) {
                displayReasoningData(data.reasoning);
                content.style.display = "block";
            } else {
                showReasoningError("No reasoning data available for this message");
            }
        })
        .catch(err => {
            loading.style.display = "none";
            showReasoningError(`Failed to load reasoning data: ${err.message}`);
        });
}

function displayReasoningData(reasoningData: any): void {
    const content = document.getElementById("reasoning-content");
    if (!content) return;
    
    content.innerHTML = `
        <div class="reasoning-summary">
            <h3>AI Reasoning Process</h3>
            <div class="reasoning-text">${reasoningData.complete_summary.replace(/\n/g, '<br>')}</div>
        </div>
    `;
}

function showReasoningError(message: string): void {
    const error = document.getElementById("reasoning-error");
    if (!error) return;
    
    error.textContent = message;
    error.style.display = "block";
}

export function hideReasoningModal(): void {
    const modal = document.getElementById("reasoning-modal");
    if (modal) {
        modal.style.display = "none";
    }
}
