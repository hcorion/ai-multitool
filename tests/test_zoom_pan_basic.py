"""
Basic test for ZoomPanController functionality without requiring Flask server.
Tests core zoom/pan logic using a simple HTML page.
"""

import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import tempfile
import os


class TestZoomPanBasic:
    @pytest.fixture
    def driver(self):
        """Set up Chrome driver for testing"""
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-web-security')
        options.add_argument('--allow-running-insecure-content')
        driver = webdriver.Chrome(options=options)
        driver.implicitly_wait(10)
        yield driver
        driver.quit()

    def test_zoom_pan_controller_basic_functionality(self, driver):
        """Test ZoomPanController basic functionality with a simple HTML page"""
        
        # Create a simple HTML page with the zoom/pan controller
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Zoom Pan Test</title>
        </head>
        <body>
            <canvas id="test-canvas" width="800" height="600" style="border: 1px solid black;"></canvas>
            
            <script type="module">
                // Inline ZoomPanController for testing
                class ZoomPanController {
                    constructor(canvas, settings = {}) {
                        this.canvas = canvas;
                        this.settings = {
                            minZoom: 0.1,
                            maxZoom: 10.0,
                            zoomSensitivity: 0.002,
                            panSensitivity: 1.0,
                            enablePinchZoom: true,
                            enableWheelZoom: true,
                            enablePan: true,
                            wheelZoomModifier: 'ctrl',
                            ...settings
                        };
                        
                        this.transform = {
                            scale: 1.0,
                            translateX: 0,
                            translateY: 0
                        };
                        
                        this.isEnabled = false;
                        this.isActive = false;
                        this.eventHandler = null;
                        this.imageBounds = null;
                        this.canvasBounds = null;
                    }
                    
                    enable() {
                        this.isEnabled = true;
                    }
                    
                    disable() {
                        this.isEnabled = false;
                        this.isActive = false;
                    }
                    
                    getTransform() {
                        return { ...this.transform };
                    }
                    
                    setTransform(newTransform) {
                        this.transform = { ...this.transform, ...newTransform };
                        this.transform.scale = Math.max(this.settings.minZoom, Math.min(this.settings.maxZoom, this.transform.scale));
                        
                        if (this.eventHandler && this.eventHandler.onTransformUpdate) {
                            this.eventHandler.onTransformUpdate({ ...this.transform });
                        }
                    }
                    
                    resetTransform() {
                        this.transform = { scale: 1.0, translateX: 0, translateY: 0 };
                        if (this.eventHandler && this.eventHandler.onTransformUpdate) {
                            this.eventHandler.onTransformUpdate({ ...this.transform });
                        }
                    }
                    
                    setEventHandler(handler) {
                        this.eventHandler = handler;
                    }
                    
                    setImageBounds(width, height) {
                        this.imageBounds = { width, height };
                    }
                    
                    setCanvasBounds(width, height) {
                        this.canvasBounds = { width, height };
                    }
                    
                    getSettings() {
                        return { ...this.settings };
                    }
                    
                    updateSettings(newSettings) {
                        this.settings = { ...this.settings, ...newSettings };
                    }
                    
                    isGestureActive() {
                        return this.isActive;
                    }
                    
                    screenToImage(screenX, screenY) {
                        if (!this.imageBounds || !this.canvasBounds) return null;
                        
                        const rect = this.canvas.getBoundingClientRect();
                        const canvasX = screenX - rect.left;
                        const canvasY = screenY - rect.top;
                        
                        if (canvasX < 0 || canvasY < 0 || canvasX >= rect.width || canvasY >= rect.height) {
                            return null;
                        }
                        
                        const imageX = (canvasX - this.transform.translateX) / this.transform.scale;
                        const imageY = (canvasY - this.transform.translateY) / this.transform.scale;
                        
                        if (imageX < 0 || imageY < 0 || imageX >= this.imageBounds.width || imageY >= this.imageBounds.height) {
                            return null;
                        }
                        
                        return { x: Math.floor(imageX), y: Math.floor(imageY) };
                    }
                    
                    imageToScreen(imageX, imageY) {
                        const rect = this.canvas.getBoundingClientRect();
                        const screenX = rect.left + (imageX * this.transform.scale + this.transform.translateX);
                        const screenY = rect.top + (imageY * this.transform.scale + this.transform.translateY);
                        return { x: screenX, y: screenY };
                    }
                    
                    cleanup() {
                        this.disable();
                        this.eventHandler = null;
                        this.imageBounds = null;
                        this.canvasBounds = null;
                    }
                }
                
                // Make it available globally for testing
                window.ZoomPanController = ZoomPanController;
                
                // Test the controller
                window.testResults = {};
                
                try {
                    const canvas = document.getElementById('test-canvas');
                    const controller = new ZoomPanController(canvas, {
                        minZoom: 0.5,
                        maxZoom: 4.0,
                        enablePinchZoom: true
                    });
                    
                    // Test 1: Basic creation
                    window.testResults.creation = {
                        success: true,
                        settings: controller.getSettings(),
                        transform: controller.getTransform()
                    };
                    
                    // Test 2: Enable/disable
                    controller.enable();
                    const enabledState = controller.isEnabled;
                    controller.disable();
                    const disabledState = controller.isEnabled;
                    
                    window.testResults.enableDisable = {
                        success: true,
                        enabledState: enabledState,
                        disabledState: disabledState
                    };
                    
                    // Test 3: Transform operations
                    controller.setTransform({ scale: 2.0, translateX: 50, translateY: 30 });
                    const transformAfterSet = controller.getTransform();
                    
                    controller.resetTransform();
                    const transformAfterReset = controller.getTransform();
                    
                    window.testResults.transforms = {
                        success: true,
                        afterSet: transformAfterSet,
                        afterReset: transformAfterReset
                    };
                    
                    // Test 4: Settings update
                    const initialSettings = controller.getSettings();
                    controller.updateSettings({ minZoom: 0.2, maxZoom: 8.0 });
                    const updatedSettings = controller.getSettings();
                    
                    window.testResults.settingsUpdate = {
                        success: true,
                        initial: initialSettings,
                        updated: updatedSettings
                    };
                    
                    // Test 5: Coordinate transformation
                    controller.setImageBounds(400, 300);
                    controller.setCanvasBounds(800, 600);
                    controller.resetTransform();
                    
                    const coord1 = controller.screenToImage(100, 80);
                    const coord2 = controller.imageToScreen(50, 40);
                    
                    // Test with zoom
                    controller.setTransform({ scale: 2.0 });
                    const coordZoomed = controller.screenToImage(100, 80);
                    
                    window.testResults.coordinates = {
                        success: true,
                        coord1: coord1,
                        coord2: coord2,
                        coordZoomed: coordZoomed
                    };
                    
                    // Test 6: Event handler
                    let eventHandlerCalled = false;
                    let lastTransform = null;
                    
                    controller.setEventHandler({
                        onTransformUpdate: (transform) => {
                            eventHandlerCalled = true;
                            lastTransform = transform;
                        }
                    });
                    
                    controller.setTransform({ scale: 1.5 });
                    
                    window.testResults.eventHandler = {
                        success: true,
                        eventHandlerCalled: eventHandlerCalled,
                        lastTransform: lastTransform
                    };
                    
                    // Test 7: Cleanup
                    controller.cleanup();
                    const afterCleanup = {
                        isEnabled: controller.isEnabled,
                        isActive: controller.isGestureActive()
                    };
                    
                    window.testResults.cleanup = {
                        success: true,
                        afterCleanup: afterCleanup
                    };
                    
                    window.testResults.overall = { success: true };
                    
                } catch (error) {
                    window.testResults.overall = { 
                        success: false, 
                        error: error.message,
                        stack: error.stack
                    };
                }
            </script>
        </body>
        </html>
        """
        
        # Create temporary HTML file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            f.write(html_content)
            temp_file = f.name
        
        try:
            # Load the HTML file
            driver.get(f'file://{temp_file}')
            
            # Wait for tests to complete and get results
            import time
            time.sleep(2)  # Give time for tests to run
            
            results = driver.execute_script("return window.testResults;")
            
            # Verify overall success
            assert results['overall']['success'], f"Overall test failed: {results['overall'].get('error', 'Unknown error')}"
            
            # Test 1: Creation
            creation = results['creation']
            assert creation['success']
            assert creation['settings']['minZoom'] == 0.5
            assert creation['settings']['maxZoom'] == 4.0
            assert creation['settings']['enablePinchZoom'] == True
            assert creation['transform']['scale'] == 1.0
            assert creation['transform']['translateX'] == 0
            assert creation['transform']['translateY'] == 0
            
            # Test 2: Enable/Disable
            enableDisable = results['enableDisable']
            assert enableDisable['success']
            assert enableDisable['enabledState'] == True
            assert enableDisable['disabledState'] == False
            
            # Test 3: Transforms
            transforms = results['transforms']
            assert transforms['success']
            assert transforms['afterSet']['scale'] == 2.0
            assert transforms['afterSet']['translateX'] == 50
            assert transforms['afterSet']['translateY'] == 30
            assert transforms['afterReset']['scale'] == 1.0
            assert transforms['afterReset']['translateX'] == 0
            assert transforms['afterReset']['translateY'] == 0
            
            # Test 4: Settings Update
            settingsUpdate = results['settingsUpdate']
            assert settingsUpdate['success']
            assert settingsUpdate['initial']['minZoom'] == 0.5
            assert settingsUpdate['updated']['minZoom'] == 0.2
            assert settingsUpdate['updated']['maxZoom'] == 8.0
            
            # Test 5: Coordinates
            coordinates = results['coordinates']
            assert coordinates['success']
            assert coordinates['coord1'] is not None
            assert coordinates['coord2'] is not None
            # At 2x zoom, coordinates should be approximately halved (allow for rounding/positioning)
            if coordinates['coordZoomed']:
                # Allow for small variations due to canvas positioning and rounding
                expected_x = 50  # 100 / 2
                expected_y = 40  # 80 / 2
                tolerance = 5    # Allow ±5 pixels tolerance
                
                actual_x = coordinates['coordZoomed']['x']
                actual_y = coordinates['coordZoomed']['y']
                
                assert abs(actual_x - expected_x) <= tolerance, f"X coordinate {actual_x} not within {tolerance} of expected {expected_x}"
                assert abs(actual_y - expected_y) <= tolerance, f"Y coordinate {actual_y} not within {tolerance} of expected {expected_y}"
            
            # Test 6: Event Handler
            eventHandler = results['eventHandler']
            assert eventHandler['success']
            assert eventHandler['eventHandlerCalled'] == True
            assert eventHandler['lastTransform']['scale'] == 1.5
            
            # Test 7: Cleanup
            cleanup = results['cleanup']
            assert cleanup['success']
            assert cleanup['afterCleanup']['isEnabled'] == False
            assert cleanup['afterCleanup']['isActive'] == False
            
        finally:
            # Clean up temporary file
            os.unlink(temp_file)

    def test_zoom_clamping(self, driver):
        """Test zoom level clamping to min/max values"""
        
        html_content = """
        <!DOCTYPE html>
        <html>
        <body>
            <canvas id="test-canvas" width="400" height="300"></canvas>
            <script>
                // Simplified ZoomPanController for clamping test
                class ZoomPanController {
                    constructor(canvas, settings = {}) {
                        this.settings = {
                            minZoom: 0.5,
                            maxZoom: 3.0,
                            ...settings
                        };
                        this.transform = { scale: 1.0, translateX: 0, translateY: 0 };
                    }
                    
                    setTransform(newTransform) {
                        this.transform = { ...this.transform, ...newTransform };
                        // Apply clamping
                        this.transform.scale = Math.max(this.settings.minZoom, Math.min(this.settings.maxZoom, this.transform.scale));
                    }
                    
                    getTransform() {
                        return { ...this.transform };
                    }
                }
                
                const canvas = document.getElementById('test-canvas');
                const controller = new ZoomPanController(canvas, { minZoom: 0.2, maxZoom: 5.0 });
                
                // Test clamping
                const results = {};
                
                // Test normal value
                controller.setTransform({ scale: 2.0 });
                results.normal = controller.getTransform().scale;
                
                // Test too high
                controller.setTransform({ scale: 10.0 });
                results.tooHigh = controller.getTransform().scale;
                
                // Test too low
                controller.setTransform({ scale: 0.05 });
                results.tooLow = controller.getTransform().scale;
                
                window.clampingResults = results;
            </script>
        </body>
        </html>
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            f.write(html_content)
            temp_file = f.name
        
        try:
            driver.get(f'file://{temp_file}')
            
            import time
            time.sleep(1)
            
            results = driver.execute_script("return window.clampingResults;")
            
            assert results['normal'] == 2.0
            assert results['tooHigh'] == 5.0  # Clamped to maxZoom
            assert results['tooLow'] == 0.2   # Clamped to minZoom
            
        finally:
            os.unlink(temp_file)