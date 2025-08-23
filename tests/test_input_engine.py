"""
Test suite for InputEngine functionality
Tests the unified pointer input handling system
"""

import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import time


class TestInputEngine:
    """Test InputEngine pointer input handling"""

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

    def test_input_engine_initialization(self, driver):
        """Test that InputEngine can be initialized properly"""
        driver.get('http://localhost:5000/test-inpainting-canvas')
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "test-button"))
        )
        
        # Execute JavaScript to test InputEngine initialization
        result = driver.execute_script("""
            return new Promise((resolve) => {
                import('/static/js/input-engine.js').then(({ InputEngine }) => {
                    // Create a test canvas
                    const canvas = document.createElement('canvas');
                    canvas.width = 100;
                    canvas.height = 100;
                    document.body.appendChild(canvas);
                    
                    // Create InputEngine instance
                    const inputEngine = new InputEngine(canvas);
                    
                    // Test basic properties
                    const settings = inputEngine.getSettings();
                    const isEnabled = inputEngine.getActivePointerCount() === 0;
                    
                    // Cleanup
                    inputEngine.cleanup();
                    document.body.removeChild(canvas);
                    
                    resolve({
                        success: true,
                        settings: settings,
                        initialPointerCount: isEnabled
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
        assert 'enableDrawing' in result['settings']
        assert 'preventScrolling' in result['settings']
        assert 'capturePointer' in result['settings']

    def test_input_engine_event_handling(self, driver):
        """Test that InputEngine properly handles pointer events"""
        driver.get('http://localhost:5000/test-inpainting-canvas')
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "test-button"))
        )
        
        # Execute JavaScript to test event handling
        result = driver.execute_script("""
            return new Promise((resolve) => {
                import('/static/js/input-engine.js').then(({ InputEngine }) => {
                    // Create a test canvas
                    const canvas = document.createElement('canvas');
                    canvas.width = 200;
                    canvas.height = 200;
                    canvas.style.position = 'absolute';
                    canvas.style.top = '0px';
                    canvas.style.left = '0px';
                    document.body.appendChild(canvas);
                    
                    let eventCount = 0;
                    let lastEventType = '';
                    
                    // Create InputEngine instance with event handler
                    const inputEngine = new InputEngine(canvas);
                    inputEngine.setEventHandler((event) => {
                        eventCount++;
                        lastEventType = event.type;
                    });
                    
                    inputEngine.enable();
                    
                    // Simulate pointer events
                    const pointerDownEvent = new PointerEvent('pointerdown', {
                        pointerId: 1,
                        pointerType: 'mouse',
                        isPrimary: true,
                        clientX: 50,
                        clientY: 50,
                        bubbles: true
                    });
                    
                    const pointerMoveEvent = new PointerEvent('pointermove', {
                        pointerId: 1,
                        pointerType: 'mouse',
                        isPrimary: true,
                        clientX: 60,
                        clientY: 60,
                        bubbles: true
                    });
                    
                    const pointerUpEvent = new PointerEvent('pointerup', {
                        pointerId: 1,
                        pointerType: 'mouse',
                        isPrimary: true,
                        clientX: 60,
                        clientY: 60,
                        bubbles: true
                    });
                    
                    // Dispatch events
                    canvas.dispatchEvent(pointerDownEvent);
                    canvas.dispatchEvent(pointerMoveEvent);
                    canvas.dispatchEvent(pointerUpEvent);
                    
                    // Small delay to ensure events are processed
                    setTimeout(() => {
                        // Cleanup
                        inputEngine.cleanup();
                        document.body.removeChild(canvas);
                        
                        resolve({
                            success: true,
                            eventCount: eventCount,
                            lastEventType: lastEventType
                        });
                    }, 100);
                    
                }).catch(error => {
                    resolve({
                        success: false,
                        error: error.message
                    });
                });
            });
        """)
        
        assert result['success'] == True
        assert result['eventCount'] >= 1  # At least one event should be handled
        assert result['lastEventType'] in ['start', 'move', 'end']

    def test_input_engine_cursor_preview(self, driver):
        """Test that InputEngine creates and manages cursor preview"""
        driver.get('http://localhost:5000/test-inpainting-canvas')
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "test-button"))
        )
        
        # Execute JavaScript to test cursor preview
        result = driver.execute_script("""
            return new Promise((resolve) => {
                import('/static/js/input-engine.js').then(({ InputEngine }) => {
                    // Create a test canvas
                    const canvas = document.createElement('canvas');
                    canvas.width = 100;
                    canvas.height = 100;
                    document.body.appendChild(canvas);
                    
                    // Create InputEngine instance
                    const inputEngine = new InputEngine(canvas);
                    inputEngine.enable();
                    
                    // Test cursor size update
                    inputEngine.updateCursorSize(30);
                    
                    // Test cursor mode update
                    inputEngine.updateCursorMode('paint');
                    inputEngine.updateCursorMode('erase');
                    
                    // Check if cursor preview element exists
                    const cursorElements = document.querySelectorAll('.brush-cursor-preview');
                    const hasCursorPreview = cursorElements.length > 0;
                    
                    // Cleanup
                    inputEngine.cleanup();
                    document.body.removeChild(canvas);
                    
                    resolve({
                        success: true,
                        hasCursorPreview: hasCursorPreview
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
        assert result['hasCursorPreview'] == True

    def test_input_engine_touch_action_prevention(self, driver):
        """Test that InputEngine properly sets touch-action: none"""
        driver.get('http://localhost:5000/test-inpainting-canvas')
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "test-button"))
        )
        
        # Execute JavaScript to test touch-action prevention
        result = driver.execute_script("""
            return new Promise((resolve) => {
                import('/static/js/input-engine.js').then(({ InputEngine }) => {
                    // Create a test canvas
                    const canvas = document.createElement('canvas');
                    canvas.width = 100;
                    canvas.height = 100;
                    document.body.appendChild(canvas);
                    
                    // Create InputEngine instance with preventScrolling enabled
                    const inputEngine = new InputEngine(canvas, {
                        preventScrolling: true
                    });
                    
                    // Check touch-action style
                    const touchAction = canvas.style.touchAction;
                    
                    // Test settings update
                    inputEngine.updateSettings({ preventScrolling: false });
                    const touchActionAfterUpdate = canvas.style.touchAction;
                    
                    // Cleanup
                    inputEngine.cleanup();
                    document.body.removeChild(canvas);
                    
                    resolve({
                        success: true,
                        initialTouchAction: touchAction,
                        touchActionAfterUpdate: touchActionAfterUpdate
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
        assert result['initialTouchAction'] == 'none'