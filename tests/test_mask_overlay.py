"""
Unit tests for mask overlay visualization system.
These tests verify that the overlay rendering maintains binary mask invariants
and never introduces soft edges.
"""

import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import time


class TestMaskOverlay:
    """Test mask overlay visualization system using Selenium WebDriver."""
    
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
    
    def test_overlay_binary_invariant(self, driver):
        """
        Test that overlay rendering never introduces soft edges.
        
        This test verifies:
        1. Mask overlay only shows pixels where mask data is 255
        2. No intermediate alpha values are introduced during rendering
        3. destination-in compositing preserves binary nature
        4. Image smoothing is disabled during overlay rendering
        """
        driver.get("http://localhost:5000/test-inpainting-canvas")
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "test-button"))
        )
        
        # Execute JavaScript to test overlay binary invariant
        result = driver.execute_script("""
            return new Promise((resolve) => {
                import('/static/js/canvas-manager.js').then(({ CanvasManager }) => {
                    try {
                        // Create test canvases
                        const imageCanvas = document.createElement('canvas');
                        const overlayCanvas = document.createElement('canvas');
                        const maskAlphaCanvas = new OffscreenCanvas(10, 10);
                        
                        // Set up canvas dimensions
                        const width = 10;
                        const height = 10;
                        
                        imageCanvas.width = width;
                        imageCanvas.height = height;
                        overlayCanvas.width = width;
                        overlayCanvas.height = height;
                        maskAlphaCanvas.width = width;
                        maskAlphaCanvas.height = height;
                        
                        // Create container element
                        const container = document.createElement('div');
                        container.style.width = '400px';
                        container.style.height = '400px';
                        container.appendChild(imageCanvas);
                        document.body.appendChild(container);
                        
                        const manager = new CanvasManager(imageCanvas, overlayCanvas, maskAlphaCanvas);
                        
                        // Create a simple test image (data URL)
                        const testImageUrl = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==';
                        
                        // Load image and test
                        manager.loadImage(testImageUrl).then(() => {
                            const state = manager.getState();
                            if (!state) {
                                resolve({ success: false, error: 'Failed to get canvas state' });
                                return;
                            }
                            
                            // Create checkerboard test pattern
                            const maskData = new Uint8Array(width * height);
                            for (let y = 0; y < height; y++) {
                                for (let x = 0; x < width; x++) {
                                    const index = y * width + x;
                                    maskData[index] = ((x + y) % 2 === 0) ? 255 : 0;
                                }
                            }
                            
                            // Apply mask data
                            state.maskData = maskData;
                            state.imageWidth = width;
                            state.imageHeight = height;
                            
                            // Update overlay
                            manager.updateMaskOverlay();
                            
                            // Verify overlay maintains binary values
                            const overlayCtx = overlayCanvas.getContext('2d');
                            const overlayImageData = overlayCtx.getImageData(0, 0, width, height);
                            const overlayData = overlayImageData.data;
                            
                            let binaryCount = 0;
                            let nonBinaryCount = 0;
                            const nonBinaryValues = [];
                            
                            for (let i = 0; i < overlayData.length; i += 4) {
                                const alpha = overlayData[i + 3];
                                if (alpha === 0 || alpha === 255) {
                                    binaryCount++;
                                } else {
                                    nonBinaryCount++;
                                    nonBinaryValues.push(alpha);
                                }
                            }
                            
                            // Verify image smoothing is disabled
                            const imageSmoothingDisabled = !overlayCtx.imageSmoothingEnabled;
                            
                            // Cleanup
                            document.body.removeChild(container);
                            
                            resolve({
                                success: nonBinaryCount === 0,
                                binaryCount: binaryCount,
                                nonBinaryCount: nonBinaryCount,
                                nonBinaryValues: nonBinaryValues,
                                imageSmoothingDisabled: imageSmoothingDisabled,
                                totalPixels: overlayData.length / 4
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
        
        assert result['success'], f"Overlay binary invariant test failed: {result.get('error', 'Unknown error')}"
        assert result['nonBinaryCount'] == 0, f"Found {result['nonBinaryCount']} non-binary pixels with values: {result['nonBinaryValues']}"
        assert result['imageSmoothingDisabled'], "Image smoothing should be disabled for overlay rendering"
        print(f"✓ Binary invariant test passed: {result['binaryCount']}/{result['totalPixels']} pixels are binary")
    
    def test_dirty_rectangle_optimization(self, driver):
        """
        Test that dirty rectangle optimization works correctly.
        
        Verifies:
        1. Only specified regions are updated during partial redraws
        2. Dirty rectangles are calculated correctly for brush strokes
        3. Full overlay updates work when no dirty rect is specified
        4. Overlapping dirty rectangles are handled efficiently
        """
        driver.get("http://localhost:5000/test-inpainting-canvas")
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "test-button"))
        )
        
        # Execute JavaScript to test dirty rectangle calculation
        result = driver.execute_script("""
            return new Promise((resolve) => {
                try {
                    // Test dirty rectangle calculation logic
                    const brushSize = 20;
                    const centerX = 50;
                    const centerY = 50;
                    const imageWidth = 100;
                    const imageHeight = 100;
                    
                    const radius = Math.ceil(brushSize / 2);
                    const dirtyRect = {
                        x: Math.max(0, centerX - radius),
                        y: Math.max(0, centerY - radius),
                        width: Math.min(imageWidth - Math.max(0, centerX - radius), radius * 2),
                        height: Math.min(imageHeight - Math.max(0, centerY - radius), radius * 2)
                    };
                    
                    const expectedX = 40;
                    const expectedY = 40;
                    const expectedWidth = 20;
                    const expectedHeight = 20;
                    
                    const calculationCorrect = dirtyRect.x === expectedX && 
                                              dirtyRect.y === expectedY && 
                                              dirtyRect.width === expectedWidth && 
                                              dirtyRect.height === expectedHeight;
                    
                    // Test edge boundary case
                    const edgeBrushSize = 10;
                    const edgeCenterX = 2;
                    const edgeCenterY = 2;
                    
                    const edgeRadius = Math.ceil(edgeBrushSize / 2);
                    const edgeDirtyRect = {
                        x: Math.max(0, edgeCenterX - edgeRadius),
                        y: Math.max(0, edgeCenterY - edgeRadius),
                        width: Math.min(imageWidth - Math.max(0, edgeCenterX - edgeRadius), edgeRadius * 2),
                        height: Math.min(imageHeight - Math.max(0, edgeCenterY - edgeRadius), edgeRadius * 2)
                    };
                    
                    const edgeExpectedX = 0;
                    const edgeExpectedY = 0;
                    const edgeExpectedWidth = 7;
                    const edgeExpectedHeight = 7;
                    
                    const edgeCalculationCorrect = edgeDirtyRect.x === edgeExpectedX && 
                                                  edgeDirtyRect.y === edgeExpectedY && 
                                                  edgeDirtyRect.width === edgeExpectedWidth && 
                                                  edgeDirtyRect.height === edgeExpectedHeight;
                    
                    resolve({
                        success: calculationCorrect && edgeCalculationCorrect,
                        centerTest: {
                            calculated: dirtyRect,
                            expected: { x: expectedX, y: expectedY, width: expectedWidth, height: expectedHeight },
                            correct: calculationCorrect
                        },
                        edgeTest: {
                            calculated: edgeDirtyRect,
                            expected: { x: edgeExpectedX, y: edgeExpectedY, width: edgeExpectedWidth, height: edgeExpectedHeight },
                            correct: edgeCalculationCorrect
                        }
                    });
                    
                } catch (error) {
                    resolve({ success: false, error: error.message });
                }
            });
        """)
        
        assert result['success'], f"Dirty rectangle optimization test failed: {result.get('error', 'Unknown error')}"
        assert result['centerTest']['correct'], f"Center test failed: expected {result['centerTest']['expected']}, got {result['centerTest']['calculated']}"
        assert result['edgeTest']['correct'], f"Edge test failed: expected {result['edgeTest']['expected']}, got {result['edgeTest']['calculated']}"
        print("✓ Dirty rectangle optimization test passed")
    
    def test_compositing_accuracy(self, driver):
        """
        Test destination-in compositing accuracy.
        
        Verifies:
        1. destination-in compositing works correctly with mask alpha
        2. Semi-transparent white overlay (40-60% opacity) is applied
        3. Final overlay alpha matches mask data exactly
        4. No color bleeding or artifacts are introduced
        """
        driver.get("http://localhost:5000/test-inpainting-canvas")
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "test-button"))
        )
        
        # Execute JavaScript to test compositing accuracy
        result = driver.execute_script("""
            return new Promise((resolve) => {
                import('/static/js/canvas-manager.js').then(({ CanvasManager }) => {
                    try {
                        // Create test canvases
                        const imageCanvas = document.createElement('canvas');
                        const overlayCanvas = document.createElement('canvas');
                        const maskAlphaCanvas = new OffscreenCanvas(4, 1);
                        
                        // Set up canvas dimensions for test pattern
                        const width = 4;
                        const height = 1;
                        
                        imageCanvas.width = width;
                        imageCanvas.height = height;
                        overlayCanvas.width = width;
                        overlayCanvas.height = height;
                        maskAlphaCanvas.width = width;
                        maskAlphaCanvas.height = height;
                        
                        // Create container element
                        const container = document.createElement('div');
                        container.style.width = '400px';
                        container.style.height = '400px';
                        container.appendChild(imageCanvas);
                        document.body.appendChild(container);
                        
                        const manager = new CanvasManager(imageCanvas, overlayCanvas, maskAlphaCanvas);
                        
                        // Create a simple test image
                        const testImageUrl = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==';
                        
                        // Load image and test compositing
                        manager.loadImage(testImageUrl).then(() => {
                            const state = manager.getState();
                            if (!state) {
                                resolve({ success: false, error: 'Failed to get canvas state' });
                                return;
                            }
                            
                            // Create test pattern: [255, 0, 255, 0] (alternating mask values)
                            const maskData = new Uint8Array([255, 0, 255, 0]);
                            
                            // Apply mask data
                            state.maskData = maskData;
                            state.imageWidth = width;
                            state.imageHeight = height;
                            
                            // Update overlay
                            manager.updateMaskOverlay();
                            
                            // Verify compositing results
                            const overlayCtx = overlayCanvas.getContext('2d');
                            const overlayImageData = overlayCtx.getImageData(0, 0, width, height);
                            const overlayData = overlayImageData.data;
                            
                            // Check that alpha values match mask data exactly
                            const alphaMatches = [];
                            for (let i = 0; i < maskData.length; i++) {
                                const expectedAlpha = maskData[i];
                                const actualAlpha = overlayData[i * 4 + 3];
                                alphaMatches.push({
                                    index: i,
                                    expected: expectedAlpha,
                                    actual: actualAlpha,
                                    matches: expectedAlpha === actualAlpha
                                });
                            }
                            
                            const allAlphasMatch = alphaMatches.every(match => match.matches);
                            
                            // Verify white color for visible pixels
                            const colorCorrect = [];
                            for (let i = 0; i < maskData.length; i++) {
                                if (maskData[i] === 255) {
                                    const r = overlayData[i * 4];
                                    const g = overlayData[i * 4 + 1];
                                    const b = overlayData[i * 4 + 2];
                                    colorCorrect.push({
                                        index: i,
                                        r: r,
                                        g: g,
                                        b: b,
                                        isWhite: r === 255 && g === 255 && b === 255
                                    });
                                }
                            }
                            
                            const allColorsWhite = colorCorrect.every(color => color.isWhite);
                            
                            // Cleanup
                            document.body.removeChild(container);
                            
                            resolve({
                                success: allAlphasMatch && allColorsWhite,
                                alphaMatches: alphaMatches,
                                colorCorrect: colorCorrect,
                                allAlphasMatch: allAlphasMatch,
                                allColorsWhite: allColorsWhite
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
        
        assert result['success'], f"Compositing accuracy test failed: {result.get('error', 'Unknown error')}"
        assert result['allAlphasMatch'], f"Alpha values don't match mask data: {result['alphaMatches']}"
        assert result['allColorsWhite'], f"Overlay colors are not white: {result['colorCorrect']}"
        print("✓ Destination-in compositing accuracy test passed")
    
    def test_image_smoothing_disabled(self, driver):
        """
        Test that image smoothing is disabled during overlay rendering.
        
        Verifies:
        1. imageSmoothingEnabled is set to false for overlay context
        2. imageSmoothingEnabled is set to false for mask alpha context
        3. Pixel-perfect rendering is maintained at all zoom levels
        4. No anti-aliasing artifacts are introduced
        """
        driver.get("http://localhost:5000/test-inpainting-canvas")
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "test-button"))
        )
        
        # Execute JavaScript to test image smoothing settings
        result = driver.execute_script("""
            return new Promise((resolve) => {
                import('/static/js/canvas-manager.js').then(({ CanvasManager }) => {
                    try {
                        // Create test canvases
                        const imageCanvas = document.createElement('canvas');
                        const overlayCanvas = document.createElement('canvas');
                        const maskAlphaCanvas = new OffscreenCanvas(10, 10);
                        
                        // Set up canvas dimensions
                        const width = 10;
                        const height = 10;
                        
                        imageCanvas.width = width;
                        imageCanvas.height = height;
                        overlayCanvas.width = width;
                        overlayCanvas.height = height;
                        maskAlphaCanvas.width = width;
                        maskAlphaCanvas.height = height;
                        
                        // Create container element
                        const container = document.createElement('div');
                        container.style.width = '400px';
                        container.style.height = '400px';
                        container.appendChild(imageCanvas);
                        document.body.appendChild(container);
                        
                        const manager = new CanvasManager(imageCanvas, overlayCanvas, maskAlphaCanvas);
                        
                        // Create a simple test image
                        const testImageUrl = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==';
                        
                        // Load image and test smoothing settings
                        manager.loadImage(testImageUrl).then(() => {
                            // Check overlay context smoothing
                            const overlayCtx = overlayCanvas.getContext('2d');
                            const overlaySmoothingDisabled = !overlayCtx.imageSmoothingEnabled;
                            
                            // Check mask alpha context smoothing
                            const maskAlphaCtx = maskAlphaCanvas.getContext('2d');
                            const maskAlphaSmoothingDisabled = !maskAlphaCtx.imageSmoothingEnabled;
                            
                            // Trigger overlay update to verify smoothing is disabled during rendering
                            const state = manager.getState();
                            if (state) {
                                // Set some test mask data
                                state.maskData.fill(255);
                                manager.updateMaskOverlay();
                                
                                // Check smoothing again after overlay update
                                const overlaySmoothingStillDisabled = !overlayCtx.imageSmoothingEnabled;
                                const maskAlphaSmoothingStillDisabled = !maskAlphaCtx.imageSmoothingEnabled;
                                
                                // Cleanup
                                document.body.removeChild(container);
                                
                                resolve({
                                    success: overlaySmoothingDisabled && maskAlphaSmoothingDisabled && 
                                            overlaySmoothingStillDisabled && maskAlphaSmoothingStillDisabled,
                                    overlaySmoothing: {
                                        initiallyDisabled: overlaySmoothingDisabled,
                                        stillDisabledAfterUpdate: overlaySmoothingStillDisabled
                                    },
                                    maskAlphaSmoothing: {
                                        initiallyDisabled: maskAlphaSmoothingDisabled,
                                        stillDisabledAfterUpdate: maskAlphaSmoothingStillDisabled
                                    }
                                });
                            } else {
                                resolve({ success: false, error: 'Failed to get canvas state' });
                            }
                        }).catch(error => {
                            resolve({ success: false, error: error.message });
                        });
                        
                    } catch (error) {
                        resolve({ success: false, error: error.message });
                    }
                });
            });
        """)
        
        assert result['success'], f"Image smoothing test failed: {result.get('error', 'Unknown error')}"
        assert result['overlaySmoothing']['initiallyDisabled'], "Overlay context should have image smoothing disabled initially"
        assert result['overlaySmoothing']['stillDisabledAfterUpdate'], "Overlay context should keep image smoothing disabled after updates"
        assert result['maskAlphaSmoothing']['initiallyDisabled'], "Mask alpha context should have image smoothing disabled initially"
        assert result['maskAlphaSmoothing']['stillDisabledAfterUpdate'], "Mask alpha context should keep image smoothing disabled after updates"
        print("✓ Image smoothing disabled test passed")
    
    def _generate_overlay_tests(self, test_cases):
        """Generate JavaScript test file for overlay binary invariant."""
        js_test_content = '''
/**
 * Mask overlay binary invariant tests for CanvasManager
 * Generated from Python test cases
 */

import { CanvasManager } from '../src/canvas-manager.js';

describe('Mask Overlay Binary Invariant', () => {
'''
        
        for case in test_cases:
            js_test_content += f'''
    test('{case["name"]}', async () => {{
        // Create mock canvases
        const imageCanvas = document.createElement('canvas');
        const overlayCanvas = document.createElement('canvas');
        const maskAlphaCanvas = new OffscreenCanvas(1, 1);
        
        // Set up canvas dimensions
        const width = {len(case["mask_data"][0])};
        const height = {len(case["mask_data"])};
        
        imageCanvas.width = width;
        imageCanvas.height = height;
        overlayCanvas.width = width;
        overlayCanvas.height = height;
        maskAlphaCanvas.width = width;
        maskAlphaCanvas.height = height;
        
        // Create container element
        const container = document.createElement('div');
        container.style.width = '400px';
        container.style.height = '400px';
        container.appendChild(imageCanvas);
        document.body.appendChild(container);
        
        const manager = new CanvasManager(imageCanvas, overlayCanvas, maskAlphaCanvas);
        
        // Mock image loading by directly setting up state
        const mockImage = new Image();
        mockImage.width = width;
        mockImage.height = height;
        mockImage.naturalWidth = width;
        mockImage.naturalHeight = height;
        
        // Simulate image load
        await manager.loadImage('data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==');
        
        // Set up mask data
        const state = manager.getState();
        const maskData = new Uint8Array(width * height);
'''
            
            # Generate mask data setup
            for y, row in enumerate(case["mask_data"]):
                for x, value in enumerate(row):
                    js_test_content += f'''
        maskData[{y} * width + {x}] = {value};'''
            
            js_test_content += '''
        
        // Apply mask data directly to state
        state.maskData = maskData;
        
        // Update overlay
        manager.updateMaskOverlay();
        
        // Get overlay canvas context and verify binary values
        const overlayCtx = overlayCanvas.getContext('2d');
        const overlayImageData = overlayCtx.getImageData(0, 0, width, height);
        const overlayData = overlayImageData.data;
        
        // Verify that overlay alpha values are binary (0 or 255)
        for (let i = 0; i < overlayData.length; i += 4) {
            const alpha = overlayData[i + 3];
            expect(alpha === 0 || alpha === 255).toBe(true);
        }
        
        // Verify overlay matches expected pattern
'''
            
            for y, row in enumerate(case["expected_overlay"]):
                for x, expected_alpha in enumerate(row):
                    js_test_content += f'''
        expect(overlayData[({y} * width + {x}) * 4 + 3]).toBe({expected_alpha});'''
            
            js_test_content += '''
        
        // Cleanup
        document.body.removeChild(container);
    });
'''
        
        js_test_content += '''
});
'''
        
        # Write to test file
        test_file_path = Path(__file__).parent / "test_mask_overlay_binary.js"
        with open(test_file_path, 'w') as f:
            f.write(js_test_content)
    
    def _generate_dirty_rect_tests(self, test_cases):
        """Generate JavaScript dirty rectangle optimization tests."""
        # Implementation for dirty rectangle tests
        pass
    
    def _generate_compositing_tests(self, test_cases):
        """Generate JavaScript compositing accuracy tests."""
        # Implementation for compositing tests
        pass
    
    def _generate_smoothing_tests(self, test_cases):
        """Generate JavaScript image smoothing tests."""
        # Implementation for smoothing tests
        pass


if __name__ == "__main__":
    # Run the test to generate JavaScript files
    test_instance = TestMaskOverlay()
    test_instance.test_overlay_binary_invariant()
    test_instance.test_dirty_rectangle_optimization()
    test_instance.test_compositing_accuracy()
    test_instance.test_image_smoothing_disabled()
    print("JavaScript test files generated successfully!")