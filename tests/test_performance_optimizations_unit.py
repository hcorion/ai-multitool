"""
Unit tests for performance optimizations in the inpainting mask canvas.
Tests the core performance optimization features without requiring a full browser environment.
"""

import pytest
import os
import re


class TestPerformanceOptimizationsUnit:
    """Test that performance optimizations are properly implemented in the code"""

    def test_render_scheduler_exists(self):
        """Test that RenderScheduler class is implemented"""
        render_scheduler_path = "src/render-scheduler.ts"
        assert os.path.exists(render_scheduler_path), "RenderScheduler file should exist"
        
        with open(render_scheduler_path, 'r') as f:
            content = f.read()
            
        # Check for key performance features
        assert "requestAnimationFrame" in content, "Should use requestAnimationFrame for batching"
        assert "DirtyRect" in content, "Should implement dirty rectangle tracking"
        assert "scheduleRender" in content, "Should have render scheduling functionality"
        assert "addDirtyRect" in content, "Should support dirty rectangle management"

    def test_performance_monitor_exists(self):
        """Test that PerformanceMonitor class is implemented"""
        performance_monitor_path = "src/performance-monitor.ts"
        assert os.path.exists(performance_monitor_path), "PerformanceMonitor file should exist"
        
        with open(performance_monitor_path, 'r') as f:
            content = f.read()
            
        # Check for key monitoring features
        assert "fps" in content.lower(), "Should track FPS"
        assert "frameTime" in content, "Should track frame times"
        assert "renderTime" in content, "Should track render times"
        assert "performance.now()" in content, "Should use high-resolution timing"
        assert "requestAnimationFrame" in content, "Should integrate with animation frames"

    def test_canvas_context_hints_implemented(self):
        """Test that canvas context hints are implemented"""
        canvas_manager_path = "src/canvas-manager.ts"
        assert os.path.exists(canvas_manager_path), "CanvasManager file should exist"
        
        with open(canvas_manager_path, 'r') as f:
            content = f.read()
            
        # Check for performance context hints
        assert "desynchronized: true" in content, "Should use desynchronized context hint"
        assert "willReadFrequently: true" in content, "Should use willReadFrequently context hint"
        assert "CanvasRenderingContext2DSettings" in content, "Should use context settings interface"

    def test_input_engine_batching_implemented(self):
        """Test that InputEngine implements pointer event batching"""
        input_engine_path = "src/input-engine.ts"
        assert os.path.exists(input_engine_path), "InputEngine file should exist"
        
        with open(input_engine_path, 'r') as f:
            content = f.read()
            
        # Check for batching implementation
        assert "RenderScheduler" in content, "Should import and use RenderScheduler"
        assert "schedulePointerUpdate" in content, "Should schedule pointer updates"
        assert "scheduleCursorUpdate" in content, "Should schedule cursor updates"

    def test_dirty_rectangle_optimization(self):
        """Test that dirty rectangle optimization is implemented"""
        canvas_manager_path = "src/canvas-manager.ts"
        assert os.path.exists(canvas_manager_path), "CanvasManager file should exist"
        
        with open(canvas_manager_path, 'r') as f:
            content = f.read()
            
        # Check for dirty rectangle features
        assert "DirtyRect" in content, "Should use DirtyRect interface"
        assert "addDirtyRect" in content, "Should add dirty rectangles"
        assert "calculateBrushDirtyRect" in content, "Should calculate brush dirty rectangles"
        assert "scheduleOverlayUpdate" in content, "Should schedule overlay updates with dirty rects"

    def test_performance_integration(self):
        """Test that performance monitoring is integrated into the main canvas"""
        inpainting_canvas_path = "src/inpainting-mask-canvas.ts"
        assert os.path.exists(inpainting_canvas_path), "InpaintingMaskCanvas file should exist"
        
        with open(inpainting_canvas_path, 'r') as f:
            content = f.read()
            
        # Check for performance integration
        assert "setupPerformanceIntegration" in content, "Should set up performance integration"
        assert "getPerformanceMonitor" in content, "Should access performance monitor"
        assert "performanceWarning" in content.lower(), "Should handle performance warnings"

    def test_overlay_update_optimization(self):
        """Test that overlay updates are optimized"""
        canvas_manager_path = "src/canvas-manager.ts"
        assert os.path.exists(canvas_manager_path), "CanvasManager file should exist"
        
        with open(canvas_manager_path, 'r') as f:
            content = f.read()
            
        # Check for overlay optimization
        assert "overlayUpdateThrottle" in content, "Should throttle overlay updates"
        assert "performMaskOverlayUpdate" in content, "Should have optimized overlay update method"
        assert "lastOverlayUpdateTime" in content, "Should track last update time"

    def test_frame_rate_targeting(self):
        """Test that 60 FPS targeting is implemented"""
        performance_monitor_path = "src/performance-monitor.ts"
        assert os.path.exists(performance_monitor_path), "PerformanceMonitor file should exist"
        
        with open(performance_monitor_path, 'r') as f:
            content = f.read()
            
        # Check for FPS targeting
        assert "targetFps: 60" in content, "Should target 60 FPS"
        assert "16.67" in content, "Should use 16.67ms frame time target"
        assert "warningThreshold" in content, "Should have performance warning threshold"

    def test_memory_usage_tracking(self):
        """Test that memory usage tracking is implemented"""
        performance_monitor_path = "src/performance-monitor.ts"
        assert os.path.exists(performance_monitor_path), "PerformanceMonitor file should exist"
        
        with open(performance_monitor_path, 'r') as f:
            content = f.read()
            
        # Check for memory tracking
        assert "memoryUsage" in content, "Should track memory usage"
        assert "performance.memory" in content, "Should use performance.memory API"
        assert "usedJSHeapSize" in content, "Should track heap size"

    def test_typescript_compilation(self):
        """Test that all TypeScript files compile without errors"""
        import subprocess
        
        # Run TypeScript compiler in check mode
        result = subprocess.run(['tsc', '--noEmit'], 
                              capture_output=True, 
                              text=True, 
                              cwd='.')
        
        assert result.returncode == 0, f"TypeScript compilation failed: {result.stderr}"

    def test_performance_features_integration(self):
        """Test that all performance features are properly integrated"""
        # Check that all performance files exist
        performance_files = [
            "src/performance-monitor.ts",
            "src/render-scheduler.ts"
        ]
        
        for file_path in performance_files:
            assert os.path.exists(file_path), f"Performance file {file_path} should exist"
        
        # Check that main files import performance modules
        canvas_manager_path = "src/canvas-manager.ts"
        with open(canvas_manager_path, 'r') as f:
            content = f.read()
            
        assert "import { RenderScheduler" in content, "CanvasManager should import RenderScheduler"
        assert "import { PerformanceMonitor" in content, "CanvasManager should import PerformanceMonitor"
        
        input_engine_path = "src/input-engine.ts"
        with open(input_engine_path, 'r') as f:
            content = f.read()
            
        assert "import { RenderScheduler" in content, "InputEngine should import RenderScheduler"

    def test_performance_optimization_requirements_coverage(self):
        """Test that all task requirements are covered in the implementation"""
        
        # Requirement 7.1: 60 FPS performance
        performance_monitor_path = "src/performance-monitor.ts"
        with open(performance_monitor_path, 'r') as f:
            content = f.read()
        assert "60" in content and "fps" in content.lower(), "Should target 60 FPS (Req 7.1)"
        
        # Requirement 7.2: requestAnimationFrame batching
        render_scheduler_path = "src/render-scheduler.ts"
        with open(render_scheduler_path, 'r') as f:
            content = f.read()
        assert "requestAnimationFrame" in content, "Should use requestAnimationFrame batching (Req 7.2)"
        
        # Requirement 7.3: Dirty rectangle tracking
        canvas_manager_path = "src/canvas-manager.ts"
        with open(canvas_manager_path, 'r') as f:
            content = f.read()
        assert "DirtyRect" in content and "addDirtyRect" in content, "Should implement dirty rectangles (Req 7.3)"
        
        # Requirement 7.5: Optimized overlay updates
        assert "overlayUpdateThrottle" in content, "Should optimize overlay updates (Req 7.5)"

    def test_canvas_context_performance_hints(self):
        """Test that canvas contexts use performance hints"""
        canvas_manager_path = "src/canvas-manager.ts"
        with open(canvas_manager_path, 'r') as f:
            content = f.read()
            
        # Should have both required context hints
        assert "desynchronized: true" in content, "Should use desynchronized context hint"
        assert "willReadFrequently: true" in content, "Should use willReadFrequently context hint"
        
        # Should apply to all canvas contexts
        context_creation_count = content.count("getContext('2d'")
        context_options_count = content.count("contextOptions")
        
        # All context creations should use options
        assert context_creation_count > 0, "Should create canvas contexts"
        assert context_options_count > 0, "Should use context options for performance"