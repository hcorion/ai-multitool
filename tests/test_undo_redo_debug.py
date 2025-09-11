"""
Debug test for undo/redo button issues
"""

import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options


class TestUndoRedoDebug:
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

    def test_debug_undo_redo_flow(self, driver):
        """Debug the undo/redo flow to see what's happening"""
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
                            
                            const log = [];
                            
                            // Helper to log button states
                            const logState = (phase) => {
                                const historyState = maskCanvas.historyManager.getState();
                                log.push({
                                    phase: phase,
                                    historyState: historyState,
                                    undoDisabled: undoBtn ? undoBtn.disabled : true,
                                    redoDisabled: redoBtn ? redoBtn.disabled : true
                                });
                            };
                            
                            logState('initial');
                            
                            // Draw a stroke
                            await inputHandler.call(maskCanvas, { type: 'start', clientX: 400, clientY: 300 });
                            await inputHandler.call(maskCanvas, { type: 'end', clientX: 410, clientY: 310 });
                            await new Promise(resolve => setTimeout(resolve, 300)); // Wait longer for async
                            
                            logState('after_stroke');
                            
                            // Try undo
                            if (undoBtn && !undoBtn.disabled) {
                                log.push({ phase: 'clicking_undo', message: 'Undo button clicked' });
                                undoBtn.click();
                                await new Promise(resolve => setTimeout(resolve, 500)); // Wait longer for async
                                logState('after_undo');
                            } else {
                                log.push({ phase: 'undo_failed', message: 'Undo button was disabled or not found' });
                            }
                            
                            // Try redo
                            if (redoBtn && !redoBtn.disabled) {
                                log.push({ phase: 'clicking_redo', message: 'Redo button clicked' });
                                redoBtn.click();
                                await new Promise(resolve => setTimeout(resolve, 500)); // Wait longer for async
                                logState('after_redo');
                            } else {
                                log.push({ phase: 'redo_failed', message: 'Redo button was disabled or not found' });
                            }
                            
                            // Cleanup
                            maskCanvas.hide();
                            container.remove();
                            
                            resolve({
                                success: true,
                                log: log
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
        
        assert result['success'], f"Debug test failed: {result.get('error', 'Unknown error')}"
        
        log = result['log']
        
        print("🔍 Undo/Redo Debug Log:")
        for entry in log:
            if 'historyState' in entry:
                print(f"  {entry['phase']}:")
                print(f"    History: canUndo={entry['historyState']['canUndo']}, canRedo={entry['historyState']['canRedo']}, strokeCount={entry['historyState']['strokeCount']}")
                print(f"    Buttons: undoDisabled={entry['undoDisabled']}, redoDisabled={entry['redoDisabled']}")
            else:
                print(f"  {entry['phase']}: {entry['message']}")
        
        # Find key states
        initial = next((e for e in log if e['phase'] == 'initial'), None)
        after_stroke = next((e for e in log if e['phase'] == 'after_stroke'), None)
        after_undo = next((e for e in log if e['phase'] == 'after_undo'), None)
        
        # Verify progression
        if initial:
            assert initial['historyState']['strokeCount'] == 0, "Initial stroke count should be 0"
            assert initial['undoDisabled'] == True, "Undo should be initially disabled"
            assert initial['redoDisabled'] == True, "Redo should be initially disabled"
        
        if after_stroke:
            assert after_stroke['historyState']['strokeCount'] > 0, "Stroke count should increase after drawing"
            assert after_stroke['undoDisabled'] == False, "Undo should be enabled after drawing"
        
        if after_undo:
            assert after_undo['historyState']['canRedo'] == True, "History should show redo available after undo"
            # This is the key test - redo button should be enabled after undo
            print(f"🔍 After undo: canRedo={after_undo['historyState']['canRedo']}, redoDisabled={after_undo['redoDisabled']}")
        
        print("✅ Debug test completed - check log above for details")