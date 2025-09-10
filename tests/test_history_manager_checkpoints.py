"""
Tests for the HistoryManager checkpoint system - tile-based checkpoints and deterministic replay
"""

import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options


class TestHistoryManagerCheckpoints:
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

    def test_tile_based_checkpoint_creation(self, driver):
        """Test tile-based checkpoint creation and reconstruction"""
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
                        
                        // Set image dimensions for tile-based checkpoints
                        const imageWidth = 512;
                        const imageHeight = 512;
                        historyManager.setImageDimensions(imageWidth, imageHeight);
                        
                        // Create test mask data with a pattern
                        const maskData = new Uint8Array(imageWidth * imageHeight);
                        maskData.fill(0);
                        
                        // Create a pattern in the mask (diagonal line)
                        for (let i = 0; i < Math.min(imageWidth, imageHeight); i++) {
                            const index = i * imageWidth + i;
                            if (index < maskData.length) {
                                maskData[index] = 255;
                            }
                        }
                        
                        // Add a stroke first
                        const stroke = {
                            points: [{ x: 10, y: 10 }],
                            brushSize: 15,
                            mode: 'paint',
                            timestamp: Date.now()
                        };
                        historyManager.addStroke(stroke);
                        
                        // Create tile-based checkpoint
                        const checkpoint = historyManager.createTileBasedCheckpoint(maskData);
                        
                        // Verify checkpoint properties
                        if (!checkpoint.tiles || checkpoint.tiles.length === 0) {
                            throw new Error('Checkpoint should have tiles');
                        }
                        if (checkpoint.imageWidth !== imageWidth) {
                            throw new Error('Checkpoint should store image width');
                        }
                        if (checkpoint.imageHeight !== imageHeight) {
                            throw new Error('Checkpoint should store image height');
                        }
                        if (checkpoint.tileSize !== 256) {
                            throw new Error('Checkpoint should use 256x256 tiles');
                        }
                        
                        // Reconstruct mask from checkpoint
                        const reconstructedMask = historyManager.reconstructMaskFromCheckpoint(checkpoint);
                        
                        // Verify reconstruction matches original
                        if (reconstructedMask.length !== maskData.length) {
                            throw new Error('Reconstructed mask should have same length as original');
                        }
                        
                        // Check that the diagonal pattern is preserved
                        let patternMatches = 0;
                        for (let i = 0; i < Math.min(imageWidth, imageHeight); i++) {
                            const index = i * imageWidth + i;
                            if (index < maskData.length && reconstructedMask[index] === 255) {
                                patternMatches++;
                            }
                        }
                        
                        if (patternMatches < Math.min(imageWidth, imageHeight) * 0.9) {
                            throw new Error('Reconstructed mask should preserve the diagonal pattern');
                        }
                        
                        resolve({
                            success: true,
                            message: 'Tile-based checkpoint test passed',
                            tileCount: checkpoint.tiles.length,
                            patternMatches: patternMatches
                        });
                    } catch (error) {
                        resolve({ success: false, error: error.message });
                    }
                });
            });
        """)
        
        assert result['success'], f"Test failed: {result.get('error', 'Unknown error')}"
        print(f"Created checkpoint with {result.get('tileCount', 0)} tiles")

    def test_periodic_checkpoint_creation(self, driver):
        """Test automatic periodic checkpoint creation"""
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
                        
                        // Set image dimensions and checkpoint interval
                        historyManager.setImageDimensions(256, 256);
                        historyManager.setCheckpointInterval(3); // Create checkpoint every 3 strokes
                        
                        // Create test mask data
                        const maskData = new Uint8Array(256 * 256);
                        maskData.fill(128); // Fill with test pattern
                        
                        // Add strokes and check for automatic checkpoint creation
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
                        const stroke3 = {
                            points: [{ x: 30, y: 30 }],
                            brushSize: 25,
                            mode: 'paint',
                            timestamp: Date.now() + 2
                        };
                        
                        // Add first two strokes (no checkpoint should be created yet)
                        historyManager.addStroke(stroke1, maskData);
                        historyManager.addStroke(stroke2, maskData);
                        
                        let debugInfo = historyManager.exportDebugInfo();
                        if (debugInfo.checkpointCount !== 0) {
                            throw new Error('No checkpoint should be created after 2 strokes');
                        }
                        if (debugInfo.strokesSinceLastCheckpoint !== 2) {
                            throw new Error('Should have 2 strokes since last checkpoint');
                        }
                        
                        // Add third stroke (should trigger checkpoint creation)
                        historyManager.addStroke(stroke3, maskData);
                        
                        debugInfo = historyManager.exportDebugInfo();
                        if (debugInfo.checkpointCount !== 1) {
                            throw new Error('One checkpoint should be created after 3 strokes');
                        }
                        if (debugInfo.strokesSinceLastCheckpoint !== 0) {
                            throw new Error('Stroke counter should reset after checkpoint creation');
                        }
                        
                        // Verify checkpoint interval getter/setter
                        if (historyManager.getCheckpointInterval() !== 3) {
                            throw new Error('Checkpoint interval should be 3');
                        }
                        
                        historyManager.setCheckpointInterval(5);
                        if (historyManager.getCheckpointInterval() !== 5) {
                            throw new Error('Checkpoint interval should be updated to 5');
                        }
                        
                        resolve({
                            success: true,
                            message: 'Periodic checkpoint creation test passed'
                        });
                    } catch (error) {
                        resolve({ success: false, error: error.message });
                    }
                });
            });
        """)
        
        assert result['success'], f"Test failed: {result.get('error', 'Unknown error')}"

    def test_deterministic_replay(self, driver):
        """Test deterministic replay from checkpoints produces identical results"""
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
                        
                        // Set image dimensions
                        const imageWidth = 256;
                        const imageHeight = 256;
                        historyManager.setImageDimensions(imageWidth, imageHeight);
                        
                        // Create initial mask data
                        const initialMaskData = new Uint8Array(imageWidth * imageHeight);
                        initialMaskData.fill(0);
                        
                        // Add some strokes
                        const strokes = [
                            {
                                points: [{ x: 10, y: 10 }, { x: 15, y: 15 }],
                                brushSize: 10,
                                mode: 'paint',
                                timestamp: Date.now()
                            },
                            {
                                points: [{ x: 20, y: 20 }, { x: 25, y: 25 }],
                                brushSize: 15,
                                mode: 'erase',
                                timestamp: Date.now() + 1
                            },
                            {
                                points: [{ x: 30, y: 30 }, { x: 35, y: 35 }],
                                brushSize: 20,
                                mode: 'paint',
                                timestamp: Date.now() + 2
                            }
                        ];
                        
                        // Add first stroke to history
                        historyManager.addStroke(strokes[0], initialMaskData);
                        
                        // Create a checkpoint after first stroke
                        const checkpointMaskData = new Uint8Array(initialMaskData);
                        // Simulate applying first stroke to mask data
                        for (let i = 0; i < 100; i++) {
                            checkpointMaskData[i] = 255; // Simulate painted area
                        }
                        
                        const checkpoint = historyManager.createTileBasedCheckpoint(checkpointMaskData);
                        
                        // Add remaining strokes
                        historyManager.addStroke(strokes[1], initialMaskData);
                        historyManager.addStroke(strokes[2], initialMaskData);
                        
                        // Test replay from checkpoint
                        const replayedStrokes = [];
                        const replayCallback = (stroke) => {
                            replayedStrokes.push(stroke);
                        };
                        
                        const reconstructedMask = historyManager.replayFromCheckpoint(
                            checkpoint, 
                            historyManager.getState().currentIndex, 
                            replayCallback
                        );
                        
                        // Verify replay produces expected results
                        if (reconstructedMask.length !== checkpointMaskData.length) {
                            throw new Error('Reconstructed mask should have same length as checkpoint mask');
                        }
                        
                        // Verify strokes to replay
                        const strokesToReplay = historyManager.getStrokesFromCheckpoint(
                            checkpoint, 
                            historyManager.getState().currentIndex
                        );
                        
                        if (strokesToReplay.length !== 2) {
                            throw new Error('Should have 2 strokes to replay from checkpoint');
                        }
                        
                        // Test multiple replays produce identical results
                        const replay1 = historyManager.reconstructMaskFromCheckpoint(checkpoint);
                        const replay2 = historyManager.reconstructMaskFromCheckpoint(checkpoint);
                        
                        // Compare byte by byte
                        let identical = true;
                        for (let i = 0; i < replay1.length; i++) {
                            if (replay1[i] !== replay2[i]) {
                                identical = false;
                                break;
                            }
                        }
                        
                        if (!identical) {
                            throw new Error('Multiple replays should produce identical results');
                        }
                        
                        resolve({
                            success: true,
                            message: 'Deterministic replay test passed',
                            strokesToReplay: strokesToReplay.length,
                            replayedStrokes: replayedStrokes.length
                        });
                    } catch (error) {
                        resolve({ success: false, error: error.message });
                    }
                });
            });
        """)
        
        assert result['success'], f"Test failed: {result.get('error', 'Unknown error')}"

    def test_memory_management_with_tiles(self, driver):
        """Test memory management with tile-based checkpoints"""
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
                        const historyManager = new HistoryManager(5); // Very low memory limit (5MB)
                        
                        // Set image dimensions
                        historyManager.setImageDimensions(512, 512);
                        
                        // Create large mask data
                        const maskData = new Uint8Array(512 * 512);
                        maskData.fill(128);
                        
                        // Add many strokes and checkpoints to test memory management
                        for (let i = 0; i < 20; i++) {
                            const stroke = {
                                points: [{ x: i * 10, y: i * 10 }],
                                brushSize: 15,
                                mode: i % 2 === 0 ? 'paint' : 'erase',
                                timestamp: Date.now() + i
                            };
                            
                            historyManager.addStroke(stroke, maskData);
                            
                            // Create additional checkpoints
                            if (i % 5 === 0) {
                                historyManager.createTileBasedCheckpoint(maskData);
                            }
                        }
                        
                        // Check that memory management worked
                        const memoryUsage = historyManager.getMemoryUsageMB();
                        const maxMemory = historyManager.getMaxMemoryMB();
                        
                        if (memoryUsage > maxMemory * 1.5) {
                            throw new Error(`Memory usage (${memoryUsage}MB) should be close to limit (${maxMemory}MB)`);
                        }
                        
                        // Verify history is still functional
                        const state = historyManager.getState();
                        if (state.strokeCount === 0) {
                            throw new Error('Should still have some strokes after memory management');
                        }
                        
                        // Test that we can still undo/redo
                        if (!state.canUndo) {
                            throw new Error('Should be able to undo after memory management');
                        }
                        
                        const undoneStroke = historyManager.undo();
                        if (!undoneStroke) {
                            throw new Error('Undo should work after memory management');
                        }
                        
                        const redoneStroke = historyManager.redo();
                        if (!redoneStroke) {
                            throw new Error('Redo should work after memory management');
                        }
                        
                        resolve({
                            success: true,
                            message: 'Memory management with tiles test passed',
                            memoryUsage: memoryUsage,
                            maxMemory: maxMemory,
                            strokeCount: state.strokeCount
                        });
                    } catch (error) {
                        resolve({ success: false, error: error.message });
                    }
                });
            });
        """)
        
        assert result['success'], f"Test failed: {result.get('error', 'Unknown error')}"
        print(f"Memory usage: {result.get('memoryUsage', 0):.2f}MB, Max: {result.get('maxMemory', 0)}MB")

    def test_tile_optimization(self, driver):
        """Test that empty tiles are not stored (optimization)"""
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
                        
                        // Set image dimensions
                        const imageWidth = 512;
                        const imageHeight = 512;
                        historyManager.setImageDimensions(imageWidth, imageHeight);
                        
                        // Create mostly empty mask data (only paint a small area)
                        const maskData = new Uint8Array(imageWidth * imageHeight);
                        maskData.fill(0);
                        
                        // Paint only a small 10x10 area in the top-left corner
                        for (let y = 0; y < 10; y++) {
                            for (let x = 0; x < 10; x++) {
                                const index = y * imageWidth + x;
                                maskData[index] = 255;
                            }
                        }
                        
                        // Add a stroke
                        const stroke = {
                            points: [{ x: 5, y: 5 }],
                            brushSize: 10,
                            mode: 'paint',
                            timestamp: Date.now()
                        };
                        historyManager.addStroke(stroke);
                        
                        // Create checkpoint
                        const checkpoint = historyManager.createTileBasedCheckpoint(maskData);
                        
                        // Calculate expected number of tiles for 512x512 image
                        const tilesX = Math.ceil(imageWidth / 256);
                        const tilesY = Math.ceil(imageHeight / 256);
                        const totalPossibleTiles = tilesX * tilesY;
                        
                        // Should have much fewer tiles than total possible (only non-empty ones)
                        if (checkpoint.tiles.length >= totalPossibleTiles) {
                            throw new Error(`Should have fewer tiles (${checkpoint.tiles.length}) than total possible (${totalPossibleTiles})`);
                        }
                        
                        // Should have at least 1 tile (the one with painted area)
                        if (checkpoint.tiles.length === 0) {
                            throw new Error('Should have at least 1 tile with painted area');
                        }
                        
                        // Verify reconstruction still works correctly
                        const reconstructedMask = historyManager.reconstructMaskFromCheckpoint(checkpoint);
                        
                        // Check that the painted area is preserved
                        let paintedPixels = 0;
                        for (let y = 0; y < 10; y++) {
                            for (let x = 0; x < 10; x++) {
                                const index = y * imageWidth + x;
                                if (reconstructedMask[index] === 255) {
                                    paintedPixels++;
                                }
                            }
                        }
                        
                        if (paintedPixels !== 100) {
                            throw new Error(`Should have 100 painted pixels, got ${paintedPixels}`);
                        }
                        
                        resolve({
                            success: true,
                            message: 'Tile optimization test passed',
                            tilesStored: checkpoint.tiles.length,
                            totalPossibleTiles: totalPossibleTiles,
                            paintedPixels: paintedPixels
                        });
                    } catch (error) {
                        resolve({ success: false, error: error.message });
                    }
                });
            });
        """)
        
        assert result['success'], f"Test failed: {result.get('error', 'Unknown error')}"
        print(f"Stored {result.get('tilesStored', 0)} tiles out of {result.get('totalPossibleTiles', 0)} possible")

    def test_checkpoint_compatibility(self, driver):
        """Test compatibility between full checkpoints and tile-based checkpoints"""
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
                        
                        // Set image dimensions
                        const imageWidth = 256;
                        const imageHeight = 256;
                        historyManager.setImageDimensions(imageWidth, imageHeight);
                        
                        // Create test mask data
                        const maskData = new Uint8Array(imageWidth * imageHeight);
                        for (let i = 0; i < maskData.length; i++) {
                            maskData[i] = i % 256; // Create a pattern
                        }
                        
                        // Add a stroke
                        const stroke = {
                            points: [{ x: 10, y: 10 }],
                            brushSize: 15,
                            mode: 'paint',
                            timestamp: Date.now()
                        };
                        historyManager.addStroke(stroke);
                        
                        // Create both types of checkpoints
                        const fullCheckpoint = historyManager.createFullCheckpoint(maskData);
                        const tileCheckpoint = historyManager.createTileBasedCheckpoint(maskData);
                        
                        // Verify both checkpoints can be reconstructed
                        const fullReconstructed = historyManager.reconstructMaskFromCheckpoint(fullCheckpoint);
                        const tileReconstructed = historyManager.reconstructMaskFromCheckpoint(tileCheckpoint);
                        
                        // Compare reconstructed masks
                        if (fullReconstructed.length !== tileReconstructed.length) {
                            throw new Error('Reconstructed masks should have same length');
                        }
                        
                        let differences = 0;
                        for (let i = 0; i < fullReconstructed.length; i++) {
                            if (fullReconstructed[i] !== tileReconstructed[i]) {
                                differences++;
                            }
                        }
                        
                        if (differences > 0) {
                            throw new Error(`Full and tile reconstructions should be identical, found ${differences} differences`);
                        }
                        
                        // Verify checkpoint properties
                        if (!fullCheckpoint.maskData) {
                            throw new Error('Full checkpoint should have maskData');
                        }
                        if (fullCheckpoint.tiles) {
                            throw new Error('Full checkpoint should not have tiles');
                        }
                        
                        if (tileCheckpoint.maskData) {
                            throw new Error('Tile checkpoint should not have maskData');
                        }
                        if (!tileCheckpoint.tiles) {
                            throw new Error('Tile checkpoint should have tiles');
                        }
                        
                        resolve({
                            success: true,
                            message: 'Checkpoint compatibility test passed',
                            differences: differences
                        });
                    } catch (error) {
                        resolve({ success: false, error: error.message });
                    }
                });
            });
        """)
        
        assert result['success'], f"Test failed: {result.get('error', 'Unknown error')}"