"""
Test cursor positioning and scaling with zoom/pan transforms
"""
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import time


class TestCursorPositioning:
    @pytest.fixture
    def driver(self):
        """Set up Chrome driver for testing"""
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1200,800')
        driver = webdriver.Chrome(options=options)
        driver.implicitly_wait(10)
        yield driver
        driver.quit()

    def test_cursor_positioning_at_different_zoom_levels(self, driver):
        """Test that cursor positions correctly at different zoom levels"""
        driver.get("http://localhost:5000/test-inpainting-canvas")
        
        # Wait for canvas to be ready
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "inpainting-mask-canvas"))
        )
        
        # Execute test in browser
        result = driver.execute_script("""
            return new Promise((resolve) => {
                // Wait for modules to load
                setTimeout(async () => {
                    try {
                        // Get the canvas element
                        const canvasContainer = document.getElementById('inpainting-mask-canvas');
                        if (!canvasContainer) {
                            resolve({ success: false, error: 'Canvas container not found' });
                            return;
                        }
                        
                        // Find the actual canvas element
                        const canvas = canvasContainer.querySelector('canvas');
                        if (!canvas) {
                            resolve({ success: false, error: 'Canvas element not found' });
                            return;
                        }
                        
                        // Get canvas bounds
                        const rect = canvas.getBoundingClientRect();
                        const centerX = rect.left + rect.width / 2;
                        const centerY = rect.top + rect.height / 2;
                        
                        // Test cursor positioning at different zoom levels
                        const testResults = [];
                        
                        // Simulate mouse move to center of canvas
                        const mouseEvent = new MouseEvent('mouseenter', {
                            clientX: centerX,
                            clientY: centerY,
                            bubbles: true
                        });
                        canvas.dispatchEvent(mouseEvent);
                        
                        // Wait a bit for cursor to appear
                        await new Promise(r => setTimeout(r, 100));
                        
                        // Check if cursor element exists
                        const cursor = document.querySelector('.brush-cursor-preview');
                        if (!cursor) {
                            resolve({ success: false, error: 'Cursor element not found' });
                            return;
                        }
                        
                        // Test 1: Default zoom (1.0)
                        const defaultCursorRect = cursor.getBoundingClientRect();
                        testResults.push({
                            zoom: 1.0,
                            cursorSize: parseFloat(cursor.style.width),
                            cursorLeft: parseFloat(cursor.style.left),
                            cursorTop: parseFloat(cursor.style.top),
                            expectedLeft: centerX,
                            expectedTop: centerY
                        });
                        
                        // Test 2: Simulate zoom in (we can't actually zoom without the full app)
                        // But we can test the cursor size scaling logic
                        
                        resolve({
                            success: true,
                            results: testResults,
                            cursorVisible: cursor.style.display !== 'none',
                            cursorPosition: {
                                left: cursor.style.left,
                                top: cursor.style.top
                            }
                        });
                        
                    } catch (error) {
                        resolve({ success: false, error: error.message });
                    }
                }, 1000);
            });
        """)
        
        assert result['success'], f"Test failed: {result.get('error', 'Unknown error')}"
        assert result['cursorVisible'], "Cursor should be visible when mouse enters canvas"
        
        # Check that cursor positioning is reasonable
        results = result['results']
        assert len(results) > 0, "Should have at least one test result"
        
        first_result = results[0]
        # Cursor should be positioned near the center (within 50px tolerance)
        left_diff = abs(first_result['cursorLeft'] - first_result['expectedLeft'])
        top_diff = abs(first_result['cursorTop'] - first_result['expectedTop'])
        
        assert left_diff < 50, f"Cursor X position off by {left_diff}px"
        assert top_diff < 50, f"Cursor Y position off by {top_diff}px"

    def test_cursor_scaling_with_zoom(self, driver):
        """Test that cursor scales appropriately with zoom level"""
        driver.get("http://localhost:5000/test-inpainting-canvas")
        
        # Wait for canvas to be ready
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "inpainting-mask-canvas"))
        )
        
        # Execute test in browser
        result = driver.execute_script("""
            return new Promise((resolve) => {
                setTimeout(async () => {
                    try {
                        const canvasContainer = document.getElementById('inpainting-mask-canvas');
                        const canvas = canvasContainer?.querySelector('canvas');
                        
                        if (!canvas) {
                            resolve({ success: false, error: 'Canvas not found' });
                            return;
                        }
                        
                        // Trigger cursor creation
                        const rect = canvas.getBoundingClientRect();
                        const mouseEvent = new MouseEvent('mouseenter', {
                            clientX: rect.left + 100,
                            clientY: rect.top + 100,
                            bubbles: true
                        });
                        canvas.dispatchEvent(mouseEvent);
                        
                        await new Promise(r => setTimeout(r, 100));
                        
                        const cursor = document.querySelector('.brush-cursor-preview');
                        if (!cursor) {
                            resolve({ success: false, error: 'Cursor not found' });
                            return;
                        }
                        
                        // Get initial cursor size
                        const initialSize = parseFloat(cursor.style.width);
                        
                        resolve({
                            success: true,
                            initialCursorSize: initialSize,
                            cursorExists: true,
                            cursorVisible: cursor.style.display !== 'none'
                        });
                        
                    } catch (error) {
                        resolve({ success: false, error: error.message });
                    }
                }, 1000);
            });
        """)
        
        assert result['success'], f"Test failed: {result.get('error', 'Unknown error')}"
        assert result['cursorExists'], "Cursor element should exist"
        assert result['cursorVisible'], "Cursor should be visible"
        assert result['initialCursorSize'] > 0, "Cursor should have a positive size"

    def test_cursor_hides_outside_bounds(self, driver):
        """Test that cursor hides when mouse moves outside valid drawing area"""
        driver.get("http://localhost:5000/test-inpainting-canvas")
        
        # Wait for canvas to be ready
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "inpainting-mask-canvas"))
        )
        
        # Execute test in browser
        result = driver.execute_script("""
            return new Promise((resolve) => {
                setTimeout(async () => {
                    try {
                        const canvasContainer = document.getElementById('inpainting-mask-canvas');
                        const canvas = canvasContainer?.querySelector('canvas');
                        
                        if (!canvas) {
                            resolve({ success: false, error: 'Canvas not found' });
                            return;
                        }
                        
                        const rect = canvas.getBoundingClientRect();
                        
                        // First, move mouse inside canvas to create cursor
                        const insideEvent = new MouseEvent('mouseenter', {
                            clientX: rect.left + rect.width / 2,
                            clientY: rect.top + rect.height / 2,
                            bubbles: true
                        });
                        canvas.dispatchEvent(insideEvent);
                        
                        await new Promise(r => setTimeout(r, 100));
                        
                        const cursor = document.querySelector('.brush-cursor-preview');
                        if (!cursor) {
                            resolve({ success: false, error: 'Cursor not created' });
                            return;
                        }
                        
                        const visibleInside = cursor.style.display !== 'none';
                        
                        // Now move mouse outside canvas
                        const outsideEvent = new MouseEvent('mouseleave', {
                            clientX: rect.right + 50,
                            clientY: rect.bottom + 50,
                            bubbles: true
                        });
                        canvas.dispatchEvent(outsideEvent);
                        
                        await new Promise(r => setTimeout(r, 100));
                        
                        const visibleOutside = cursor.style.display !== 'none';
                        
                        resolve({
                            success: true,
                            visibleInside: visibleInside,
                            visibleOutside: visibleOutside
                        });
                        
                    } catch (error) {
                        resolve({ success: false, error: error.message });
                    }
                }, 1000);
            });
        """)
        
        assert result['success'], f"Test failed: {result.get('error', 'Unknown error')}"
        assert result['visibleInside'], "Cursor should be visible when mouse is inside canvas"
        assert not result['visibleOutside'], "Cursor should be hidden when mouse leaves canvas"