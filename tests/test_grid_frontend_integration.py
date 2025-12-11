"""
Integration test for grid generation frontend functionality.
"""

import json
import os
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time


@pytest.mark.skip(reason="Requires running Flask server - manual test only")
class TestGridFrontendIntegration:
    """Test grid generation frontend integration."""

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

    def test_advanced_options_toggle(self, driver):
        """Test that advanced options can be toggled."""
        # Create test prompt file
        os.makedirs('static/prompts/testuser', exist_ok=True)
        with open('static/prompts/testuser/test_colors.txt', 'w') as f:
            f.write('red\nblue\ngreen\nyellow')

        driver.get("http://localhost:5000/login")
        
        # Login as testuser
        username_input = driver.find_element(By.NAME, "username")
        username_input.send_keys("testuser")
        login_button = driver.find_element(By.CSS_SELECTOR, "input[type='submit']")
        login_button.click()

        # Wait for main page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "prompt-form"))
        )

        # Test advanced options toggle
        result = driver.execute_script("""
            return new Promise((resolve) => {
                try {
                    // Find the advanced toggle button
                    const advancedToggle = document.getElementById('advanced-toggle');
                    const advancedDropdown = document.getElementById('advanced-dropdown');
                    
                    if (!advancedToggle || !advancedDropdown) {
                        resolve({ success: false, error: 'Advanced elements not found' });
                        return;
                    }
                    
                    // Initially should be hidden
                    const initiallyHidden = advancedDropdown.style.display === 'none' || 
                                          getComputedStyle(advancedDropdown).display === 'none';
                    
                    // Click to show
                    advancedToggle.click();
                    
                    // Check if it's now visible
                    const nowVisible = advancedDropdown.style.display === 'block' || 
                                     getComputedStyle(advancedDropdown).display === 'block';
                    
                    resolve({
                        success: true,
                        initiallyHidden: initiallyHidden,
                        nowVisible: nowVisible
                    });
                } catch (error) {
                    resolve({ success: false, error: error.message });
                }
            });
        """)

        assert result['success'], f"Test failed: {result.get('error', 'Unknown error')}"
        assert result['nowVisible'], "Advanced dropdown should be visible after clicking toggle"

    def test_grid_checkbox_functionality(self, driver):
        """Test that the grid generation checkbox works."""
        driver.get("http://localhost:5000/login")
        
        # Login as testuser
        username_input = driver.find_element(By.NAME, "username")
        username_input.send_keys("testuser")
        login_button = driver.find_element(By.CSS_SELECTOR, "input[type='submit']")
        login_button.click()

        # Wait for main page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "prompt-form"))
        )

        # Test grid checkbox functionality
        result = driver.execute_script("""
            return new Promise((resolve) => {
                try {
                    // Show advanced options first
                    const advancedToggle = document.getElementById('advanced-toggle');
                    advancedToggle.click();
                    
                    // Find grid elements
                    const gridCheckbox = document.getElementById('advanced-generate-grid');
                    const gridInput = document.getElementById('grid-prompt-file');
                    const inputContainer = document.querySelector('.advanced-input-container');
                    
                    if (!gridCheckbox || !gridInput || !inputContainer) {
                        resolve({ success: false, error: 'Grid elements not found' });
                        return;
                    }
                    
                    // Initially input should be disabled and container hidden
                    const initiallyDisabled = gridInput.disabled;
                    const initiallyHidden = inputContainer.style.display === 'none' || 
                                          getComputedStyle(inputContainer).display === 'none';
                    
                    // Check the checkbox
                    gridCheckbox.checked = true;
                    gridCheckbox.dispatchEvent(new Event('change'));
                    
                    // Now input should be enabled and container visible
                    const nowEnabled = !gridInput.disabled;
                    const nowVisible = inputContainer.style.display === 'block' || 
                                     getComputedStyle(inputContainer).display === 'block';
                    
                    resolve({
                        success: true,
                        initiallyDisabled: initiallyDisabled,
                        initiallyHidden: initiallyHidden,
                        nowEnabled: nowEnabled,
                        nowVisible: nowVisible
                    });
                } catch (error) {
                    resolve({ success: false, error: error.message });
                }
            });
        """)

        assert result['success'], f"Test failed: {result.get('error', 'Unknown error')}"
        assert result['initiallyDisabled'], "Grid input should initially be disabled"
        assert result['initiallyHidden'], "Grid input container should initially be hidden"
        assert result['nowEnabled'], "Grid input should be enabled after checking checkbox"
        assert result['nowVisible'], "Grid input container should be visible after checking checkbox"

    @pytest.mark.skip(reason="Requires running Flask server - manual test only")
    def test_grid_generation_flow(self, driver):
        """Test the complete grid generation flow (requires running server)."""
        # This test would require a running Flask server with mocked image generation
        # It's marked as skip for automated testing but can be run manually
        pass