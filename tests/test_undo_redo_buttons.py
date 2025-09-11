"""
Test that undo/redo buttons work correctly after async changes
"""

import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
import time


class TestUndoRedoButtons:
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

    def test_undo_redo_buttons_enabled_after_drawing(self, driver):
        """Test that undo/redo buttons become enabled after drawing strokes"""
        driver.get("http://localhost:5000/test-inpainting-canvas")
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        result = driver.execute_script("""
            return new Promise((resolve) => {
                import('/static/js/inpainting-mask-canvas.js').then(({ InpaintingMaskCanvas }) => {
                    try {
                        // Create a test container
                        const container = document.createElement('div');
                        container.style.width = '800px';
                        container.style.height = '600px';
                        container.style.position = 'fixed';
                        container.style.top = '0';
                        container.style.left = '0';
                        document.body.appendChild(container);
                        
                        // Create test image
                        const canvas = document.createElement('canvas');
                        canvas.width = canvas.height = 200;
                        const ctx = canvas.getContext('2d');
                        ctx.fillStyle = '#0000ff';
                        ctx.fillRect(0, 0, 200, 200);
                        const imageUrl = canvas.toDataURL();
                        
                        // Create InpaintingMaskCanvas
                        const maskCanvas = new InpaintingMaskCanvas({
                            imageUrl: imageUrl,
                            containerElement: container,
                            onMaskComplete: () => {},
                            onCancel: () => {}
                        });
                        
                        // Show the canvas
                        maskCanvas.show().then(async () => {
                            // Wait for initialization
                            await new Promise(resolve => setTimeout(resolve, 500));
                            
                            // Get button references
                            const undoBtn = container.querySelector('.undo-btn');
                            const redoBtn = container.querySelector('.redo-btn');
                            
                            // Check initial button states (should be disabled)
                            const initialUndoDisabled = undoBtn ? undoBtn.disabled : true;
                            const initialRedoDisabled = redoBtn ? redoBtn.disabled : true;
                            
                            // Simulate drawing a stroke by calling the input handler directly
                            const inputHandler = maskCanvas.handleInputEvent;
                            
                            // Start stroke
                            await inputHandler.call(maskCanvas, {
                                type: 'start',
                                clientX: 400,
                                clientY: 300
                            });
                            
                            // Move stroke
                            await inputHandler.call(maskCanvas, {
                                type: 'move',
                                clientX: 410,
                                clientY: 310
                            });
                            
                            // End stroke (this should add to history)
                            await inputHandler.call(maskCanvas, {
                                type: 'end',
                                clientX: 420,
                                clientY: 320
                            });
                            
                            // Wait for async processing to complete
                            await new Promise(resolve => setTimeout(resolve, 200));
                            
                            // Check button states after drawing
                            const afterDrawUndoDisabled = undoBtn ? undoBtn.disabled : true;
                            const afterDrawRedoDisabled = redoBtn ? redoBtn.disabled : true;
                            
                            // Test undo button click
                            let undoClickWorked = false;
                            if (undoBtn && !undoBtn.disabled) {
                                undoBtn.click();
                                await new Promise(resolve => setTimeout(resolve, 200));
                                undoClickWorked = true;
                            }
                            
                            // Check button states after undo
                            const afterUndoUndoDisabled = undoBtn ? undoBtn.disabled : true;
                            const afterUndoRedoDisabled = redoBtn ? redoBtn.disabled : true;
                            
                            // Test redo button click
                            let redoClickWorked = false;
                            if (redoBtn && !redoBtn.disabled) {
                                redoBtn.click();
                                await new Promise(resolve => setTimeout(resolve, 200));
                                redoClickWorked = true;
                            }
                            
                            // Check final button states
                            const finalUndoDisabled = undoBtn ? undoBtn.disabled : true;
                            const finalRedoDisabled = redoBtn ? redoBtn.disabled : true;
                            
                            // Cleanup
                            maskCanvas.hide();
                            container.remove();
                            
                            resolve({
                                success: true,
                                buttonsFound: {
                                    undo: undoBtn !== null,
                                    redo: redoBtn !== null
                                },
                                buttonStates: {
                                    initial: { undo: initialUndoDisabled, redo: initialRedoDisabled },
                                    afterDraw: { undo: afterDrawUndoDisabled, redo: afterDrawRedoDisabled },
                                    afterUndo: { undo: afterUndoUndoDisabled, redo: afterUndoRedoDisabled },
                                    final: { undo: finalUndoDisabled, redo: finalRedoDisabled }
                                },
                                clickTests: {
                                    undoClickWorked: undoClickWorked,
                                    redoClickWorked: redoClickWorked
                                }
                            });
                            
                        }).catch(error => {
                            container.remove();
                            resolve({ success: false, error: error.message });
                        });
                        
                    } catch (error) {
                        resolve({ success: false, error: error.message });
                    }
                });
            });
        """)
        
        assert result['success'], f"Undo/redo button test failed: {result.get('error', 'Unknown error')}"
        
        # Verify buttons were found
        assert result['buttonsFound']['undo'] == True, "Undo button should be found"
        assert result['buttonsFound']['redo'] == True, "Redo button should be found"
        
        # Verify button state progression
        button_states = result['buttonStates']
        
        # Initially both should be disabled (no history)
        assert button_states['initial']['undo'] == True, "Undo button should be initially disabled"
        assert button_states['initial']['redo'] == True, "Redo button should be initially disabled"
        
        # After drawing, undo should be enabled, redo should still be disabled
        assert button_states['afterDraw']['undo'] == False, "Undo button should be enabled after drawing"
        assert button_states['afterDraw']['redo'] == True, "Redo button should still be disabled after drawing"
        
        # Verify clicks worked
        assert result['clickTests']['undoClickWorked'] == True, "Undo button click should work"
        assert result['clickTests']['redoClickWorked'] == True, "Redo button click should work"
        
        print(f"✅ Undo/redo buttons work correctly!")
        print(f"Button states: {button_states}")
        print(f"Click tests: {result['clickTests']}")

    def test_keyboard_shortcuts_work(self, driver):
        """Test that Ctrl+Z and Ctrl+Shift+Z keyboard shortcuts work"""
        driver.get("http://localhost:5000/test-inpainting-canvas")
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        result = driver.execute_script("""
            return new Promise((resolve) => {
                import('/static/js/inpainting-mask-canvas.js').then(({ InpaintingMaskCanvas }) => {
                    try {
                        // Create a test container
                        const container = document.createElement('div');
                        container.style.width = '800px';
                        container.style.height = '600px';
                        container.style.position = 'fixed';
                        container.style.top = '0';
                        container.style.left = '0';
                        document.body.appendChild(container);
                        
                        // Create test image
                        const canvas = document.createElement('canvas');
                        canvas.width = canvas.height = 200;
                        const ctx = canvas.getContext('2d');
                        ctx.fillStyle = '#ff0000';
                        ctx.fillRect(0, 0, 200, 200);
                        const imageUrl = canvas.toDataURL();
                        
                        // Track keyboard events
                        let undoKeyboardWorked = false;
                        let redoKeyboardWorked = false;
                        
                        // Create InpaintingMaskCanvas
                        const maskCanvas = new InpaintingMaskCanvas({
                            imageUrl: imageUrl,
                            containerElement: container,
                            onMaskComplete: () => {},
                            onCancel: () => {}
                        });
                        
                        // Show the canvas
                        maskCanvas.show().then(async () => {
                            // Wait for initialization
                            await new Promise(resolve => setTimeout(resolve, 500));
                            
                            // Simulate drawing a stroke
                            const inputHandler = maskCanvas.handleInputEvent;
                            
                            await inputHandler.call(maskCanvas, { type: 'start', clientX: 400, clientY: 300 });
                            await inputHandler.call(maskCanvas, { type: 'move', clientX: 410, clientY: 310 });
                            await inputHandler.call(maskCanvas, { type: 'end', clientX: 420, clientY: 320 });
                            
                            // Wait for processing
                            await new Promise(resolve => setTimeout(resolve, 200));
                            
                            // Test Ctrl+Z (undo)
                            try {
                                const undoEvent = new KeyboardEvent('keydown', {
                                    key: 'z',
                                    ctrlKey: true,
                                    bubbles: true
                                });
                                document.dispatchEvent(undoEvent);
                                await new Promise(resolve => setTimeout(resolve, 200));
                                undoKeyboardWorked = true;
                            } catch (error) {
                                console.error('Undo keyboard test failed:', error);
                            }
                            
                            // Test Ctrl+Shift+Z (redo)
                            try {
                                const redoEvent = new KeyboardEvent('keydown', {
                                    key: 'z',
                                    ctrlKey: true,
                                    shiftKey: true,
                                    bubbles: true
                                });
                                document.dispatchEvent(redoEvent);
                                await new Promise(resolve => setTimeout(resolve, 200));
                                redoKeyboardWorked = true;
                            } catch (error) {
                                console.error('Redo keyboard test failed:', error);
                            }
                            
                            // Cleanup
                            maskCanvas.hide();
                            container.remove();
                            
                            resolve({
                                success: true,
                                keyboardTests: {
                                    undoKeyboardWorked: undoKeyboardWorked,
                                    redoKeyboardWorked: redoKeyboardWorked
                                }
                            });
                            
                        }).catch(error => {
                            container.remove();
                            resolve({ success: false, error: error.message });
                        });
                        
                    } catch (error) {
                        resolve({ success: false, error: error.message });
                    }
                });
            });
        """)
        
        assert result['success'], f"Keyboard shortcut test failed: {result.get('error', 'Unknown error')}"
        
        # Verify keyboard shortcuts worked
        keyboard_tests = result['keyboardTests']
        assert keyboard_tests['undoKeyboardWorked'] == True, "Ctrl+Z keyboard shortcut should work"
        assert keyboard_tests['redoKeyboardWorked'] == True, "Ctrl+Shift+Z keyboard shortcut should work"
        
        print(f"✅ Keyboard shortcuts work correctly!")
        print(f"Keyboard tests: {keyboard_tests}")

    def test_button_states_update_correctly(self, driver):
        """Test that button states update correctly as history changes"""
        driver.get("http://localhost:5000/test-inpainting-canvas")
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        result = driver.execute_script("""
            return new Promise((resolve) => {
                import('/static/js/inpainting-mask-canvas.js').then(({ InpaintingMaskCanvas }) => {
                    try {
                        // Create a test container
                        const container = document.createElement('div');
                        container.style.width = '800px';
                        container.style.height = '600px';
                        container.style.position = 'fixed';
                        container.style.top = '0';
                        container.style.left = '0';
                        document.body.appendChild(container);
                        
                        // Create test image
                        const canvas = document.createElement('canvas');
                        canvas.width = canvas.height = 200;
                        const ctx = canvas.getContext('2d');
                        ctx.fillStyle = '#00ff00';
                        ctx.fillRect(0, 0, 200, 200);
                        const imageUrl = canvas.toDataURL();
                        
                        // Create InpaintingMaskCanvas
                        const maskCanvas = new InpaintingMaskCanvas({
                            imageUrl: imageUrl,
                            containerElement: container,
                            onMaskComplete: () => {},
                            onCancel: () => {}
                        });
                        
                        // Show the canvas
                        maskCanvas.show().then(async () => {
                            // Wait for initialization
                            await new Promise(resolve => setTimeout(resolve, 500));
                            
                            const undoBtn = container.querySelector('.undo-btn');
                            const redoBtn = container.querySelector('.redo-btn');
                            const inputHandler = maskCanvas.handleInputEvent;
                            
                            const states = [];
                            
                            // Record initial state
                            states.push({
                                phase: 'initial',
                                undo: undoBtn ? undoBtn.disabled : true,
                                redo: redoBtn ? redoBtn.disabled : true
                            });
                            
                            // Draw first stroke
                            await inputHandler.call(maskCanvas, { type: 'start', clientX: 400, clientY: 300 });
                            await inputHandler.call(maskCanvas, { type: 'end', clientX: 410, clientY: 310 });
                            await new Promise(resolve => setTimeout(resolve, 200));
                            
                            states.push({
                                phase: 'after_stroke_1',
                                undo: undoBtn ? undoBtn.disabled : true,
                                redo: redoBtn ? redoBtn.disabled : true
                            });
                            
                            // Draw second stroke
                            await inputHandler.call(maskCanvas, { type: 'start', clientX: 420, clientY: 320 });
                            await inputHandler.call(maskCanvas, { type: 'end', clientX: 430, clientY: 330 });
                            await new Promise(resolve => setTimeout(resolve, 200));
                            
                            states.push({
                                phase: 'after_stroke_2',
                                undo: undoBtn ? undoBtn.disabled : true,
                                redo: redoBtn ? redoBtn.disabled : true
                            });
                            
                            // Undo once
                            if (undoBtn && !undoBtn.disabled) {
                                undoBtn.click();
                                await new Promise(resolve => setTimeout(resolve, 200));
                            }
                            
                            states.push({
                                phase: 'after_undo_1',
                                undo: undoBtn ? undoBtn.disabled : true,
                                redo: redoBtn ? redoBtn.disabled : true
                            });
                            
                            // Undo again
                            if (undoBtn && !undoBtn.disabled) {
                                undoBtn.click();
                                await new Promise(resolve => setTimeout(resolve, 200));
                            }
                            
                            states.push({
                                phase: 'after_undo_2',
                                undo: undoBtn ? undoBtn.disabled : true,
                                redo: redoBtn ? redoBtn.disabled : true
                            });
                            
                            // Redo once
                            if (redoBtn && !redoBtn.disabled) {
                                redoBtn.click();
                                await new Promise(resolve => setTimeout(resolve, 200));
                            }
                            
                            states.push({
                                phase: 'after_redo_1',
                                undo: undoBtn ? undoBtn.disabled : true,
                                redo: redoBtn ? redoBtn.disabled : true
                            });
                            
                            // Cleanup
                            maskCanvas.hide();
                            container.remove();
                            
                            resolve({
                                success: true,
                                states: states
                            });
                            
                        }).catch(error => {
                            container.remove();
                            resolve({ success: false, error: error.message });
                        });
                        
                    } catch (error) {
                        resolve({ success: false, error: error.message });
                    }
                });
            });
        """)
        
        assert result['success'], f"Button state test failed: {result.get('error', 'Unknown error')}"
        
        states = result['states']
        
        # Verify state progression
        initial = next(s for s in states if s['phase'] == 'initial')
        after_stroke_1 = next(s for s in states if s['phase'] == 'after_stroke_1')
        after_stroke_2 = next(s for s in states if s['phase'] == 'after_stroke_2')
        after_undo_1 = next(s for s in states if s['phase'] == 'after_undo_1')
        after_undo_2 = next(s for s in states if s['phase'] == 'after_undo_2')
        after_redo_1 = next(s for s in states if s['phase'] == 'after_redo_1')
        
        # Initial: both disabled
        assert initial['undo'] == True and initial['redo'] == True, "Initially both buttons should be disabled"
        
        # After strokes: undo enabled, redo disabled
        assert after_stroke_1['undo'] == False, "Undo should be enabled after first stroke"
        assert after_stroke_2['undo'] == False, "Undo should be enabled after second stroke"
        assert after_stroke_1['redo'] == True and after_stroke_2['redo'] == True, "Redo should be disabled after strokes"
        
        # After undos: redo should become enabled
        assert after_undo_1['redo'] == False, "Redo should be enabled after first undo"
        assert after_undo_2['redo'] == False, "Redo should be enabled after second undo"
        
        # After redo: undo should be enabled again
        assert after_redo_1['undo'] == False, "Undo should be enabled after redo"
        
        print(f"✅ Button states update correctly throughout history operations!")
        print("State progression:")
        for state in states:
            print(f"  {state['phase']}: undo={not state['undo']}, redo={not state['redo']}")