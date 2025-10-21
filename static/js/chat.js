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
        messageDiv.className = message.role === "user" ? "user-message" : "ai-message";
        messageDiv.innerHTML = utils.unescapeHTML(html);
        // Add reasoning button and metadata for assistant messages
        if (message.role === "assistant") {
            addReasoningButton(messageDiv, index);
            addMessageMetadata(messageDiv, message);
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
 * Add metadata display to assistant messages
 */
function addMessageMetadata(messageElement, message) {
    try {
        const metadataContainer = document.createElement("div");
        metadataContainer.className = "message-metadata";
        const metadataItems = [];
        // Add reasoning level indicator
        if (message.reasoning_level) {
            const reasoningLevel = message.reasoning_level;
            const reasoningDisplay = formatReasoningLevel(reasoningLevel);
            metadataItems.push(`<span class="metadata-reasoning" title="Reasoning Level">${reasoningDisplay}</span>`);
        }
        // Add model indicator
        if (message.model) {
            const modelDisplay = formatModelName(message.model);
            metadataItems.push(`<span class="metadata-model" title="AI Model">${modelDisplay}</span>`);
        }
        // Add agent preset indicator (if not default)
        if (message.agent_preset_id && message.agent_preset_id !== 'default') {
            metadataItems.push(`<span class="metadata-preset" title="Agent Preset">Custom Agent</span>`);
        }
        if (metadataItems.length > 0) {
            metadataContainer.innerHTML = metadataItems.join(' • ');
            messageElement.appendChild(metadataContainer);
        }
    }
    catch (error) {
        console.warn("Failed to add message metadata:", error);
        // Continue without metadata - chat functionality should not be affected
    }
}
/**
 * Format reasoning level for display
 */
function formatReasoningLevel(level) {
    switch (level) {
        case 'high':
            return '🧠 High';
        case 'medium':
            return '⚡ Medium';
        case 'low':
            return '💨 Low';
        default:
            return level;
    }
}
/**
 * Format model name for display
 */
function formatModelName(model) {
    switch (model) {
        case 'gpt-5':
            return 'GPT-5';
        case 'gpt-5-mini':
            return 'GPT-5 Mini';
        case 'gpt-5-pro':
            return 'GPT-5 Pro';
        default:
            return model;
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
    const reasoningContent = document.getElementById("reasoning-content");
    const searchContent = document.getElementById("search-content");
    const loading = document.getElementById("reasoning-loading");
    const error = document.getElementById("reasoning-error");
    if (!modal || !reasoningContent || !searchContent || !loading || !error) {
        console.error("Reasoning modal elements not found");
        showReasoningError("Modal interface not available");
        return;
    }
    // Reset modal state
    reasoningContent.style.display = "none";
    searchContent.style.display = "none";
    error.style.display = "none";
    loading.style.display = "block";
    modal.style.display = "block";
    // Initialize tab functionality
    initializeModalTabs();
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
            reasoningContent.style.display = "block";
            // Display web search data if available
            if (data.web_searches && data.web_searches.length > 0) {
                displayWebSearchData(data.web_searches);
                enableSearchTab();
            }
            else {
                disableSearchTab();
            }
            // Show reasoning tab by default
            switchModalTab('reasoning');
        }
        else if (data.reasoning && data.reasoning.summary_parts && data.reasoning.summary_parts.length > 0) {
            // Fallback to summary parts if complete summary is not available
            const fallbackData = {
                ...data.reasoning,
                complete_summary: data.reasoning.summary_parts.join('\n\n')
            };
            displayReasoningData(fallbackData);
            reasoningContent.style.display = "block";
            // Display web search data if available
            if (data.web_searches && data.web_searches.length > 0) {
                displayWebSearchData(data.web_searches);
                enableSearchTab();
            }
            else {
                disableSearchTab();
            }
            // Show reasoning tab by default
            switchModalTab('reasoning');
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
/**
 * Initialize modal tab functionality
 */
function initializeModalTabs() {
    const tabButtons = document.querySelectorAll('.tab-button');
    tabButtons.forEach(button => {
        button.addEventListener('click', (e) => {
            const target = e.target;
            const tabName = target.getAttribute('data-tab');
            if (tabName && !target.disabled) {
                switchModalTab(tabName);
            }
        });
    });
}
/**
 * Switch between modal tabs
 */
function switchModalTab(tabName) {
    // Update tab buttons
    const tabButtons = document.querySelectorAll('.tab-button');
    tabButtons.forEach(button => {
        const buttonTab = button.getAttribute('data-tab');
        if (buttonTab === tabName) {
            button.classList.add('active');
        }
        else {
            button.classList.remove('active');
        }
    });
    // Update tab content
    const tabContents = document.querySelectorAll('.tab-content');
    tabContents.forEach(content => {
        const contentTab = content.getAttribute('data-tab');
        if (contentTab === tabName) {
            content.style.display = 'block';
        }
        else {
            content.style.display = 'none';
        }
    });
}
/**
 * Enable the search tab
 */
function enableSearchTab() {
    const searchTabButton = document.querySelector('.tab-button[data-tab="search"]');
    if (searchTabButton) {
        searchTabButton.disabled = false;
        searchTabButton.style.opacity = '1';
    }
}
/**
 * Disable the search tab
 */
function disableSearchTab() {
    const searchTabButton = document.querySelector('.tab-button[data-tab="search"]');
    if (searchTabButton) {
        searchTabButton.disabled = true;
        searchTabButton.style.opacity = '0.5';
    }
}
/**
 * Display web search data in the search tab
 */
function displayWebSearchData(searchData) {
    const searchContent = document.getElementById("search-content");
    if (!searchContent)
        return;
    try {
        if (!searchData || searchData.length === 0) {
            searchContent.innerHTML = `
                <div class="no-search-data">
                    No web search data available for this message.
                </div>
            `;
            return;
        }
        let searchHtml = `
            <div class="search-summary">
                <h3>Web Search Activity</h3>
            </div>
        `;
        searchData.forEach((search, index) => {
            const query = escapeHtml(search.query || 'Unknown query');
            const status = search.status || 'unknown';
            const timestamp = search.timestamp ? new Date(search.timestamp * 1000).toLocaleString() : 'Unknown time';
            const actionType = search.action_type || 'search';
            searchHtml += `
                <div class="search-item">
                    <div class="search-query">${query}</div>
                    <div class="search-status ${status}">${formatSearchStatus(status)}</div>
                    <div class="search-details">
                        <div>Action: ${escapeHtml(actionType)}</div>
                        ${search.sources ? `<div>Sources: ${escapeHtml(search.sources.join(', '))}</div>` : ''}
                    </div>
                    <div class="search-timestamp">${timestamp}</div>
                </div>
            `;
        });
        searchContent.innerHTML = searchHtml;
    }
    catch (error) {
        console.error("Error displaying web search data:", error);
        searchContent.innerHTML = `
            <div class="error-message">
                Failed to display web search data
            </div>
        `;
    }
}
/**
 * Format search status for display
 */
function formatSearchStatus(status) {
    switch (status) {
        case 'completed':
            return 'Completed';
        case 'in_progress':
            return 'In Progress';
        case 'searching':
            return 'Searching';
        case 'failed':
            return 'Failed';
        default:
            return 'Unknown';
    }
}
/**
 * Handle web search status updates
 */
export function handleWebSearchStatus(status) {
    try {
        let message = "";
        let isActive = false;
        switch (status.type) {
            case 'search_started':
                message = "Searching...";
                isActive = true;
                break;
            case 'search_in_progress':
                message = "Searching...";
                isActive = true;
                break;
            case 'search_completed':
                message = "Search done";
                isActive = false;
                break;
        }
        updateStatusDisplay(message, isActive, 'search');
        // Auto-hide completed status after a brief delay
        if (status.type === 'search_completed') {
            setTimeout(() => {
                clearStatusDisplay('search');
            }, 1500);
        }
    }
    catch (error) {
        console.warn("Error handling web search status:", error);
        // Continue without status display - don't block chat functionality
    }
}
/**
 * Handle reasoning status updates
 */
export function handleReasoningStatus(status) {
    try {
        let message = "";
        let isActive = false;
        switch (status.type) {
            case 'reasoning_started':
                message = "Thinking...";
                isActive = true;
                break;
            case 'reasoning_in_progress':
                message = "Thinking...";
                isActive = true;
                break;
            case 'reasoning_completed':
                message = "Thinking done";
                isActive = false;
                break;
        }
        updateStatusDisplay(message, isActive, 'reasoning');
        // Auto-hide completed status after a brief delay
        if (status.type === 'reasoning_completed') {
            setTimeout(() => {
                clearStatusDisplay('reasoning');
            }, 1500);
        }
    }
    catch (error) {
        console.warn("Error handling reasoning status:", error);
        // Continue without status display - don't block chat functionality
    }
}
/**
 * Update the status display in the chat interface
 */
function updateStatusDisplay(message, isActive, statusType) {
    try {
        // Get or create status container
        let statusContainer = document.getElementById('chat-status-container');
        if (!statusContainer) {
            statusContainer = document.createElement('div');
            statusContainer.id = 'chat-status-container';
            statusContainer.className = 'chat-status-container';
            // Insert before chat input
            const chatInput = document.getElementById('chat-input');
            if (chatInput && chatInput.parentNode) {
                chatInput.parentNode.insertBefore(statusContainer, chatInput);
            }
        }
        // Get or create status element for this type
        let statusElement = document.getElementById(`chat-status-${statusType}`);
        if (!statusElement) {
            statusElement = document.createElement('div');
            statusElement.id = `chat-status-${statusType}`;
            statusElement.className = `chat-status-item chat-status-${statusType}`;
            statusContainer.appendChild(statusElement);
        }
        // Update status content
        statusElement.textContent = message;
        statusElement.style.display = 'block';
        // Add/remove active class for styling
        if (isActive) {
            statusElement.classList.add('active');
        }
        else {
            statusElement.classList.remove('active');
        }
    }
    catch (error) {
        console.warn("Error updating status display:", error);
        // Continue without status display - don't block chat functionality
    }
}
/**
 * Clear status display for a specific type
 */
function clearStatusDisplay(statusType) {
    try {
        const statusElement = document.getElementById(`chat-status-${statusType}`);
        if (statusElement) {
            statusElement.style.display = 'none';
            statusElement.classList.remove('active');
        }
    }
    catch (error) {
        console.warn("Error clearing status display:", error);
        // Continue silently - don't block chat functionality
    }
}
