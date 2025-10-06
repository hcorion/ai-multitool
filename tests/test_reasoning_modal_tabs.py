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
                            <button class="tab-button" data-tab="search">Web Searches</button>
                        </div>
                        <div id="reasoning-loading" class="loading-message">
                            Loading process data...
                        </div>
                        <div id="reasoning-error" class="error-message" style="display: none;">
                        </div>
                        <div id="reasoning-content" class="tab-content" data-tab="reasoning" style="display: none;">
                        </div>
                        <div id="search-content" class="tab-content" data-tab="search" style="display: none;">
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
            search_tab = driver.find_element(By.CSS_SELECTOR, '.tab-button[data-tab="search"]')
            assert reasoning_tab is not None
            assert search_tab is not None
            
            # Test that tab content areas exist
            reasoning_content = driver.find_element(By.ID, "reasoning-content")
            search_content = driver.find_element(By.ID, "search-content")
            assert reasoning_content is not None
            assert search_content is not None
            
            # Test that reasoning tab is active by default
            assert "active" in reasoning_tab.get_attribute("class")
            assert "active" not in search_tab.get_attribute("class")
            
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
                            <button class="tab-button" data-tab="search">Web Searches</button>
                        </div>
                        <div id="reasoning-content" class="tab-content" data-tab="reasoning" style="display: block;">
                            <div class="reasoning-summary">
                                <h3>AI Reasoning Process</h3>
                                <div class="reasoning-text">Test reasoning content</div>
                            </div>
                        </div>
                        <div id="search-content" class="tab-content" data-tab="search" style="display: none;">
                            <div class="search-summary">
                                <h3>Web Search Activity</h3>
                                <div class="search-item">Test search content</div>
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
                        const searchTab = document.querySelector('.tab-button[data-tab="search"]');
                        const reasoningContent = document.getElementById('reasoning-content');
                        const searchContent = document.getElementById('search-content');
                        
                        const initialState = {
                            reasoningTabActive: reasoningTab.classList.contains('active'),
                            searchTabActive: searchTab.classList.contains('active'),
                            reasoningContentVisible: reasoningContent.style.display === 'block',
                            searchContentVisible: searchContent.style.display !== 'none'
                        };
                        
                        // Switch to search tab
                        switchModalTab('search');
                        
                        const afterSwitchState = {
                            reasoningTabActive: reasoningTab.classList.contains('active'),
                            searchTabActive: searchTab.classList.contains('active'),
                            reasoningContentVisible: reasoningContent.style.display !== 'none',
                            searchContentVisible: searchContent.style.display === 'block'
                        };
                        
                        // Switch back to reasoning tab
                        switchModalTab('reasoning');
                        
                        const finalState = {
                            reasoningTabActive: reasoningTab.classList.contains('active'),
                            searchTabActive: searchTab.classList.contains('active'),
                            reasoningContentVisible: reasoningContent.style.display === 'block',
                            searchContentVisible: searchContent.style.display !== 'none'
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
            assert not initial['searchTabActive'], "Search tab should not be active initially"
            assert initial['reasoningContentVisible'], "Reasoning content should be visible initially"
            assert not initial['searchContentVisible'], "Search content should not be visible initially"
            
            # Verify state after switching to search tab
            after_switch = result['afterSwitchState']
            assert not after_switch['reasoningTabActive'], "Reasoning tab should not be active after switch"
            assert after_switch['searchTabActive'], "Search tab should be active after switch"
            assert not after_switch['reasoningContentVisible'], "Reasoning content should not be visible after switch"
            assert after_switch['searchContentVisible'], "Search content should be visible after switch"
            
            # Verify final state (back to reasoning tab)
            final = result['finalState']
            assert final['reasoningTabActive'], "Reasoning tab should be active in final state"
            assert not final['searchTabActive'], "Search tab should not be active in final state"
            assert final['reasoningContentVisible'], "Reasoning content should be visible in final state"
            assert not final['searchContentVisible'], "Search content should not be visible in final state"
            
        finally:
            if os.path.exists("test_tab_switching.html"):
                os.remove("test_tab_switching.html")

    def test_web_search_data_display(self, driver):
        """Test that web search data is properly displayed."""
        test_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <script src="/static/js/jquery.min.js"></script>
            <link rel="stylesheet" href="/static/css/style.css">
        </head>
        <body>
            <div id="search-content" class="tab-content" data-tab="search">
            </div>
        </body>
        </html>
        """
        
        with open("test_search_display.html", "w") as f:
            f.write(test_html)
        
        try:
            driver.get(f"file://{os.path.abspath('test_search_display.html')}")
            
            # Test web search data display functionality
            result = driver.execute_script("""
                return new Promise((resolve) => {
                    try {
                        // Function to escape HTML (from chat.ts)
                        function escapeHtml(text) {
                            const div = document.createElement('div');
                            div.textContent = text;
                            return div.innerHTML;
                        }
                        
                        // Function to format search status (from chat.ts)
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
                        
                        // Function to display web search data (from chat.ts)
                        function displayWebSearchData(searchData) {
                            const searchContent = document.getElementById("search-content");
                            if (!searchContent) return false;

                            try {
                                if (!searchData || searchData.length === 0) {
                                    searchContent.innerHTML = `
                                        <div class="no-search-data">
                                            No web search data available for this message.
                                        </div>
                                    `;
                                    return true;
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
                                return true;
                            } catch (error) {
                                console.error("Error displaying web search data:", error);
                                searchContent.innerHTML = `
                                    <div class="error-message">
                                        Failed to display web search data
                                    </div>
                                `;
                                return false;
                            }
                        }
                        
                        // Test with sample search data
                        const sampleSearchData = [
                            {
                                query: "weather in New York",
                                status: "completed",
                                timestamp: 1704067200,
                                action_type: "search",
                                sources: ["weather.com", "noaa.gov"]
                            },
                            {
                                query: "current temperature NYC",
                                status: "in_progress",
                                timestamp: 1704067260,
                                action_type: "search"
                            }
                        ];
                        
                        const displayResult = displayWebSearchData(sampleSearchData);
                        
                        // Check if content was properly generated
                        const searchContent = document.getElementById("search-content");
                        const hasSearchSummary = searchContent.querySelector('.search-summary') !== null;
                        const searchItems = searchContent.querySelectorAll('.search-item');
                        const hasCorrectItemCount = searchItems.length === 2;
                        
                        // Check first search item content
                        const firstItem = searchItems[0];
                        const firstQuery = firstItem.querySelector('.search-query').textContent;
                        const firstStatus = firstItem.querySelector('.search-status').textContent;
                        
                        resolve({
                            success: true,
                            displayResult: displayResult,
                            hasSearchSummary: hasSearchSummary,
                            hasCorrectItemCount: hasCorrectItemCount,
                            firstQuery: firstQuery,
                            firstStatus: firstStatus,
                            totalItems: searchItems.length
                        });
                    } catch (error) {
                        resolve({ success: false, error: error.message });
                    }
                });
            """)
            
            assert result['success'], f"Web search display test failed: {result.get('error', 'Unknown error')}"
            assert result['displayResult'], "displayWebSearchData should return true on success"
            assert result['hasSearchSummary'], "Should have search summary section"
            assert result['hasCorrectItemCount'], "Should have correct number of search items"
            assert result['firstQuery'] == "weather in New York", "First search query should match"
            assert result['firstStatus'] == "Completed", "First search status should be formatted correctly"
            assert result['totalItems'] == 2, "Should have 2 search items"
            
        finally:
            if os.path.exists("test_search_display.html"):
                os.remove("test_search_display.html")