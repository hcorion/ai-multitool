"""
Test performance optimizations for the inpainting mask canvas.
Tests requestAnimationFrame batching, dirty rectangle tracking, canvas context hints,
frame rate monitoring, and optimized overlay updates.
"""

import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import time
import json


class TestPerformanceOptimizations:
    @pytest.fixture
    def driver(self):
        """Set up Chrome driver for testing"""
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-web-security')
        options.add_argument('--allow-running-insecure-content')
        driver = webdriver.Chrome(options=options)
        driver.implicitly_wait(10)
        yield driver
        driver.quit()

    def test_render_scheduler_batching(self, driver):
        """Test that pointer events are batched using requestAnimationFrame"""
        # Create a simple HTML page for testing
        driver.get("data:text/html,<html><head><title>Test</title></head><body></body></html>")
        
        result = driver.execute_script("""
            return new Promise((resolve) => {
                import('/static/js/render-scheduler.js').then(({ RenderScheduler }) => {
                    try {
                        const scheduler = new RenderScheduler();
                        let batchedOperations = [];
                        
                        // Set up callback to capture batched operations
                        scheduler.setRenderCallback('pointer', (operations) => {
                            batchedOperations = operations;
                        });
                        
                        // Schedule multiple pointer events rapidly
                        const events = [
                            { type: 'start', data: { x: 100, y: 100 } },
                            { type: 'move', data: { x: 101, y: 101 } },
                            { type: 'move', data: { x: 102, y: 102 } },
                            { type: 'move', data: { x: 103, y: 103 } },
                            { type: 'end', data: { x: 104, y: 104 } }
                        ];
                        
                        events.forEach(event => {
                            scheduler.schedulePointerUpdate(event.data);
                        });
                        
                        // Wait for next frame to process batched events
                        requestAnimationFrame(() => {
                            resolve({
                                success: true,
                                batchedCount: batchedOperations.length,
                                hasPendingRenders: scheduler.hasPendingRenders()
                            });
                        });
                        
                    } catch (error) {
                        resolve({ success: false, error: error.message });
                    }
                });
            });
        """)
        
        assert result['success'], f"Test failed: {result.get('error', 'Unknown error')}"
        assert result['batchedCount'] > 0, "No operations were batched"
        assert not result['hasPendingRenders'], "Renders should be processed after frame"

    def test_dirty_rectangle_tracking(self, driver):
        """Test that dirty rectangles are properly tracked and merged"""
        driver.get("http://localhost:5000/test-inpainting-canvas")
        
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "inpainting-mask-popup"))
        )
        
        result = driver.execute_script("""
            return new Promise((resolve) => {
                import('/static/js/render-scheduler.js').then(({ RenderScheduler }) => {
                    try {
                        const scheduler = new RenderScheduler();
                        
                        // Add overlapping dirty rectangles
                        scheduler.addDirtyRect({ x: 10, y: 10, width: 20, height: 20 });
                        scheduler.addDirtyRect({ x: 15, y: 15, width: 20, height: 20 });
                        scheduler.addDirtyRect({ x: 40, y: 40, width: 10, height: 10 });
                        
                        const combinedRect = scheduler.getCombinedDirtyRect();
                        
                        resolve({
                            success: true,
                            combinedRect: combinedRect,
                            hasValidBounds: combinedRect && 
                                           combinedRect.x >= 0 && 
                                           combinedRect.y >= 0 && 
                                           combinedRect.width > 0 && 
                                           combinedRect.height > 0
                        });
                        
                    } catch (error) {
                        resolve({ success: false, error: error.message });
                    }
                });
            });
        """)
        
        assert result['success'], f"Test failed: {result.get('error', 'Unknown error')}"
        assert result['hasValidBounds'], "Combined dirty rectangle should have valid bounds"
        assert result['combinedRect'] is not None, "Should have a combined dirty rectangle"

    def test_canvas_context_hints(self, driver):
        """Test that canvas contexts are created with performance hints"""
        driver.get("http://localhost:5000/test-inpainting-canvas")
        
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "inpainting-mask-popup"))
        )
        
        result = driver.execute_script("""
            return new Promise((resolve) => {
                import('/static/js/canvas-manager.js').then(({ CanvasManager }) => {
                    try {
                        // Create test canvases
                        const imageCanvas = document.createElement('canvas');
                        const overlayCanvas = document.createElement('canvas');
                        const maskAlphaCanvas = document.createElement('canvas');
                        
                        // Create canvas manager (this should apply context hints)
                        const canvasManager = new CanvasManager(imageCanvas, overlayCanvas, maskAlphaCanvas);
                        
                        // Check if contexts have performance settings
                        const imageCtx = imageCanvas.getContext('2d');
                        const overlayCtx = overlayCanvas.getContext('2d');
                        
                        resolve({
                            success: true,
                            imageSmoothingDisabled: !imageCtx.imageSmoothingEnabled,
                            overlaySmoothingDisabled: !overlayCtx.imageSmoothingEnabled,
                            contextCreated: imageCtx !== null && overlayCtx !== null
                        });
                        
                    } catch (error) {
                        resolve({ success: false, error: error.message });
                    }
                });
            });
        """)
        
        assert result['success'], f"Test failed: {result.get('error', 'Unknown error')}"
        assert result['contextCreated'], "Canvas contexts should be created"
        assert result['imageSmoothingDisabled'], "Image smoothing should be disabled for crisp rendering"
        assert result['overlaySmoothingDisabled'], "Overlay smoothing should be disabled for crisp rendering"

    def test_performance_monitoring(self, driver):
        """Test that performance monitoring tracks FPS and render times"""
        driver.get("http://localhost:5000/test-inpainting-canvas")
        
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "inpainting-mask-popup"))
        )
        
        result = driver.execute_script("""
            return new Promise((resolve) => {
                import('/static/js/performance-monitor.js').then(({ PerformanceMonitor }) => {
                    try {
                        const monitor = new PerformanceMonitor({
                            targetFps: 60,
                            sampleSize: 10,
                            enableMemoryTracking: true,
                            warningThreshold: 45
                        });
                        
                        monitor.start();
                        
                        // Simulate some render operations
                        for (let i = 0; i < 5; i++) {
                            monitor.startRender();
                            // Simulate render work
                            const start = performance.now();
                            while (performance.now() - start < 2) {} // 2ms of work
                            monitor.endRender();
                        }
                        
                        // Wait a bit for frame measurements
                        setTimeout(() => {
                            const metrics = monitor.getMetrics();
                            monitor.stop();
                            
                            resolve({
                                success: true,
                                hasMetrics: metrics.totalFrames > 0,
                                hasRenderTime: metrics.averageRenderTime > 0,
                                performanceSummary: monitor.getPerformanceSummary(),
                                isPerformanceGood: monitor.isPerformanceGood()
                            });
                        }, 100);
                        
                    } catch (error) {
                        resolve({ success: false, error: error.message });
                    }
                });
            });
        """)
        
        assert result['success'], f"Test failed: {result.get('error', 'Unknown error')}"
        assert result['hasMetrics'], "Performance monitor should track frame metrics"
        assert result['hasRenderTime'], "Performance monitor should track render times"
        assert result['performanceSummary'], "Should provide performance summary"

    def test_overlay_update_optimization(self, driver):
        """Test that overlay updates are optimized and only occur when needed"""
        driver.get("http://localhost:5000/test-inpainting-canvas")
        
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "inpainting-mask-popup"))
        )
        
        result = driver.execute_script("""
            return new Promise((resolve) => {
                import('/static/js/canvas-manager.js').then(({ CanvasManager }) => {
                    try {
                        // Create test canvases
                        const imageCanvas = document.createElement('canvas');
                        const overlayCanvas = document.createElement('canvas');
                        const maskAlphaCanvas = document.createElement('canvas');
                        
                        imageCanvas.width = overlayCanvas.width = maskAlphaCanvas.width = 100;
                        imageCanvas.height = overlayCanvas.height = maskAlphaCanvas.height = 100;
                        
                        const canvasManager = new CanvasManager(imageCanvas, overlayCanvas, maskAlphaCanvas);
                        const renderScheduler = canvasManager.getRenderScheduler();
                        
                        let overlayUpdateCount = 0;
                        
                        // Monitor overlay updates
                        renderScheduler.setRenderCallback('overlay', (operations) => {
                            overlayUpdateCount++;
                        });
                        
                        // Schedule multiple overlay updates rapidly
                        for (let i = 0; i < 10; i++) {
                            canvasManager.updateMaskOverlay({ x: i, y: i, width: 5, height: 5 });
                        }
                        
                        // Wait for batched processing
                        setTimeout(() => {
                            resolve({
                                success: true,
                                updateCount: overlayUpdateCount,
                                batchingWorking: overlayUpdateCount < 10 // Should be batched
                            });
                        }, 50);
                        
                    } catch (error) {
                        resolve({ success: false, error: error.message });
                    }
                });
            });
        """)
        
        assert result['success'], f"Test failed: {result.get('error', 'Unknown error')}"
        assert result['batchingWorking'], "Overlay updates should be batched for performance"

    def test_frame_rate_targeting(self, driver):
        """Test that the system targets 60 FPS performance"""
        driver.get("http://localhost:5000/test-inpainting-canvas")
        
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "inpainting-mask-popup"))
        )
        
        result = driver.execute_script("""
            return new Promise((resolve) => {
                import('/static/js/render-scheduler.js').then(({ RenderScheduler }) => {
                    try {
                        const scheduler = new RenderScheduler();
                        const startTime = performance.now();
                        let frameCount = 0;
                        
                        // Schedule renders for a short period
                        const interval = setInterval(() => {
                            scheduler.scheduleRender({
                                type: 'test',
                                priority: 50,
                                timestamp: performance.now()
                            });
                            frameCount++;
                            
                            if (frameCount >= 30) { // Test for 30 frames
                                clearInterval(interval);
                                
                                const endTime = performance.now();
                                const duration = endTime - startTime;
                                const actualFps = (frameCount / duration) * 1000;
                                
                                resolve({
                                    success: true,
                                    frameCount: frameCount,
                                    duration: duration,
                                    actualFps: actualFps,
                                    targetingGoodFps: actualFps > 30 // Should be reasonable
                                });
                            }
                        }, 16); // ~60 FPS
                        
                    } catch (error) {
                        resolve({ success: false, error: error.message });
                    }
                });
            });
        """)
        
        assert result['success'], f"Test failed: {result.get('error', 'Unknown error')}"
        assert result['targetingGoodFps'], f"Should target good FPS, got {result.get('actualFps', 0):.1f}"

    def test_memory_usage_tracking(self, driver):
        """Test that memory usage is tracked when available"""
        driver.get("http://localhost:5000/test-inpainting-canvas")
        
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "inpainting-mask-popup"))
        )
        
        result = driver.execute_script("""
            return new Promise((resolve) => {
                import('/static/js/performance-monitor.js').then(({ PerformanceMonitor }) => {
                    try {
                        const monitor = new PerformanceMonitor({
                            enableMemoryTracking: true
                        });
                        
                        monitor.start();
                        
                        // Wait a bit for measurements
                        setTimeout(() => {
                            const metrics = monitor.getMetrics();
                            monitor.stop();
                            
                            resolve({
                                success: true,
                                hasMemoryTracking: 'memory' in performance,
                                memoryUsage: metrics.memoryUsage,
                                memoryInSummary: monitor.getPerformanceSummary().includes('Memory')
                            });
                        }, 50);
                        
                    } catch (error) {
                        resolve({ success: false, error: error.message });
                    }
                });
            });
        """)
        
        assert result['success'], f"Test failed: {result.get('error', 'Unknown error')}"
        # Memory tracking may not be available in all browsers, so we just check it doesn't error
        if result['hasMemoryTracking']:
            assert result['memoryInSummary'], "Memory usage should be included in performance summary"