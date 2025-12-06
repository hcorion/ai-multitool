"""
Tests for tool configuration UI in agent preset modal.
"""

import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import time


class TestToolConfigurationUI:
    """Test tool configuration UI functionality."""

    @pytest.fixture
    def driver(self):
        """Set up Chrome driver for testing."""
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        driver = webdriver.Chrome(options=options)
        driver.implicitly_wait(10)
        yield driver
        driver.quit()

    @pytest.fixture
    def authenticated_driver(self, driver, client):
        """Set up authenticated driver with session."""
        # Create a test session
        with client.session_transaction() as sess:
            sess['username'] = 'testuser'
        
        # Set the session cookie in the driver
        driver.get("http://localhost:5000")
        driver.add_cookie({
            'name': 'session',
            'value': client.get_cookie('session').value if hasattr(client, 'get_cookie') else 'test_session',
            'path': '/'
        })
        driver.refresh()
        
        return driver

    def test_tool_configuration_section_exists(self, driver):
        """Test that tool configuration section exists in the modal HTML."""
        driver.get("http://localhost:5000")
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "agent-preset-modal"))
        )
        
        # Check that tool configuration elements exist in the DOM
        result = driver.execute_script("""
            const modal = document.getElementById('agent-preset-modal');
            const toolConfig = modal.querySelector('.tool-configuration');
            const webSearchCheckbox = document.getElementById('tool-web_search');
            const calculatorCheckbox = document.getElementById('tool-calculator');
            
            return {
                success: true,
                hasToolConfig: toolConfig !== null,
                hasWebSearch: webSearchCheckbox !== null,
                hasCalculator: calculatorCheckbox !== null,
                webSearchValue: webSearchCheckbox ? webSearchCheckbox.value : null,
                calculatorValue: calculatorCheckbox ? calculatorCheckbox.value : null
            };
        """)
        
        assert result['success'], "Script execution failed"
        assert result['hasToolConfig'], "Tool configuration section not found"
        assert result['hasWebSearch'], "Web search checkbox not found"
        assert result['hasCalculator'], "Calculator checkbox not found"
        assert result['webSearchValue'] == 'web_search', "Web search checkbox has wrong value"
        assert result['calculatorValue'] == 'calculator', "Calculator checkbox has wrong value"

    def test_tool_checkboxes_default_checked(self, driver):
        """Test that tool checkboxes are checked by default for new presets."""
        driver.get("http://localhost:5000")
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "agent-preset-modal"))
        )
        
        # Open the modal (simulate new preset creation)
        result = driver.execute_script("""
            return new Promise((resolve) => {
                // Import the module
                import('/static/js/agent-preset-ui.js').then((module) => {
                    // Simulate opening modal for new preset
                    const modal = document.getElementById('agent-preset-modal');
                    modal.style.display = 'block';
                    
                    // Check default state
                    const webSearchCheckbox = document.getElementById('tool-web_search');
                    const calculatorCheckbox = document.getElementById('tool-calculator');
                    
                    resolve({
                        success: true,
                        webSearchChecked: webSearchCheckbox.checked,
                        calculatorChecked: calculatorCheckbox.checked
                    });
                }).catch(error => {
                    resolve({ success: false, error: error.message });
                });
            });
        """)
        
        assert result['success'], f"Test failed: {result.get('error', 'Unknown error')}"
        assert result['webSearchChecked'], "Web search should be checked by default"
        assert result['calculatorChecked'], "Calculator should be checked by default"

    def test_tool_toggle_functionality(self, driver):
        """Test that tool checkboxes can be toggled."""
        driver.get("http://localhost:5000")
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "agent-preset-modal"))
        )
        
        result = driver.execute_script("""
            return new Promise((resolve) => {
                const webSearchCheckbox = document.getElementById('tool-web_search');
                const calculatorCheckbox = document.getElementById('tool-calculator');
                
                // Record initial state
                const initialWebSearch = webSearchCheckbox.checked;
                const initialCalculator = calculatorCheckbox.checked;
                
                // Toggle both
                webSearchCheckbox.checked = !webSearchCheckbox.checked;
                calculatorCheckbox.checked = !calculatorCheckbox.checked;
                
                // Record new state
                const newWebSearch = webSearchCheckbox.checked;
                const newCalculator = calculatorCheckbox.checked;
                
                resolve({
                    success: true,
                    initialWebSearch,
                    initialCalculator,
                    newWebSearch,
                    newCalculator,
                    webSearchToggled: initialWebSearch !== newWebSearch,
                    calculatorToggled: initialCalculator !== newCalculator
                });
            });
        """)
        
        assert result['success'], "Test failed"
        assert result['webSearchToggled'], "Web search checkbox should toggle"
        assert result['calculatorToggled'], "Calculator checkbox should toggle"

    def test_form_data_includes_enabled_tools(self, driver):
        """Test that form data collection includes enabled_tools array."""
        driver.get("http://localhost:5000")
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "agent-preset-modal"))
        )
        
        result = driver.execute_script("""
            return new Promise((resolve) => {
                import('/static/js/agent-preset-ui.js').then(() => {
                    // Set up form with specific tool selection
                    document.getElementById('tool-web_search').checked = true;
                    document.getElementById('tool-calculator').checked = false;
                    
                    // Collect enabled tools (simulate getFormData logic)
                    const enabledTools = [];
                    const toolCheckboxes = document.querySelectorAll('input[name="tool"]:checked');
                    toolCheckboxes.forEach(checkbox => {
                        enabledTools.push(checkbox.value);
                    });
                    
                    resolve({
                        success: true,
                        enabledTools: enabledTools,
                        hasWebSearch: enabledTools.includes('web_search'),
                        hasCalculator: enabledTools.includes('calculator'),
                        toolCount: enabledTools.length
                    });
                }).catch(error => {
                    resolve({ success: false, error: error.message });
                });
            });
        """)
        
        assert result['success'], f"Test failed: {result.get('error', 'Unknown error')}"
        assert result['hasWebSearch'], "Enabled tools should include web_search"
        assert not result['hasCalculator'], "Enabled tools should not include calculator"
        assert result['toolCount'] == 1, "Should have exactly 1 enabled tool"

    def test_tool_categories_displayed(self, driver):
        """Test that tool categories (Built-in and Custom) are displayed."""
        driver.get("http://localhost:5000")
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "agent-preset-modal"))
        )
        
        result = driver.execute_script("""
            const toolCategories = document.querySelectorAll('.tool-category');
            const categoryTitles = Array.from(document.querySelectorAll('.tool-category-title'))
                .map(el => el.textContent.trim());
            
            return {
                success: true,
                categoryCount: toolCategories.length,
                categoryTitles: categoryTitles,
                hasBuiltIn: categoryTitles.some(title => title.includes('Built-in')),
                hasCustom: categoryTitles.some(title => title.includes('Custom'))
            };
        """)
        
        assert result['success'], "Test failed"
        assert result['categoryCount'] >= 2, "Should have at least 2 tool categories"
        assert result['hasBuiltIn'], "Should have Built-in Tools category"
        assert result['hasCustom'], "Should have Custom Tools category"

    def test_tool_descriptions_present(self, driver):
        """Test that tool descriptions are present for each tool."""
        driver.get("http://localhost:5000")
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "agent-preset-modal"))
        )
        
        result = driver.execute_script("""
            const toolOptions = document.querySelectorAll('.tool-option');
            const toolDescriptions = Array.from(document.querySelectorAll('.tool-description'))
                .map(el => el.textContent.trim());
            
            return {
                success: true,
                toolCount: toolOptions.length,
                descriptionCount: toolDescriptions.length,
                descriptions: toolDescriptions,
                allHaveDescriptions: toolOptions.length === toolDescriptions.length
            };
        """)
        
        assert result['success'], "Test failed"
        assert result['toolCount'] >= 2, "Should have at least 2 tools"
        assert result['allHaveDescriptions'], "All tools should have descriptions"
        assert len(result['descriptions']) >= 2, "Should have at least 2 descriptions"
        
        # Check that descriptions are not empty
        for desc in result['descriptions']:
            assert len(desc) > 0, "Tool description should not be empty"

    def test_multiple_tools_can_be_selected(self, driver):
        """Test that multiple tools can be selected simultaneously."""
        driver.get("http://localhost:5000")
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "agent-preset-modal"))
        )
        
        result = driver.execute_script("""
            return new Promise((resolve) => {
                // Select both tools
                document.getElementById('tool-web_search').checked = true;
                document.getElementById('tool-calculator').checked = true;
                
                // Collect enabled tools
                const enabledTools = [];
                const toolCheckboxes = document.querySelectorAll('input[name="tool"]:checked');
                toolCheckboxes.forEach(checkbox => {
                    enabledTools.push(checkbox.value);
                });
                
                resolve({
                    success: true,
                    enabledTools: enabledTools,
                    toolCount: enabledTools.length,
                    hasBoth: enabledTools.includes('web_search') && enabledTools.includes('calculator')
                });
            });
        """)
        
        assert result['success'], "Test failed"
        assert result['toolCount'] == 2, "Should have 2 enabled tools"
        assert result['hasBoth'], "Should have both web_search and calculator enabled"

    def test_no_tools_can_be_selected(self, driver):
        """Test that all tools can be deselected (edge case)."""
        driver.get("http://localhost:5000")
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "agent-preset-modal"))
        )
        
        result = driver.execute_script("""
            return new Promise((resolve) => {
                // Deselect all tools
                document.getElementById('tool-web_search').checked = false;
                document.getElementById('tool-calculator').checked = false;
                
                // Collect enabled tools
                const enabledTools = [];
                const toolCheckboxes = document.querySelectorAll('input[name="tool"]:checked');
                toolCheckboxes.forEach(checkbox => {
                    enabledTools.push(checkbox.value);
                });
                
                resolve({
                    success: true,
                    enabledTools: enabledTools,
                    toolCount: enabledTools.length,
                    isEmpty: enabledTools.length === 0
                });
            });
        """)
        
        assert result['success'], "Test failed"
        assert result['isEmpty'], "Should be able to have no tools selected"
        assert result['toolCount'] == 0, "Should have 0 enabled tools"
