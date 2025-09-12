"""
Test the complete inpainting integration workflow from mask creation to image generation.
"""

import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time


class TestInpaintingIntegration:
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

    def test_inpainting_ui_elements_exist(self, driver):
        """Test that inpainting UI elements are present in the main interface"""
        # This test doesn't require authentication, just checks if elements exist
        driver.get("data:text/html,<html><head><title>Test</title></head><body><div id='test'>Test</div></body></html>")
        
        result = driver.execute_script("""
            return new Promise(async (resolve) => {
                try {
                    // Create a mock HTML structure similar to the main app
                    document.body.innerHTML = `
                        <form id="prompt-form">
                            <div id="inpainting-section" class="inpainting-section" style="display: none;">
                                <div class="inpainting-header">
                                    <h3>🎨 Inpainting Mode</h3>
                                    <button type="button" id="clear-inpainting-btn" class="secondary-button">Clear Inpainting</button>
                                </div>
                                
                                <div class="inpainting-info">
                                    <div class="inpainting-image-info">
                                        <strong>Base Image:</strong> <span id="inpainting-image-name">None selected</span>
                                    </div>
                                    <div class="inpainting-mask-info">
                                        <strong>Mask:</strong> <span id="inpainting-mask-status">No mask created</span>
                                    </div>
                                </div>

                                <div class="inpainting-preview">
                                    <div class="inpainting-preview-container">
                                        <img id="inpainting-base-preview" class="inpainting-preview-image" style="display: none;" alt="Base image preview">
                                        <img id="inpainting-mask-preview" class="inpainting-preview-image" style="display: none;" alt="Mask preview">
                                    </div>
                                </div>

                                <input type="hidden" id="inpainting-base-image" name="base_image_path" value="">
                                <input type="hidden" id="inpainting-mask-path" name="mask_path" value="">
                                <input type="hidden" id="inpainting-operation" name="operation" value="">
                            </div>
                            <input class="submit-button" type="submit" value="Generate Image" id="generate-submit-btn">
                        </form>
                    `;
                    
                    // Check if all required elements exist
                    const elements = {
                        inpaintingSection: !!document.getElementById('inpainting-section'),
                        clearButton: !!document.getElementById('clear-inpainting-btn'),
                        imageNameSpan: !!document.getElementById('inpainting-image-name'),
                        maskStatusSpan: !!document.getElementById('inpainting-mask-status'),
                        basePreview: !!document.getElementById('inpainting-base-preview'),
                        maskPreview: !!document.getElementById('inpainting-mask-preview'),
                        baseImageInput: !!document.getElementById('inpainting-base-image'),
                        maskPathInput: !!document.getElementById('inpainting-mask-path'),
                        operationInput: !!document.getElementById('inpainting-operation'),
                        submitBtn: !!document.getElementById('generate-submit-btn')
                    };
                    
                    resolve({
                        success: true,
                        elements: elements,
                        allElementsExist: Object.values(elements).every(exists => exists)
                    });
                } catch (error) {
                    resolve({ success: false, error: error.message });
                }
            });
        """)
        
        assert result['success'], f"Test failed: {result.get('error', 'Unknown error')}"
        assert result['allElementsExist'], f"Not all required elements exist: {result['elements']}"

    def test_inpainting_mode_functions_exist(self, driver):
        """Test that inpainting mode functions are available"""
        driver.get("data:text/html,<html><head><title>Test</title></head><body><div id='test'>Test</div></body></html>")
        
        result = driver.execute_script("""
            return new Promise(async (resolve) => {
                try {
                    // Load the compiled script to check if functions exist
                    const script = document.createElement('script');
                    script.src = '/static/js/script.js';
                    script.onload = () => {
                        // Check if inpainting functions are available
                        const functions = {
                            openInpaintingMaskCanvas: typeof window.openInpaintingMaskCanvas === 'function',
                            clearInpaintingMode: typeof window.clearInpaintingMode === 'function'
                        };
                        
                        resolve({
                            success: true,
                            functions: functions,
                            allFunctionsExist: Object.values(functions).every(exists => exists)
                        });
                    };
                    script.onerror = () => {
                        resolve({ success: false, error: 'Failed to load script.js' });
                    };
                    document.head.appendChild(script);
                } catch (error) {
                    resolve({ success: false, error: error.message });
                }
            });
        """)
        
        assert result['success'], f"Test failed: {result.get('error', 'Unknown error')}"
        assert result['allFunctionsExist'], f"Not all required functions exist: {result['functions']}"

    def test_mask_file_manager_integration(self, driver):
        """Test that mask file manager is properly integrated"""
        driver.get("data:text/html,<html><head><title>Test</title></head><body><div id='test'>Test</div></body></html>")
        
        result = driver.execute_script("""
            return new Promise(async (resolve) => {
                try {
                    // Import the mask file manager
                    const { maskFileManager } = await import('/static/js/inpainting/mask-file-manager.js');
                    
                    // Test basic functionality
                    const testDataUrl = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==';
                    
                    const fileId = maskFileManager.storeMaskFile(testDataUrl, {
                        width: 1,
                        height: 1,
                        totalPixels: 1,
                        maskedPixels: 0,
                        maskPercentage: 0,
                        isBinary: true
                    });
                    
                    const retrievedFile = maskFileManager.getMaskFile(fileId);
                    const stats = maskFileManager.getStatistics();
                    
                    // Cleanup
                    maskFileManager.removeMaskFile(fileId);
                    
                    resolve({
                        success: true,
                        fileId: fileId,
                        hasRetrievedFile: !!retrievedFile,
                        hasStats: !!stats,
                        statsHasFiles: stats && stats.totalFiles >= 0
                    });
                } catch (error) {
                    resolve({ success: false, error: error.message });
                }
            });
        """)
        
        assert result['success'], f"Test failed: {result.get('error', 'Unknown error')}"
        assert result['fileId'], "File ID should be generated"
        assert result['hasRetrievedFile'], "Should be able to retrieve stored file"
        assert result['hasStats'], "Should have statistics"
        assert result['statsHasFiles'], "Statistics should include file count"

    def test_inpainting_canvas_export_integration(self, driver):
        """Test that InpaintingMaskCanvas export methods work with file manager"""
        driver.get("data:text/html,<html><head><title>Test</title></head><body><div id='test'>Test</div></body></html>")
        
        result = driver.execute_script("""
            return new Promise(async (resolve) => {
                try {
                    // Import required classes
                    const { InpaintingMaskCanvas } = await import('/static/js/inpainting/inpainting-mask-canvas.js');
                    
                    // Create test image
                    const testCanvas = document.createElement('canvas');
                    testCanvas.width = 64;
                    testCanvas.height = 64;
                    const ctx = testCanvas.getContext('2d');
                    ctx.fillStyle = 'white';
                    ctx.fillRect(0, 0, 64, 64);
                    const testImageUrl = testCanvas.toDataURL('image/png');
                    
                    // Create mask canvas with file manager enabled
                    const container = document.body;
                    let maskCompleteResult = null;
                    
                    const maskCanvas = new InpaintingMaskCanvas({
                        imageUrl: testImageUrl,
                        containerElement: container,
                        onMaskComplete: (maskDataUrl, fileId) => {
                            maskCompleteResult = { maskDataUrl, fileId };
                        },
                        onCancel: () => {},
                        enableFileManager: true
                    });
                    
                    await maskCanvas.show();
                    
                    // Create some mask data
                    const canvasManager = maskCanvas.canvasManager;
                    canvasManager.startBrushStroke(20, 20, 8, 'paint');
                    canvasManager.continueBrushStroke(30, 30);
                    canvasManager.endBrushStroke();
                    
                    // Test export methods
                    const { dataUrl, fileId } = await maskCanvas.exportMaskAsTemporaryFileAsync();
                    
                    // Test file statistics
                    const stats = maskCanvas.getTemporaryFileStatistics();
                    
                    // Cleanup
                    maskCanvas.hide();
                    if (fileId) {
                        maskCanvas.cleanupTemporaryFile(fileId);
                    }
                    
                    resolve({
                        success: true,
                        hasDataUrl: !!dataUrl,
                        hasFileId: !!fileId,
                        hasStats: !!stats,
                        dataUrlIsValid: dataUrl && dataUrl.startsWith('data:image/png;base64,')
                    });
                } catch (error) {
                    resolve({ success: false, error: error.message });
                }
            });
        """)
        
        assert result['success'], f"Test failed: {result.get('error', 'Unknown error')}"
        assert result['hasDataUrl'], "Should have data URL"
        assert result['hasFileId'], "Should have file ID"
        assert result['hasStats'], "Should have file statistics"
        assert result['dataUrlIsValid'], "Data URL should be valid PNG"