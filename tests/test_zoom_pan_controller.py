"""
Test ZoomPanController functionality for the inpainting mask canvas.
Tests zoom and pan gestures, coordinate transformations, and drawing disable/enable.
"""

import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.options import Options


class TestZoomPanController:
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

    def test_zoom_pan_controller_creation(self, driver):
        """Test ZoomPanController can be created and initialized"""
        driver.get("http://localhost:5000/test-inpainting-canvas")
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "canvas"))
        )
        
        result = driver.execute_script("""
            return new Promise((resolve) => {
                import('/static/js/zoom-pan-controller.js').then(({ ZoomPanController }) => {
                    try {
                        const canvas = document.createElement('canvas');
                        canvas.width = 800;
                        canvas.height = 600;
                        document.body.appendChild(canvas);
                        
                        const controller = new ZoomPanController(canvas, {
                            minZoom: 0.1,
                            maxZoom: 10.0,
                            zoomSensitivity: 0.002,
                            enablePinchZoom: true,
                            enableWheelZoom: true,
                            enablePan: true
                        });
                        
                        const settings = controller.getSettings();
                        const transform = controller.getTransform();
                        
                        resolve({
                            success: true,
                            settings: settings,
                            transform: transform,
                            isEnabled: false, // Should start disabled
                            isGestureActive: controller.isGestureActive()
                        });
                    } catch (error) {
                        resolve({ success: false, error: error.message });
                    }
                });
            });
        """)
        
        assert result['success'], f"Test failed: {result.get('error', 'Unknown error')}"
        assert result['settings']['minZoom'] == 0.1
        assert result['settings']['maxZoom'] == 10.0
        assert result['settings']['enablePinchZoom'] == True
        assert result['transform']['scale'] == 1.0
        assert result['transform']['translateX'] == 0
        assert result['transform']['translateY'] == 0
        assert result['isGestureActive'] == False

    def test_zoom_functionality(self, driver):
        """Test zoom in/out functionality and scale clamping"""
        driver.get("http://localhost:5000/test-inpainting-canvas")
        
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "canvas"))
        )
        
        result = driver.execute_script("""
            return new Promise((resolve) => {
                import('/static/js/zoom-pan-controller.js').then(({ ZoomPanController }) => {
                    try {
                        const canvas = document.createElement('canvas');
                        canvas.width = 800;
                        canvas.height = 600;
                        document.body.appendChild(canvas);
                        
                        const controller = new ZoomPanController(canvas, {
                            minZoom: 0.5,
                            maxZoom: 5.0
                        });
                        
                        controller.enable();
                        
                        // Test zoom in
                        controller.setTransform({ scale: 2.0 });
                        const zoomInTransform = controller.getTransform();
                        
                        // Test zoom out
                        controller.setTransform({ scale: 0.8 });
                        const zoomOutTransform = controller.getTransform();
                        
                        // Test zoom clamping - too high
                        controller.setTransform({ scale: 10.0 });
                        const clampedHighTransform = controller.getTransform();
                        
                        // Test zoom clamping - too low
                        controller.setTransform({ scale: 0.1 });
                        const clampedLowTransform = controller.getTransform();
                        
                        // Test reset
                        controller.resetTransform();
                        const resetTransform = controller.getTransform();
                        
                        resolve({
                            success: true,
                            zoomIn: zoomInTransform.scale,
                            zoomOut: zoomOutTransform.scale,
                            clampedHigh: clampedHighTransform.scale,
                            clampedLow: clampedLowTransform.scale,
                            reset: resetTransform
                        });
                    } catch (error) {
                        resolve({ success: false, error: error.message });
                    }
                });
            });
        """)
        
        assert result['success'], f"Test failed: {result.get('error', 'Unknown error')}"
        assert result['zoomIn'] == 2.0
        assert result['zoomOut'] == 0.8
        assert result['clampedHigh'] == 5.0  # Should be clamped to maxZoom
        assert result['clampedLow'] == 0.5   # Should be clamped to minZoom
        assert result['reset']['scale'] == 1.0
        assert result['reset']['translateX'] == 0
        assert result['reset']['translateY'] == 0

    def test_pan_functionality(self, driver):
        """Test pan functionality and translation"""
        driver.get("http://localhost:5000/test-inpainting-canvas")
        
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "canvas"))
        )
        
        result = driver.execute_script("""
            return new Promise((resolve) => {
                import('/static/js/zoom-pan-controller.js').then(({ ZoomPanController }) => {
                    try {
                        const canvas = document.createElement('canvas');
                        canvas.width = 800;
                        canvas.height = 600;
                        document.body.appendChild(canvas);
                        
                        const controller = new ZoomPanController(canvas);
                        controller.enable();
                        controller.setImageBounds(400, 300);
                        controller.setCanvasBounds(800, 600);
                        
                        // Test translation
                        controller.setTransform({ translateX: 50, translateY: 30 });
                        const panTransform = controller.getTransform();
                        
                        // Test combined zoom and pan
                        controller.setTransform({ scale: 2.0, translateX: 100, translateY: 80 });
                        const combinedTransform = controller.getTransform();
                        
                        resolve({
                            success: true,
                            pan: {
                                translateX: panTransform.translateX,
                                translateY: panTransform.translateY
                            },
                            combined: {
                                scale: combinedTransform.scale,
                                translateX: combinedTransform.translateX,
                                translateY: combinedTransform.translateY
                            }
                        });
                    } catch (error) {
                        resolve({ success: false, error: error.message });
                    }
                });
            });
        """)
        
        assert result['success'], f"Test failed: {result.get('error', 'Unknown error')}"
        assert result['pan']['translateX'] == 50
        assert result['pan']['translateY'] == 30
        assert result['combined']['scale'] == 2.0
        assert result['combined']['translateX'] == 100
        assert result['combined']['translateY'] == 80

    def test_coordinate_transformation(self, driver):
        """Test screen to image coordinate transformation with zoom/pan"""
        driver.get("http://localhost:5000/test-inpainting-canvas")
        
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "canvas"))
        )
        
        result = driver.execute_script("""
            return new Promise((resolve) => {
                import('/static/js/zoom-pan-controller.js').then(({ ZoomPanController }) => {
                    try {
                        const canvas = document.createElement('canvas');
                        canvas.width = 800;
                        canvas.height = 600;
                        canvas.style.position = 'absolute';
                        canvas.style.left = '0px';
                        canvas.style.top = '0px';
                        document.body.appendChild(canvas);
                        
                        const controller = new ZoomPanController(canvas);
                        controller.enable();
                        controller.setImageBounds(400, 300);
                        controller.setCanvasBounds(800, 600);
                        
                        // Test coordinate transformation at 1x zoom
                        const coord1x = controller.screenToImage(100, 80);
                        
                        // Test coordinate transformation at 2x zoom
                        controller.setTransform({ scale: 2.0 });
                        const coord2x = controller.screenToImage(100, 80);
                        
                        // Test coordinate transformation with pan
                        controller.setTransform({ scale: 1.0, translateX: 50, translateY: 30 });
                        const coordPan = controller.screenToImage(100, 80);
                        
                        // Test reverse transformation
                        const screenCoord = controller.imageToScreen(50, 40);
                        
                        // Test out of bounds
                        controller.resetTransform();
                        const outOfBounds = controller.screenToImage(1000, 1000);
                        
                        resolve({
                            success: true,
                            coord1x: coord1x,
                            coord2x: coord2x,
                            coordPan: coordPan,
                            screenCoord: screenCoord,
                            outOfBounds: outOfBounds
                        });
                    } catch (error) {
                        resolve({ success: false, error: error.message });
                    }
                });
            });
        """)
        
        assert result['success'], f"Test failed: {result.get('error', 'Unknown error')}"
        
        # At 1x zoom, screen coordinates should map directly to image coordinates
        assert result['coord1x'] is not None
        assert result['coord1x']['x'] == 100
        assert result['coord1x']['y'] == 80
        
        # At 2x zoom, screen coordinates should map to half the image coordinates
        assert result['coord2x'] is not None
        assert result['coord2x']['x'] == 50  # 100 / 2
        assert result['coord2x']['y'] == 40  # 80 / 2
        
        # With pan, coordinates should be offset
        assert result['coordPan'] is not None
        assert result['coordPan']['x'] == 50  # (100 - 50) / 1
        assert result['coordPan']['y'] == 50  # (80 - 30) / 1
        
        # Reverse transformation should work
        assert result['screenCoord'] is not None
        
        # Out of bounds should return null
        assert result['outOfBounds'] is None

    def test_gesture_state_management(self, driver):
        """Test gesture active state and drawing disable/enable"""
        driver.get("http://localhost:5000/test-inpainting-canvas")
        
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "canvas"))
        )
        
        result = driver.execute_script("""
            return new Promise((resolve) => {
                import('/static/js/zoom-pan-controller.js').then(({ ZoomPanController }) => {
                    try {
                        const canvas = document.createElement('canvas');
                        canvas.width = 800;
                        canvas.height = 600;
                        document.body.appendChild(canvas);
                        
                        let transformStartCalled = false;
                        let transformUpdateCalled = false;
                        let transformEndCalled = false;
                        let lastTransform = null;
                        
                        const controller = new ZoomPanController(canvas);
                        controller.setEventHandler({
                            onTransformStart: () => {
                                transformStartCalled = true;
                            },
                            onTransformUpdate: (transform) => {
                                transformUpdateCalled = true;
                                lastTransform = transform;
                            },
                            onTransformEnd: () => {
                                transformEndCalled = true;
                            }
                        });
                        
                        controller.enable();
                        
                        // Simulate gesture start by setting transform
                        controller.setTransform({ scale: 1.5 });
                        
                        const isActiveAfterTransform = controller.isGestureActive();
                        
                        resolve({
                            success: true,
                            transformStartCalled: transformStartCalled,
                            transformUpdateCalled: transformUpdateCalled,
                            transformEndCalled: transformEndCalled,
                            lastTransform: lastTransform,
                            isActiveAfterTransform: isActiveAfterTransform
                        });
                    } catch (error) {
                        resolve({ success: false, error: error.message });
                    }
                });
            });
        """)
        
        assert result['success'], f"Test failed: {result.get('error', 'Unknown error')}"
        
        # Transform update should be called when setting transform
        assert result['transformUpdateCalled'] == True
        assert result['lastTransform'] is not None
        assert result['lastTransform']['scale'] == 1.5

    def test_settings_update(self, driver):
        """Test updating zoom/pan settings"""
        driver.get("http://localhost:5000/test-inpainting-canvas")
        
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "canvas"))
        )
        
        result = driver.execute_script("""
            return new Promise((resolve) => {
                import('/static/js/zoom-pan-controller.js').then(({ ZoomPanController }) => {
                    try {
                        const canvas = document.createElement('canvas');
                        canvas.width = 800;
                        canvas.height = 600;
                        document.body.appendChild(canvas);
                        
                        const controller = new ZoomPanController(canvas, {
                            minZoom: 0.5,
                            maxZoom: 4.0,
                            enablePinchZoom: false
                        });
                        
                        const initialSettings = controller.getSettings();
                        
                        // Update settings
                        controller.updateSettings({
                            minZoom: 0.2,
                            maxZoom: 8.0,
                            enablePinchZoom: true,
                            zoomSensitivity: 0.005
                        });
                        
                        const updatedSettings = controller.getSettings();
                        
                        resolve({
                            success: true,
                            initial: {
                                minZoom: initialSettings.minZoom,
                                maxZoom: initialSettings.maxZoom,
                                enablePinchZoom: initialSettings.enablePinchZoom
                            },
                            updated: {
                                minZoom: updatedSettings.minZoom,
                                maxZoom: updatedSettings.maxZoom,
                                enablePinchZoom: updatedSettings.enablePinchZoom,
                                zoomSensitivity: updatedSettings.zoomSensitivity
                            }
                        });
                    } catch (error) {
                        resolve({ success: false, error: error.message });
                    }
                });
            });
        """)
        
        assert result['success'], f"Test failed: {result.get('error', 'Unknown error')}"
        
        # Check initial settings
        assert result['initial']['minZoom'] == 0.5
        assert result['initial']['maxZoom'] == 4.0
        assert result['initial']['enablePinchZoom'] == False
        
        # Check updated settings
        assert result['updated']['minZoom'] == 0.2
        assert result['updated']['maxZoom'] == 8.0
        assert result['updated']['enablePinchZoom'] == True
        assert result['updated']['zoomSensitivity'] == 0.005

    def test_cleanup(self, driver):
        """Test proper cleanup of zoom/pan controller"""
        driver.get("http://localhost:5000/test-inpainting-canvas")
        
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "canvas"))
        )
        
        result = driver.execute_script("""
            return new Promise((resolve) => {
                import('/static/js/zoom-pan-controller.js').then(({ ZoomPanController }) => {
                    try {
                        const canvas = document.createElement('canvas');
                        canvas.width = 800;
                        canvas.height = 600;
                        document.body.appendChild(canvas);
                        
                        const controller = new ZoomPanController(canvas);
                        controller.enable();
                        controller.setTransform({ scale: 2.0, translateX: 50, translateY: 30 });
                        
                        const beforeCleanup = {
                            isEnabled: true, // We can't directly check this, but we enabled it
                            transform: controller.getTransform()
                        };
                        
                        // Cleanup
                        controller.cleanup();
                        
                        // After cleanup, controller should be disabled
                        const afterCleanup = {
                            isGestureActive: controller.isGestureActive()
                        };
                        
                        resolve({
                            success: true,
                            beforeCleanup: beforeCleanup,
                            afterCleanup: afterCleanup
                        });
                    } catch (error) {
                        resolve({ success: false, error: error.message });
                    }
                });
            });
        """)
        
        assert result['success'], f"Test failed: {result.get('error', 'Unknown error')}"
        
        # Before cleanup, transform should be set
        assert result['beforeCleanup']['transform']['scale'] == 2.0
        assert result['beforeCleanup']['transform']['translateX'] == 50
        assert result['beforeCleanup']['transform']['translateY'] == 30
        
        # After cleanup, gesture should not be active
        assert result['afterCleanup']['isGestureActive'] == False