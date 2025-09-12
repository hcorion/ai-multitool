"""
Comprehensive tests for mask export functionality including binary invariant verification,
PNG export with exact resolution, temporary file cleanup system, and implementation verification.
"""

import pytest
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class TestMaskExport:
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

    # === Functional Tests (Implementation verification replaced with actual functionality testing) ===
    
    # === Unit Tests ===
    
    def test_canvas_manager_export_methods(self, driver):
        """Test CanvasManager export methods directly"""
        driver.get("data:text/html,<html><head><title>Test</title></head><body><div id='test'>Test</div></body></html>")
        
        result = driver.execute_script("""
            return new Promise(async (resolve) => {
                try {
                    // Import the CanvasManager class
                    const { CanvasManager } = await import('/static/js/inpainting/canvas-manager.js');
                    
                    // Create test canvases
                    const imageCanvas = document.createElement('canvas');
                    const overlayCanvas = document.createElement('canvas');
                    const maskAlphaCanvas = document.createElement('canvas');
                    
                    imageCanvas.width = 100;
                    imageCanvas.height = 80;
                    overlayCanvas.width = 100;
                    overlayCanvas.height = 80;
                    maskAlphaCanvas.width = 100;
                    maskAlphaCanvas.height = 80;
                    
                    // Create canvas manager
                    const canvasManager = new CanvasManager(imageCanvas, overlayCanvas, maskAlphaCanvas);
                    
                    // Create a test image
                    const testCanvas = document.createElement('canvas');
                    testCanvas.width = 100;
                    testCanvas.height = 80;
                    const ctx = testCanvas.getContext('2d');
                    ctx.fillStyle = 'white';
                    ctx.fillRect(0, 0, 100, 80);
                    const testImageUrl = testCanvas.toDataURL('image/png');
                    
                    // Load the image
                    await canvasManager.loadImage(testImageUrl);
                    
                    // Create some mask data
                    for (let x = 40; x < 50; x++) {
                        for (let y = 35; y < 45; y++) {
                            canvasManager.updateMaskData(x, y, 255);
                        }
                    }
                    
                    // Test export methods
                    const pngDataUrl = canvasManager.exportMaskAsPNG();
                    const metadata = canvasManager.exportMaskMetadata();
                    const imageData = canvasManager.exportMaskImageData();
                    
                    // Test async export
                    const asyncResult = await canvasManager.exportMaskAsPNGAsync();
                    
                    // Validate results
                    const isValidPNG = pngDataUrl.startsWith('data:image/png;base64,');
                    const asyncIsValidPNG = asyncResult.startsWith('data:image/png;base64,');
                    
                    // Calculate expected values
                    const expectedMaskedPixels = 10 * 10; // 100 pixels
                    const expectedTotalPixels = 100 * 80; // 8000 pixels
                    
                    resolve({
                        success: true,
                        isValidPNG: isValidPNG,
                        asyncIsValidPNG: asyncIsValidPNG,
                        metadata: metadata,
                        hasImageData: !!imageData,
                        expectedMaskedPixels: expectedMaskedPixels,
                        expectedTotalPixels: expectedTotalPixels,
                        masksMatch: pngDataUrl === asyncResult
                    });
                } catch (error) {
                    resolve({ success: false, error: error.message, stack: error.stack });
                }
            });
        """)
        
        assert result['success'], f"Test failed: {result.get('error', 'Unknown error')}\nStack: {result.get('stack', 'No stack')}"
        assert result['isValidPNG'], "Sync PNG export should be valid"
        assert result['asyncIsValidPNG'], "Async PNG export should be valid"
        assert result['hasImageData'], "Should have image data"
        assert result['metadata']['width'] == 100, "Width should be 100"
        assert result['metadata']['height'] == 80, "Height should be 80"
        assert result['metadata']['totalPixels'] == result['expectedTotalPixels'], "Total pixels should match"
        assert result['metadata']['isBinary'], "Mask should be binary"
        assert result['metadata']['maskedPixels'] == result['expectedMaskedPixels'], f"Expected {result['expectedMaskedPixels']} masked pixels, got {result['metadata']['maskedPixels']}"
        assert result['masksMatch'], "Sync and async exports should match" 
   
    def test_mask_file_manager_functionality(self, driver):
        """Test MaskFileManager functionality"""
        driver.get("data:text/html,<html><head><title>Test</title></head><body><div id='test'>Test</div></body></html>")
        
        result = driver.execute_script("""
            return new Promise(async (resolve) => {
                try {
                    // Import the MaskFileManager class
                    const { MaskFileManager } = await import('/static/js/inpainting/mask-file-manager.js');
                    
                    // Create a test file manager
                    const fileManager = new MaskFileManager({
                        maxAge: 1000, // 1 second for testing
                        maxFiles: 3
                    });
                    
                    // Create test data URLs
                    const testCanvas = document.createElement('canvas');
                    testCanvas.width = 50;
                    testCanvas.height = 50;
                    const ctx = testCanvas.getContext('2d');
                    ctx.fillStyle = 'black';
                    ctx.fillRect(0, 0, 50, 50);
                    const testDataUrl = testCanvas.toDataURL('image/png');
                    
                    // Test file storage
                    const fileId1 = fileManager.storeMaskFile(testDataUrl, {
                        width: 50,
                        height: 50,
                        totalPixels: 2500,
                        maskedPixels: 2500,
                        maskPercentage: 100,
                        isBinary: true
                    });
                    
                    const fileId2 = fileManager.storeMaskFile(testDataUrl);
                    const fileId3 = fileManager.storeMaskFile(testDataUrl);
                    
                    // Test retrieval
                    const file1 = fileManager.getMaskFile(fileId1);
                    
                    // Test statistics
                    const stats1 = fileManager.getStatistics();
                    
                    // Test file limit (should trigger cleanup)
                    const fileId4 = fileManager.storeMaskFile(testDataUrl);
                    const stats2 = fileManager.getStatistics();
                    
                    // Test manual cleanup
                    const cleanupResult = fileManager.removeMaskFile(fileId2);
                    const stats3 = fileManager.getStatistics();
                    
                    // Test cleanup all
                    const cleanupAllCount = fileManager.cleanupAllFiles();
                    const stats4 = fileManager.getStatistics();
                    
                    resolve({
                        success: true,
                        fileId1: fileId1,
                        hasFile1: !!file1,
                        file1HasMetadata: !!(file1 && file1.metadata),
                        stats1: stats1,
                        stats2: stats2,
                        stats3: stats3,
                        stats4: stats4,
                        cleanupResult: cleanupResult,
                        cleanupAllCount: cleanupAllCount
                    });
                } catch (error) {
                    resolve({ success: false, error: error.message, stack: error.stack });
                }
            });
        """)
        
        assert result['success'], f"Test failed: {result.get('error', 'Unknown error')}\nStack: {result.get('stack', 'No stack')}"
        assert result['fileId1'], "File ID should be generated"
        assert result['hasFile1'], "Should be able to retrieve stored file"
        assert result['file1HasMetadata'], "File should have metadata"
        assert result['stats1']['totalFiles'] >= 3, "Should have at least 3 files after creation"
        assert result['stats2']['totalFiles'] <= 3, "Should enforce file limit"
        assert result['cleanupResult'], "Manual cleanup should succeed"
        assert result['stats4']['totalFiles'] == 0, "Should have no files after cleanup all"    
