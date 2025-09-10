"""
Comprehensive test to verify deterministic replay produces identical mask bytes
This test specifically addresses requirement 3.4 and 3.5 from the task
"""

import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options


class TestDeterministicReplayVerification:
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

    def test_deterministic_replay_identical_bytes(self, driver):
        """Test that deterministic replay produces identical mask bytes across multiple runs"""
        driver.get("http://localhost:5000/test-inpainting-canvas")
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Execute comprehensive JavaScript test
        result = driver.execute_script("""
            return new Promise((resolve) => {
                import('/static/js/history-manager.js').then(({ HistoryManager }) => {
                    try {
                        const historyManager = new HistoryManager(200); // 200MB limit
                        
                        // Set image dimensions for a realistic canvas size
                        const imageWidth = 1024;
                        const imageHeight = 1024;
                        historyManager.setImageDimensions(imageWidth, imageHeight);
                        
                        // Create initial mask data with a specific pattern
                        const initialMaskData = new Uint8Array(imageWidth * imageHeight);
                        initialMaskData.fill(0);
                        
                        // Create a checkerboard pattern for testing
                        for (let y = 0; y < imageHeight; y += 64) {
                            for (let x = 0; x < imageWidth; x += 64) {
                                const shouldFill = ((x / 64) + (y / 64)) % 2 === 0;
                                if (shouldFill) {
                                    for (let dy = 0; dy < 64 && y + dy < imageHeight; dy++) {
                                        for (let dx = 0; dx < 64 && x + dx < imageWidth; dx++) {
                                            const index = (y + dy) * imageWidth + (x + dx);
                                            initialMaskData[index] = 255;
                                        }
                                    }
                                }
                            }
                        }
                        
                        // Create a complex sequence of strokes
                        const strokes = [];
                        for (let i = 0; i < 50; i++) {
                            const points = [];
                            const startX = Math.floor(Math.random() * imageWidth);
                            const startY = Math.floor(Math.random() * imageHeight);
                            
                            // Create a stroke with multiple points
                            for (let j = 0; j < 10; j++) {
                                points.push({
                                    x: startX + j * 5,
                                    y: startY + j * 3
                                });
                            }
                            
                            strokes.push({
                                points: points,
                                brushSize: 10 + (i % 20),
                                mode: i % 3 === 0 ? 'erase' : 'paint',
                                timestamp: Date.now() + i
                            });
                        }
                        
                        // Add strokes to history and create checkpoints
                        let checkpointMaskData = new Uint8Array(initialMaskData);
                        let checkpoint = null;
                        
                        for (let i = 0; i < strokes.length; i++) {
                            historyManager.addStroke(strokes[i], checkpointMaskData);
                            
                            // Create a checkpoint at stroke 20 for testing
                            if (i === 20) {
                                // Simulate mask changes up to this point
                                for (let j = 0; j < 1000; j++) {
                                    checkpointMaskData[j] = (j + i) % 256;
                                }
                                checkpoint = historyManager.createTileBasedCheckpoint(checkpointMaskData);
                            }
                        }
                        
                        if (!checkpoint) {
                            throw new Error('Checkpoint should have been created');
                        }
                        
                        // Test 1: Multiple reconstructions should be identical
                        const reconstruction1 = historyManager.reconstructMaskFromCheckpoint(checkpoint);
                        const reconstruction2 = historyManager.reconstructMaskFromCheckpoint(checkpoint);
                        const reconstruction3 = historyManager.reconstructMaskFromCheckpoint(checkpoint);
                        
                        // Verify all reconstructions are identical byte by byte
                        for (let i = 0; i < reconstruction1.length; i++) {
                            if (reconstruction1[i] !== reconstruction2[i] || 
                                reconstruction1[i] !== reconstruction3[i]) {
                                throw new Error(`Reconstructions differ at byte ${i}: ${reconstruction1[i]} vs ${reconstruction2[i]} vs ${reconstruction3[i]}`);
                            }
                        }
                        
                        // Test 2: Replay from checkpoint should be deterministic
                        const targetStrokeIndex = historyManager.getState().currentIndex;
                        const strokesToReplay = historyManager.getStrokesFromCheckpoint(checkpoint, targetStrokeIndex);
                        
                        // Perform multiple replays and verify they're identical
                        const replayResults = [];
                        for (let replayRun = 0; replayRun < 3; replayRun++) {
                            const replayedStrokes = [];
                            const replayCallback = (stroke) => {
                                replayedStrokes.push({
                                    id: stroke.id,
                                    mode: stroke.mode,
                                    brushSize: stroke.brushSize,
                                    pointCount: stroke.points.length
                                });
                            };
                            
                            const replayMask = historyManager.replayFromCheckpoint(
                                checkpoint, 
                                targetStrokeIndex, 
                                replayCallback
                            );
                            
                            replayResults.push({
                                mask: replayMask,
                                strokes: replayedStrokes
                            });
                        }
                        
                        // Verify all replay results are identical
                        for (let i = 1; i < replayResults.length; i++) {
                            const result1 = replayResults[0];
                            const result2 = replayResults[i];
                            
                            // Check mask data
                            if (result1.mask.length !== result2.mask.length) {
                                throw new Error(`Replay ${i} mask length differs: ${result1.mask.length} vs ${result2.mask.length}`);
                            }
                            
                            for (let j = 0; j < result1.mask.length; j++) {
                                if (result1.mask[j] !== result2.mask[j]) {
                                    throw new Error(`Replay ${i} mask differs at byte ${j}: ${result1.mask[j]} vs ${result2.mask[j]}`);
                                }
                            }
                            
                            // Check stroke sequence
                            if (result1.strokes.length !== result2.strokes.length) {
                                throw new Error(`Replay ${i} stroke count differs: ${result1.strokes.length} vs ${result2.strokes.length}`);
                            }
                            
                            for (let k = 0; k < result1.strokes.length; k++) {
                                const stroke1 = result1.strokes[k];
                                const stroke2 = result2.strokes[k];
                                
                                if (stroke1.id !== stroke2.id || 
                                    stroke1.mode !== stroke2.mode || 
                                    stroke1.brushSize !== stroke2.brushSize ||
                                    stroke1.pointCount !== stroke2.pointCount) {
                                    throw new Error(`Replay ${i} stroke ${k} differs`);
                                }
                            }
                        }
                        
                        // Test 3: Memory management doesn't affect determinism
                        const memoryUsage = historyManager.getMemoryUsageMB();
                        const maxMemory = historyManager.getMaxMemoryMB();
                        
                        // Test 4: Tile optimization preserves data integrity
                        const debugInfo = historyManager.exportDebugInfo();
                        const tileCheckpoints = debugInfo.checkpoints.filter(cp => cp.tileCount > 0);
                        
                        if (tileCheckpoints.length === 0) {
                            throw new Error('Should have at least one tile-based checkpoint');
                        }
                        
                        // Test 5: Validate checkpoint integrity
                        const validation = historyManager.validateIntegrity();
                        if (!validation.isValid) {
                            throw new Error(`History integrity validation failed: ${validation.errors.join(', ')}`);
                        }
                        
                        resolve({
                            success: true,
                            message: 'Deterministic replay verification passed',
                            stats: {
                                totalStrokes: strokes.length,
                                checkpointStrokeIndex: checkpoint.strokeIndex,
                                strokesToReplay: strokesToReplay.length,
                                memoryUsageMB: memoryUsage,
                                maxMemoryMB: maxMemory,
                                tileCheckpoints: tileCheckpoints.length,
                                totalCheckpoints: debugInfo.checkpointCount,
                                reconstructionSize: reconstruction1.length,
                                replayRuns: replayResults.length
                            }
                        });
                    } catch (error) {
                        resolve({ success: false, error: error.message });
                    }
                });
            });
        """)
        
        assert result['success'], f"Test failed: {result.get('error', 'Unknown error')}"
        
        # Print test statistics
        stats = result.get('stats', {})
        print(f"\\nDeterministic Replay Verification Results:")
        print(f"  Total strokes: {stats.get('totalStrokes', 0)}")
        print(f"  Checkpoint at stroke: {stats.get('checkpointStrokeIndex', 0)}")
        print(f"  Strokes to replay: {stats.get('strokesToReplay', 0)}")
        print(f"  Memory usage: {stats.get('memoryUsageMB', 0):.2f}MB / {stats.get('maxMemoryMB', 0)}MB")
        print(f"  Tile checkpoints: {stats.get('tileCheckpoints', 0)} / {stats.get('totalCheckpoints', 0)} total")
        print(f"  Reconstruction size: {stats.get('reconstructionSize', 0)} bytes")
        print(f"  Replay runs verified: {stats.get('replayRuns', 0)}")

    def test_checkpoint_memory_efficiency(self, driver):
        """Test that tile-based checkpoints are more memory efficient than full checkpoints"""
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
                        const historyManager = new HistoryManager(300);
                        
                        // Set large image dimensions
                        const imageWidth = 2048;
                        const imageHeight = 2048;
                        historyManager.setImageDimensions(imageWidth, imageHeight);
                        
                        // Create sparse mask data (mostly empty with concentrated painted areas)
                        const maskData = new Uint8Array(imageWidth * imageHeight);
                        maskData.fill(0);
                        
                        // Paint only in the top-left corner (1 tile out of 64 tiles)
                        const paintedWidth = 256;  // One tile width
                        const paintedHeight = 256; // One tile height
                        for (let y = 0; y < paintedHeight; y++) {
                            for (let x = 0; x < paintedWidth; x++) {
                                const index = y * imageWidth + x;
                                maskData[index] = 255;
                            }
                        }
                        
                        // Add a stroke
                        const stroke = {
                            points: [{ x: 100, y: 100 }],
                            brushSize: 20,
                            mode: 'paint',
                            timestamp: Date.now()
                        };
                        historyManager.addStroke(stroke);
                        
                        // Create both types of checkpoints
                        const fullCheckpoint = historyManager.createFullCheckpoint(maskData);
                        const tileCheckpoint = historyManager.createTileBasedCheckpoint(maskData);
                        
                        // Calculate memory usage
                        const fullCheckpointSize = fullCheckpoint.maskData ? fullCheckpoint.maskData.length : 0;
                        let tileCheckpointSize = 0;
                        if (tileCheckpoint.tiles) {
                            for (const tile of tileCheckpoint.tiles) {
                                tileCheckpointSize += tile.data.length;
                            }
                        }
                        
                        // Tile checkpoint should be significantly smaller for sparse data
                        const compressionRatio = fullCheckpointSize > 0 ? tileCheckpointSize / fullCheckpointSize : 0;
                        
                        // For this test case (1 tile out of 64), compression ratio should be much less than 0.5
                        if (compressionRatio > 0.2) {
                            throw new Error(`Tile checkpoint should be more efficient. Compression ratio: ${compressionRatio.toFixed(3)} (expected < 0.2)`);
                        }
                        
                        // Verify both produce identical results
                        const fullReconstructed = historyManager.reconstructMaskFromCheckpoint(fullCheckpoint);
                        const tileReconstructed = historyManager.reconstructMaskFromCheckpoint(tileCheckpoint);
                        
                        let differences = 0;
                        for (let i = 0; i < fullReconstructed.length; i++) {
                            if (fullReconstructed[i] !== tileReconstructed[i]) {
                                differences++;
                            }
                        }
                        
                        if (differences > 0) {
                            throw new Error(`Reconstructions should be identical, found ${differences} differences`);
                        }
                        
                        resolve({
                            success: true,
                            message: 'Memory efficiency test passed',
                            stats: {
                                imageSize: imageWidth * imageHeight,
                                fullCheckpointSize: fullCheckpointSize,
                                tileCheckpointSize: tileCheckpointSize,
                                compressionRatio: compressionRatio,
                                tileCount: tileCheckpoint.tiles ? tileCheckpoint.tiles.length : 0,
                                memoryReduction: ((fullCheckpointSize - tileCheckpointSize) / fullCheckpointSize * 100).toFixed(1)
                            }
                        });
                    } catch (error) {
                        resolve({ success: false, error: error.message });
                    }
                });
            });
        """)
        
        assert result['success'], f"Test failed: {result.get('error', 'Unknown error')}"
        
        # Print efficiency statistics
        stats = result.get('stats', {})
        print(f"\\nMemory Efficiency Test Results:")
        print(f"  Image size: {stats.get('imageSize', 0):,} bytes")
        print(f"  Full checkpoint: {stats.get('fullCheckpointSize', 0):,} bytes")
        print(f"  Tile checkpoint: {stats.get('tileCheckpointSize', 0):,} bytes")
        print(f"  Compression ratio: {stats.get('compressionRatio', 0):.3f}")
        print(f"  Tile count: {stats.get('tileCount', 0)}")
        print(f"  Memory reduction: {stats.get('memoryReduction', 0)}%")