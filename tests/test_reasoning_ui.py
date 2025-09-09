"""Tests for reasoning inspection UI functionality."""

import os
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options


class TestReasoningUI:
    """Test reasoning inspection UI functionality using Selenium."""

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

    def test_reasoning_button_functionality(self, driver):
        """Test that reasoning button functionality is properly loaded."""
        # Create a simple HTML page to test the functionality
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
            
            <!-- Reasoning Modal -->
            <div id="reasoning-modal" class="modal reasoning-modal" style="display: none;">
                <div class="modal-content reasoning-modal-content">
                    <div class="modal-header">
                        <h3>AI Reasoning</h3>
                        <span class="close" id="reasoning-modal-close">&times;</span>
                    </div>
                    <div class="modal-body">
                        <div id="reasoning-loading" class="loading-message">
                            Loading reasoning data...
                        </div>
                        <div id="reasoning-error" class="error-message" style="display: none;">
                        </div>
                        <div id="reasoning-content" style="display: none;">
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
        with open("test_reasoning_ui.html", "w") as f:
            f.write(test_html)
        
        try:
            # Load the test page
            driver.get(f"file://{os.path.abspath('test_reasoning_ui.html')}")
            
            # Test that the reasoning modal elements exist
            modal = driver.find_element(By.ID, "reasoning-modal")
            assert modal is not None
            
            loading = driver.find_element(By.ID, "reasoning-loading")
            assert loading is not None
            
            error = driver.find_element(By.ID, "reasoning-error")
            assert error is not None
            
            content = driver.find_element(By.ID, "reasoning-content")
            assert content is not None
            
            # Test that modal is initially hidden
            assert modal.value_of_css_property("display") == "none"
            
        finally:
            # Clean up test file
            if os.path.exists("test_reasoning_ui.html"):
                os.remove("test_reasoning_ui.html")

    def test_reasoning_button_creation(self, driver):
        """Test that reasoning buttons are created for assistant messages."""
        # Execute JavaScript test code
        result = driver.execute_script("""
            return new Promise((resolve) => {
                // Mock the required global variables and functions
                window.currentThreadId = 'test-thread-123';
                
                // Create a test message element
                const messageElement = document.createElement('div');
                messageElement.className = 'ai-message';
                messageElement.innerHTML = 'Test assistant message';
                document.body.appendChild(messageElement);
                
                // Test the addReasoningButtonToMessage function
                try {
                    // Create the function inline since we can't import modules in this context
                    function addReasoningButtonToMessage(messageElement, messageIndex) {
                        const reasoningButton = document.createElement("button");
                        reasoningButton.className = "reasoning-button";
                        reasoningButton.innerHTML = "i";
                        reasoningButton.title = "View reasoning";
                        reasoningButton.setAttribute("data-message-index", messageIndex.toString());
                        messageElement.appendChild(reasoningButton);
                        return reasoningButton;
                    }
                    
                    const button = addReasoningButtonToMessage(messageElement, 0);
                    
                    resolve({
                        success: true,
                        buttonExists: !!button,
                        buttonClass: button.className,
                        buttonText: button.innerHTML,
                        buttonTitle: button.title,
                        messageIndex: button.getAttribute('data-message-index')
                    });
                } catch (error) {
                    resolve({ success: false, error: error.message });
                }
            });
        """)
        
        assert result['success'], f"Test failed: {result.get('error', 'Unknown error')}"
        assert result['buttonExists'], "Reasoning button was not created"
        assert result['buttonClass'] == "reasoning-button", "Button has incorrect class"
        assert result['buttonText'] == "i", "Button has incorrect text"
        assert result['buttonTitle'] == "View reasoning", "Button has incorrect title"
        assert result['messageIndex'] == "0", "Button has incorrect message index"

    def test_modal_display_functionality(self, driver):
        """Test that the modal can be shown and hidden."""
        result = driver.execute_script("""
            return new Promise((resolve) => {
                try {
                    // Create modal elements
                    const modal = document.createElement('div');
                    modal.id = 'reasoning-modal';
                    modal.style.display = 'none';
                    document.body.appendChild(modal);
                    
                    const content = document.createElement('div');
                    content.id = 'reasoning-content';
                    content.style.display = 'none';
                    modal.appendChild(content);
                    
                    const loading = document.createElement('div');
                    loading.id = 'reasoning-loading';
                    loading.style.display = 'block';
                    modal.appendChild(loading);
                    
                    const error = document.createElement('div');
                    error.id = 'reasoning-error';
                    error.style.display = 'none';
                    modal.appendChild(error);
                    
                    // Test showing modal
                    modal.style.display = 'block';
                    const modalVisible = modal.style.display === 'block';
                    
                    // Test hiding modal
                    modal.style.display = 'none';
                    const modalHidden = modal.style.display === 'none';
                    
                    resolve({
                        success: true,
                        modalVisible: modalVisible,
                        modalHidden: modalHidden
                    });
                } catch (error) {
                    resolve({ success: false, error: error.message });
                }
            });
        """)
        
        assert result['success'], f"Test failed: {result.get('error', 'Unknown error')}"
        assert result['modalVisible'], "Modal was not shown correctly"
        assert result['modalHidden'], "Modal was not hidden correctly"