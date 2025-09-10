"""
Test to verify that the reasoning inspection button works with existing conversations.
This test specifically addresses the bug where currentThreadId was not available
when loading existing conversations.
"""

import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time


class TestReasoningConversationIdFix:
    @pytest.fixture
    def driver(self):
        """Set up Chrome driver for testing"""
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-web-security')
        options.add_argument('--allow-running-insecure-content')
        driver = webdriver.Chrome(options=options)
        driver.implicitly_wait(10)
        yield driver
        driver.quit()

    def test_current_thread_id_exposed_on_conversation_load(self, driver):
        """Test that currentThreadId is properly exposed to window when loading existing conversations"""
        driver.get("http://localhost:5000")
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "chatTab"))
        )
        
        # Execute JavaScript test code
        result = driver.execute_script("""
            return new Promise((resolve) => {
                try {
                    // Import the chat module
                    import('/static/js/chat.js').then(({ onConversationSelected }) => {
                        // Mock a conversation data response
                        const mockChatData = {
                            type: 'message_list',
                            text: '',
                            delta: '',
                            snapshot: '',
                            threadId: 'test-thread-123',
                            status: 'complete',
                            messages: [
                                { role: 'user', text: 'Hello' },
                                { role: 'assistant', text: 'Hi there!' }
                            ]
                        };
                        
                        // Mock the AJAX call to return our test data
                        const originalAjax = $.ajax;
                        $.ajax = function(options) {
                            if (options.url && options.url.includes('/chat?thread_id=')) {
                                // Simulate successful response
                                setTimeout(() => {
                                    options.success(JSON.stringify(mockChatData));
                                }, 100);
                            } else {
                                return originalAjax.apply(this, arguments);
                            }
                        };
                        
                        // Test the onConversationSelected function
                        onConversationSelected('test-thread-123', (chatData) => {
                            try {
                                // Check if currentThreadId is available on window
                                const windowThreadId = window.currentThreadId;
                                
                                resolve({
                                    success: true,
                                    windowThreadId: windowThreadId,
                                    chatDataThreadId: chatData.threadId,
                                    isExposed: windowThreadId === 'test-thread-123'
                                });
                            } catch (error) {
                                resolve({
                                    success: false,
                                    error: error.message
                                });
                            } finally {
                                // Restore original AJAX
                                $.ajax = originalAjax;
                            }
                        });
                        
                    }).catch(error => {
                        resolve({
                            success: false,
                            error: 'Failed to import chat module: ' + error.message
                        });
                    });
                } catch (error) {
                    resolve({
                        success: false,
                        error: error.message
                    });
                }
            });
        """)
        
        assert result['success'], f"Test failed: {result.get('error', 'Unknown error')}"
        assert result['isExposed'], f"currentThreadId not properly exposed to window. Window value: {result.get('windowThreadId')}, Expected: test-thread-123"
        assert result['windowThreadId'] == 'test-thread-123', f"Window currentThreadId mismatch: got {result['windowThreadId']}, expected test-thread-123"

    def test_reasoning_button_finds_conversation_id_after_load(self, driver):
        """Test that reasoning button can find conversation ID after loading an existing conversation"""
        driver.get("http://localhost:5000")
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "chatTab"))
        )
        
        # Execute JavaScript test code
        result = driver.execute_script("""
            return new Promise((resolve) => {
                try {
                    // Import required modules
                    Promise.all([
                        import('/static/js/chat.js'),
                        import('/static/js/script.js')
                    ]).then(([chatModule, scriptModule]) => {
                        
                        // Set up test conversation ID
                        window.currentThreadId = 'test-conversation-456';
                        
                        // Create a mock chat history container
                        const chatHistory = document.createElement('div');
                        chatHistory.id = 'chat-history';
                        document.body.appendChild(chatHistory);
                        
                        // Create mock reasoning modal elements
                        const modal = document.createElement('div');
                        modal.id = 'reasoning-modal';
                        modal.style.display = 'none';
                        
                        const content = document.createElement('div');
                        content.id = 'reasoning-content';
                        content.style.display = 'none';
                        
                        const loading = document.createElement('div');
                        loading.id = 'reasoning-loading';
                        loading.style.display = 'none';
                        
                        const error = document.createElement('div');
                        error.id = 'reasoning-error';
                        error.style.display = 'none';
                        
                        modal.appendChild(content);
                        modal.appendChild(loading);
                        modal.appendChild(error);
                        document.body.appendChild(modal);
                        
                        // Mock messages with assistant message
                        const mockMessages = [
                            { role: 'user', text: 'Test question' },
                            { role: 'assistant', text: 'Test response' }
                        ];
                        
                        // Use the refreshChatMessages function to create reasoning buttons
                        chatModule.refreshChatMessages(mockMessages);
                        
                        // Find the reasoning button
                        const reasoningButton = document.querySelector('.reasoning-button');
                        
                        if (!reasoningButton) {
                            resolve({
                                success: false,
                                error: 'Reasoning button not found'
                            });
                            return;
                        }
                        
                        // Mock the fetch call to avoid actual API calls
                        const originalFetch = window.fetch;
                        window.fetch = function(url, options) {
                            if (url.includes('/chat/reasoning/')) {
                                return Promise.resolve({
                                    ok: true,
                                    json: () => Promise.resolve({
                                        reasoning: {
                                            complete_summary: 'Test reasoning summary'
                                        }
                                    })
                                });
                            }
                            return originalFetch.apply(this, arguments);
                        };
                        
                        // Test clicking the reasoning button
                        let clickResult = null;
                        try {
                            reasoningButton.click();
                            
                            // Check if modal opened (indicating conversation ID was found)
                            setTimeout(() => {
                                const modalDisplay = modal.style.display;
                                const loadingDisplay = loading.style.display;
                                
                                resolve({
                                    success: true,
                                    modalOpened: modalDisplay === 'block',
                                    loadingShown: loadingDisplay === 'block',
                                    conversationId: window.currentThreadId
                                });
                                
                                // Restore original fetch
                                window.fetch = originalFetch;
                            }, 200);
                            
                        } catch (error) {
                            resolve({
                                success: false,
                                error: 'Error clicking reasoning button: ' + error.message
                            });
                            
                            // Restore original fetch
                            window.fetch = originalFetch;
                        }
                        
                    }).catch(error => {
                        resolve({
                            success: false,
                            error: 'Failed to import modules: ' + error.message
                        });
                    });
                } catch (error) {
                    resolve({
                        success: false,
                        error: error.message
                    });
                }
            });
        """)
        
        assert result['success'], f"Test failed: {result.get('error', 'Unknown error')}"
        assert result['modalOpened'], "Reasoning modal did not open, indicating conversation ID was not found"
        assert result['conversationId'] == 'test-conversation-456', f"Conversation ID mismatch: {result['conversationId']}"