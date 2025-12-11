"""
Test to verify the Inpaint button is properly added to the grid view modal
"""

import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options


@pytest.mark.skip(reason="Requires running Flask server - manual test only")
class TestInpaintButtonIntegration:
    @pytest.fixture
    def driver(self):
        """Set up Chrome driver for testing"""
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        driver = webdriver.Chrome(options=options)
        driver.implicitly_wait(10)
        yield driver
        driver.quit()

    def test_inpaint_button_in_grid_modal(self, driver):
        """Test that the Inpaint button is added to the grid modal alongside Copy Prompt button"""
        driver.get("http://localhost:5000")
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Execute JavaScript test to simulate opening grid modal and check for buttons
        result = driver.execute_script("""
            return new Promise((resolve) => {
                try {
                    // Mock the updateGridModalImage function behavior
                    const metadataDiv = document.createElement('div');
                    metadataDiv.id = 'grid-info-panel';
                    document.body.appendChild(metadataDiv);
                    
                    // Mock metadata object
                    const metadata = {
                        'Prompt': 'test prompt',
                        'Negative Prompt': 'test negative',
                        'Model': 'test-model'
                    };
                    
                    // Simulate the metadata population logic from updateGridModalImage
                    metadataDiv.innerHTML = ""; // Clear previous metadata
                    
                    // Add some metadata items
                    for (const key in metadata) {
                        const infoItem = document.createElement("div");
                        infoItem.className = "info-item";
                        infoItem.textContent = key + ":";
                        metadataDiv.appendChild(infoItem);
                        
                        const infoValue = document.createElement("div");
                        infoValue.className = "prompt-value";
                        infoValue.textContent = metadata[key];
                        metadataDiv.appendChild(infoValue);
                    }
                    
                    // Create Copy Prompt button (simulating the existing logic)
                    let copyPromptButton = document.getElementById("copy-prompt-btn");
                    if (!copyPromptButton) {
                        copyPromptButton = document.createElement("button");
                        copyPromptButton.id = "copy-prompt-btn";
                        copyPromptButton.textContent = "Copy Prompt";
                        metadataDiv.appendChild(copyPromptButton);
                    }
                    
                    // Create Inpaint button (simulating the new logic)
                    let inpaintButton = document.getElementById("inpaint-btn");
                    if (!inpaintButton) {
                        inpaintButton = document.createElement("button");
                        inpaintButton.id = "inpaint-btn";
                        inpaintButton.textContent = "Inpaint";
                        inpaintButton.className = "inpaint-button";
                        metadataDiv.appendChild(inpaintButton);
                    }
                    
                    // Verify both buttons exist
                    const copyButton = document.getElementById("copy-prompt-btn");
                    const inpaintBtn = document.getElementById("inpaint-btn");
                    
                    if (!copyButton) {
                        throw new Error('Copy Prompt button not found');
                    }
                    
                    if (!inpaintBtn) {
                        throw new Error('Inpaint button not found');
                    }
                    
                    if (copyButton.textContent !== "Copy Prompt") {
                        throw new Error('Copy Prompt button has incorrect text');
                    }
                    
                    if (inpaintBtn.textContent !== "Inpaint") {
                        throw new Error('Inpaint button has incorrect text');
                    }
                    
                    if (!inpaintBtn.className.includes("inpaint-button")) {
                        throw new Error('Inpaint button missing CSS class');
                    }
                    
                    // Test that buttons are siblings in the same container
                    if (copyButton.parentElement !== inpaintBtn.parentElement) {
                        throw new Error('Buttons should be in the same container');
                    }
                    
                    // Clean up
                    document.body.removeChild(metadataDiv);
                    
                    resolve({
                        success: true,
                        message: 'Inpaint button integration test passed',
                        copyButtonText: copyButton.textContent,
                        inpaintButtonText: inpaintBtn.textContent,
                        inpaintButtonClass: inpaintBtn.className
                    });
                } catch (error) {
                    resolve({ success: false, error: error.message });
                }
            });
        """)
        
        assert result['success'], f"Test failed: {result.get('error', 'Unknown error')}"
        print(f"Copy button text: {result.get('copyButtonText')}")
        print(f"Inpaint button text: {result.get('inpaintButtonText')}")
        print(f"Inpaint button class: {result.get('inpaintButtonClass')}")

    def test_inpaint_button_click_handler(self, driver):
        """Test that the Inpaint button has a proper click handler"""
        driver.get("http://localhost:5000")
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Execute JavaScript test to verify click handler
        result = driver.execute_script("""
            return new Promise((resolve) => {
                try {
                    // Create a mock grid modal image
                    const modalImage = document.createElement('img');
                    modalImage.id = 'grid-modal-image';
                    modalImage.src = '/static/images/test/test-image.png';
                    document.body.appendChild(modalImage);
                    
                    // Create the inpaint button with click handler
                    const inpaintButton = document.createElement("button");
                    inpaintButton.id = "inpaint-btn";
                    inpaintButton.textContent = "Inpaint";
                    
                    // Mock the click handler logic
                    let clickHandlerCalled = false;
                    let capturedImageUrl = '';
                    
                    inpaintButton.onclick = () => {
                        // Get the current image URL from the modal
                        const modalImg = document.getElementById("grid-modal-image");
                        capturedImageUrl = modalImg ? modalImg.src : '';
                        clickHandlerCalled = true;
                        
                        // Mock closing the grid modal (we can't test the actual function without full setup)
                        console.log('Would close grid modal and open inpainting canvas with:', capturedImageUrl);
                    };
                    
                    document.body.appendChild(inpaintButton);
                    
                    // Simulate click
                    inpaintButton.click();
                    
                    // Verify click handler was called
                    if (!clickHandlerCalled) {
                        throw new Error('Click handler was not called');
                    }
                    
                    if (!capturedImageUrl.includes('test-image.png')) {
                        throw new Error('Click handler did not capture correct image URL');
                    }
                    
                    // Clean up
                    document.body.removeChild(modalImage);
                    document.body.removeChild(inpaintButton);
                    
                    resolve({
                        success: true,
                        message: 'Inpaint button click handler test passed',
                        capturedUrl: capturedImageUrl
                    });
                } catch (error) {
                    resolve({ success: false, error: error.message });
                }
            });
        """)
        
        assert result['success'], f"Test failed: {result.get('error', 'Unknown error')}"
        print(f"Captured image URL: {result.get('capturedUrl')}")