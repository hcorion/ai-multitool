"""
Tests for the HistoryManager class - stroke-based undo/redo functionality
"""

import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options


class TestHistoryManager:
    @pytest.fixture
    def driver(self):
        """Set up Chrome driver for testing"""
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        driver = webdriver.Chrome(options=options)
        driver.implicitly_wait(10)
        yield driver
        driver.quit()

    def test_history_manager_basic_functionality(self, driver):
        """Test basic HistoryManager functionality"""
        driver.get("http://localhost:5000/test-inpainting-canvas")
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Execute JavaScript test
        result = driver.execute_script("""
            return new Promise((resolve) => {
                import('/static/js/history-manager.js').then(({ HistoryManager }) => {
                    try {
                        // Create a HistoryManager instance
                        const historyManager = new HistoryManager(100); // 100MB limit
                        
                        // Test initial state
                        const initialState = historyManager.getState();
                        if (initialState.canUndo !== false) {
                            throw new Error('Initial state should not allow undo');
                        }
                        if (initialState.canRedo !== false) {
                            throw new Error('Initial state should not allow redo');
                        }
                        if (initialState.strokeCount !== 0) {
                            throw new Error('Initial stroke count should be 0');
                        }
                        if (initialState.currentIndex !== -1) {
                            throw new Error('Initial current index should be -1');
                        }
                        
                        resolve({
                            success: true,
                            message: 'HistoryManager basic functionality test passed'
                        });
                    } catch (error) {
                        resolve({ success: false, error: error.message });
                    }
                });
            });
        """)
        
        assert result['success'], f"Test failed: {result.get('error', 'Unknown error')}"

    def test_history_manager_add_stroke(self, driver):
        """Test adding strokes to history"""
        driver.get("http://localhost:5000/test-inpainting-canvas")
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Execute JavaScript test
        result = driver.execute_script("""
            return new Promise((resolve) => {
                import('/static/js/history-manager.js').then(({ HistoryManager }) => {
                    try {
                        const historyManager = new HistoryManager(100);
                        
                        // Create a test stroke
                        const testStroke = {
                            points: [{ x: 10, y: 10 }, { x: 20, y: 20 }],
                            brushSize: 15,
                            mode: 'paint',
                            timestamp: Date.now()
                        };
                        
                        // Add stroke to history
                        const strokeCommand = historyManager.addStroke(testStroke);
                        
                        // Verify stroke command has ID
                        if (!strokeCommand.id || !strokeCommand.id.startsWith('stroke_')) {
                            throw new Error('Stroke command should have ID starting with "stroke_"');
                        }
                        
                        // Verify state after adding stroke
                        const state = historyManager.getState();
                        if (state.strokeCount !== 1) {
                            throw new Error('Stroke count should be 1 after adding stroke');
                        }
                        if (state.currentIndex !== 0) {
                            throw new Error('Current index should be 0 after adding first stroke');
                        }
                        if (!state.canUndo) {
                            throw new Error('Should be able to undo after adding stroke');
                        }
                        if (state.canRedo) {
                            throw new Error('Should not be able to redo after adding stroke');
                        }
                        
                        resolve({
                            success: true,
                            message: 'Add stroke test passed'
                        });
                    } catch (error) {
                        resolve({ success: false, error: error.message });
                    }
                });
            });
        """)
        
        assert result['success'], f"Test failed: {result.get('error', 'Unknown error')}"

    def test_history_manager_undo_redo(self, driver):
        """Test undo and redo functionality"""
        driver.get("http://localhost:5000/test-inpainting-canvas")
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Execute JavaScript test
        result = driver.execute_script("""
            return new Promise((resolve) => {
                import('/static/js/history-manager.js').then(({ HistoryManager }) => {
                    try {
                        const historyManager = new HistoryManager(100);
                        
                        // Add two test strokes
                        const stroke1 = {
                            points: [{ x: 10, y: 10 }],
                            brushSize: 15,
                            mode: 'paint',
                            timestamp: Date.now()
                        };
                        const stroke2 = {
                            points: [{ x: 20, y: 20 }],
                            brushSize: 20,
                            mode: 'erase',
                            timestamp: Date.now() + 1
                        };
                        
                        const cmd1 = historyManager.addStroke(stroke1);
                        const cmd2 = historyManager.addStroke(stroke2);
                        
                        // Test undo
                        const undoneStroke = historyManager.undo();
                        if (!undoneStroke || undoneStroke.id !== cmd2.id) {
                            throw new Error('Undo should return the last added stroke');
                        }
                        
                        let state = historyManager.getState();
                        if (state.currentIndex !== 0) {
                            throw new Error('Current index should be 0 after undo');
                        }
                        if (!state.canRedo) {
                            throw new Error('Should be able to redo after undo');
                        }
                        
                        // Test redo
                        const redoneStroke = historyManager.redo();
                        if (!redoneStroke || redoneStroke.id !== cmd2.id) {
                            throw new Error('Redo should return the undone stroke');
                        }
                        
                        state = historyManager.getState();
                        if (state.currentIndex !== 1) {
                            throw new Error('Current index should be 1 after redo');
                        }
                        if (state.canRedo) {
                            throw new Error('Should not be able to redo after redoing last stroke');
                        }
                        
                        resolve({
                            success: true,
                            message: 'Undo/redo test passed'
                        });
                    } catch (error) {
                        resolve({ success: false, error: error.message });
                    }
                });
            });
        """)
        
        assert result['success'], f"Test failed: {result.get('error', 'Unknown error')}"

    def test_history_manager_clear_redo_on_new_stroke(self, driver):
        """Test that redo history is cleared when new strokes are added"""
        driver.get("http://localhost:5000/test-inpainting-canvas")
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Execute JavaScript test
        result = driver.execute_script("""
            return new Promise((resolve) => {
                import('/static/js/history-manager.js').then(({ HistoryManager }) => {
                    try {
                        const historyManager = new HistoryManager(100);
                        
                        // Add two strokes
                        const stroke1 = {
                            points: [{ x: 10, y: 10 }],
                            brushSize: 15,
                            mode: 'paint',
                            timestamp: Date.now()
                        };
                        const stroke2 = {
                            points: [{ x: 20, y: 20 }],
                            brushSize: 20,
                            mode: 'erase',
                            timestamp: Date.now() + 1
                        };
                        
                        historyManager.addStroke(stroke1);
                        historyManager.addStroke(stroke2);
                        
                        // Undo one stroke
                        historyManager.undo();
                        
                        // Verify we can redo
                        let state = historyManager.getState();
                        if (!state.canRedo) {
                            throw new Error('Should be able to redo after undo');
                        }
                        
                        // Add a new stroke (should clear redo history)
                        const stroke3 = {
                            points: [{ x: 30, y: 30 }],
                            brushSize: 25,
                            mode: 'paint',
                            timestamp: Date.now() + 2
                        };
                        historyManager.addStroke(stroke3);
                        
                        // Verify redo history is cleared
                        state = historyManager.getState();
                        if (state.canRedo) {
                            throw new Error('Redo history should be cleared after adding new stroke');
                        }
                        if (state.strokeCount !== 2) {
                            throw new Error('Stroke count should be 2 after clearing redo history');
                        }
                        
                        resolve({
                            success: true,
                            message: 'Clear redo history test passed'
                        });
                    } catch (error) {
                        resolve({ success: false, error: error.message });
                    }
                });
            });
        """)
        
        assert result['success'], f"Test failed: {result.get('error', 'Unknown error')}"

    def test_history_manager_checkpoints(self, driver):
        """Test checkpoint functionality"""
        driver.get("http://localhost:5000/test-inpainting-canvas")
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Execute JavaScript test
        result = driver.execute_script("""
            return new Promise((resolve) => {
                import('/static/js/history-manager.js').then(({ HistoryManager }) => {
                    try {
                        const historyManager = new HistoryManager(100);
                        
                        // Create test mask data
                        const maskData = new Uint8Array(100 * 100); // 100x100 mask
                        maskData.fill(128); // Fill with test data
                        
                        // Add some strokes first
                        const stroke1 = {
                            points: [{ x: 10, y: 10 }],
                            brushSize: 15,
                            mode: 'paint',
                            timestamp: Date.now()
                        };
                        historyManager.addStroke(stroke1);
                        
                        // Create a checkpoint
                        const checkpoint = historyManager.createCheckpoint(maskData);
                        
                        // Verify checkpoint properties
                        if (!checkpoint.id || !checkpoint.id.startsWith('checkpoint_')) {
                            throw new Error('Checkpoint should have ID starting with "checkpoint_"');
                        }
                        if (checkpoint.strokeIndex !== 0) {
                            throw new Error('Checkpoint stroke index should be 0');
                        }
                        if (checkpoint.maskData.length !== maskData.length) {
                            throw new Error('Checkpoint mask data should have same length as original');
                        }
                        
                        // Test getting nearest checkpoint
                        const nearestCheckpoint = historyManager.getNearestCheckpoint(0);
                        if (!nearestCheckpoint || nearestCheckpoint.id !== checkpoint.id) {
                            throw new Error('Should find the created checkpoint');
                        }
                        
                        // Test getting strokes from checkpoint
                        const stroke2 = {
                            points: [{ x: 20, y: 20 }],
                            brushSize: 20,
                            mode: 'erase',
                            timestamp: Date.now() + 1
                        };
                        historyManager.addStroke(stroke2);
                        
                        const strokesFromCheckpoint = historyManager.getStrokesFromCheckpoint(checkpoint, 1);
                        if (strokesFromCheckpoint.length !== 1) {
                            throw new Error('Should get 1 stroke from checkpoint to index 1');
                        }
                        
                        resolve({
                            success: true,
                            message: 'Checkpoint functionality test passed'
                        });
                    } catch (error) {
                        resolve({ success: false, error: error.message });
                    }
                });
            });
        """)
        
        assert result['success'], f"Test failed: {result.get('error', 'Unknown error')}"

    def test_history_manager_memory_management(self, driver):
        """Test memory management functionality"""
        driver.get("http://localhost:5000/test-inpainting-canvas")
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Execute JavaScript test
        result = driver.execute_script("""
            return new Promise((resolve) => {
                import('/static/js/history-manager.js').then(({ HistoryManager }) => {
                    try {
                        const historyManager = new HistoryManager(1); // Very low memory limit (1MB)
                        
                        // Test memory usage calculation
                        const initialUsage = historyManager.getMemoryUsageMB();
                        if (initialUsage < 0) {
                            throw new Error('Memory usage should be non-negative');
                        }
                        
                        // Test setting memory limit
                        historyManager.setMaxMemoryMB(50);
                        if (historyManager.getMaxMemoryMB() !== 50) {
                            throw new Error('Memory limit should be updated to 50MB');
                        }
                        
                        // Test minimum memory limit enforcement
                        historyManager.setMaxMemoryMB(10); // Below minimum
                        if (historyManager.getMaxMemoryMB() < 50) {
                            throw new Error('Memory limit should be at least 50MB');
                        }
                        
                        resolve({
                            success: true,
                            message: 'Memory management test passed'
                        });
                    } catch (error) {
                        resolve({ success: false, error: error.message });
                    }
                });
            });
        """)
        
        assert result['success'], f"Test failed: {result.get('error', 'Unknown error')}"

    def test_history_manager_validation(self, driver):
        """Test history state validation"""
        driver.get("http://localhost:5000/test-inpainting-canvas")
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Execute JavaScript test
        result = driver.execute_script("""
            return new Promise((resolve) => {
                import('/static/js/history-manager.js').then(({ HistoryManager }) => {
                    try {
                        const historyManager = new HistoryManager(100);
                        
                        // Test validation on empty history
                        let validation = historyManager.validateIntegrity();
                        if (!validation.isValid) {
                            throw new Error('Empty history should be valid');
                        }
                        if (validation.errors.length !== 0) {
                            throw new Error('Empty history should have no errors');
                        }
                        
                        // Add some strokes and test validation
                        const stroke1 = {
                            points: [{ x: 10, y: 10 }],
                            brushSize: 15,
                            mode: 'paint',
                            timestamp: Date.now()
                        };
                        const stroke2 = {
                            points: [{ x: 20, y: 20 }],
                            brushSize: 20,
                            mode: 'erase',
                            timestamp: Date.now() + 1
                        };
                        
                        historyManager.addStroke(stroke1);
                        historyManager.addStroke(stroke2);
                        
                        validation = historyManager.validateIntegrity();
                        if (!validation.isValid) {
                            throw new Error('Valid history should pass validation: ' + validation.errors.join(', '));
                        }
                        
                        // Test debug info export
                        const debugInfo = historyManager.exportDebugInfo();
                        if (debugInfo.strokeCount !== 2) {
                            throw new Error('Debug info should show 2 strokes');
                        }
                        if (debugInfo.currentIndex !== 1) {
                            throw new Error('Debug info should show current index 1');
                        }
                        
                        resolve({
                            success: true,
                            message: 'Validation test passed'
                        });
                    } catch (error) {
                        resolve({ success: false, error: error.message });
                    }
                });
            });
        """)
        
        assert result['success'], f"Test failed: {result.get('error', 'Unknown error')}"

    def test_history_manager_clear(self, driver):
        """Test clearing history"""
        driver.get("http://localhost:5000/test-inpainting-canvas")
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Execute JavaScript test
        result = driver.execute_script("""
            return new Promise((resolve) => {
                import('/static/js/history-manager.js').then(({ HistoryManager }) => {
                    try {
                        const historyManager = new HistoryManager(100);
                        
                        // Add some strokes and checkpoints
                        const stroke1 = {
                            points: [{ x: 10, y: 10 }],
                            brushSize: 15,
                            mode: 'paint',
                            timestamp: Date.now()
                        };
                        historyManager.addStroke(stroke1);
                        
                        const maskData = new Uint8Array(100);
                        historyManager.createCheckpoint(maskData);
                        
                        // Verify history has content
                        let state = historyManager.getState();
                        if (state.strokeCount === 0) {
                            throw new Error('History should have strokes before clear');
                        }
                        
                        // Clear history
                        historyManager.clear();
                        
                        // Verify history is cleared
                        state = historyManager.getState();
                        if (state.strokeCount !== 0) {
                            throw new Error('Stroke count should be 0 after clear');
                        }
                        if (state.currentIndex !== -1) {
                            throw new Error('Current index should be -1 after clear');
                        }
                        if (state.canUndo || state.canRedo) {
                            throw new Error('Should not be able to undo/redo after clear');
                        }
                        
                        const debugInfo = historyManager.exportDebugInfo();
                        if (debugInfo.checkpointCount !== 0) {
                            throw new Error('Checkpoint count should be 0 after clear');
                        }
                        
                        resolve({
                            success: true,
                            message: 'Clear history test passed'
                        });
                    } catch (error) {
                        resolve({ success: false, error: error.message });
                    }
                });
            });
        """)
        
        assert result['success'], f"Test failed: {result.get('error', 'Unknown error')}"