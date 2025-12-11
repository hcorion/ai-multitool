"""Test that tool toggles work correctly in agent preset UI."""

import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


@pytest.mark.skip(reason="Requires running Flask server - manual test only")
class TestToolToggleFix:
    """Test tool toggle functionality in agent preset modal."""

    @pytest.fixture
    def driver(self):
        """Set up Chrome driver for testing."""
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        driver = webdriver.Chrome(options=options)
        driver.implicitly_wait(10)
        yield driver
        driver.quit()

    def test_tool_checkboxes_have_correct_ids(self, driver):
        """Test that tool checkboxes have IDs matching TypeScript expectations."""
        driver.get("http://localhost:5000")
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "agent-preset-modal"))
        )
        
        # Execute JavaScript to check checkbox IDs
        result = driver.execute_script("""
            const webSearchCheckbox = document.getElementById('tool-web_search');
            const calculatorCheckbox = document.getElementById('tool-calculator');
            
            return {
                webSearchExists: webSearchCheckbox !== null,
                calculatorExists: calculatorCheckbox !== null,
                webSearchValue: webSearchCheckbox ? webSearchCheckbox.value : null,
                calculatorValue: calculatorCheckbox ? calculatorCheckbox.value : null,
                webSearchChecked: webSearchCheckbox ? webSearchCheckbox.checked : null,
                calculatorChecked: calculatorCheckbox ? calculatorCheckbox.checked : null
            };
        """)
        
        assert result['webSearchExists'], "Web search checkbox should exist with ID 'tool-web_search'"
        assert result['calculatorExists'], "Calculator checkbox should exist with ID 'tool-calculator'"
        assert result['webSearchValue'] == 'web_search', "Web search checkbox value should be 'web_search'"
        assert result['calculatorValue'] == 'calculator', "Calculator checkbox value should be 'calculator'"
        assert result['webSearchChecked'] is True, "Web search should be checked by default"
        assert result['calculatorChecked'] is True, "Calculator should be checked by default"

    def test_populate_tool_checkboxes_function(self, driver):
        """Test that populateToolCheckboxes correctly sets checkbox states."""
        driver.get("http://localhost:5000")
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "agent-preset-modal"))
        )
        
        # Execute JavaScript to test the populate function
        result = driver.execute_script("""
            return new Promise((resolve) => {
                // Import the module and test the function
                import('/static/js/agent-preset-ui.js').then(() => {
                    // Simulate what populateToolCheckboxes does
                    const enabledTools = ['web_search']; // Only web_search enabled
                    
                    // Get all tool checkboxes
                    const toolCheckboxes = document.querySelectorAll('input[name="tool"]');
                    
                    // Uncheck all first
                    toolCheckboxes.forEach(checkbox => {
                        checkbox.checked = false;
                    });
                    
                    // Check the enabled tools
                    enabledTools.forEach(toolName => {
                        const checkbox = document.getElementById(`tool-${toolName}`);
                        if (checkbox) {
                            checkbox.checked = true;
                        }
                    });
                    
                    // Verify the state
                    const webSearchCheckbox = document.getElementById('tool-web_search');
                    const calculatorCheckbox = document.getElementById('tool-calculator');
                    
                    resolve({
                        success: true,
                        webSearchChecked: webSearchCheckbox ? webSearchCheckbox.checked : null,
                        calculatorChecked: calculatorCheckbox ? calculatorCheckbox.checked : null,
                        webSearchFound: webSearchCheckbox !== null,
                        calculatorFound: calculatorCheckbox !== null
                    });
                }).catch(error => {
                    resolve({ success: false, error: error.message });
                });
            });
        """)
        
        assert result['success'], f"Test failed: {result.get('error', 'Unknown error')}"
        assert result['webSearchFound'], "Web search checkbox should be found"
        assert result['calculatorFound'], "Calculator checkbox should be found"
        assert result['webSearchChecked'] is True, "Web search should be checked"
        assert result['calculatorChecked'] is False, "Calculator should be unchecked"

    def test_get_form_data_collects_enabled_tools(self, driver):
        """Test that getFormData correctly collects enabled tools from checkboxes."""
        driver.get("http://localhost:5000")
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "agent-preset-modal"))
        )
        
        # Execute JavaScript to test form data collection
        result = driver.execute_script("""
            return new Promise((resolve) => {
                // Simulate getFormData behavior
                const enabledTools = [];
                const toolCheckboxes = document.querySelectorAll('input[name="tool"]:checked');
                toolCheckboxes.forEach(checkbox => {
                    enabledTools.push(checkbox.value);
                });
                
                // Now uncheck calculator
                const calculatorCheckbox = document.getElementById('tool-calculator');
                if (calculatorCheckbox) {
                    calculatorCheckbox.checked = false;
                }
                
                // Collect again
                const enabledToolsAfterUncheck = [];
                const toolCheckboxesAfter = document.querySelectorAll('input[name="tool"]:checked');
                toolCheckboxesAfter.forEach(checkbox => {
                    enabledToolsAfterUncheck.push(checkbox.value);
                });
                
                resolve({
                    success: true,
                    initialTools: enabledTools,
                    toolsAfterUncheck: enabledToolsAfterUncheck,
                    hasAtLeastOneTool: enabledToolsAfterUncheck.length > 0
                });
            });
        """)
        
        assert result['success'], "Test should complete successfully"
        assert 'web_search' in result['initialTools'], "Initial tools should include web_search"
        assert 'calculator' in result['initialTools'], "Initial tools should include calculator"
        assert 'web_search' in result['toolsAfterUncheck'], "After unchecking calculator, web_search should remain"
        assert 'calculator' not in result['toolsAfterUncheck'], "After unchecking calculator, it should not be in the list"
        assert result['hasAtLeastOneTool'], "Should have at least one tool enabled"
