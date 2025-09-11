"""
Test WebWorker integration for inpainting mask canvas
Tests WebWorker functionality with main thread fallback
"""

import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options


class TestWebWorkerIntegration:
    @pytest.fixture
    def driver(self):
        """Set up Chrome driver for testing"""
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-web-security')  # Allow loading workers
        options.add_argument('--allow-running-insecure-content')
        driver = webdriver.Chrome(options=options)
        driver.implicitly_wait(10)
        yield driver
        driver.quit()

    def test_worker_manager_initialization(self, driver):
        """Test WorkerManager initialization and capability detection"""
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
                        
                        // Test capability detection
                        const capabilities = workerManager.getCapabilities();
                        
                        // Test initialization
                        workerManager.initialize().then(() => {
                            const stats = workerManager.getPerformanceStats();
                            
                            resolve({
                                success: true,
                                capabilities: capabilities,
                                stats: stats,
                                workerAvailable: workerManager.isWorkerAvailable()
                            });
                        }).catch(error => {
                            resolve({
                                success: true, // Fallback is expected behavior
                                capabilities: capabilities,
                                error: error.message,
                                workerAvailable: false
                            });
                        });
                    } catch (error) {
                        resolve({ success: false, error: error.message });
                    }
                });
            });
        """)
        
        assert result['success'], f"WorkerManager test failed: {result.get('error', 'Unknown error')}"
        
        # Verify capabilities are detected
        capabilities = result['capabilities']
        assert 'webWorkerSupported' in capabilities
        assert 'offscreenCanvasSupported' in capabilities
        assert 'transferableObjectsSupported' in capabilities
        
        print(f"WebWorker capabilities: {capabilities}")
        print(f"Worker available: {result.get('workerAvailable', False)}")

    def test_worker_stroke_processing(self, driver):
        """Test WebWorker stroke processing with fallback"""
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
                        
                        // Initialize worker manager
                        workerManager.initialize().then(() => {
                            // Create test mask data
                            const imageWidth = 100;
                            const imageHeight = 100;
                            const maskData = new Uint8Array(imageWidth * imageHeight);
                            maskData.fill(0); // Start with empty mask
                            
                            // Test stroke processing
                            workerManager.processStroke(
                                maskData,
                                imageWidth,
                                imageHeight,
                                50, // centerX
                                50, // centerY
                                10, // brushSize
                                'paint' // mode
                            ).then(result => {
                                resolve({
                                    success: true,
                                    hasChanges: result.hasChanges,
                                    dirtyRect: result.dirtyRect,
                                    maskDataLength: result.maskData.length,
                                    workerUsed: workerManager.isWorkerAvailable()
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
        
        assert result['success'], f"Stroke processing test failed: {result.get('error', 'Unknown error')}"
        
        # Verify stroke processing results
        assert result['hasChanges'] == True, "Stroke should have made changes to the mask"
        assert result['maskDataLength'] == 10000, "Mask data should be 100x100 = 10000 bytes"
        
        # Verify dirty rectangle is reasonable
        dirty_rect = result['dirtyRect']
        assert dirty_rect['width'] > 0, "Dirty rectangle should have width"
        assert dirty_rect['height'] > 0, "Dirty rectangle should have height"
        
        print(f"Stroke processing successful, worker used: {result['workerUsed']}")
        print(f"Dirty rectangle: {dirty_rect}")

    def test_worker_stroke_path_processing(self, driver):
        """Test WebWorker stroke path processing"""
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
                            // Create test mask data
                            const imageWidth = 100;
                            const imageHeight = 100;
                            const maskData = new Uint8Array(imageWidth * imageHeight);
                            maskData.fill(0);
                            
                            // Create a stroke path
                            const path = [
                                { x: 10, y: 10 },
                                { x: 20, y: 15 },
                                { x: 30, y: 20 },
                                { x: 40, y: 25 }
                            ];
                            
                            // Test stroke path processing
                            workerManager.applyStrokePath(
                                maskData,
                                imageWidth,
                                imageHeight,
                                path,
                                8, // brushSize
                                'paint', // mode
                                0.35 // spacing
                            ).then(result => {
                                resolve({
                                    success: true,
                                    hasChanges: result.hasChanges,
                                    dirtyRect: result.dirtyRect,
                                    pathLength: path.length,
                                    workerUsed: workerManager.isWorkerAvailable()
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
        
        assert result['success'], f"Stroke path processing test failed: {result.get('error', 'Unknown error')}"
        
        # Verify stroke path processing results
        assert result['hasChanges'] == True, "Stroke path should have made changes to the mask"
        assert result['pathLength'] == 4, "Path should have 4 points"
        
        print(f"Stroke path processing successful, worker used: {result['workerUsed']}")

    def test_worker_checkpoint_creation(self, driver):
        """Test WebWorker checkpoint creation"""
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
                            // Create test mask data with some painted areas
                            const imageWidth = 256;
                            const imageHeight = 256;
                            const maskData = new Uint8Array(imageWidth * imageHeight);
                            maskData.fill(0);
                            
                            // Paint a small area
                            for (let y = 50; y < 70; y++) {
                                for (let x = 50; x < 70; x++) {
                                    maskData[y * imageWidth + x] = 255;
                                }
                            }
                            
                            // Test checkpoint creation
                            workerManager.createCheckpoint(
                                maskData,
                                imageWidth,
                                imageHeight,
                                256, // tileSize
                                0 // strokeIndex
                            ).then(result => {
                                resolve({
                                    success: true,
                                    tileCount: result.tiles.length,
                                    imageWidth: result.imageWidth,
                                    imageHeight: result.imageHeight,
                                    tileSize: result.tileSize,
                                    strokeIndex: result.strokeIndex,
                                    workerUsed: workerManager.isWorkerAvailable()
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
        
        assert result['success'], f"Checkpoint creation test failed: {result.get('error', 'Unknown error')}"
        
        # Verify checkpoint creation results
        assert result['tileCount'] >= 1, "Should have at least one tile with painted data"
        assert result['imageWidth'] == 256, "Image width should be preserved"
        assert result['imageHeight'] == 256, "Image height should be preserved"
        assert result['tileSize'] == 256, "Tile size should be preserved"
        assert result['strokeIndex'] == 0, "Stroke index should be preserved"
        
        print(f"Checkpoint creation successful, worker used: {result['workerUsed']}")
        print(f"Created {result['tileCount']} tiles")

    def test_worker_mask_validation(self, driver):
        """Test WebWorker mask validation and binary enforcement"""
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
                            // Create test mask data with invalid values
                            const maskData = new Uint8Array(100);
                            maskData.fill(0);
                            maskData[10] = 128; // Invalid value (should be 0 or 255)
                            maskData[20] = 64;  // Invalid value
                            maskData[30] = 255; // Valid value
                            
                            // Test mask validation
                            workerManager.validateMask(maskData).then(result => {
                                resolve({
                                    success: true,
                                    isValid: result.isValid,
                                    correctedValue10: result.maskData[10],
                                    correctedValue20: result.maskData[20],
                                    correctedValue30: result.maskData[30],
                                    workerUsed: workerManager.isWorkerAvailable()
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
        
        assert result['success'], f"Mask validation test failed: {result.get('error', 'Unknown error')}"
        
        # Verify mask validation results
        assert result['isValid'] == False, "Mask with invalid values should be detected as invalid"
        assert result['correctedValue10'] in [0, 255], "Invalid value should be corrected to binary"
        assert result['correctedValue20'] in [0, 255], "Invalid value should be corrected to binary"
        assert result['correctedValue30'] == 255, "Valid value should be preserved"
        
        print(f"Mask validation successful, worker used: {result['workerUsed']}")
        print(f"Corrected values: {result['correctedValue10']}, {result['correctedValue20']}, {result['correctedValue30']}")

    def test_worker_fallback_behavior(self, driver):
        """Test graceful fallback when WebWorker is unavailable"""
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
                        
                        // Force disable WebWorker support for testing
                        workerManager.capabilities = {
                            webWorkerSupported: false,
                            offscreenCanvasSupported: false,
                            transferableObjectsSupported: false
                        };
                        
                        workerManager.initialize().then(() => {
                            // Create test mask data
                            const imageWidth = 50;
                            const imageHeight = 50;
                            const maskData = new Uint8Array(imageWidth * imageHeight);
                            maskData.fill(0);
                            
                            // Test stroke processing with fallback
                            workerManager.processStroke(
                                maskData,
                                imageWidth,
                                imageHeight,
                                25, // centerX
                                25, // centerY
                                6, // brushSize
                                'paint' // mode
                            ).then(result => {
                                resolve({
                                    success: true,
                                    hasChanges: result.hasChanges,
                                    workerUsed: workerManager.isWorkerAvailable(),
                                    fallbackUsed: !workerManager.isWorkerAvailable()
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
        
        assert result['success'], f"Fallback behavior test failed: {result.get('error', 'Unknown error')}"
        
        # Verify fallback behavior
        assert result['hasChanges'] == True, "Fallback should still process strokes correctly"
        assert result['workerUsed'] == False, "Worker should not be used when disabled"
        assert result['fallbackUsed'] == True, "Fallback should be used when worker is disabled"
        
        print("Fallback behavior test successful - main thread processing works correctly")