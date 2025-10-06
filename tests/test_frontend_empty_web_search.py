"""Test frontend handling of empty web search data."""

import os
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options


class TestFrontendEmptyWebSearch:
    """Test frontend handling when web search data is empty."""

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

    def test_modal_with_empty_web_search_data(self, driver):
        """Test that modal handles empty web search data gracefully."""
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
                            <button class="tab-button" data-tab="search" disabled style="opacity: 0.5;">Web Searches</button>
                        </div>
                        <div id="reasoning-content" class="tab-content" data-tab="reasoning" style="display: block;">
                            <div class="reasoning-summary">
                                <h3>AI Reasoning Process</h3>
                                <div class="reasoning-text">This is test reasoning content without web searches.</div>
                            </div>
                        </div>
                        <div id="search-content" class="tab-content" data-tab="search" style="display: none;">
                            <div class="no-search-data">
                                No web search data available for this message.
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        with open("test_empty_search.html", "w") as f:
            f.write(test_html)
        
        try:
            driver.get(f"file://{os.path.abspath('test_empty_search.html')}")
            
            # Test that reasoning tab is active and search tab is disabled
            reasoning_tab = driver.find_element(By.CSS_SELECTOR, '.tab-button[data-tab="reasoning"]')
            search_tab = driver.find_element(By.CSS_SELECTOR, '.tab-button[data-tab="search"]')
            
            assert "active" in reasoning_tab.get_attribute("class")
            assert reasoning_tab.is_enabled()
            
            assert "active" not in search_tab.get_attribute("class")
            assert not search_tab.is_enabled()
            
            # Test that reasoning content is visible and search content is hidden
            reasoning_content = driver.find_element(By.ID, "reasoning-content")
            search_content = driver.find_element(By.ID, "search-content")
            
            assert reasoning_content.is_displayed()
            assert not search_content.is_displayed()
            
            # Test that no-search-data message is present (even if hidden)
            no_search_message = driver.find_element(By.CLASS_NAME, "no-search-data")
            # Use get_attribute to get the text content even if element is hidden
            message_text = driver.execute_script("return arguments[0].textContent;", no_search_message)
            assert "No web search data available" in message_text
            
        finally:
            if os.path.exists("test_empty_search.html"):
                os.remove("test_empty_search.html")

    def test_modal_with_web_search_data(self, driver):
        """Test that modal displays web search data when available."""
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
                                <div class="reasoning-text">This reasoning involved web searches.</div>
                            </div>
                        </div>
                        <div id="search-content" class="tab-content" data-tab="search" style="display: none;">
                            <div class="search-summary">
                                <h3>Web Search Activity</h3>
                            </div>
                            <div class="search-item">
                                <div class="search-query">test weather query</div>
                                <div class="search-status completed">Completed</div>
                                <div class="search-details">
                                    <div>Action: search</div>
                                    <div>Sources: weather.com, noaa.gov</div>
                                </div>
                                <div class="search-timestamp">1/1/2024, 12:00:00 PM</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        with open("test_with_search.html", "w") as f:
            f.write(test_html)
        
        try:
            driver.get(f"file://{os.path.abspath('test_with_search.html')}")
            
            # Test that both tabs are enabled
            reasoning_tab = driver.find_element(By.CSS_SELECTOR, '.tab-button[data-tab="reasoning"]')
            search_tab = driver.find_element(By.CSS_SELECTOR, '.tab-button[data-tab="search"]')
            
            assert reasoning_tab.is_enabled()
            assert search_tab.is_enabled()
            
            # Test tab switching functionality
            result = driver.execute_script("""
                return new Promise((resolve) => {
                    try {
                        const reasoningTab = document.querySelector('.tab-button[data-tab="reasoning"]');
                        const searchTab = document.querySelector('.tab-button[data-tab="search"]');
                        const reasoningContent = document.getElementById('reasoning-content');
                        const searchContent = document.getElementById('search-content');
                        
                        // Initial state
                        const initialState = {
                            reasoningActive: reasoningTab.classList.contains('active'),
                            searchActive: searchTab.classList.contains('active'),
                            reasoningVisible: reasoningContent.style.display !== 'none',
                            searchVisible: searchContent.style.display !== 'none'
                        };
                        
                        // Click search tab
                        searchTab.click();
                        
                        // Simulate tab switching logic
                        reasoningTab.classList.remove('active');
                        searchTab.classList.add('active');
                        reasoningContent.style.display = 'none';
                        searchContent.style.display = 'block';
                        
                        const afterClickState = {
                            reasoningActive: reasoningTab.classList.contains('active'),
                            searchActive: searchTab.classList.contains('active'),
                            reasoningVisible: reasoningContent.style.display !== 'none',
                            searchVisible: searchContent.style.display !== 'none'
                        };
                        
                        // Check search content
                        const searchQuery = document.querySelector('.search-query').textContent;
                        const searchStatus = document.querySelector('.search-status').textContent;
                        
                        resolve({
                            success: true,
                            initialState: initialState,
                            afterClickState: afterClickState,
                            searchQuery: searchQuery,
                            searchStatus: searchStatus
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
            assert not initial['searchActive'], "Search tab should not be active initially"
            assert initial['reasoningVisible'], "Reasoning content should be visible initially"
            assert not initial['searchVisible'], "Search content should not be visible initially"
            
            # Verify state after clicking search tab
            after_click = result['afterClickState']
            assert not after_click['reasoningActive'], "Reasoning tab should not be active after click"
            assert after_click['searchActive'], "Search tab should be active after click"
            assert not after_click['reasoningVisible'], "Reasoning content should not be visible after click"
            assert after_click['searchVisible'], "Search content should be visible after click"
            
            # Verify search content
            assert result['searchQuery'] == "test weather query"
            assert result['searchStatus'] == "Completed"
            
        finally:
            if os.path.exists("test_with_search.html"):
                os.remove("test_with_search.html")