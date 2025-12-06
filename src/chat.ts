import * as utils from "./utils.js";

export type ChatMessage = {
    role: string;
    text: string;
    timestamp?: number;
    response_id?: string;
    reasoning_data?: any;
    agent_preset_id?: string;
    model?: string;
    reasoning_level?: string;
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

export interface WebSearchStatus {
    type: 'search_started' | 'search_in_progress' | 'search_completed';
    item_id: string;
    output_index: number;
    sequence_number: number;
    status?: string;
}

export interface ReasoningStatus {
    type: 'reasoning_started' | 'reasoning_in_progress' | 'reasoning_completed';
    part_id?: string;
    status?: string;
}

/**
 * Load conversation data from server.
 * @param conversationId - Conversation ID to load
 * @returns Promise with conversation data
 */
export async function onConversationSelected(conversationId: string): Promise<MessageHistory> {
    return new Promise((resolve, reject) => {
        $.ajax({
            type: "GET",
            url: "/chat?thread_id=" + encodeURIComponent(conversationId),
            contentType: "application/json",
            scriptCharset: "utf-8",
            success: (response: string | MessageHistory) => {
                try {
                    // Handle both string and object responses
                    const chatData: MessageHistory = typeof response === 'string' 
                        ? JSON.parse(response) 
                        : response;
                    
                    // Validate response structure
                    if (!chatData || typeof chatData !== 'object') {
                        throw new Error('Invalid response format');
                    }
                    
                    resolve(chatData);
                } catch (error) {
                    reject(new Error(`Failed to parse chat data: ${error}`));
                }
            },
            error: (xhr: JQuery.jqXHR) => {
                const errorMessage = xhr.responseJSON?.error_message 
                    || xhr.responseJSON?.error 
                    || xhr.statusText 
                    || 'Unknown error';
                reject(new Error(`Error loading conversation: ${errorMessage}`));
            },
        });
    });
}


showdown.extension("highlight", function () {
    return [
        {
            type: "output",
            filter: function (text) {
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

/**
 * Check if element is scrolled to bottom.
 * @param element - Element to check
 * @param threshold - Distance threshold in pixels
 * @returns True if at bottom
 */
function isScrolledToBottom(element: HTMLElement, threshold: number = 50): boolean {
    return element.scrollTop + element.clientHeight >= element.scrollHeight - threshold;
}

/**
 * Render chat messages with markdown and syntax highlighting.
 * @param messages - Messages to render
 */
export function refreshChatMessages(messages: ChatMessage[]): void {
    const chatHistory = document.getElementById("chat-history") as HTMLDivElement | null;
    if (!chatHistory) {
        console.error("Chat history element not found");
        return;
    }
    
    const wasAtBottom = isScrolledToBottom(chatHistory);

    chatHistory.innerHTML = "";
    // Display AI response in chat history
    messages.forEach((message, messageIndex) => {
        const converter = new showdown.Converter({
            strikethrough: true,
            smoothLivePreview: true,
            tasklists: true,
            tables: true,
            extensions: ["highlight"],
        });
        const text = message.text;
        const html = converter.makeHtml(text);

        const messageDiv = document.createElement("div");
        messageDiv.className = message.role === "user" ? "user-message" : "ai-message";
        messageDiv.innerHTML = utils.unescapeHTML(html);

        // Add reasoning button and metadata for assistant messages
        if (message.role === "assistant") {
            addReasoningButton(messageDiv, messageIndex);
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
 * Add reasoning inspection button to message.
 * @param messageElement - Message element
 * @param messageIndex - Message index
 */
function addReasoningButton(messageElement: HTMLElement, messageIndex: number): void {
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
    } catch (error) {
        console.warn("Failed to add reasoning button:", error);
        // Continue without reasoning button - chat functionality should not be affected
    }
}

/**
 * Add metadata display to message (model, reasoning level, preset).
 * @param messageElement - Message element
 * @param message - Message data
 */
function addMessageMetadata(messageElement: HTMLElement, message: ChatMessage): void {
    try {
        const metadataContainer = document.createElement("div");
        metadataContainer.className = "message-metadata";

        const metadataItems: string[] = [];

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
    } catch (error) {
        console.warn("Failed to add message metadata:", error);
        // Continue without metadata - chat functionality should not be affected
    }
}

/**
 * Format reasoning level with emoji.
 * @param level - Reasoning level
 * @returns Formatted string
 */
function formatReasoningLevel(level: string): string {
    switch (level) {
        case 'high':
            return '🧠 High';
        case 'medium':
            return '⚡ Medium';
        case 'low':
            return '💨 Low';
        case 'none':
            return '❌ None';
        default:
            return level;
    }
}

/**
 * Format model name for display.
 * @param model - Model identifier
 * @returns Formatted name
 */
function formatModelName(model: string): string {
    switch (model) {
        case 'gpt-5.1':
            return 'GPT-5.1';
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
 * Show reasoning modal for message.
 * @param messageIndex - Message index
 */
function showReasoningModal(messageIndex: number): void {
    // Get current conversation ID - this should be available globally
    const conversationId = (window as any).currentThreadId;
    if (!conversationId) {
        showReasoningError("No conversation selected");
        return;
    }

    // Show modal with loading state
    const modal = document.getElementById("reasoning-modal");
    const reasoningContent = document.getElementById("reasoning-content");
    const toolsContent = document.getElementById("tools-content");
    const loading = document.getElementById("reasoning-loading");
    const error = document.getElementById("reasoning-error");

    if (!modal || !reasoningContent || !toolsContent || !loading || !error) {
        console.error("Reasoning modal elements not found");
        showReasoningError("Modal interface not available");
        return;
    }

    // Reset modal state
    reasoningContent.style.display = "none";
    toolsContent.style.display = "none";
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
                } else if (response.status === 400) {
                    throw new Error("Invalid request - this message may not support reasoning");
                } else if (response.status === 401) {
                    throw new Error("Authentication required - please refresh the page");
                } else if (response.status === 500) {
                    throw new Error("Server error - please try again later");
                } else {
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

            // Check what data is available
            const hasReasoning = data.reasoning && (data.reasoning.complete_summary || (data.reasoning.summary_parts && data.reasoning.summary_parts.length > 0));
            const hasToolOutputs = data.tool_outputs && data.tool_outputs.length > 0;
            const hasWebSearches = data.web_searches && data.web_searches.length > 0;
            
            // Need at least some data to display
            if (!hasReasoning && !hasToolOutputs && !hasWebSearches) {
                showReasoningError("No reasoning data available for this message");
                return;
            }
            
            // Display reasoning data if available
            if (hasReasoning) {
                const reasoningToDisplay = data.reasoning.complete_summary 
                    ? data.reasoning 
                    : { ...data.reasoning, complete_summary: data.reasoning.summary_parts.join('\n\n') };
                displayReasoningData(reasoningToDisplay);
                reasoningContent.style.display = "block";
            } else {
                // No reasoning but we have tool data - show placeholder
                reasoningContent.innerHTML = `<div class="no-reasoning-data">No reasoning data for this message.</div>`;
                reasoningContent.style.display = "block";
            }
            
            // Display tool outputs if available
            if (hasToolOutputs || hasWebSearches) {
                displayToolOutputs(data.tool_outputs || [], data.web_searches || []);
                enableToolsTab();
            } else {
                disableToolsTab();
            }
            
            // Show reasoning tab by default if available, otherwise tools tab
            if (hasReasoning) {
                switchModalTab('reasoning');
            } else if (hasToolOutputs || hasWebSearches) {
                switchModalTab('tools');
            }
        })
        .catch(err => {
            clearTimeout(timeoutId);
            loading.style.display = "none";

            // Handle different types of errors
            if (err.name === 'AbortError') {
                showReasoningError("Request timed out - please try again");
            } else if (err.name === 'TypeError' && err.message.includes('fetch')) {
                showReasoningError("Network error - please check your connection");
            } else {
                showReasoningError(`Failed to load reasoning data: ${err.message}`);
            }

            console.error("Reasoning modal error:", err);
        });
}

/**
 * Display reasoning data in modal.
 * @param reasoningData - Reasoning data
 */
function displayReasoningData(reasoningData: any): void {
    const content = document.getElementById("reasoning-content");
    if (!content) return;

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
    } catch (error) {
        console.error("Error displaying reasoning data:", error);
        showReasoningError("Failed to display reasoning data");
    }
}

/**
 * Escape HTML to prevent XSS.
 * @param text - Text to escape
 * @returns Escaped text
 */
function escapeHtml(text: string): string {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Show error in reasoning modal.
 * @param message - Error message
 */
function showReasoningError(message: string): void {
    console.error(message);
    const error = document.getElementById("reasoning-error");
    if (!error) return;

    error.textContent = message;
    error.style.display = "block";
}

/**
 * Hide reasoning modal.
 */
export function hideReasoningModal(): void {
    const modal = document.getElementById("reasoning-modal");
    if (modal) {
        modal.style.display = "none";
    }
}

/**
 * Initialize modal tab switching.
 */
function initializeModalTabs(): void {
    const tabButtons = document.querySelectorAll('.tab-button');
    tabButtons.forEach(button => {
        button.addEventListener('click', (e) => {
            const target = e.target as HTMLButtonElement;
            const tabName = target.getAttribute('data-tab');
            if (tabName && !target.disabled) {
                switchModalTab(tabName as 'reasoning' | 'tools');
            }
        });
    });
}

/**
 * Switch modal tab.
 * @param tabName - Tab to switch to
 */
function switchModalTab(tabName: 'reasoning' | 'tools'): void {
    // Update tab buttons
    const tabButtons = document.querySelectorAll('.tab-button');
    tabButtons.forEach(button => {
        const buttonTab = button.getAttribute('data-tab');
        if (buttonTab === tabName) {
            button.classList.add('active');
        } else {
            button.classList.remove('active');
        }
    });
    
    // Update tab content
    const tabContents = document.querySelectorAll('.tab-content');
    tabContents.forEach(content => {
        const contentTab = content.getAttribute('data-tab');
        if (contentTab === tabName) {
            (content as HTMLElement).style.display = 'block';
        } else {
            (content as HTMLElement).style.display = 'none';
        }
    });
}

/**
 * Enable tools tab.
 */
function enableToolsTab(): void {
    const toolsTabButton = document.querySelector('.tab-button[data-tab="tools"]') as HTMLButtonElement;
    if (toolsTabButton) {
        toolsTabButton.disabled = false;
        toolsTabButton.style.opacity = '1';
    }
}

/**
 * Disable tools tab.
 */
function disableToolsTab(): void {
    const toolsTabButton = document.querySelector('.tab-button[data-tab="tools"]') as HTMLButtonElement;
    if (toolsTabButton) {
        toolsTabButton.disabled = true;
        toolsTabButton.style.opacity = '0.5';
    }
}

/**
 * Display tool outputs in the Tools tab.
 * @param toolOutputs - Tool execution results
 * @param webSearches - Web search activity (legacy support)
 */
function displayToolOutputs(toolOutputs: any[], webSearches: any[]): void {
    const toolsContent = document.getElementById("tools-content");
    if (!toolsContent) return;

    try {
        const hasToolOutputs = toolOutputs && toolOutputs.length > 0;
        const hasWebSearches = webSearches && webSearches.length > 0;

        if (!hasToolOutputs && !hasWebSearches) {
            toolsContent.innerHTML = `
                <div class="no-tool-data">
                    No tool activity for this message.
                </div>
            `;
            return;
        }

        let html = `<div class="tools-summary"><h3>Tool Activity</h3></div>`;

        // Display custom tool outputs
        if (hasToolOutputs) {
            toolOutputs.forEach((tool) => {
                const toolName = escapeHtml(tool.tool_name || 'Unknown tool');
                const success = tool.success;
                const timestamp = tool.timestamp ? new Date(tool.timestamp * 1000).toLocaleString() : '';
                const statusClass = success ? 'success' : 'error';
                const statusText = success ? 'Success' : 'Error';
                
                // Use formatted display strings if available, otherwise fall back to raw data
                const inputDisplay = tool.input_display !== undefined 
                    ? escapeHtml(tool.input_display) 
                    : escapeHtml(formatToolData(tool.input));
                const outputDisplay = tool.output_display !== undefined 
                    ? escapeHtml(tool.output_display) 
                    : escapeHtml(formatToolData(tool.output));

                html += `
                    <div class="tool-item">
                        <div class="tool-header">
                            <span class="tool-name">${toolName}</span>
                            <span class="tool-status ${statusClass}">${statusText}</span>
                        </div>
                        <div class="tool-details">
                            <div class="tool-section">
                                <div class="tool-section-label">Input:</div>
                                <pre class="tool-data">${inputDisplay}</pre>
                            </div>
                            <div class="tool-section">
                                <div class="tool-section-label">Output:</div>
                                <pre class="tool-data">${outputDisplay}</pre>
                            </div>
                        </div>
                        ${timestamp ? `<div class="tool-timestamp">${timestamp}</div>` : ''}
                    </div>
                `;
            });
        }

        // Display web searches (as a special tool type for backward compatibility)
        if (hasWebSearches) {
            webSearches.forEach((search) => {
                const query = escapeHtml(search.query || 'Unknown query');
                const status = search.status || 'unknown';
                const timestamp = search.timestamp ? new Date(search.timestamp * 1000).toLocaleString() : '';
                const statusClass = status === 'completed' ? 'success' : (status === 'failed' ? 'error' : 'pending');

                html += `
                    <div class="tool-item">
                        <div class="tool-header">
                            <span class="tool-name">Web Search</span>
                            <span class="tool-status ${statusClass}">${formatSearchStatus(status)}</span>
                        </div>
                        <div class="tool-details">
                            <div class="tool-section">
                                <div class="tool-section-label">Query:</div>
                                <pre class="tool-data">${query}</pre>
                            </div>
                        </div>
                        ${timestamp ? `<div class="tool-timestamp">${timestamp}</div>` : ''}
                    </div>
                `;
            });
        }

        toolsContent.innerHTML = html;
    } catch (error) {
        console.error("Error displaying tool outputs:", error);
        toolsContent.innerHTML = `
            <div class="error-message">
                Failed to display tool data
            </div>
        `;
    }
}

/**
 * Format tool data for display.
 * @param data - Tool input or output data
 * @returns Formatted string
 */
function formatToolData(data: any): string {
    if (data === null || data === undefined) {
        return 'N/A';
    }
    if (typeof data === 'string') {
        return data;
    }
    try {
        return JSON.stringify(data, null, 2);
    } catch {
        return String(data);
    }
}

/**
 * Format search status.
 * @param status - Status code
 * @returns Formatted string
 */
function formatSearchStatus(status: string): string {
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
 * Handle web search status updates.
 * @param status - Search status event
 */
export function handleWebSearchStatus(status: WebSearchStatus): void {
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

    } catch (error) {
        console.warn("Error handling web search status:", error);
        // Continue without status display - don't block chat functionality
    }
}

/**
 * Handle reasoning status updates.
 * @param status - Reasoning status event
 */
export function handleReasoningStatus(status: ReasoningStatus): void {
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

    } catch (error) {
        console.warn("Error handling reasoning status:", error);
        // Continue without status display - don't block chat functionality
    }
}

/**
 * Update status display.
 * @param message - Status message
 * @param isActive - Activity state
 * @param statusType - Status type
 */
function updateStatusDisplay(message: string, isActive: boolean, statusType: 'search' | 'reasoning'): void {
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
        } else {
            statusElement.classList.remove('active');
        }

    } catch (error) {
        console.warn("Error updating status display:", error);
        // Continue without status display - don't block chat functionality
    }
}

/**
 * Clear status display.
 * @param statusType - Status type to clear
 */
function clearStatusDisplay(statusType: 'search' | 'reasoning'): void {
    try {
        const statusElement = document.getElementById(`chat-status-${statusType}`);
        if (statusElement) {
            statusElement.style.display = 'none';
            statusElement.classList.remove('active');
        }
    } catch (error) {
        console.warn("Error clearing status display:", error);
        // Continue silently - don't block chat functionality
    }
}
