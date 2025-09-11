"""
Test WebWorker integration with the full inpainting mask canvas system
Tests end-to-end WebWorker functionality in the complete canvas environment
"""

import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options


class TestWebWorkerCanvasIntegration:
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

    def test_canvas_manager_worker_integration(self, driver):
        """Test CanvasManager integration with WorkerManager"""
        driver.get("http://localhost:5000/test-inpainting-canvas")
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        result = driver.execute_script("""
            return new Promise((resolve) => {
                import('/static/js/canvas-manager.js').then(({ CanvasManager }) => {
                    try {
                        // Create test container and canvases
                        const container = document.createElement('div');
                        container.style.width = '100px';
                        container.style.height = '100px';
                        document.body.appendChild(container);
                        
                        const imageCanvas = document.createElement('canvas');
                        const overlayCanvas = document.createElement('canvas');
                        const maskAlphaCanvas = document.createElement('canvas');
                        
                        imageCanvas.width = overlayCanvas.width = maskAlphaCanvas.width = 100;
                        imageCanvas.height = overlayCanvas.height = maskAlphaCanvas.height = 100;
                        
                        container.appendChild(imageCanvas);
                        container.appendChild(overlayCanvas);
                        
                        // Create CanvasManager (which includes WorkerManager)
                        const canvasManager = new CanvasManager(imageCanvas, overlayCanvas, maskAlphaCanvas);
                        
                        // Create a simple test image
                        const img = new Image();
                        img.onload = async () => {
                            try {
                                // Load image into canvas manager
                                await canvasManager.loadImage(img.src);
                                
                                // Get worker manager
                                const workerManager = canvasManager.getWorkerManager();
                                const capabilities = workerManager.getCapabilities();
                                
                                // Test async brush stroke
                                const stroke = {
                                    points: [{ x: 50, y: 50 }, { x: 55, y: 55 }],
                                    brushSize: 10,
                                    mode: 'paint',
                                    timestamp: Date.now()
                                };
                                
                                const hasChanges = await canvasManager.applyBrushStrokeAsync(stroke);
                                
                                // Test async mask validation
                                const isValid = await canvasManager.validateMaskAsync();
                                
                                // Test async mask export
                                const exportResult = await canvasManager.exportMaskAsync();
                                
                                // Get performance stats
                                const perfStats = canvasManager.getPerformanceStats();
                                
                                // Cleanup
                                container.remove();
                                
                                resolve({
                                    success: true,
                                    capabilities: capabilities,
                                    hasChanges: hasChanges,
                                    isValid: isValid,
                                    exportResult: exportResult ? {
                                        width: exportResult.imageWidth,
                                        height: exportResult.imageHeight,
                                        dataLength: exportResult.maskData.length
                                    } : null,
                                    perfStats: perfStats,
                                    workerAvailable: workerManager.isWorkerAvailable()
                                });
                            } catch (error) {
                                resolve({ success: false, error: error.message });
                            }
                        };
                        
                        img.onerror = () => {
                            resolve({ success: false, error: 'Failed to load test image' });
                        };
                        
                        // Create a simple test image data URL
                        const canvas = document.createElement('canvas');
                        canvas.width = canvas.height = 100;
                        const ctx = canvas.getContext('2d');
                        ctx.fillStyle = '#ff0000';
                        ctx.fillRect(0, 0, 100, 100);
                        img.src = canvas.toDataURL();
                        
                    } catch (error) {
                        resolve({ success: false, error: error.message });
                    }
                });
            });
        """)
        
        assert result['success'], f"Canvas-Worker integration test failed: {result.get('error', 'Unknown error')}"
        
        # Verify integration results
        assert 'capabilities' in result, "Should have worker capabilities"
        assert result['hasChanges'] == True, "Async brush stroke should make changes"
        assert result['isValid'] == True, "Mask should be valid after processing"
        
        # Verify export result
        export_result = result['exportResult']
        assert export_result is not None, "Should be able to export mask"
        assert export_result['width'] == 100, "Export should preserve image width"
        assert export_result['height'] == 100, "Export should preserve image height"
        assert export_result['dataLength'] == 10000, "Export should have correct data length"
        
        # Verify performance stats include worker info
        perf_stats = result['perfStats']
        assert 'worker' in perf_stats, "Performance stats should include worker info"
        
        print(f"Canvas-Worker integration successful")
        print(f"Worker available: {result['workerAvailable']}")
        print(f"Worker capabilities: {result['capabilities']}")

    def test_history_manager_worker_integration(self, driver):
        """Test HistoryManager integration with WorkerManager for async checkpoints"""
        driver.get("http://localhost:5000/test-inpainting-canvas")
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        result = driver.execute_script("""
            return new Promise((resolve) => {
                Promise.all([
                    import('/static/js/history-manager.js'),
                    import('/static/js/worker-manager.js')
                ]).then(([{ HistoryManager }, { WorkerManager }]) => {
                    try {
                        // Create WorkerManager and HistoryManager
                        const workerManager = new WorkerManager();
                        const historyManager = new HistoryManager(250, workerManager);
                        
                        // Set image dimensions
                        historyManager.setImageDimensions(128, 128);
                        
                        workerManager.initialize().then(async () => {
                            try {
                                // Create test mask data
                                const maskData = new Uint8Array(128 * 128);
                                maskData.fill(0);
                                
                                // Paint some data
                                for (let y = 30; y < 50; y++) {
                                    for (let x = 30; x < 50; x++) {
                                        maskData[y * 128 + x] = 255;
                                    }
                                }
                                
                                // Test async checkpoint creation
                                const checkpoint = await historyManager.createTileBasedCheckpointAsync(maskData);
                                
                                // Verify checkpoint
                                const isValidCheckpoint = checkpoint && 
                                    checkpoint.tiles && 
                                    checkpoint.tiles.length > 0 &&
                                    checkpoint.imageWidth === 128 &&
                                    checkpoint.imageHeight === 128;
                                
                                // Test checkpoint reconstruction
                                const reconstructedMask = historyManager.reconstructMaskFromCheckpoint(checkpoint);
                                const reconstructionValid = reconstructedMask.length === maskData.length;
                                
                                resolve({
                                    success: true,
                                    checkpointValid: isValidCheckpoint,
                                    tileCount: checkpoint.tiles.length,
                                    reconstructionValid: reconstructionValid,
                                    workerUsed: workerManager.isWorkerAvailable()
                                });
                            } catch (error) {
                                resolve({ success: false, error: error.message });
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
        
        assert result['success'], f"History-Worker integration test failed: {result.get('error', 'Unknown error')}"
        
        # Verify integration results
        assert result['checkpointValid'] == True, "Async checkpoint should be valid"
        assert result['tileCount'] >= 1, "Should have at least one tile with data"
        assert result['reconstructionValid'] == True, "Should be able to reconstruct mask from checkpoint"
        
        print(f"History-Worker integration successful")
        print(f"Worker used: {result['workerUsed']}")
        print(f"Tiles created: {result['tileCount']}")

    def test_full_canvas_worker_performance(self, driver):
        """Test WebWorker performance in full canvas environment"""
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
                        
                        // Show the canvas and test performance
                        maskCanvas.show().then(() => {
                            // Access internal components for testing
                            const canvasManager = maskCanvas.canvasManager;
                            const workerManager = canvasManager.getWorkerManager();
                            
                            // Perform multiple async operations to test performance
                            const performanceTest = async () => {
                                const startTime = performance.now();
                                
                                // Create multiple strokes
                                const strokes = [];
                                for (let i = 0; i < 5; i++) {
                                    const stroke = {
                                        points: [
                                            { x: 50 + i * 10, y: 50 + i * 10 },
                                            { x: 60 + i * 10, y: 60 + i * 10 }
                                        ],
                                        brushSize: 8,
                                        mode: 'paint',
                                        timestamp: Date.now()
                                    };
                                    strokes.push(stroke);
                                    
                                    // Apply stroke asynchronously
                                    await canvasManager.applyBrushStrokeAsync(stroke);
                                }
                                
                                // Validate mask
                                await canvasManager.validateMaskAsync();
                                
                                // Export mask
                                await canvasManager.exportMaskAsync();
                                
                                const endTime = performance.now();
                                const totalTime = endTime - startTime;
                                
                                // Get performance stats
                                const perfStats = canvasManager.getPerformanceStats();
                                
                                return {
                                    totalTime: totalTime,
                                    strokeCount: strokes.length,
                                    perfStats: perfStats,
                                    workerAvailable: workerManager.isWorkerAvailable()
                                };
                            };
                            
                            performanceTest().then(perfResult => {
                                // Cleanup
                                maskCanvas.hide();
                                container.remove();
                                
                                resolve({
                                    success: true,
                                    ...perfResult
                                });
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
        
        assert result['success'], f"Performance test failed: {result.get('error', 'Unknown error')}"
        
        # Verify performance results
        assert result['totalTime'] > 0, "Should have measurable execution time"
        assert result['strokeCount'] == 5, "Should have processed all strokes"
        assert 'perfStats' in result, "Should have performance statistics"
        
        # Performance should be reasonable (less than 5 seconds for 5 strokes)
        assert result['totalTime'] < 5000, f"Performance should be reasonable, got {result['totalTime']}ms"
        
        print(f"Full canvas performance test successful")
        print(f"Total time: {result['totalTime']:.2f}ms for {result['strokeCount']} strokes")
        print(f"Worker available: {result['workerAvailable']}")
        print(f"Average time per stroke: {result['totalTime'] / result['strokeCount']:.2f}ms")

    def test_worker_error_handling(self, driver):
        """Test WebWorker error handling and recovery"""
        driver.get("http://localhost:5000/test-inpainting-canvas")
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        result = driver.execute_script("""
            return new Promise((resolve) => {
                import('/static/js/worker-manager.js').then(({ WorkerManager }) => {
                    try {
                        const workerManager = new WorkerManager();
                        
                        workerManager.initialize().then(() => {
                            // Test with invalid data to trigger error handling
                            const invalidMaskData = null; // This should cause an error
                            
                            workerManager.processStroke(
                                invalidMaskData,
                                100,
                                100,
                                50,
                                50,
                                10,
                                'paint'
                            ).then(result => {
                                // This shouldn't succeed with null data
                                resolve({ success: false, error: 'Should have failed with null data' });
                            }).catch(error => {
                                // Error handling should work
                                resolve({
                                    success: true,
                                    errorHandled: true,
                                    errorMessage: error.message,
                                    workerAvailable: workerManager.isWorkerAvailable()
                                });
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
        
        assert result['success'], f"Error handling test failed: {result.get('error', 'Unknown error')}"
        
        # Verify error handling
        assert result['errorHandled'] == True, "Should handle errors gracefully"
        assert 'errorMessage' in result, "Should provide error message"
        
        print(f"Error handling test successful")
        print(f"Error message: {result['errorMessage']}")

    def test_worker_cleanup(self, driver):
        """Test WebWorker cleanup and resource management"""
        driver.get("http://localhost:5000/test-inpainting-canvas")
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        result = driver.execute_script("""
            return new Promise((resolve) => {
                import('/static/js/worker-manager.js').then(({ WorkerManager }) => {
                    try {
                        const workerManager = new WorkerManager();
                        
                        workerManager.initialize().then(() => {
                            // Get initial stats
                            const initialStats = workerManager.getPerformanceStats();
                            const wasWorkerAvailable = workerManager.isWorkerAvailable();
                            
                            // Cleanup worker
                            workerManager.cleanup();
                            
                            // Get stats after cleanup
                            const finalStats = workerManager.getPerformanceStats();
                            const isWorkerAvailableAfterCleanup = workerManager.isWorkerAvailable();
                            
                            resolve({
                                success: true,
                                wasWorkerAvailable: wasWorkerAvailable,
                                isWorkerAvailableAfterCleanup: isWorkerAvailableAfterCleanup,
                                initialPendingMessages: initialStats.pendingMessages,
                                finalPendingMessages: finalStats.pendingMessages,
                                cleanupSuccessful: !isWorkerAvailableAfterCleanup
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
        
        assert result['success'], f"Cleanup test failed: {result.get('error', 'Unknown error')}"
        
        # Verify cleanup behavior
        assert result['isWorkerAvailableAfterCleanup'] == False, "Worker should not be available after cleanup"
        assert result['finalPendingMessages'] == 0, "Should have no pending messages after cleanup"
        assert result['cleanupSuccessful'] == True, "Cleanup should be successful"
        
        print(f"Cleanup test successful")
        print(f"Worker was available: {result['wasWorkerAvailable']}")
        print(f"Worker available after cleanup: {result['isWorkerAvailableAfterCleanup']}")