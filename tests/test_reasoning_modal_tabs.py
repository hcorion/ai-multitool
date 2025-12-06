"""Tests for reasoning modal tabbed interface functionality."""

import os
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options


class TestReasoningModalTabs:
    """Test reasoning modal tabbed interface functionality using Selenium."""

    @pytest.fixture
    def driver(self):
        """Set up Chrome driver for testing."""
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        driver = webdriver.Chrome(options=options)
        driver.implicitly_wait(10)
        yield driver
        driver.quit()

    def test_tabbed_modal_structure(self, driver):
        """Test that the tabbed modal structure is properly created."""
        # Create a test HTML page with the new tabbed modal structure
        test_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <script src="/static/js/jquery.min.js"></script>
            <script src="/static/js/showdown.min.js"></script>
            <script src="/static/js/highlight.min.js"></script>
            <link rel="stylesheet" href="/static/css/style.css">
        </head>
        <body>
            <div id="chat-history">
                <div class="ai-message">Test assistant message</div>
            </div>
            
            <!-- Reasoning Modal with Tabs -->
            <div id="reasoning-modal" class="modal reasoning-modal" style="display: none;">
                <div class="modal-content reasoning-modal-content">
                    <div class="modal-header">
                        <h3>AI Process Details</h3>
                        <span class="close" id="reasoning-modal-close">&times;</span>
                    </div>
                    <div class="modal-body">
                        <div class="modal-tabs">
                            <button class="tab-button active" data-tab="reasoning">Reasoning</button>
                            <button class="tab-button" data-tab="tools">Tools</button>
                        </div>
                        <div id="reasoning-loading" class="loading-message">
                            Loading process data...
                        </div>
                        <div id="reasoning-error" class="error-message" style="display: none;">
                        </div>
                        <div id="reasoning-content" class="tab-content" data-tab="reasoning" style="display: none;">
                        </div>
                        <div id="tools-content" class="tab-content" data-tab="tools" style="display: none;">
                        </div>
                    </div>
                </div>
            </div>
            
            <script type="module" src="/static/js/chat.js"></script>
            <script type="module" src="/static/js/script.js"></script>
        </body>
        </html>
        """
        
        # Write test HTML to a temporary file
        with open("test_reasoning_modal_tabs.html", "w") as f:
            f.write(test_html)
        
        try:
            # Load the test page
            driver.get(f"file://{os.path.abspath('test_reasoning_modal_tabs.html')}")
            
            # Test that the modal elements exist
            modal = driver.find_element(By.ID, "reasoning-modal")
            assert modal is not None
            
            # Test that tab buttons exist
            reasoning_tab = driver.find_element(By.CSS_SELECTOR, '.tab-button[data-tab="reasoning"]')
            tools_tab = driver.find_element(By.CSS_SELECTOR, '.tab-button[data-tab="tools"]')
            assert reasoning_tab is not None
            assert tools_tab is not None
            
            # Test that tab content areas exist
            reasoning_content = driver.find_element(By.ID, "reasoning-content")
            tools_content = driver.find_element(By.ID, "tools-content")
            assert reasoning_content is not None
            assert tools_content is not None
            
            # Test that reasoning tab is active by default
            assert "active" in reasoning_tab.get_attribute("class")
            assert "active" not in tools_tab.get_attribute("class")
            
            # Test that modal is initially hidden
            assert modal.value_of_css_property("display") == "none"
            
        finally:
            # Clean up test file
            if os.path.exists("test_reasoning_modal_tabs.html"):
                os.remove("test_reasoning_modal_tabs.html")

    def test_tab_switching_functionality(self, driver):
        """Test that tab switching works correctly."""
        # Create test HTML with JavaScript functionality
        test_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <script src="/static/js/jquery.min.js"></script>
            <link rel="stylesheet" href="/static/css/style.css">
        </head>
        <body>
            <div id="reasoning-modal" class="modal reasoning-modal" style="display: block;">
                <div class="modal-content reasoning-modal-content">
                    <div class="modal-header">
                        <h3>AI Process Details</h3>
                        <span class="close" id="reasoning-modal-close">&times;</span>
                    </div>
                    <div class="modal-body">
                        <div class="modal-tabs">
                            <button class="tab-button active" data-tab="reasoning">Reasoning</button>
                            <button class="tab-button" data-tab="tools">Tools</button>
                        </div>
                        <div id="reasoning-content" class="tab-content" data-tab="reasoning" style="display: block;">
                            <div class="reasoning-summary">
                                <h3>AI Reasoning Process</h3>
                                <div class="reasoning-text">Test reasoning content</div>
                            </div>
                        </div>
                        <div id="tools-content" class="tab-content" data-tab="tools" style="display: none;">
                            <div class="tools-summary">
                                <h3>Tool Activity</h3>
                                <div class="tool-item">Test tool content</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        with open("test_tab_switching.html", "w") as f:
            f.write(test_html)
        
        try:
            driver.get(f"file://{os.path.abspath('test_tab_switching.html')}")
            
            # Test tab switching functionality with JavaScript
            result = driver.execute_script("""
                return new Promise((resolve) => {
                    try {
                        // Function to switch tabs (simulating the chat.ts functionality)
                        function switchModalTab(tabName) {
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
                                    content.style.display = 'block';
                                } else {
                                    content.style.display = 'none';
                                }
                            });
                        }
                        
                        // Test initial state
                        const reasoningTab = document.querySelector('.tab-button[data-tab="reasoning"]');
                        const toolsTab = document.querySelector('.tab-button[data-tab="tools"]');
                        const reasoningContent = document.getElementById('reasoning-content');
                        const toolsContent = document.getElementById('tools-content');
                        
                        const initialState = {
                            reasoningTabActive: reasoningTab.classList.contains('active'),
                            toolsTabActive: toolsTab.classList.contains('active'),
                            reasoningContentVisible: reasoningContent.style.display === 'block',
                            toolsContentVisible: toolsContent.style.display !== 'none'
                        };
                        
                        // Switch to tools tab
                        switchModalTab('tools');
                        
                        const afterSwitchState = {
                            reasoningTabActive: reasoningTab.classList.contains('active'),
                            toolsTabActive: toolsTab.classList.contains('active'),
                            reasoningContentVisible: reasoningContent.style.display !== 'none',
                            toolsContentVisible: toolsContent.style.display === 'block'
                        };
                        
                        // Switch back to reasoning tab
                        switchModalTab('reasoning');
                        
                        const finalState = {
                            reasoningTabActive: reasoningTab.classList.contains('active'),
                            toolsTabActive: toolsTab.classList.contains('active'),
                            reasoningContentVisible: reasoningContent.style.display === 'block',
                            toolsContentVisible: toolsContent.style.display !== 'none'
                        };
                        
                        resolve({
                            success: true,
                            initialState: initialState,
                            afterSwitchState: afterSwitchState,
                            finalState: finalState
                        });
                    } catch (error) {
                        resolve({ success: false, error: error.message });
                    }
                });
            """)
            
            assert result['success'], f"Tab switching test failed: {result.get('error', 'Unknown error')}"
            
            # Verify initial state (reasoning tab active)
            initial = result['initialState']
            assert initial['reasoningTabActive'], "Reasoning tab should be active initially"
            assert not initial['toolsTabActive'], "Tools tab should not be active initially"
            assert initial['reasoningContentVisible'], "Reasoning content should be visible initially"
            assert not initial['toolsContentVisible'], "Tools content should not be visible initially"
            
            # Verify state after switching to tools tab
            after_switch = result['afterSwitchState']
            assert not after_switch['reasoningTabActive'], "Reasoning tab should not be active after switch"
            assert after_switch['toolsTabActive'], "Tools tab should be active after switch"
            assert not after_switch['reasoningContentVisible'], "Reasoning content should not be visible after switch"
            assert after_switch['toolsContentVisible'], "Tools content should be visible after switch"
            
            # Verify final state (back to reasoning tab)
            final = result['finalState']
            assert final['reasoningTabActive'], "Reasoning tab should be active in final state"
            assert not final['toolsTabActive'], "Tools tab should not be active in final state"
            assert final['reasoningContentVisible'], "Reasoning content should be visible in final state"
            assert not final['toolsContentVisible'], "Tools content should not be visible in final state"
            
        finally:
            if os.path.exists("test_tab_switching.html"):
                os.remove("test_tab_switching.html")

    def test_tool_outputs_display(self, driver):
        """Test that tool outputs are properly displayed."""
        test_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <script src="/static/js/jquery.min.js"></script>
            <link rel="stylesheet" href="/static/css/style.css">
        </head>
        <body>
            <div id="tools-content" class="tab-content" data-tab="tools">
            </div>
        </body>
        </html>
        """
        
        with open("test_tools_display.html", "w") as f:
            f.write(test_html)
        
        try:
            driver.get(f"file://{os.path.abspath('test_tools_display.html')}")
            
            # Test tool outputs display functionality
            result = driver.execute_script("""
                return new Promise((resolve) => {
                    try {
                        // Function to escape HTML (from chat.ts)
                        function escapeHtml(text) {
                            const div = document.createElement('div');
                            div.textContent = text;
                            return div.innerHTML;
                        }
                        
                        // Function to format tool data
                        function formatToolData(data) {
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
                        
                        // Function to format search status (for backward compatibility)
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
                        
                        // Function to display tool outputs (from chat.ts)
                        function displayToolOutputs(toolOutputs, webSearches) {
                            const toolsContent = document.getElementById("tools-content");
                            if (!toolsContent) return false;

                            try {
                                const hasToolOutputs = toolOutputs && toolOutputs.length > 0;
                                const hasWebSearches = webSearches && webSearches.length > 0;

                                if (!hasToolOutputs && !hasWebSearches) {
                                    toolsContent.innerHTML = `
                                        <div class="no-tool-data">
                                            No tool activity for this message.
                                        </div>
                                    `;
                                    return true;
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

                                        html += `
                                            <div class="tool-item">
                                                <div class="tool-header">
                                                    <span class="tool-name">${toolName}</span>
                                                    <span class="tool-status ${statusClass}">${statusText}</span>
                                                </div>
                                                <div class="tool-details">
                                                    <div class="tool-section">
                                                        <div class="tool-section-label">Input:</div>
                                                        <pre class="tool-data">${escapeHtml(formatToolData(tool.input))}</pre>
                                                    </div>
                                                    <div class="tool-section">
                                                        <div class="tool-section-label">Output:</div>
                                                        <pre class="tool-data">${escapeHtml(formatToolData(tool.output))}</pre>
                                                    </div>
                                                </div>
                                                ${timestamp ? `<div class="tool-timestamp">${timestamp}</div>` : ''}
                                            </div>
                                        `;
                                    });
                                }

                                // Display web searches (as a special tool type)
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
                                return true;
                            } catch (error) {
                                console.error("Error displaying tool outputs:", error);
                                toolsContent.innerHTML = `
                                    <div class="error-message">
                                        Failed to display tool data
                                    </div>
                                `;
                                return false;
                            }
                        }
                        
                        // Test with sample tool outputs (calculator example)
                        const sampleToolOutputs = [
                            {
                                tool_name: "calculator",
                                input: { expression: "2 + 2" },
                                output: { success: true, result: 4, expression: "2 + 2" },
                                success: true,
                                timestamp: 1704067200
                            },
                            {
                                tool_name: "calculator",
                                input: { expression: "pow(2, 8)" },
                                output: { success: true, result: 256, expression: "pow(2, 8)" },
                                success: true,
                                timestamp: 1704067260
                            }
                        ];
                        
                        const displayResult = displayToolOutputs(sampleToolOutputs, []);
                        
                        // Check if content was properly generated
                        const toolsContent = document.getElementById("tools-content");
                        const hasToolsSummary = toolsContent.querySelector('.tools-summary') !== null;
                        const toolItems = toolsContent.querySelectorAll('.tool-item');
                        const hasCorrectItemCount = toolItems.length === 2;
                        
                        // Check first tool item content
                        const firstItem = toolItems[0];
                        const firstToolName = firstItem.querySelector('.tool-name').textContent;
                        const firstStatus = firstItem.querySelector('.tool-status').textContent;
                        
                        resolve({
                            success: true,
                            displayResult: displayResult,
                            hasToolsSummary: hasToolsSummary,
                            hasCorrectItemCount: hasCorrectItemCount,
                            firstToolName: firstToolName,
                            firstStatus: firstStatus,
                            totalItems: toolItems.length
                        });
                    } catch (error) {
                        resolve({ success: false, error: error.message });
                    }
                });
            """)
            
            assert result['success'], f"Tool outputs display test failed: {result.get('error', 'Unknown error')}"
            assert result['displayResult'], "displayToolOutputs should return true on success"
            assert result['hasToolsSummary'], "Should have tools summary section"
            assert result['hasCorrectItemCount'], "Should have correct number of tool items"
            assert result['firstToolName'] == "calculator", "First tool name should match"
            assert result['firstStatus'] == "Success", "First tool status should be formatted correctly"
            assert result['totalItems'] == 2, "Should have 2 tool items"
            
        finally:
            if os.path.exists("test_tools_display.html"):
                os.remove("test_tools_display.html")
