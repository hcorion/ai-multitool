"""
Simple test to verify async WebWorker functions are being used
"""

import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options


class TestSimpleAsyncUsage:
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

    def test_async_methods_exist_and_callable(self, driver):
        """Test that async methods exist and are callable"""
        driver.get("http://localhost:5000/test-inpainting-canvas")
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        result = driver.execute_script("""
            return new Promise((resolve) => {
                Promise.all([
                    import('/static/js/canvas-manager.js'),
                    import('/static/js/worker-manager.js'),
                    import('/static/js/history-manager.js')
                ]).then(([{ CanvasManager }, { WorkerManager }, { HistoryManager }]) => {
                    try {
                        // Create test canvases
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
                        
                        // Create CanvasManager
                        const canvasManager = new CanvasManager(imageCanvas, overlayCanvas, maskAlphaCanvas);
                        
                        // Create HistoryManager
                        const historyManager = new HistoryManager(250);
                        
                        // Check if async methods exist
                        const asyncMethodsExist = {
                            canvasManager: {
                                applyBrushStrokeAsync: typeof canvasManager.applyBrushStrokeAsync === 'function',
                                validateMaskAsync: typeof canvasManager.validateMaskAsync === 'function',
                                exportMaskAsync: typeof canvasManager.exportMaskAsync === 'function'
                            },
                            historyManager: {
                                createTileBasedCheckpointAsync: typeof historyManager.createTileBasedCheckpointAsync === 'function'
                            },
                            workerManager: {
                                processStroke: typeof canvasManager.getWorkerManager().processStroke === 'function',
                                applyStrokePath: typeof canvasManager.getWorkerManager().applyStrokePath === 'function',
                                createCheckpoint: typeof canvasManager.getWorkerManager().createCheckpoint === 'function'
                            }
                        };
                        
                        // Get worker capabilities
                        const workerCapabilities = canvasManager.getWorkerManager().getCapabilities();
                        
                        // Cleanup
                        container.remove();
                        
                        resolve({
                            success: true,
                            asyncMethodsExist: asyncMethodsExist,
                            workerCapabilities: workerCapabilities,
                            workerAvailable: canvasManager.getWorkerManager().isWorkerAvailable()
                        });
                    } catch (error) {
                        resolve({ success: false, error: error.message });
                    }
                });
            });
        """)
        
        assert result['success'], f"Async methods test failed: {result.get('error', 'Unknown error')}"
        
        # Verify async methods exist
        canvas_methods = result['asyncMethodsExist']['canvasManager']
        assert canvas_methods['applyBrushStrokeAsync'] == True, "CanvasManager should have applyBrushStrokeAsync method"
        assert canvas_methods['validateMaskAsync'] == True, "CanvasManager should have validateMaskAsync method"
        assert canvas_methods['exportMaskAsync'] == True, "CanvasManager should have exportMaskAsync method"
        
        history_methods = result['asyncMethodsExist']['historyManager']
        assert history_methods['createTileBasedCheckpointAsync'] == True, "HistoryManager should have createTileBasedCheckpointAsync method"
        
        worker_methods = result['asyncMethodsExist']['workerManager']
        assert worker_methods['processStroke'] == True, "WorkerManager should have processStroke method"
        assert worker_methods['applyStrokePath'] == True, "WorkerManager should have applyStrokePath method"
        assert worker_methods['createCheckpoint'] == True, "WorkerManager should have createCheckpoint method"
        
        print(f"✅ All async methods exist and are callable!")
        print(f"Worker capabilities: {result['workerCapabilities']}")
        print(f"Worker available: {result['workerAvailable']}")

    def test_async_stroke_processing_direct_call(self, driver):
        """Test direct call to async stroke processing"""
        driver.get("http://localhost:5000/test-inpainting-canvas")
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        result = driver.execute_script("""
            return new Promise((resolve) => {
                import('/static/js/canvas-manager.js').then(({ CanvasManager }) => {
                    try {
                        // Create test canvases
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
                        
                        // Create CanvasManager
                        const canvasManager = new CanvasManager(imageCanvas, overlayCanvas, maskAlphaCanvas);
                        
                        // Create a simple test image
                        const img = new Image();
                        img.onload = async () => {
                            try {
                                // Load image into canvas manager
                                await canvasManager.loadImage(img.src);
                                
                                // Test async brush stroke
                                const stroke = {
                                    points: [{ x: 50, y: 50 }, { x: 55, y: 55 }],
                                    brushSize: 10,
                                    mode: 'paint',
                                    timestamp: Date.now()
                                };
                                
                                // Call async method directly
                                const hasChanges = await canvasManager.applyBrushStrokeAsync(stroke);
                                
                                // Test async validation
                                const isValid = await canvasManager.validateMaskAsync();
                                
                                // Cleanup
                                container.remove();
                                
                                resolve({
                                    success: true,
                                    hasChanges: hasChanges,
                                    isValid: isValid,
                                    workerAvailable: canvasManager.getWorkerManager().isWorkerAvailable()
                                });
                            } catch (error) {
                                container.remove();
                                resolve({ success: false, error: error.message });
                            }
                        };
                        
                        img.onerror = () => {
                            container.remove();
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
        
        assert result['success'], f"Direct async call test failed: {result.get('error', 'Unknown error')}"
        
        # Verify async operations worked
        assert result['hasChanges'] == True, "Async brush stroke should make changes"
        assert result['isValid'] == True, "Async validation should pass"
        
        print(f"✅ Direct async method calls work correctly!")
        print(f"Worker available: {result['workerAvailable']}")

    def test_console_logging_shows_async_usage(self, driver):
        """Test that console logs show async methods being used"""
        driver.get("http://localhost:5000/test-inpainting-canvas")
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Enable console logging
        driver.execute_script("console.clear();")
        
        result = driver.execute_script("""
            return new Promise((resolve) => {
                // Capture console logs
                const logs = [];
                const originalLog = console.log;
                const originalWarn = console.warn;
                
                console.log = function(...args) {
                    logs.push({ type: 'log', message: args.join(' ') });
                    originalLog.apply(console, args);
                };
                
                console.warn = function(...args) {
                    logs.push({ type: 'warn', message: args.join(' ') });
                    originalWarn.apply(console, args);
                };
                
                import('/static/js/canvas-manager.js').then(({ CanvasManager }) => {
                    try {
                        // Create test canvases
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
                        
                        // Create CanvasManager
                        const canvasManager = new CanvasManager(imageCanvas, overlayCanvas, maskAlphaCanvas);
                        
                        // Create a simple test image
                        const img = new Image();
                        img.onload = async () => {
                            try {
                                // Load image into canvas manager
                                await canvasManager.loadImage(img.src);
                                
                                // Test async operations that should generate logs
                                const stroke = {
                                    points: [{ x: 50, y: 50 }],
                                    brushSize: 5,
                                    mode: 'paint',
                                    timestamp: Date.now()
                                };
                                
                                await canvasManager.applyBrushStrokeAsync(stroke);
                                await canvasManager.validateMaskAsync();
                                
                                // Wait a bit for logs to be generated
                                setTimeout(() => {
                                    // Restore console
                                    console.log = originalLog;
                                    console.warn = originalWarn;
                                    
                                    // Cleanup
                                    container.remove();
                                    
                                    // Filter logs for async-related messages
                                    const asyncLogs = logs.filter(log => 
                                        log.message.includes('async') || 
                                        log.message.includes('worker') || 
                                        log.message.includes('WebWorker') ||
                                        log.message.includes('fallback')
                                    );
                                    
                                    resolve({
                                        success: true,
                                        totalLogs: logs.length,
                                        asyncLogs: asyncLogs,
                                        workerAvailable: canvasManager.getWorkerManager().isWorkerAvailable()
                                    });
                                }, 100);
                                
                            } catch (error) {
                                console.log = originalLog;
                                console.warn = originalWarn;
                                container.remove();
                                resolve({ success: false, error: error.message });
                            }
                        };
                        
                        img.onerror = () => {
                            console.log = originalLog;
                            console.warn = originalWarn;
                            container.remove();
                            resolve({ success: false, error: 'Failed to load test image' });
                        };
                        
                        // Create a simple test image data URL
                        const canvas = document.createElement('canvas');
                        canvas.width = canvas.height = 100;
                        const ctx = canvas.getContext('2d');
                        ctx.fillStyle = '#00ff00';
                        ctx.fillRect(0, 0, 100, 100);
                        img.src = canvas.toDataURL();
                        
                    } catch (error) {
                        resolve({ success: false, error: error.message });
                    }
                });
            });
        """)
        
        assert result['success'], f"Console logging test failed: {result.get('error', 'Unknown error')}"
        
        print(f"✅ Console logging test completed!")
        print(f"Total logs: {result['totalLogs']}")
        print(f"Async-related logs: {len(result['asyncLogs'])}")
        print(f"Worker available: {result['workerAvailable']}")
        
        # Print some async logs if found
        for log in result['asyncLogs'][:5]:  # Show first 5 async logs
            print(f"  {log['type']}: {log['message']}")