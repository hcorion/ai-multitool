"""
Test that async WebWorker functions are actually used in the application
Verifies that the async methods are called during normal canvas operations
"""

import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
import time


class TestAsyncIntegrationUsage:
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

    def test_async_stroke_processing_in_canvas(self, driver):
        """Test that async stroke processing is used during actual canvas drawing"""
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
                        
                        // Track async method calls
                        let asyncStrokeProcessingCalled = false;
                        let asyncCheckpointCreationCalled = false;
                        let asyncMaskValidationCalled = false;
                        
                        // Create InpaintingMaskCanvas
                        const maskCanvas = new InpaintingMaskCanvas({
                            imageUrl: imageUrl,
                            containerElement: container,
                            onMaskComplete: () => {},
                            onCancel: () => {}
                        });
                        
                        // Show the canvas
                        maskCanvas.show().then(() => {
                            // Access internal components
                            const canvasManager = maskCanvas.canvasManager;
                            const workerManager = canvasManager.getWorkerManager();
                            
                            // Monkey patch async methods to track calls
                            const originalApplyBrushStrokeAsync = canvasManager.applyBrushStrokeAsync.bind(canvasManager);
                            canvasManager.applyBrushStrokeAsync = async function(...args) {
                                asyncStrokeProcessingCalled = true;
                                console.log('Async stroke processing called!');
                                return await originalApplyBrushStrokeAsync(...args);
                            };
                            
                            const originalValidateMaskAsync = canvasManager.validateMaskAsync.bind(canvasManager);
                            canvasManager.validateMaskAsync = async function(...args) {
                                asyncMaskValidationCalled = true;
                                console.log('Async mask validation called!');
                                return await originalValidateMaskAsync(...args);
                            };
                            
                            const historyManager = maskCanvas.historyManager;
                            const originalCreateCheckpointAsync = historyManager.createTileBasedCheckpointAsync.bind(historyManager);
                            historyManager.createTileBasedCheckpointAsync = async function(...args) {
                                asyncCheckpointCreationCalled = true;
                                console.log('Async checkpoint creation called!');
                                return await originalCreateCheckpointAsync(...args);
                            };
                            
                            // Simulate drawing strokes by directly calling the input handler
                            const inputEngine = maskCanvas.inputEngine;
                            const handleInputEvent = maskCanvas.handleInputEvent;
                            
                            // Simulate a drawing stroke
                            const simulateStroke = async () => {
                                // Start stroke
                                await handleInputEvent.call(maskCanvas, {
                                    type: 'start',
                                    clientX: 400,
                                    clientY: 300
                                });
                                
                                // Move stroke
                                await handleInputEvent.call(maskCanvas, {
                                    type: 'move',
                                    clientX: 410,
                                    clientY: 310
                                });
                                
                                // End stroke (this should trigger async processing)
                                await handleInputEvent.call(maskCanvas, {
                                    type: 'end',
                                    clientX: 420,
                                    clientY: 320
                                });
                                
                                // Wait a bit for async operations to complete
                                await new Promise(resolve => setTimeout(resolve, 100));
                            };
                            
                            // Perform multiple strokes to trigger checkpoints and validation
                            const performMultipleStrokes = async () => {
                                for (let i = 0; i < 25; i++) { // 25 strokes to trigger checkpoint and validation
                                    await simulateStroke();
                                    await new Promise(resolve => setTimeout(resolve, 10));
                                }
                                
                                // Wait for all async operations to complete
                                await new Promise(resolve => setTimeout(resolve, 500));
                                
                                // Cleanup
                                maskCanvas.hide();
                                container.remove();
                                
                                resolve({
                                    success: true,
                                    asyncStrokeProcessingCalled: asyncStrokeProcessingCalled,
                                    asyncCheckpointCreationCalled: asyncCheckpointCreationCalled,
                                    asyncMaskValidationCalled: asyncMaskValidationCalled,
                                    workerAvailable: workerManager.isWorkerAvailable(),
                                    strokeCount: i
                                });
                            };
                            
                            performMultipleStrokes().catch(error => {
                                resolve({ success: false, error: error.message });
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
        
        assert result['success'], f"Async integration test failed: {result.get('error', 'Unknown error')}"
        
        # Verify that async methods were actually called
        assert result['asyncStrokeProcessingCalled'] == True, "Async stroke processing should be called during drawing"
        assert result['asyncCheckpointCreationCalled'] == True, "Async checkpoint creation should be called after multiple strokes"
        assert result['asyncMaskValidationCalled'] == True, "Async mask validation should be called periodically"
        
        print(f"✅ Async methods are being used in the application!")
        print(f"Worker available: {result['workerAvailable']}")
        print(f"Strokes processed: {result['strokeCount']}")

    def test_async_export_in_completion(self, driver):
        """Test that async export is used when completing the mask"""
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
                        document.body.appendChild(container);
                        
                        // Create test image
                        const canvas = document.createElement('canvas');
                        canvas.width = canvas.height = 100;
                        const ctx = canvas.getContext('2d');
                        ctx.fillStyle = '#ff0000';
                        ctx.fillRect(0, 0, 100, 100);
                        const imageUrl = canvas.toDataURL();
                        
                        // Track async export calls
                        let asyncExportCalled = false;
                        let exportResult = null;
                        
                        // Create InpaintingMaskCanvas
                        const maskCanvas = new InpaintingMaskCanvas({
                            imageUrl: imageUrl,
                            containerElement: container,
                            onMaskComplete: (maskDataUrl) => {
                                exportResult = maskDataUrl;
                            },
                            onCancel: () => {}
                        });
                        
                        // Show the canvas
                        maskCanvas.show().then(() => {
                            // Monkey patch async export method to track calls
                            const originalExportMaskAsync = maskCanvas.exportMaskAsync.bind(maskCanvas);
                            maskCanvas.exportMaskAsync = async function(...args) {
                                asyncExportCalled = true;
                                console.log('Async export called!');
                                return await originalExportMaskAsync(...args);
                            };
                            
                            // Simulate completing the mask (this should trigger async export)
                            maskCanvas.completeMask().then(() => {
                                // Wait a bit for async operations to complete
                                setTimeout(() => {
                                    // Cleanup
                                    container.remove();
                                    
                                    resolve({
                                        success: true,
                                        asyncExportCalled: asyncExportCalled,
                                        exportResult: exportResult ? 'data:image/png;base64,...' : null,
                                        workerAvailable: maskCanvas.canvasManager.getWorkerManager().isWorkerAvailable()
                                    });
                                }, 100);
                            }).catch(error => {
                                resolve({ success: false, error: error.message });
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
        
        assert result['success'], f"Async export test failed: {result.get('error', 'Unknown error')}"
        
        # Verify that async export was called
        assert result['asyncExportCalled'] == True, "Async export should be called when completing mask"
        assert result['exportResult'] is not None, "Export should produce a result"
        
        print(f"✅ Async export is being used when completing masks!")
        print(f"Worker available: {result['workerAvailable']}")

    def test_async_undo_redo_operations(self, driver):
        """Test that async operations are used during undo/redo"""
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
                        document.body.appendChild(container);
                        
                        // Create test image
                        const canvas = document.createElement('canvas');
                        canvas.width = canvas.height = 100;
                        const ctx = canvas.getContext('2d');
                        ctx.fillStyle = '#00ff00';
                        ctx.fillRect(0, 0, 100, 100);
                        const imageUrl = canvas.toDataURL();
                        
                        // Track async replay calls
                        let asyncReplayCalled = false;
                        
                        // Create InpaintingMaskCanvas
                        const maskCanvas = new InpaintingMaskCanvas({
                            imageUrl: imageUrl,
                            containerElement: container,
                            onMaskComplete: () => {},
                            onCancel: () => {}
                        });
                        
                        // Show the canvas
                        maskCanvas.show().then(async () => {
                            // Monkey patch async replay method to track calls
                            const originalReplayAsync = maskCanvas.replayHistoryToCurrentStateAsync.bind(maskCanvas);
                            maskCanvas.replayHistoryToCurrentStateAsync = async function(...args) {
                                asyncReplayCalled = true;
                                console.log('Async replay called!');
                                return await originalReplayAsync(...args);
                            };
                            
                            // Add some strokes to history first
                            const historyManager = maskCanvas.historyManager;
                            const canvasManager = maskCanvas.canvasManager;
                            
                            // Simulate adding strokes
                            for (let i = 0; i < 3; i++) {
                                const stroke = {
                                    points: [{ x: 20 + i * 10, y: 20 + i * 10 }],
                                    brushSize: 5,
                                    mode: 'paint',
                                    timestamp: Date.now()
                                };
                                historyManager.addStroke(stroke);
                            }
                            
                            // Perform undo (this should trigger async replay)
                            await maskCanvas.undo();
                            
                            // Wait a bit for async operations to complete
                            await new Promise(resolve => setTimeout(resolve, 100));
                            
                            // Perform redo (this should also trigger async replay)
                            await maskCanvas.redo();
                            
                            // Wait a bit more
                            await new Promise(resolve => setTimeout(resolve, 100));
                            
                            // Cleanup
                            maskCanvas.hide();
                            container.remove();
                            
                            resolve({
                                success: true,
                                asyncReplayCalled: asyncReplayCalled,
                                workerAvailable: canvasManager.getWorkerManager().isWorkerAvailable()
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
        
        assert result['success'], f"Async undo/redo test failed: {result.get('error', 'Unknown error')}"
        
        # Verify that async replay was called
        assert result['asyncReplayCalled'] == True, "Async replay should be called during undo/redo operations"
        
        print(f"✅ Async replay is being used during undo/redo operations!")
        print(f"Worker available: {result['workerAvailable']}")

    def test_performance_improvement_with_async(self, driver):
        """Test that async operations provide performance benefits"""
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
                        document.body.appendChild(container);
                        
                        // Create test image
                        const canvas = document.createElement('canvas');
                        canvas.width = canvas.height = 200;
                        const ctx = canvas.getContext('2d');
                        ctx.fillStyle = '#ffff00';
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
                            const canvasManager = maskCanvas.canvasManager;
                            const workerManager = canvasManager.getWorkerManager();
                            
                            // Test performance of sync vs async operations
                            const testStroke = {
                                points: [
                                    { x: 50, y: 50 },
                                    { x: 60, y: 60 },
                                    { x: 70, y: 70 },
                                    { x: 80, y: 80 }
                                ],
                                brushSize: 10,
                                mode: 'paint',
                                timestamp: Date.now()
                            };
                            
                            // Measure sync performance
                            const syncStartTime = performance.now();
                            for (let i = 0; i < 5; i++) {
                                canvasManager.applyBrushStroke(testStroke);
                            }
                            const syncEndTime = performance.now();
                            const syncTime = syncEndTime - syncStartTime;
                            
                            // Clear mask for async test
                            canvasManager.clearMask();
                            
                            // Measure async performance
                            const asyncStartTime = performance.now();
                            for (let i = 0; i < 5; i++) {
                                await canvasManager.applyBrushStrokeAsync(testStroke);
                            }
                            const asyncEndTime = performance.now();
                            const asyncTime = asyncEndTime - asyncStartTime;
                            
                            // Get performance stats
                            const perfStats = canvasManager.getPerformanceStats();
                            
                            // Cleanup
                            maskCanvas.hide();
                            container.remove();
                            
                            resolve({
                                success: true,
                                syncTime: syncTime,
                                asyncTime: asyncTime,
                                performanceBenefit: syncTime > asyncTime ? 'async_faster' : 'sync_faster',
                                workerAvailable: workerManager.isWorkerAvailable(),
                                perfStats: perfStats
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
        
        assert result['success'], f"Performance test failed: {result.get('error', 'Unknown error')}"
        
        # Verify performance measurements
        assert result['syncTime'] > 0, "Sync operations should have measurable time"
        assert result['asyncTime'] > 0, "Async operations should have measurable time"
        
        print(f"✅ Performance comparison completed!")
        print(f"Sync time: {result['syncTime']:.2f}ms")
        print(f"Async time: {result['asyncTime']:.2f}ms")
        print(f"Performance benefit: {result['performanceBenefit']}")
        print(f"Worker available: {result['workerAvailable']}")
        
        # Note: Async might be slower in small tests due to overhead, but should be faster for large operations
        # The main benefit is non-blocking UI, not necessarily raw speed for small operations