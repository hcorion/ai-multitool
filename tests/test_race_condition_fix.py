"""
Test for race condition fix in inpainting brush stroke handling.
Tests that move events are properly handled even when processed before start events.
"""

import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import time


class TestRaceConditionFix:
    @pytest.fixture
    def driver(self):
        """Set up Chrome driver for testing"""
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-web-security")
        options.add_argument("--allow-running-insecure-content")
        driver = webdriver.Chrome(options=options)
        driver.implicitly_wait(10)
        yield driver
        driver.quit()

    def test_rapid_brush_strokes_no_race_condition(self, driver):
        """Test that rapid brush strokes don't cause race condition errors"""
        driver.get("http://localhost:5000/test-inpainting-canvas")

        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.CLASS_NAME, "inpainting-mask-canvas-container")
            )
        )

        # Execute test that simulates rapid brush strokes
        result = driver.execute_script("""
            return new Promise((resolve) => {
                // Import required modules
                Promise.all([
                    import('/static/js/inpainting-mask-canvas.js'),
                    import('/static/js/canvas-manager.js'),
                    import('/static/js/brush-engine.js'),
                    import('/static/js/input-engine.js'),
                    import('/static/js/render-scheduler.js')
                ]).then(([
                    { InpaintingMaskCanvas },
                    { CanvasManager },
                    { BrushEngine },
                    { InputEngine },
                    { RenderScheduler }
                ]) => {
                    try {
                        // Create test image data
                        const canvas = document.createElement('canvas');
                        canvas.width = 100;
                        canvas.height = 100;
                        const ctx = canvas.getContext('2d');
                        ctx.fillStyle = 'blue';
                        ctx.fillRect(0, 0, 100, 100);
                        const imageUrl = canvas.toDataURL();
                        
                        // Create container
                        const container = document.createElement('div');
                        container.style.width = '400px';
                        container.style.height = '400px';
                        document.body.appendChild(container);
                        
                        // Create inpainting mask canvas
                        const maskCanvas = new InpaintingMaskCanvas({
                            containerElement: container,
                            onMaskComplete: () => {},
                            onCancel: () => {}
                        });
                        
                        // Show and load image
                        maskCanvas.show(imageUrl).then(() => {
                            // Get the canvas manager and input engine
                            const canvasManager = maskCanvas.canvasManager;
                            const inputEngine = maskCanvas.inputEngine;
                            
                            if (!canvasManager || !inputEngine) {
                                resolve({ success: false, error: 'Canvas manager or input engine not found' });
                                return;
                            }
                            
                            // Capture console errors
                            const errors = [];
                            const originalError = console.error;
                            console.error = (...args) => {
                                errors.push(args.join(' '));
                                originalError.apply(console, args);
                            };
                            
                            // Simulate rapid pointer events that could cause race condition
                            const events = [
                                { type: 'start', clientX: 50, clientY: 50, pointerId: 1, pointerType: 'mouse', isPrimary: true },
                                { type: 'move', clientX: 51, clientY: 51, pointerId: 1, pointerType: 'mouse', isPrimary: true },
                                { type: 'move', clientX: 52, clientY: 52, pointerId: 1, pointerType: 'mouse', isPrimary: true },
                                { type: 'move', clientX: 53, clientY: 53, pointerId: 1, pointerType: 'mouse', isPrimary: true },
                                { type: 'end', clientX: 54, clientY: 54, pointerId: 1, pointerType: 'mouse', isPrimary: true }
                            ];
                            
                            // Schedule all events rapidly to test race condition handling
                            const renderScheduler = inputEngine.getRenderScheduler();
                            
                            // Schedule events in rapid succession
                            events.forEach((event, index) => {
                                setTimeout(() => {
                                    renderScheduler.schedulePointerUpdate({
                                        ...event,
                                        screenX: event.clientX,
                                        screenY: event.clientY
                                    });
                                }, index * 2); // Very rapid scheduling (2ms apart)
                            });
                            
                            // Wait for all events to be processed
                            setTimeout(() => {
                                // Restore console.error
                                console.error = originalError;
                                
                                // Check for race condition errors
                                const raceConditionErrors = errors.filter(error => 
                                    error.includes('No active stroke. Call startStroke first') ||
                                    error.includes('Error continuing brush stroke')
                                );
                                
                                // Check brush engine state
                                const brushEngine = canvasManager.getBrushEngine();
                                const currentStroke = brushEngine.getCurrentStroke();
                                
                                resolve({
                                    success: true,
                                    raceConditionErrors: raceConditionErrors.length,
                                    totalErrors: errors.length,
                                    errors: errors,
                                    hasActiveStroke: currentStroke !== null,
                                    strokeEnded: currentStroke === null // Should be null after end event
                                });
                                
                                // Cleanup
                                container.remove();
                            }, 200); // Wait for all events to process
                            
                        }).catch(error => {
                            resolve({ success: false, error: error.message });
                        });
                        
                    } catch (error) {
                        resolve({ success: false, error: error.message });
                    }
                });
            });
        """)

        assert result["success"], f"Test failed: {result.get('error', 'Unknown error')}"
        assert result["raceConditionErrors"] == 0, (
            f"Race condition errors detected: {result['raceConditionErrors']}, errors: {result['errors']}"
        )
        assert result["strokeEnded"], "Stroke should have ended after end event"
        print(f"✅ Race condition test passed - No race condition errors detected")

    def test_out_of_order_events_handling(self, driver):
        """Test that events processed out of order are handled gracefully"""
        driver.get("http://localhost:5000/test-inpainting-canvas")

        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.CLASS_NAME, "inpainting-mask-canvas-container")
            )
        )

        # Execute test that simulates out-of-order events
        result = driver.execute_script("""
            return new Promise((resolve) => {
                // Import required modules
                Promise.all([
                    import('/static/js/inpainting-mask-canvas.js'),
                    import('/static/js/canvas-manager.js'),
                    import('/static/js/brush-engine.js'),
                    import('/static/js/input-engine.js'),
                    import('/static/js/render-scheduler.js')
                ]).then(([
                    { InpaintingMaskCanvas },
                    { CanvasManager },
                    { BrushEngine },
                    { InputEngine },
                    { RenderScheduler }
                ]) => {
                    try {
                        // Create test image data
                        const canvas = document.createElement('canvas');
                        canvas.width = 100;
                        canvas.height = 100;
                        const ctx = canvas.getContext('2d');
                        ctx.fillStyle = 'red';
                        ctx.fillRect(0, 0, 100, 100);
                        const imageUrl = canvas.toDataURL();
                        
                        // Create container
                        const container = document.createElement('div');
                        container.style.width = '400px';
                        container.style.height = '400px';
                        document.body.appendChild(container);
                        
                        // Create inpainting mask canvas
                        const maskCanvas = new InpaintingMaskCanvas({
                            containerElement: container,
                            onMaskComplete: () => {},
                            onCancel: () => {}
                        });
                        
                        // Show and load image
                        maskCanvas.show(imageUrl).then(() => {
                            // Get the canvas manager and input engine
                            const canvasManager = maskCanvas.canvasManager;
                            const inputEngine = maskCanvas.inputEngine;
                            
                            if (!canvasManager || !inputEngine) {
                                resolve({ success: false, error: 'Canvas manager or input engine not found' });
                                return;
                            }
                            
                            // Capture console warnings
                            const warnings = [];
                            const originalWarn = console.warn;
                            console.warn = (...args) => {
                                warnings.push(args.join(' '));
                                originalWarn.apply(console, args);
                            };
                            
                            // Simulate out-of-order events (move before start)
                            const renderScheduler = inputEngine.getRenderScheduler();
                            
                            // Schedule move event first (should be ignored gracefully)
                            renderScheduler.schedulePointerUpdate({
                                type: 'move',
                                clientX: 51,
                                clientY: 51,
                                screenX: 51,
                                screenY: 51,
                                pointerId: 1,
                                pointerType: 'mouse',
                                isPrimary: true
                            });
                            
                            // Then schedule start event
                            setTimeout(() => {
                                renderScheduler.schedulePointerUpdate({
                                    type: 'start',
                                    clientX: 50,
                                    clientY: 50,
                                    screenX: 50,
                                    screenY: 50,
                                    pointerId: 1,
                                    pointerType: 'mouse',
                                    isPrimary: true
                                });
                            }, 10);
                            
                            // Wait for events to be processed
                            setTimeout(() => {
                                // Restore console.warn
                                console.warn = originalWarn;
                                
                                // Check that move before start was handled gracefully
                                const moveIgnoredWarnings = warnings.filter(warning => 
                                    warning.includes('Attempted to continue brush stroke without active stroke')
                                );
                                
                                // Check brush engine state
                                const brushEngine = canvasManager.getBrushEngine();
                                const currentStroke = brushEngine.getCurrentStroke();
                                
                                resolve({
                                    success: true,
                                    moveIgnoredWarnings: moveIgnoredWarnings.length,
                                    totalWarnings: warnings.length,
                                    warnings: warnings,
                                    hasActiveStroke: currentStroke !== null,
                                    strokeStarted: currentStroke !== null // Should have active stroke after start event
                                });
                                
                                // Cleanup
                                container.remove();
                            }, 100);
                            
                        }).catch(error => {
                            resolve({ success: false, error: error.message });
                        });
                        
                    } catch (error) {
                        resolve({ success: false, error: error.message });
                    }
                });
            });
        """)

        assert result["success"], f"Test failed: {result.get('error', 'Unknown error')}"
        assert result["moveIgnoredWarnings"] > 0, (
            "Move event before start should have been ignored with warning"
        )
        assert result["strokeStarted"], "Stroke should have started after start event"
        print(
            f"✅ Out-of-order events test passed - Move before start was handled gracefully"
        )

    def test_event_ordering_in_render_scheduler(self, driver):
        """Test that the render scheduler properly orders events by type and timestamp"""
        driver.get("http://localhost:5000/test-inpainting-canvas")

        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.CLASS_NAME, "inpainting-mask-canvas-container")
            )
        )

        # Execute test for event ordering
        result = driver.execute_script("""
            return new Promise((resolve) => {
                import('/static/js/render-scheduler.js').then(({ RenderScheduler }) => {
                    try {
                        const scheduler = new RenderScheduler();
                        const processedEvents = [];
                        
                        // Set up callback to capture processed events
                        scheduler.setRenderCallback('pointer', (operations) => {
                            operations.forEach(op => {
                                processedEvents.push({
                                    type: op.data.type,
                                    timestamp: op.timestamp,
                                    priority: op.priority
                                });
                            });
                        });
                        
                        // Schedule events in wrong order (move, start, end)
                        const baseTime = performance.now();
                        
                        scheduler.schedulePointerUpdate({
                            type: 'move',
                            clientX: 51,
                            clientY: 51
                        });
                        
                        scheduler.schedulePointerUpdate({
                            type: 'start',
                            clientX: 50,
                            clientY: 50
                        });
                        
                        scheduler.schedulePointerUpdate({
                            type: 'end',
                            clientX: 52,
                            clientY: 52
                        });
                        
                        // Wait for events to be processed
                        setTimeout(() => {
                            // Check that events were reordered correctly
                            const eventTypes = processedEvents.map(e => e.type);
                            const priorities = processedEvents.map(e => e.priority);
                            
                            resolve({
                                success: true,
                                eventTypes: eventTypes,
                                priorities: priorities,
                                correctOrder: eventTypes.join(',') === 'start,move,end',
                                startPriority: priorities[0],
                                movePriority: priorities[1],
                                endPriority: priorities[2]
                            });
                        }, 50);
                        
                    } catch (error) {
                        resolve({ success: false, error: error.message });
                    }
                });
            });
        """)

        assert result["success"], f"Test failed: {result.get('error', 'Unknown error')}"
        assert result["correctOrder"], (
            f"Events not in correct order: {result['eventTypes']}"
        )
        assert result["startPriority"] > result["movePriority"], (
            "Start event should have higher priority than move"
        )
        assert result["movePriority"] > result["endPriority"], (
            "Move event should have higher priority than end"
        )
        print(
            f"✅ Event ordering test passed - Events processed in correct order: {result['eventTypes']}"
        )
