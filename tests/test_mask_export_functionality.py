"""
Test mask export functionality including binary invariant verification,
PNG export with exact resolution, and temporary file cleanup system.
"""

import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class TestMaskExportFunctionality:
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

    def test_mask_export_binary_invariant(self, driver):
        """Test that exported masks contain only binary values (0 or 255)"""
        driver.get("http://localhost:5000/")
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "prompt-form"))
        )
        
        result = driver.execute_script("""
            return new Promise((resolve) => {
                // Create test image (100x100 white image)
                const testCanvas = document.createElement('canvas');
                testCanvas.width = 100;
                testCanvas.height = 100;
                const ctx = testCanvas.getContext('2d');
                ctx.fillStyle = 'white';
                ctx.fillRect(0, 0, 100, 100);
                const testImageUrl = testCanvas.toDataURL('image/png');
                
                // Use the global openInpaintingMaskCanvas function
                if (typeof window.openInpaintingMaskCanvas === 'function') {
                    // Mock the onMaskComplete callback to capture the result
                    let maskResult = null;
                    let originalOnComplete = null;
                    
                    // Temporarily override the function to capture mask data
                    const originalFunction = window.openInpaintingMaskCanvas;
                    window.openInpaintingMaskCanvas = async function(imageUrl) {
                        try {
                            // Import the InpaintingMaskCanvas class
                            const { InpaintingMaskCanvas } = await import('/static/js/inpainting-mask-canvas.js');
                            
                            const container = document.body;
                            const maskCanvas = new InpaintingMaskCanvas({
                                imageUrl: testImageUrl,
                                containerElement: container,
                                onMaskComplete: (maskDataUrl, fileId) => {
                                    maskResult = { maskDataUrl, fileId };
                                },
                                onCancel: () => {
                                    maskResult = { cancelled: true };
                                }
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
                            
                            // Restore original function
                            window.openInpaintingMaskCanvas = originalFunction;
                            
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
                            // Restore original function on error
                            window.openInpaintingMaskCanvas = originalFunction;
                            resolve({ success: false, error: error.message });
                        }
                    };
                    
                    // Call the function with test image
                    window.openInpaintingMaskCanvas(testImageUrl);
                } else {
                    resolve({ success: false, error: 'openInpaintingMaskCanvas function not found' });
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
                    const { InpaintingMaskCanvas } = await import('/static/js/inpainting-mask-canvas.js');
                    
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

    def test_async_mask_export_binary_invariant(self, driver):
        """Test that async exported masks maintain binary invariant"""
        driver.get("http://localhost:5000/")
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "prompt-form"))
        )
        
        result = driver.execute_script("""
            return new Promise(async (resolve) => {
                try {
                    // Create test image
                    const testCanvas = document.createElement('canvas');
                    testCanvas.width = 200;
                    testCanvas.height = 150;
                    const ctx = testCanvas.getContext('2d');
                    ctx.fillStyle = 'white';
                    ctx.fillRect(0, 0, 200, 150);
                    const testImageUrl = testCanvas.toDataURL('image/png');
                    
                    // Import the InpaintingMaskCanvas class
                    const { InpaintingMaskCanvas } = await import('/static/js/inpainting-mask-canvas.js');
                    
                    const container = document.body;
                    const maskCanvas = new InpaintingMaskCanvas({
                        imageUrl: testImageUrl,
                        containerElement: container,
                        onMaskComplete: () => {},
                        onCancel: () => {}
                    });
                    
                    await maskCanvas.show();
                    const canvasManager = maskCanvas.canvasManager;
                    
                    // Create complex mask pattern
                    for (let i = 0; i < 5; i++) {
                        const x = 20 + i * 15;
                        const y = 20 + i * 10;
                        canvasManager.startBrushStroke(x, y, 8, 'paint');
                        canvasManager.continueBrushStroke(x + 10, y + 10);
                        canvasManager.endBrushStroke();
                    }
                    
                    // Test both sync and async export
                    const syncMask = maskCanvas.exportMask();
                    const asyncMask = await maskCanvas.exportMaskAsync();
                    
                    // Get metadata for both
                    const metadata = canvasManager.exportMaskMetadata();
                    
                    // Verify both exports are valid PNGs
                    const syncIsValidPNG = syncMask.startsWith('data:image/png;base64,');
                    const asyncIsValidPNG = asyncMask.startsWith('data:image/png;base64,');
                    
                    // Verify binary invariant
                    const isBinary = metadata.isBinary;
                    
                    // Cleanup
                    maskCanvas.hide();
                    
                    resolve({
                        success: true,
                        syncIsValidPNG: syncIsValidPNG,
                        asyncIsValidPNG: asyncIsValidPNG,
                        isBinary: isBinary,
                        metadata: metadata,
                        masksMatch: syncMask === asyncMask
                    });
                } catch (error) {
                    resolve({ success: false, error: error.message });
                }
            });
        """)
        
        assert result['success'], f"Test failed: {result.get('error', 'Unknown error')}"
        assert result['syncIsValidPNG'], "Sync export is not a valid PNG"
        assert result['asyncIsValidPNG'], "Async export is not a valid PNG"
        assert result['isBinary'], "Exported mask is not binary"
        assert result['masksMatch'], "Sync and async exports should produce identical results"

    def test_temporary_file_management(self, driver):
        """Test temporary file cleanup system"""
        driver.get("http://localhost:5000/")
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "prompt-form"))
        )
        
        result = driver.execute_script("""
            return new Promise((resolve) => {
                import('/static/js/inpainting-mask-canvas.js').then(({ InpaintingMaskCanvas }) => {
                    import('/static/js/mask-file-manager.js').then(({ MaskFileManager }) => {
                        try {
                            // Create a test file manager
                            const fileManager = new MaskFileManager({
                                maxAge: 1000, // 1 second for testing
                                maxFiles: 3,
                                autoCleanupInterval: 500 // 0.5 seconds
                            });
                            
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
                            
                            maskCanvas.show().then(() => {
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
                                fileManager.cleanup();
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
                            }).catch(error => {
                                resolve({ success: false, error: error.message });
                            });
                        } catch (error) {
                            resolve({ success: false, error: error.message });
                        }
                    });
                });
            });
        """)
        
        assert result['success'], f"Test failed: {result.get('error', 'Unknown error')}"
        assert result['fileId'] is not None, "File ID should be generated"
        assert result['hasDataUrl'], "Data URL should be present"
        assert result['stats1']['totalFiles'] >= 1, "Should have at least one file after creation"
        assert result['stats2']['totalFiles'] <= 3, "Should enforce file limit"
        assert result['cleanupResult'], "Manual cleanup should succeed"

    def test_mask_export_with_metadata(self, driver):
        """Test mask export with comprehensive metadata"""
        driver.get("http://localhost:5000/")
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "prompt-form"))
        )
        
        result = driver.execute_script("""
            return new Promise((resolve) => {
                import('/static/js/inpainting-mask-canvas.js').then(({ InpaintingMaskCanvas }) => {
                    try {
                        // Create test image
                        const testCanvas = document.createElement('canvas');
                        testCanvas.width = 100;
                        testCanvas.height = 80;
                        const ctx = testCanvas.getContext('2d');
                        ctx.fillStyle = 'white';
                        ctx.fillRect(0, 0, 100, 80);
                        const testImageUrl = testCanvas.toDataURL('image/png');
                        
                        // Create mask canvas
                        const container = document.createElement('div');
                        document.body.appendChild(container);
                        
                        const maskCanvas = new InpaintingMaskCanvas({
                            imageUrl: testImageUrl,
                            containerElement: container,
                            onMaskComplete: () => {},
                            onCancel: () => {}
                        });
                        
                        maskCanvas.show().then(async () => {
                            const canvasManager = maskCanvas.canvasManager;
                            
                            // Create known mask pattern (paint a 10x10 square)
                            for (let x = 40; x < 50; x++) {
                                for (let y = 35; y < 45; y++) {
                                    canvasManager.updateMaskData(x, y, 255);
                                }
                            }
                            
                            // Export with metadata
                            const exportResult = maskCanvas.exportMaskWithMetadata();
                            const asyncExportResult = await maskCanvas.exportMaskWithMetadataAsync();
                            
                            // Calculate expected values
                            const expectedMaskedPixels = 10 * 10; // 100 pixels
                            const expectedTotalPixels = 100 * 80; // 8000 pixels
                            const expectedPercentage = (expectedMaskedPixels / expectedTotalPixels) * 100;
                            
                            // Cleanup
                            maskCanvas.hide();
                            container.remove();
                            
                            resolve({
                                success: true,
                                syncMetadata: exportResult.metadata,
                                asyncMetadata: asyncExportResult.metadata,
                                expectedMaskedPixels: expectedMaskedPixels,
                                expectedTotalPixels: expectedTotalPixels,
                                expectedPercentage: expectedPercentage
                            });
                        }).catch(error => {
                            resolve({ success: false, error: error.message });
                        });
                    } catch (error) {
                        resolve({ success: false, error: error.message });
                    }
                });
            });
        """)
        
        assert result['success'], f"Test failed: {result.get('error', 'Unknown error')}"
        
        sync_meta = result['syncMetadata']
        async_meta = result['asyncMetadata']
        
        # Verify metadata consistency
        assert sync_meta['width'] == 100, "Width should be 100"
        assert sync_meta['height'] == 80, "Height should be 80"
        assert sync_meta['totalPixels'] == result['expectedTotalPixels'], "Total pixels should match"
        assert sync_meta['isBinary'], "Mask should be binary"
        assert sync_meta['maskedPixels'] == result['expectedMaskedPixels'], f"Expected {result['expectedMaskedPixels']} masked pixels, got {sync_meta['maskedPixels']}"
        
        # Verify sync and async metadata match
        assert sync_meta['width'] == async_meta['width'], "Sync and async width should match"
        assert sync_meta['height'] == async_meta['height'], "Sync and async height should match"
        assert sync_meta['maskedPixels'] == async_meta['maskedPixels'], "Sync and async masked pixels should match"
        assert sync_meta['isBinary'] == async_meta['isBinary'], "Sync and async binary status should match"

    def test_binary_invariant_enforcement(self, driver):
        """Test that binary invariant is enforced during export even if violated"""
        driver.get("http://localhost:5000/")
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "prompt-form"))
        )
        
        result = driver.execute_script("""
            return new Promise((resolve) => {
                import('/static/js/inpainting-mask-canvas.js').then(({ InpaintingMaskCanvas }) => {
                    import('/static/js/brush-engine.js').then(({ BrushEngine }) => {
                        try {
                            // Create test image
                            const testCanvas = document.createElement('canvas');
                            testCanvas.width = 50;
                            testCanvas.height = 50;
                            const ctx = testCanvas.getContext('2d');
                            ctx.fillStyle = 'white';
                            ctx.fillRect(0, 0, 50, 50);
                            const testImageUrl = testCanvas.toDataURL('image/png');
                            
                            // Create mask canvas
                            const container = document.createElement('div');
                            document.body.appendChild(container);
                            
                            const maskCanvas = new InpaintingMaskCanvas({
                                imageUrl: testImageUrl,
                                containerElement: container,
                                onMaskComplete: () => {},
                                onCancel: () => {}
                            });
                            
                            maskCanvas.show().then(() => {
                                const canvasManager = maskCanvas.canvasManager;
                                const state = canvasManager.getState();
                                
                                // Deliberately corrupt the mask data with non-binary values
                                state.maskData[100] = 127; // Gray value
                                state.maskData[200] = 64;  // Another gray value
                                state.maskData[300] = 192; // Another gray value
                                
                                // Verify corruption
                                const isCorrupted = !BrushEngine.validateBinaryMask(state.maskData);
                                
                                // Export mask (should enforce binary invariant)
                                const maskDataUrl = maskCanvas.exportMask();
                                
                                // Check if binary invariant is now enforced
                                const isFixedAfterExport = BrushEngine.validateBinaryMask(state.maskData);
                                
                                // Get metadata to verify
                                const metadata = canvasManager.exportMaskMetadata();
                                
                                // Cleanup
                                maskCanvas.hide();
                                container.remove();
                                
                                resolve({
                                    success: true,
                                    wasCorrupted: isCorrupted,
                                    isFixedAfterExport: isFixedAfterExport,
                                    metadataIsBinary: metadata.isBinary,
                                    hasValidPNG: maskDataUrl.startsWith('data:image/png;base64,')
                                });
                            }).catch(error => {
                                resolve({ success: false, error: error.message });
                            });
                        } catch (error) {
                            resolve({ success: false, error: error.message });
                        }
                    });
                });
            });
        """)
        
        assert result['success'], f"Test failed: {result.get('error', 'Unknown error')}"
        assert result['wasCorrupted'], "Mask should have been corrupted initially"
        assert result['isFixedAfterExport'], "Binary invariant should be enforced after export"
        assert result['metadataIsBinary'], "Metadata should indicate mask is binary after export"
        assert result['hasValidPNG'], "Should produce valid PNG after fixing binary invariant"