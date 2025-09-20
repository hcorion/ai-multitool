import * as utils from "./utils.js";
/**
 * Load conversation data for the specified conversation ID
 */
export async function onConversationSelected(conversationId) {
    return new Promise((resolve, reject) => {
        $.ajax({
            type: "GET",
            url: "/chat?thread_id=" + encodeURIComponent(conversationId),
            contentType: "application/json",
            scriptCharset: "utf-8",
            success: (response) => {
                try {
                    const chatData = JSON.parse(response);
                    resolve(chatData);
                }
                catch (error) {
                    reject(new Error(`Failed to parse chat data: ${error}`));
                }
            },
            error: (error) => {
                reject(new Error(`Error loading conversation: ${error}`));
            },
        });
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
                    if (lang) {
                        left = left.slice(0, 18) + "hljs " + left.slice(18);
                        if (hljs.getLanguage(lang)) {
                            return left + hljs.highlight(lang, utils.unescapeHTML(match)).value + right;
                        }
                        else {
                            return left + hljs.highlightAuto(utils.unescapeHTML(match)).value + right;
                        }
                    }
                    else {
                        left = left.slice(0, 10) + ' class="hljs" ' + left.slice(10);
                        return left + hljs.highlightAuto(utils.unescapeHTML(match)).value + right;
                    }
                };
                return showdown.helper.replaceRecursiveRegExp(text, replacement, left, right, flags);
            },
        },
    ];
});
/**
 * Check if the chat container is scrolled to or near the bottom
 */
function isScrolledToBottom(element, threshold = 50) {
    return element.scrollTop + element.clientHeight >= element.scrollHeight - threshold;
}
/**
 * Conditionally scroll to bottom only if user is already at the bottom
 */
function smartScrollToBottom(element) {
    if (isScrolledToBottom(element)) {
        element.scrollTop = element.scrollHeight;
    }
}
/**
 * Render chat messages with markdown formatting and reasoning buttons
 */
export function refreshChatMessages(messages) {
    const chatHistory = document.getElementById("chat-history");
    const wasAtBottom = isScrolledToBottom(chatHistory);
    chatHistory.innerHTML = "";
    // Display AI response in chat history
    messages.forEach((message, index) => {
        var converter = new showdown.Converter({
            strikethrough: true,
            smoothLivePreview: true,
            tasklists: true,
            tables: true,
            extensions: ["highlight"],
        }), text = message.text, html = converter.makeHtml(text);
        const messageDiv = document.createElement("div");
        messageDiv.className = "ai-message";
        messageDiv.innerHTML = utils.unescapeHTML(html);
        // Add reasoning button for assistant messages
        if (message.role === "assistant") {
            addReasoningButton(messageDiv, index);
        }
        chatHistory.appendChild(messageDiv);
    });
    // Only scroll to bottom if user was already at the bottom
    if (wasAtBottom) {
        chatHistory.scrollTop = chatHistory.scrollHeight;
    }
}
/**
 * Add reasoning inspection button to assistant messages
 */
function addReasoningButton(messageElement, messageIndex) {
    try {
        const reasoningButton = document.createElement("button");
        reasoningButton.className = "reasoning-button";
        reasoningButton.innerHTML = "i";
        reasoningButton.title = "View reasoning";
        reasoningButton.setAttribute("data-message-index", messageIndex.toString());
        reasoningButton.addEventListener("click", (e) => {
            e.preventDefault();
            e.stopPropagation();
            // Disable button during request to prevent multiple clicks
            reasoningButton.disabled = true;
            reasoningButton.style.opacity = "0.6";
            showReasoningModal(messageIndex);
            // Re-enable button after a short delay
            setTimeout(() => {
                reasoningButton.disabled = false;
                reasoningButton.style.opacity = "1";
            }, 1000);
        });
        messageElement.appendChild(reasoningButton);
    }
    catch (error) {
        console.warn("Failed to add reasoning button:", error);
        // Continue without reasoning button - chat functionality should not be affected
    }
}
/**
 * Display reasoning data modal for the specified message
 */
function showReasoningModal(messageIndex) {
    // Get current conversation ID - this should be available globally
    const conversationId = window.currentThreadId;
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
        showReasoningError("Modal interface not available");
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
            displayReasoningData(data.reasoning);
            content.style.display = "block";
        }
        else if (data.reasoning && data.reasoning.summary_parts && data.reasoning.summary_parts.length > 0) {
            // Fallback to summary parts if complete summary is not available
            const fallbackData = {
                ...data.reasoning,
                complete_summary: data.reasoning.summary_parts.join('\n\n')
            };
            displayReasoningData(fallbackData);
            content.style.display = "block";
        }
        else {
            showReasoningError("No reasoning data available for this message");
        }
    })
        .catch(err => {
        clearTimeout(timeoutId);
        loading.style.display = "none";
        // Handle different types of errors
        if (err.name === 'AbortError') {
            showReasoningError("Request timed out - please try again");
        }
        else if (err.name === 'TypeError' && err.message.includes('fetch')) {
            showReasoningError("Network error - please check your connection");
        }
        else {
            showReasoningError(`Failed to load reasoning data: ${err.message}`);
        }
        console.error("Reasoning modal error:", err);
    });
}
/**
 * Render reasoning data content in the modal with proper formatting
 */
function displayReasoningData(reasoningData) {
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
        showReasoningError("Failed to display reasoning data");
    }
}
/**
 * Escape HTML special characters to prevent XSS attacks
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
/**
 * Display error message in reasoning modal
 */
function showReasoningError(message) {
    console.error(message);
    const error = document.getElementById("reasoning-error");
    if (!error)
        return;
    error.textContent = message;
    error.style.display = "block";
}
/**
 * Hide the reasoning inspection modal
 */
export function hideReasoningModal() {
    const modal = document.getElementById("reasoning-modal");
    if (modal) {
        modal.style.display = "none";
    }
}
