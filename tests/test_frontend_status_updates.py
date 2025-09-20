"""
Test frontend status updates using Selenium WebDriver.
"""

import json
import time
from unittest.mock import Mock, patch

import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class TestFrontendStatusUpdates:
    """Test frontend status update functionality in browser."""

    @pytest.fixture
    def driver(self):
        """Set up Chrome driver for testing"""
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        driver = webdriver.Chrome(options=options)
        driver.implicitly_wait(10)
        yield driver
        driver.quit()

    def test_web_search_status_handling(self, driver):
        """Test web search status handling in browser"""
        # Create a test HTML page with the necessary elements
        test_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Status Test</title>
            <style>
                .chat-status-container { margin: 10px 0; }
                .chat-status-item { 
                    display: none; 
                    padding: 8px 12px; 
                    margin: 4px 0; 
                    border-radius: 4px; 
                }
                .chat-status-search { 
                    background-color: rgba(33, 150, 243, 0.1); 
                    color: #1976d2; 
                    border-left: 4px solid #2196f3; 
                }
                .chat-status-reasoning { 
                    background-color: rgba(156, 39, 176, 0.1); 
                    color: #7b1fa2; 
                    border-left: 4px solid #9c27b0; 
                }
                .active { animation: pulse 1.5s infinite; }
                @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.7; } 100% { opacity: 1; } }
            </style>
        </head>
        <body>
            <div id="chat-input"></div>
            <script type="module">
                // Import the compiled chat module
                import * as chat from '/static/js/chat.js';
                
                // Expose functions for testing
                window.testHandleWebSearchStatus = chat.handleWebSearchStatus;
                window.testHandleReasoningStatus = chat.handleReasoningStatus;
            </script>
        </body>
        </html>
        """
        
        # Write test HTML to a temporary file and serve it
        driver.get("data:text/html;charset=utf-8," + test_html)
        
        # Wait for the module to load
        WebDriverWait(driver, 10).until(
            lambda d: d.execute_script("return typeof window.testHandleWebSearchStatus === 'function'")
        )
        
        # Test web search status handling
        result = driver.execute_script("""
            return new Promise((resolve) => {
                try {
                    // Test search_started status
                    const searchStatus = {
                        type: 'search_started',
                        item_id: 'ws_test123',
                        output_index: 1,
                        sequence_number: 100
                    };
                    
                    window.testHandleWebSearchStatus(searchStatus);
                    
                    // Check if status container was created
                    const statusContainer = document.getElementById('chat-status-container');
                    const searchElement = document.getElementById('chat-status-search');
                    
                    if (!statusContainer || !searchElement) {
                        resolve({ success: false, error: 'Status elements not created' });
                        return;
                    }
                    
                    // Check if search element is visible and has correct content
                    const isVisible = searchElement.style.display === 'block';
                    const hasActiveClass = searchElement.classList.contains('active');
                    const content = searchElement.textContent;
                    
                    resolve({
                        success: true,
                        isVisible: isVisible,
                        hasActiveClass: hasActiveClass,
                        content: content,
                        containerExists: !!statusContainer
                    });
                    
                } catch (error) {
                    resolve({ success: false, error: error.message });
                }
            });
        """)
        
        assert result['success'], f"Test failed: {result.get('error', 'Unknown error')}"
        assert result['containerExists'], "Status container was not created"
        assert result['isVisible'], "Search status element is not visible"
        assert result['hasActiveClass'], "Search status element does not have active class"
        assert result['content'] == "Searching...", f"Expected 'Searching...', got '{result['content']}'"

    def test_reasoning_status_handling(self, driver):
        """Test reasoning status handling in browser"""
        # Create a test HTML page with the necessary elements
        test_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Reasoning Status Test</title>
            <style>
                .chat-status-container { margin: 10px 0; }
                .chat-status-item { 
                    display: none; 
                    padding: 8px 12px; 
                    margin: 4px 0; 
                    border-radius: 4px; 
                }
                .chat-status-reasoning { 
                    background-color: rgba(156, 39, 176, 0.1); 
                    color: #7b1fa2; 
                    border-left: 4px solid #9c27b0; 
                }
                .active { animation: pulse 1.5s infinite; }
                @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.7; } 100% { opacity: 1; } }
            </style>
        </head>
        <body>
            <div id="chat-input"></div>
            <script type="module">
                // Import the compiled chat module
                import * as chat from '/static/js/chat.js';
                
                // Expose functions for testing
                window.testHandleReasoningStatus = chat.handleReasoningStatus;
            </script>
        </body>
        </html>
        """
        
        # Write test HTML to a temporary file and serve it
        driver.get("data:text/html;charset=utf-8," + test_html)
        
        # Wait for the module to load
        WebDriverWait(driver, 10).until(
            lambda d: d.execute_script("return typeof window.testHandleReasoningStatus === 'function'")
        )
        
        # Test reasoning status handling
        result = driver.execute_script("""
            return new Promise((resolve) => {
                try {
                    // Test reasoning_started status
                    const reasoningStatus = {
                        type: 'reasoning_started',
                        part_id: 'part_1'
                    };
                    
                    window.testHandleReasoningStatus(reasoningStatus);
                    
                    // Check if status container was created
                    const statusContainer = document.getElementById('chat-status-container');
                    const reasoningElement = document.getElementById('chat-status-reasoning');
                    
                    if (!statusContainer || !reasoningElement) {
                        resolve({ success: false, error: 'Status elements not created' });
                        return;
                    }
                    
                    // Check if reasoning element is visible and has correct content
                    const isVisible = reasoningElement.style.display === 'block';
                    const hasActiveClass = reasoningElement.classList.contains('active');
                    const content = reasoningElement.textContent;
                    
                    resolve({
                        success: true,
                        isVisible: isVisible,
                        hasActiveClass: hasActiveClass,
                        content: content,
                        containerExists: !!statusContainer
                    });
                    
                } catch (error) {
                    resolve({ success: false, error: error.message });
                }
            });
        """)
        
        assert result['success'], f"Test failed: {result.get('error', 'Unknown error')}"
        assert result['containerExists'], "Status container was not created"
        assert result['isVisible'], "Reasoning status element is not visible"
        assert result['hasActiveClass'], "Reasoning status element does not have active class"
        assert result['content'] == "Thinking...", f"Expected 'Thinking...', got '{result['content']}'"

    def test_status_completion_and_cleanup(self, driver):
        """Test status completion and automatic cleanup"""
        # Create a test HTML page
        test_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Status Completion Test</title>
            <style>
                .chat-status-container { margin: 10px 0; }
                .chat-status-item { 
                    display: none; 
                    padding: 8px 12px; 
                    margin: 4px 0; 
                    border-radius: 4px; 
                }
                .chat-status-search { 
                    background-color: rgba(33, 150, 243, 0.1); 
                    color: #1976d2; 
                    border-left: 4px solid #2196f3; 
                }
                .active { animation: pulse 1.5s infinite; }
                @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.7; } 100% { opacity: 1; } }
            </style>
        </head>
        <body>
            <div id="chat-input"></div>
            <script type="module">
                // Import the compiled chat module
                import * as chat from '/static/js/chat.js';
                
                // Expose functions for testing
                window.testHandleWebSearchStatus = chat.handleWebSearchStatus;
            </script>
        </body>
        </html>
        """
        
        driver.get("data:text/html;charset=utf-8," + test_html)
        
        # Wait for the module to load
        WebDriverWait(driver, 10).until(
            lambda d: d.execute_script("return typeof window.testHandleWebSearchStatus === 'function'")
        )
        
        # Test status completion and cleanup
        result = driver.execute_script("""
            return new Promise((resolve) => {
                try {
                    // Test search_completed status
                    const completedStatus = {
                        type: 'search_completed',
                        item_id: 'ws_test123',
                        output_index: 1,
                        sequence_number: 102
                    };
                    
                    window.testHandleWebSearchStatus(completedStatus);
                    
                    // Check initial state
                    const searchElement = document.getElementById('chat-status-search');
                    if (!searchElement) {
                        resolve({ success: false, error: 'Search element not created' });
                        return;
                    }
                    
                    const initialVisible = searchElement.style.display === 'block';
                    const initialActive = searchElement.classList.contains('active');
                    const initialContent = searchElement.textContent;
                    
                    // Wait for auto-cleanup (should happen after 2 seconds)
                    setTimeout(() => {
                        const finalVisible = searchElement.style.display !== 'none';
                        const finalActive = searchElement.classList.contains('active');
                        
                        resolve({
                            success: true,
                            initialVisible: initialVisible,
                            initialActive: initialActive,
                            initialContent: initialContent,
                            finalVisible: finalVisible,
                            finalActive: finalActive
                        });
                    }, 2500); // Wait a bit longer than the 2-second timeout
                    
                } catch (error) {
                    resolve({ success: false, error: error.message });
                }
            });
        """)
        
        assert result['success'], f"Test failed: {result.get('error', 'Unknown error')}"
        assert result['initialVisible'], "Search status should be visible initially"
        assert not result['initialActive'], "Completed status should not be active"
        assert result['initialContent'] == "Search done", f"Expected 'Search done', got '{result['initialContent']}'"
        assert not result['finalVisible'], "Search status should be hidden after timeout"
        assert not result['finalActive'], "Search status should not be active after timeout"