# === Integration Tests ===
    
    def test_mask_export_binary_invariant(self, driver):
        """Test that exported masks contain only binary values (0 or 255)"""
        driver.get("http://localhost:5000/")
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "prompt-form"))
        )
        
        result = driver.execute_script("""
            return new Promise(async (resolve) => {
                try {
                    // Create test image (100x100 white image)
                    const testCanvas = document.createElement('canvas');
                    testCanvas.width = 100;
                    testCanvas.height = 100;
                    const ctx = testCanvas.getContext('2d');
                    ctx.fillStyle = 'white';
                    ctx.fillRect(0, 0, 100, 100);
                    const testImageUrl = testCanvas.toDataURL('image/png');
                    
                    // Import the InpaintingMaskCanvas class
                    const { InpaintingMaskCanvas } = await import('/static/js/inpainting/inpainting-mask-canvas.js');
                    
                    const container = document.body;
                    const maskCanvas = new InpaintingMaskCanvas({
                        imageUrl: testImageUrl,
                        containerElement: container,
                        onMaskComplete: () => {},
                        onCancel: () => {}
                    });
                    
                    await maskCanvas.show();
                    
                    // Simulate some brush strokes to create mask data
                    const canvasManager = maskCanvas.canvasManager;
                    canvasManager.startBrushStroke(25, 25, 10, 'paint');
                    canvasManager.continueBrushStroke(35, 35);
                    canvasManager.endBrushStroke();
                    
                    canvasManager.startBrushStroke(75, 75, 15, 'paint');
                    canvasManager.continueBrushStroke(85, 85);
                    canvasManager.endBrushStroke();
                    
                    // Export mask and verify binary invariant
                    const maskDataUrl = maskCanvas.exportMask();
                    
                    // Get mask metadata
                    const metadata = canvasManager.exportMaskMetadata();
                    
                    // Verify the exported mask contains only binary values
                    const isBinary = metadata.isBinary;
                    
                    // Also verify the data URL format
                    const isValidPNG = maskDataUrl.startsWith('data:image/png;base64,');
                    
                    // Get the actual mask data for pixel-level verification
                    const state = canvasManager.getState();
                    let allBinary = true;
                    let nonZeroCount = 0;
                    let zeroCount = 0;
                    
                    for (let i = 0; i < state.maskData.length; i++) {
                        const value = state.maskData[i];
                        if (value === 0) {
                            zeroCount++;
                        } else if (value === 255) {
                            nonZeroCount++;
                        } else {
                            allBinary = false;
                            break;
                        }
                    }
                    
                    // Cleanup
                    maskCanvas.hide();
                    
                    resolve({
                        success: true,
                        isBinary: isBinary,
                        allBinary: allBinary,
                        isValidPNG: isValidPNG,
                        metadata: metadata,
                        pixelCounts: { zeroCount, nonZeroCount },
                        maskDataUrl: maskDataUrl.substring(0, 50) + '...' // Truncate for logging
                    });
                } catch (error) {
                    resolve({ success: false, error: error.message });
                }
            });
        """)
        
        assert result['success'], f"Test failed: {result.get('error', 'Unknown error')}"
        assert result['isBinary'], "Metadata indicates mask is not binary"
        assert result['allBinary'], "Pixel-level check found non-binary values"
        assert result['isValidPNG'], "Exported mask is not a valid PNG data URL"
        assert result['metadata']['width'] == 100, "Mask width should match image width"
        assert result['metadata']['height'] == 100, "Mask height should match image height"
        assert result['pixelCounts']['nonZeroCount'] > 0, "Should have some painted pixels"
    def test_mask_export_exact_resolution(self, driver):
        """Test that exported masks have exact image resolution"""
        driver.get("http://localhost:5000/")
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "prompt-form"))
        )
        
        result = driver.execute_script("""
            return new Promise(async (resolve) => {
                try {
                    // Test with a specific image size
                    const testSize = { width: 128, height: 96 };
                    
                    // Create test image with specific dimensions
                    const testCanvas = document.createElement('canvas');
                    testCanvas.width = testSize.width;
                    testCanvas.height = testSize.height;
                    const ctx = testCanvas.getContext('2d');
                    ctx.fillStyle = 'white';
                    ctx.fillRect(0, 0, testSize.width, testSize.height);
                    const testImageUrl = testCanvas.toDataURL('image/png');
                    
                    // Import the InpaintingMaskCanvas class
                    const { InpaintingMaskCanvas } = await import('/static/js/inpainting/inpainting-mask-canvas.js');
                    
                    const container = document.body;
                    const maskCanvas = new InpaintingMaskCanvas({
                        imageUrl: testImageUrl,
                        containerElement: container,
                        onMaskComplete: () => {},
                        onCancel: () => {}
                    });
                    
                    await maskCanvas.show();
                    
                    const canvasManager = maskCanvas.canvasManager;
                    const metadata = canvasManager.exportMaskMetadata();
                    
                    // Cleanup
                    maskCanvas.hide();
                    
                    const result = {
                        inputSize: testSize,
                        outputSize: { width: metadata.width, height: metadata.height },
                        matches: metadata.width === testSize.width && metadata.height === testSize.height
                    };
                    
                    resolve({
                        success: true,
                        result: result
                    });
                } catch (error) {
                    resolve({ success: false, error: error.message });
                }
            });
        """)
        
        assert result['success'], f"Test failed: {result.get('error', 'Unknown error')}"
        test_result = result['result']
        assert test_result['matches'], f"Resolution mismatch: input {test_result['inputSize']} != output {test_result['outputSize']}"
    
    def test_binary_invariant_enforcement(self, driver):
        """Test that binary invariant is enforced during export even if violated"""
        driver.get("data:text/html,<html><head><title>Test</title></head><body><div id='test'>Test</div></body></html>")
        
        result = driver.execute_script("""
            return new Promise(async (resolve) => {
                try {
                    // Import required classes
                    const { CanvasManager } = await import('/static/js/inpainting/canvas-manager.js');
                    const { BrushEngine } = await import('/static/js/inpainting/brush-engine.js');
                    
                    // Create test canvases
                    const imageCanvas = document.createElement('canvas');
                    const overlayCanvas = document.createElement('canvas');
                    const maskAlphaCanvas = document.createElement('canvas');
                    
                    imageCanvas.width = 50;
                    imageCanvas.height = 50;
                    overlayCanvas.width = 50;
                    overlayCanvas.height = 50;
                    maskAlphaCanvas.width = 50;
                    maskAlphaCanvas.height = 50;
                    
                    // Create canvas manager
                    const canvasManager = new CanvasManager(imageCanvas, overlayCanvas, maskAlphaCanvas);
                    
                    // Create a test image
                    const testCanvas = document.createElement('canvas');
                    testCanvas.width = 50;
                    testCanvas.height = 50;
                    const ctx = testCanvas.getContext('2d');
                    ctx.fillStyle = 'white';
                    ctx.fillRect(0, 0, 50, 50);
                    const testImageUrl = testCanvas.toDataURL('image/png');
                    
                    // Load the image
                    await canvasManager.loadImage(testImageUrl);
                    
                    const state = canvasManager.getState();
                    
                    // Deliberately corrupt the mask data with non-binary values
                    state.maskData[100] = 127; // Gray value
                    state.maskData[200] = 64;  // Another gray value
                    state.maskData[300] = 192; // Another gray value
                    
                    // Verify corruption
                    const isCorrupted = !BrushEngine.validateBinaryMask(state.maskData);
                    
                    // Export mask (should enforce binary invariant)
                    const maskDataUrl = canvasManager.exportMaskAsPNG();
                    
                    // Check if binary invariant is now enforced
                    const isFixedAfterExport = BrushEngine.validateBinaryMask(state.maskData);
                    
                    // Get metadata to verify
                    const metadata = canvasManager.exportMaskMetadata();
                    
                    resolve({
                        success: true,
                        wasCorrupted: isCorrupted,
                        isFixedAfterExport: isFixedAfterExport,
                        metadataIsBinary: metadata.isBinary,
                        hasValidPNG: maskDataUrl.startsWith('data:image/png;base64,')
                    });
                } catch (error) {
                    resolve({ success: false, error: error.message, stack: error.stack });
                }
            });
        """)
        
        assert result['success'], f"Test failed: {result.get('error', 'Unknown error')}\nStack: {result.get('stack', 'No stack')}"
        assert result['wasCorrupted'], "Mask should have been corrupted initially"
        assert result['isFixedAfterExport'], "Binary invariant should be enforced after export"
        assert result['metadataIsBinary'], "Metadata should indicate mask is binary after export"
        assert result['hasValidPNG'], "Should produce valid PNG after fixing binary invariant"
    def test_temporary_file_management(self, driver):
        """Test temporary file cleanup system"""
        driver.get("http://localhost:5000/")
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "prompt-form"))
        )
        
        result = driver.execute_script("""
            return new Promise(async (resolve) => {
                try {
                    // Import required classes
                    const { InpaintingMaskCanvas } = await import('/static/js/inpainting/inpainting-mask-canvas.js');
                    const { MaskFileManager } = await import('/static/js/inpainting/mask-file-manager.js');
                    
                    // Create test image
                    const testCanvas = document.createElement('canvas');
                    testCanvas.width = 50;
                    testCanvas.height = 50;
                    const ctx = testCanvas.getContext('2d');
                    ctx.fillStyle = 'white';
                    ctx.fillRect(0, 0, 50, 50);
                    const testImageUrl = testCanvas.toDataURL('image/png');
                    
                    // Create mask canvas with file manager
                    const container = document.createElement('div');
                    document.body.appendChild(container);
                    
                    const maskCanvas = new InpaintingMaskCanvas({
                        imageUrl: testImageUrl,
                        containerElement: container,
                        onMaskComplete: () => {},
                        onCancel: () => {},
                        enableFileManager: true
                    });
                    
                    await maskCanvas.show();
                    const canvasManager = maskCanvas.canvasManager;
                    
                    // Create some mask data
                    canvasManager.startBrushStroke(25, 25, 5, 'paint');
                    canvasManager.endBrushStroke();
                    
                    // Test temporary file creation
                    const { dataUrl, fileId } = maskCanvas.exportMaskAsTemporaryFile();
                    
                    // Verify file was created
                    const stats1 = maskCanvas.getTemporaryFileStatistics();
                    
                    // Create more files to test limit enforcement
                    const file2 = maskCanvas.exportMaskAsTemporaryFile();
                    const file3 = maskCanvas.exportMaskAsTemporaryFile();
                    const file4 = maskCanvas.exportMaskAsTemporaryFile(); // Should trigger cleanup
                    
                    const stats2 = maskCanvas.getTemporaryFileStatistics();
                    
                    // Test manual cleanup
                    const cleanupResult = maskCanvas.cleanupTemporaryFile(file2.fileId);
                    
                    const stats3 = maskCanvas.getTemporaryFileStatistics();
                    
                    // Cleanup
                    maskCanvas.hide();
                    container.remove();
                    
                    resolve({
                        success: true,
                        fileId: fileId,
                        hasDataUrl: !!dataUrl,
                        stats1: stats1,
                        stats2: stats2,
                        stats3: stats3,
                        cleanupResult: cleanupResult
                    });
                } catch (error) {
                    resolve({ success: false, error: error.message });
                }
            });
        """)
        
        assert result['success'], f"Test failed: {result.get('error', 'Unknown error')}"
        assert result['fileId'] is not None, "File ID should be generated"
        assert result['hasDataUrl'], "Data URL should be present"
        assert result['stats1']['totalFiles'] >= 1, "Should have at least one file after creation"
        assert result['stats2']['totalFiles'] <= 3, "Should enforce file limit"
        assert result['cleanupResult'], "Manual cleanup should succeed"