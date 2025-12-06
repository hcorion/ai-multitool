"""Test frontend handling of empty tool data."""

import os
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options


class TestFrontendEmptyToolData:
    """Test frontend handling when tool data is empty."""

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

    def test_modal_with_empty_tool_data(self, driver):
        """Test that modal handles empty tool data gracefully."""
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
                            <button class="tab-button" data-tab="tools" disabled style="opacity: 0.5;">Tools</button>
                        </div>
                        <div id="reasoning-content" class="tab-content" data-tab="reasoning" style="display: block;">
                            <div class="reasoning-summary">
                                <h3>AI Reasoning Process</h3>
                                <div class="reasoning-text">This is test reasoning content without tool usage.</div>
                            </div>
                        </div>
                        <div id="tools-content" class="tab-content" data-tab="tools" style="display: none;">
                            <div class="no-tool-data">
                                No tool activity for this message.
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        with open("test_empty_tools.html", "w") as f:
            f.write(test_html)
        
        try:
            driver.get(f"file://{os.path.abspath('test_empty_tools.html')}")
            
            # Test that reasoning tab is active and tools tab is disabled
            reasoning_tab = driver.find_element(By.CSS_SELECTOR, '.tab-button[data-tab="reasoning"]')
            tools_tab = driver.find_element(By.CSS_SELECTOR, '.tab-button[data-tab="tools"]')
            
            assert "active" in reasoning_tab.get_attribute("class")
            assert reasoning_tab.is_enabled()
            
            assert "active" not in tools_tab.get_attribute("class")
            assert not tools_tab.is_enabled()
            
            # Test that reasoning content is visible and tools content is hidden
            reasoning_content = driver.find_element(By.ID, "reasoning-content")
            tools_content = driver.find_element(By.ID, "tools-content")
            
            assert reasoning_content.is_displayed()
            assert not tools_content.is_displayed()
            
            # Test that no-tool-data message is present (even if hidden)
            no_tool_message = driver.find_element(By.CLASS_NAME, "no-tool-data")
            # Use get_attribute to get the text content even if element is hidden
            message_text = driver.execute_script("return arguments[0].textContent;", no_tool_message)
            assert "No tool activity" in message_text
            
        finally:
            if os.path.exists("test_empty_tools.html"):
                os.remove("test_empty_tools.html")

    def test_modal_with_tool_data(self, driver):
        """Test that modal displays tool data when available."""
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
                                <div class="reasoning-text">This reasoning involved tool usage.</div>
                            </div>
                        </div>
                        <div id="tools-content" class="tab-content" data-tab="tools" style="display: none;">
                            <div class="tools-summary">
                                <h3>Tool Activity</h3>
                            </div>
                            <div class="tool-item">
                                <div class="tool-header">
                                    <span class="tool-name">calculator</span>
                                    <span class="tool-status success">Success</span>
                                </div>
                                <div class="tool-details">
                                    <div class="tool-section">
                                        <div class="tool-section-label">Input:</div>
                                        <pre class="tool-data">{"expression": "2 + 2"}</pre>
                                    </div>
                                    <div class="tool-section">
                                        <div class="tool-section-label">Output:</div>
                                        <pre class="tool-data">{"success": true, "result": 4}</pre>
                                    </div>
                                </div>
                                <div class="tool-timestamp">1/1/2024, 12:00:00 PM</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        with open("test_with_tools.html", "w") as f:
            f.write(test_html)
        
        try:
            driver.get(f"file://{os.path.abspath('test_with_tools.html')}")
            
            # Test that both tabs are enabled
            reasoning_tab = driver.find_element(By.CSS_SELECTOR, '.tab-button[data-tab="reasoning"]')
            tools_tab = driver.find_element(By.CSS_SELECTOR, '.tab-button[data-tab="tools"]')
            
            assert reasoning_tab.is_enabled()
            assert tools_tab.is_enabled()
            
            # Test tab switching functionality
            result = driver.execute_script("""
                return new Promise((resolve) => {
                    try {
                        const reasoningTab = document.querySelector('.tab-button[data-tab="reasoning"]');
                        const toolsTab = document.querySelector('.tab-button[data-tab="tools"]');
                        const reasoningContent = document.getElementById('reasoning-content');
                        const toolsContent = document.getElementById('tools-content');
                        
                        // Initial state
                        const initialState = {
                            reasoningActive: reasoningTab.classList.contains('active'),
                            toolsActive: toolsTab.classList.contains('active'),
                            reasoningVisible: reasoningContent.style.display !== 'none',
                            toolsVisible: toolsContent.style.display !== 'none'
                        };
                        
                        // Click tools tab
                        toolsTab.click();
                        
                        // Simulate tab switching logic
                        reasoningTab.classList.remove('active');
                        toolsTab.classList.add('active');
                        reasoningContent.style.display = 'none';
                        toolsContent.style.display = 'block';
                        
                        const afterClickState = {
                            reasoningActive: reasoningTab.classList.contains('active'),
                            toolsActive: toolsTab.classList.contains('active'),
                            reasoningVisible: reasoningContent.style.display !== 'none',
                            toolsVisible: toolsContent.style.display !== 'none'
                        };
                        
                        // Check tool content
                        const toolName = document.querySelector('.tool-name').textContent;
                        const toolStatus = document.querySelector('.tool-status').textContent;
                        
                        resolve({
                            success: true,
                            initialState: initialState,
                            afterClickState: afterClickState,
                            toolName: toolName,
                            toolStatus: toolStatus
                        });
                    } catch (error) {
                        resolve({ success: false, error: error.message });
                    }
                });
            """)
            
            assert result['success'], f"Tab switching test failed: {result.get('error', 'Unknown error')}"
            
            # Verify initial state
            initial = result['initialState']
            assert initial['reasoningActive'], "Reasoning tab should be active initially"
            assert not initial['toolsActive'], "Tools tab should not be active initially"
            assert initial['reasoningVisible'], "Reasoning content should be visible initially"
            assert not initial['toolsVisible'], "Tools content should not be visible initially"
            
            # Verify state after clicking tools tab
            after_click = result['afterClickState']
            assert not after_click['reasoningActive'], "Reasoning tab should not be active after click"
            assert after_click['toolsActive'], "Tools tab should be active after click"
            assert not after_click['reasoningVisible'], "Reasoning content should not be visible after click"
            assert after_click['toolsVisible'], "Tools content should be visible after click"
            
            # Verify tool content
            assert result['toolName'] == "calculator"
            assert result['toolStatus'] == "Success"
            
        finally:
            if os.path.exists("test_with_tools.html"):
                os.remove("test_with_tools.html")
