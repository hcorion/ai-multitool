"""
Test suite for Paint and Erase Tools functionality
Tests the paint/erase tools with brush size control
"""

import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import time


class TestPaintEraseTools:
    """Test Paint and Erase Tools functionality"""

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

    def test_paint_tool_functionality(self, driver):
        """Test that paint tool stamps white (255) values to mask"""
        driver.get('http://localhost:5000/test-inpainting-canvas')
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "test-button"))
        )
        
        # Execute JavaScript to test paint tool
        result = driver.execute_script("""
            return new Promise((resolve) => {
                import('/static/js/inpainting/brush-engine.js').then(({ BrushEngine }) => {
                    // Create test mask
                    const width = 50;
                    const height = 50;
                    const maskData = new Uint8Array(width * height);
                    
                    // Create brush engine in paint mode
                    const engine = new BrushEngine({ size: 10, mode: 'paint' });
                    
                    // Apply paint stamp
                    const hasChanges = engine.applyStamp(maskData, width, height, 25, 25, 10, 'paint');
                    
                    // Count painted pixels (should be 255)
                    let paintedPixels = 0;
                    let correctValues = 0;
                    for (let i = 0; i < maskData.length; i++) {
                        if (maskData[i] > 0) {
                            paintedPixels++;
                            if (maskData[i] === 255) {
                                correctValues++;
                            }
                        }
                    }
                    
                    // Validate binary invariant
                    const isValid = BrushEngine.validateBinaryMask(maskData);
                    
                    resolve({
                        success: true,
                        hasChanges: hasChanges,
                        paintedPixels: paintedPixels,
                        correctValues: correctValues,
                        binaryValid: isValid
                    });
                    
                }).catch(error => {
                    resolve({
                        success: false,
                        error: error.message
                    });
                });
            });
        """)
        
        assert result['success'] == True
        assert result['hasChanges'] == True
        assert result['paintedPixels'] > 0
        assert result['correctValues'] == result['paintedPixels']  # All painted pixels should be 255
        assert result['binaryValid'] == True

    def test_erase_tool_functionality(self, driver):
        """Test that erase tool stamps black (0) values to mask"""
        driver.get('http://localhost:5000/test-inpainting-canvas')
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "test-button"))
        )
        
        # Execute JavaScript to test erase tool
        result = driver.execute_script("""
            return new Promise((resolve) => {
                import('/static/js/inpainting/brush-engine.js').then(({ BrushEngine }) => {
                    // Create test mask with some painted areas
                    const width = 50;
                    const height = 50;
                    const maskData = new Uint8Array(width * height);
                    
                    // Fill with white first
                    for (let i = 0; i < maskData.length; i++) {
                        maskData[i] = 255;
                    }
                    
                    // Create brush engine in erase mode
                    const engine = new BrushEngine({ size: 10, mode: 'erase' });
                    
                    // Apply erase stamp
                    const hasChanges = engine.applyStamp(maskData, width, height, 25, 25, 10, 'erase');
                    
                    // Count erased pixels (should be 0)
                    let erasedPixels = 0;
                    let remainingPixels = 0;
                    for (let i = 0; i < maskData.length; i++) {
                        if (maskData[i] === 0) {
                            erasedPixels++;
                        } else if (maskData[i] === 255) {
                            remainingPixels++;
                        }
                    }
                    
                    // Validate binary invariant
                    const isValid = BrushEngine.validateBinaryMask(maskData);
                    
                    resolve({
                        success: true,
                        hasChanges: hasChanges,
                        erasedPixels: erasedPixels,
                        remainingPixels: remainingPixels,
                        totalPixels: maskData.length,
                        binaryValid: isValid
                    });
                    
                }).catch(error => {
                    resolve({
                        success: false,
                        error: error.message
                    });
                });
            });
        """)
        
        assert result['success'] == True
        assert result['hasChanges'] == True
        assert result['erasedPixels'] > 0
        assert result['erasedPixels'] + result['remainingPixels'] == result['totalPixels']
        assert result['binaryValid'] == True

    def test_brush_size_range(self, driver):
        """Test brush size slider with 1-200 pixel range"""
        driver.get('http://localhost:5000/test-inpainting-canvas')
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "test-button"))
        )
        
        # Execute JavaScript to test brush size range
        result = driver.execute_script("""
            return new Promise((resolve) => {
                import('/static/js/inpainting/brush-engine.js').then(({ BrushEngine }) => {
                    const testSizes = [1, 25, 50, 100, 150, 200];
                    const results = [];
                    
                    for (const size of testSizes) {
                        // Create test mask
                        const width = 300;
                        const height = 300;
                        const maskData = new Uint8Array(width * height);
                        
                        // Create brush engine with test size
                        const engine = new BrushEngine({ size: size, mode: 'paint' });
                        
                        // Apply stamp
                        const hasChanges = engine.applyStamp(maskData, width, height, 150, 150, size, 'paint');
                        
                        // Count painted pixels
                        let paintedPixels = 0;
                        for (let i = 0; i < maskData.length; i++) {
                            if (maskData[i] === 255) paintedPixels++;
                        }
                        
                        results.push({
                            size: size,
                            hasChanges: hasChanges,
                            paintedPixels: paintedPixels
                        });
                    }
                    
                    resolve({
                        success: true,
                        results: results
                    });
                    
                }).catch(error => {
                    resolve({
                        success: false,
                        error: error.message
                    });
                });
            });
        """)
        
        assert result['success'] == True
        assert len(result['results']) == 6
        
        # Verify all sizes work and larger sizes paint more pixels
        for i, test_result in enumerate(result['results']):
            assert test_result['hasChanges'] == True
            assert test_result['paintedPixels'] > 0
            
            # Larger brushes should generally paint more pixels (with some tolerance for edge cases)
            if i > 0:
                prev_pixels = result['results'][i-1]['paintedPixels']
                curr_pixels = test_result['paintedPixels']
                # Allow some tolerance for very small brushes
                if test_result['size'] > 10:
                    assert curr_pixels >= prev_pixels * 0.8  # Allow some variance

    def test_brush_size_drag_resize(self, driver):
        """Test press-and-hold drag resize functionality"""
        driver.get('http://localhost:5000/test-inpainting-canvas')
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "test-button"))
        )
        
        # Click the main test button to open the canvas
        test_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Open Mask Canvas')]")
        test_button.click()
        
        # Wait for canvas to load
        time.sleep(2)
        
        # Check if drag handle exists
        drag_handle_exists = driver.execute_script("""
            const dragHandle = document.querySelector('.brush-size-drag-handle');
            return dragHandle !== null;
        """)
        
        assert drag_handle_exists == True

    def test_cursor_preview_updates(self, driver):
        """Test that cursor preview reflects current brush size"""
        driver.get('http://localhost:5000/test-inpainting-canvas')
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "test-button"))
        )
        
        # Execute JavaScript to test cursor preview updates
        result = driver.execute_script("""
            return new Promise((resolve) => {
                import('/static/js/input-engine.js').then(({ InputEngine }) => {
                    // Create test canvas
                    const canvas = document.createElement('canvas');
                    canvas.width = 200;
                    canvas.height = 200;
                    document.body.appendChild(canvas);
                    
                    // Create InputEngine
                    const inputEngine = new InputEngine(canvas);
                    inputEngine.enable();
                    
                    // Test cursor size updates
                    const testSizes = [10, 50, 100];
                    const results = [];
                    
                    for (const size of testSizes) {
                        inputEngine.updateCursorSize(size);
                        
                        // Check if cursor preview element exists and has correct size
                        const cursorElement = document.querySelector('.brush-cursor-preview');
                        if (cursorElement) {
                            const width = parseInt(cursorElement.style.width);
                            const height = parseInt(cursorElement.style.height);
                            results.push({
                                size: size,
                                actualWidth: width,
                                actualHeight: height,
                                correct: width === size && height === size
                            });
                        }
                    }
                    
                    // Test cursor mode updates
                    inputEngine.updateCursorMode('paint');
                    const paintMode = document.querySelector('.brush-cursor-preview')?.style.borderColor;
                    
                    inputEngine.updateCursorMode('erase');
                    const eraseMode = document.querySelector('.brush-cursor-preview')?.style.borderColor;
                    
                    // Cleanup
                    inputEngine.cleanup();
                    document.body.removeChild(canvas);
                    
                    resolve({
                        success: true,
                        sizeResults: results,
                        paintModeColor: paintMode,
                        eraseModeColor: eraseMode
                    });
                    
                }).catch(error => {
                    resolve({
                        success: false,
                        error: error.message
                    });
                });
            });
        """)
        
        assert result['success'] == True
        assert len(result['sizeResults']) == 3
        
        # Verify cursor sizes are correct
        for size_result in result['sizeResults']:
            assert size_result['correct'] == True
        
        # Verify cursor modes have different colors
        assert result['paintModeColor'] != result['eraseModeColor']

    def test_keyboard_shortcuts(self, driver):
        """Test keyboard shortcuts for tool switching and brush size adjustment"""
        driver.get('http://localhost:5000/test-inpainting-canvas')
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "test-button"))
        )
        
        # Click the main test button to open the canvas
        test_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Open Mask Canvas')]")
        test_button.click()
        
        # Wait for canvas to load
        time.sleep(2)
        
        # Test keyboard shortcuts
        body = driver.find_element(By.TAG_NAME, "body")
        
        # Test paint tool shortcut (P)
        body.send_keys("p")
        paint_active = driver.execute_script("""
            return document.querySelector('.paint-btn').classList.contains('active');
        """)
        assert paint_active == True
        
        # Test erase tool shortcut (E)
        body.send_keys("e")
        erase_active = driver.execute_script("""
            return document.querySelector('.erase-btn').classList.contains('active');
        """)
        assert erase_active == True
        
        # Test brush size shortcuts
        initial_size = driver.execute_script("""
            return parseInt(document.querySelector('.brush-size-slider').value);
        """)
        
        # Test increase brush size (])
        body.send_keys("]")
        increased_size = driver.execute_script("""
            return parseInt(document.querySelector('.brush-size-slider').value);
        """)
        assert increased_size > initial_size
        
        # Test decrease brush size ([)
        body.send_keys("[")
        decreased_size = driver.execute_script("""
            return parseInt(document.querySelector('.brush-size-slider').value);
        """)
        assert decreased_size < increased_size