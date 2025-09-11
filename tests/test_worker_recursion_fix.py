"""
Test that the WebWorker recursion issue is fixed
"""

import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options


class TestWorkerRecursionFix:
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

    def test_worker_initialization_no_recursion(self, driver):
        """Test that WorkerManager initialization doesn't cause recursion"""
        driver.get("http://localhost:5000/test-inpainting-canvas")
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        result = driver.execute_script("""
            return new Promise((resolve) => {
                // Set up error tracking
                let recursionError = null;
                let initializationSuccess = false;
                
                // Override console.error to catch recursion errors
                const originalError = console.error;
                console.error = function(...args) {
                    const message = args.join(' ');
                    if (message.includes('recursion') || message.includes('stack overflow')) {
                        recursionError = message;
                    }
                    originalError.apply(console, args);
                };
                
                import('/static/js/worker-manager.js').then(({ WorkerManager }) => {
                    try {
                        const workerManager = new WorkerManager();
                        
                        // Initialize with timeout to catch infinite loops
                        const initPromise = workerManager.initialize();
                        const timeoutPromise = new Promise((_, reject) => {
                            setTimeout(() => reject(new Error('Initialization timeout - possible recursion')), 10000);
                        });
                        
                        Promise.race([initPromise, timeoutPromise])
                            .then(() => {
                                initializationSuccess = true;
                                
                                // Test that we can call methods without recursion
                                const capabilities = workerManager.getCapabilities();
                                const isAvailable = workerManager.isWorkerAvailable();
                                
                                // Restore console.error
                                console.error = originalError;
                                
                                resolve({
                                    success: true,
                                    initializationSuccess: initializationSuccess,
                                    recursionError: recursionError,
                                    capabilities: capabilities,
                                    workerAvailable: isAvailable
                                });
                            })
                            .catch(error => {
                                console.error = originalError;
                                resolve({
                                    success: false,
                                    error: error.message,
                                    recursionError: recursionError,
                                    initializationSuccess: initializationSuccess
                                });
                            });
                        
                    } catch (error) {
                        console.error = originalError;
                        resolve({
                            success: false,
                            error: error.message,
                            recursionError: recursionError,
                            initializationSuccess: initializationSuccess
                        });
                    }
                });
            });
        """)
        
        assert result['success'], f"Worker initialization test failed: {result.get('error', 'Unknown error')}"
        
        # Verify no recursion occurred
        assert result['recursionError'] is None, f"Recursion error detected: {result['recursionError']}"
        
        # Verify initialization completed successfully
        assert result['initializationSuccess'] == True, "Worker initialization should complete successfully"
        
        print(f"✅ WorkerManager initialization completed without recursion!")
        print(f"Worker available: {result['workerAvailable']}")
        print(f"Capabilities: {result['capabilities']}")

    def test_multiple_initializations_safe(self, driver):
        """Test that multiple initialization calls don't cause issues"""
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
                        
                        // Call initialize multiple times rapidly
                        const initPromises = [];
                        for (let i = 0; i < 5; i++) {
                            initPromises.push(workerManager.initialize());
                        }
                        
                        // All should resolve without issues
                        Promise.all(initPromises)
                            .then(() => {
                                // Test that worker is still functional
                                const capabilities = workerManager.getCapabilities();
                                const stats = workerManager.getPerformanceStats();
                                
                                resolve({
                                    success: true,
                                    capabilities: capabilities,
                                    stats: stats,
                                    multipleInitializationsCompleted: true
                                });
                            })
                            .catch(error => {
                                resolve({
                                    success: false,
                                    error: error.message,
                                    multipleInitializationsCompleted: false
                                });
                            });
                        
                    } catch (error) {
                        resolve({
                            success: false,
                            error: error.message,
                            multipleInitializationsCompleted: false
                        });
                    }
                });
            });
        """)
        
        assert result['success'], f"Multiple initialization test failed: {result.get('error', 'Unknown error')}"
        
        # Verify multiple initializations completed
        assert result['multipleInitializationsCompleted'] == True, "Multiple initializations should complete safely"
        
        print(f"✅ Multiple WorkerManager initializations completed safely!")
        print(f"Worker initialized: {result['stats']['isInitialized']}")

    def test_worker_methods_after_initialization(self, driver):
        """Test that worker methods work correctly after initialization"""
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
                        
                        workerManager.initialize()
                            .then(async () => {
                                // Test that methods work without causing recursion
                                const testMaskData = new Uint8Array(50);
                                testMaskData.fill(0);
                                
                                try {
                                    // This should not cause recursion anymore
                                    const validationResult = await workerManager.validateMask(testMaskData);
                                    
                                    resolve({
                                        success: true,
                                        validationWorked: true,
                                        validationResult: {
                                            isValid: validationResult.isValid,
                                            dataLength: validationResult.maskData.length
                                        },
                                        workerAvailable: workerManager.isWorkerAvailable()
                                    });
                                } catch (error) {
                                    resolve({
                                        success: false,
                                        error: error.message,
                                        validationWorked: false
                                    });
                                }
                            })
                            .catch(error => {
                                resolve({
                                    success: false,
                                    error: error.message,
                                    validationWorked: false
                                });
                            });
                        
                    } catch (error) {
                        resolve({
                            success: false,
                            error: error.message,
                            validationWorked: false
                        });
                    }
                });
            });
        """)
        
        assert result['success'], f"Worker methods test failed: {result.get('error', 'Unknown error')}"
        
        # Verify validation worked
        assert result['validationWorked'] == True, "Worker validation should work after initialization"
        
        # Verify validation result
        validation_result = result['validationResult']
        assert validation_result['isValid'] == True, "Empty mask should be valid"
        assert validation_result['dataLength'] == 50, "Validation should return correct data length"
        
        print(f"✅ Worker methods work correctly after initialization!")
        print(f"Worker available: {result['workerAvailable']}")
        print(f"Validation result: {validation_result}")

    def test_browser_console_no_recursion_errors(self, driver):
        """Test that browser console shows no recursion errors"""
        driver.get("http://localhost:5000/test-async-demo")
        
        # Wait for page to load and initialize
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, "worker-status"))
        )
        
        # Wait a bit more for initialization to complete
        import time
        time.sleep(2)
        
        # Get browser console logs
        logs = driver.get_log('browser')
        
        # Filter for error logs
        error_logs = [log for log in logs if log['level'] == 'SEVERE']
        recursion_errors = [log for log in error_logs if 'recursion' in log['message'].lower() or 'stack overflow' in log['message'].lower()]
        
        # Should have no recursion errors
        assert len(recursion_errors) == 0, f"Found recursion errors in console: {recursion_errors}"
        
        print(f"✅ No recursion errors found in browser console!")
        print(f"Total console errors: {len(error_logs)}")
        print(f"Recursion-related errors: {len(recursion_errors)}")
        
        # Print any other errors for debugging (but don't fail the test)
        if error_logs:
            print("Other console errors (not recursion-related):")
            for log in error_logs[:5]:  # Show first 5 errors
                print(f"  {log['level']}: {log['message'][:100]}...")