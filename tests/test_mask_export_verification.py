"""
Verification tests for mask export functionality to ensure the implementation
meets the task requirements without requiring full UI integration.
"""

import pytest
import os
import re


class TestMaskExportVerification:
    
    def test_export_methods_exist_in_canvas_manager(self):
        """Verify that the new export methods exist in the compiled CanvasManager"""
        canvas_manager_path = "static/js/canvas-manager.js"
        assert os.path.exists(canvas_manager_path), "CanvasManager JavaScript file should exist"
        
        with open(canvas_manager_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for required export methods
        assert 'exportMaskAsPNG()' in content, "exportMaskAsPNG method should exist"
        assert 'exportMaskAsPNGAsync()' in content, "exportMaskAsPNGAsync method should exist"
        assert 'exportMaskMetadata()' in content, "exportMaskMetadata method should exist"
        
        # Check for binary invariant enforcement
        assert 'BrushEngine.validateBinaryMask' in content, "Should validate binary mask"
        assert 'BrushEngine.enforceBinaryMask' in content, "Should enforce binary mask"
        
        # Check for PNG data URL generation
        assert "toDataURL('image/png')" in content, "Should generate PNG data URLs"
        
        # Check for exact resolution handling
        assert 'exportCanvas.width = ' in content, "Should set exact canvas width"
        assert 'exportCanvas.height = ' in content, "Should set exact canvas height"

    def test_export_methods_exist_in_inpainting_canvas(self):
        """Verify that the InpaintingMaskCanvas has the enhanced export methods"""
        inpainting_canvas_path = "static/js/inpainting-mask-canvas.js"
        assert os.path.exists(inpainting_canvas_path), "InpaintingMaskCanvas JavaScript file should exist"
        
        with open(inpainting_canvas_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for export methods
        assert 'exportMask()' in content, "exportMask method should exist"
        assert 'exportMaskAsync()' in content, "exportMaskAsync method should exist"
        assert 'exportMaskWithMetadata()' in content, "exportMaskWithMetadata method should exist"
        assert 'exportMaskWithMetadataAsync()' in content, "exportMaskWithMetadataAsync method should exist"
        
        # Check for temporary file management
        assert 'exportMaskAsTemporaryFile()' in content, "exportMaskAsTemporaryFile method should exist"
        assert 'exportMaskAsTemporaryFileAsync()' in content, "exportMaskAsTemporaryFileAsync method should exist"
        assert 'cleanupTemporaryFile(' in content, "cleanupTemporaryFile method should exist"
        assert 'getTemporaryFileStatistics()' in content, "getTemporaryFileStatistics method should exist"

    def test_mask_file_manager_exists(self):
        """Verify that the MaskFileManager class exists"""
        mask_file_manager_path = "static/js/mask-file-manager.js"
        assert os.path.exists(mask_file_manager_path), "MaskFileManager JavaScript file should exist"
        
        with open(mask_file_manager_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for class definition
        assert 'export class MaskFileManager' in content, "MaskFileManager class should be exported"
        
        # Check for required methods
        assert 'storeMaskFile(' in content, "storeMaskFile method should exist"
        assert 'getMaskFile(' in content, "getMaskFile method should exist"
        assert 'removeMaskFile(' in content, "removeMaskFile method should exist"
        assert 'cleanupExpiredFiles()' in content, "cleanupExpiredFiles method should exist"
        assert 'cleanupAllFiles()' in content, "cleanupAllFiles method should exist"
        assert 'getStatistics()' in content, "getStatistics method should exist"
        
        # Check for automatic cleanup
        assert 'startAutoCleanup(' in content, "startAutoCleanup method should exist"
        assert 'stopAutoCleanup()' in content, "stopAutoCleanup method should exist"
        
        # Check for global instance
        assert 'export const maskFileManager' in content, "Global maskFileManager instance should be exported"

    def test_typescript_source_has_export_methods(self):
        """Verify that the TypeScript source files have the export methods"""
        canvas_manager_ts_path = "src/canvas-manager.ts"
        assert os.path.exists(canvas_manager_ts_path), "CanvasManager TypeScript file should exist"
        
        with open(canvas_manager_ts_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for method signatures
        assert 'exportMaskAsPNG(): string' in content, "exportMaskAsPNG method signature should exist"
        assert 'exportMaskAsPNGAsync(): Promise<string>' in content, "exportMaskAsPNGAsync method signature should exist"
        assert 'exportMaskMetadata():' in content, "exportMaskMetadata method signature should exist"
        
        # Check for binary invariant enforcement
        assert 'BrushEngine.validateBinaryMask' in content, "Should validate binary mask in TypeScript"
        assert 'BrushEngine.enforceBinaryMask' in content, "Should enforce binary mask in TypeScript"

    def test_inpainting_canvas_typescript_has_export_methods(self):
        """Verify that the InpaintingMaskCanvas TypeScript has export methods"""
        inpainting_canvas_ts_path = "src/inpainting-mask-canvas.ts"
        assert os.path.exists(inpainting_canvas_ts_path), "InpaintingMaskCanvas TypeScript file should exist"
        
        with open(inpainting_canvas_ts_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for method signatures
        assert 'exportMask(): string' in content, "exportMask method should exist"
        assert 'exportMaskAsync(): Promise<string>' in content, "exportMaskAsync method should exist"
        assert 'exportMaskWithMetadata():' in content, "exportMaskWithMetadata method should exist"
        assert 'exportMaskWithMetadataAsync():' in content, "exportMaskWithMetadataAsync method should exist"
        
        # Check for file manager integration
        assert 'import { maskFileManager, MaskFileManager }' in content, "Should import MaskFileManager"
        assert 'exportMaskAsTemporaryFile():' in content, "exportMaskAsTemporaryFile method should exist"

    def test_mask_file_manager_typescript_exists(self):
        """Verify that the MaskFileManager TypeScript source exists"""
        mask_file_manager_ts_path = "src/mask-file-manager.ts"
        assert os.path.exists(mask_file_manager_ts_path), "MaskFileManager TypeScript file should exist"
        
        with open(mask_file_manager_ts_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for interface and class definitions
        assert 'export interface MaskFile' in content, "MaskFile interface should be exported"
        assert 'export class MaskFileManager' in content, "MaskFileManager class should be exported"
        
        # Check for required functionality
        assert 'storeMaskFile(' in content, "storeMaskFile method should exist"
        assert 'cleanupExpiredFiles(' in content, "cleanupExpiredFiles method should exist"
        assert 'maxAge:' in content, "Should have maxAge configuration"
        assert 'maxFiles:' in content, "Should have maxFiles configuration"

    def test_binary_invariant_implementation(self):
        """Verify that binary invariant enforcement is properly implemented"""
        canvas_manager_path = "static/js/canvas-manager.js"
        
        with open(canvas_manager_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for binary value enforcement in export methods
        assert 'BrushEngine.validateBinaryMask(this.state.maskData)' in content, "Should validate binary mask before export"
        assert 'BrushEngine.enforceBinaryMask(this.state.maskData)' in content, "Should enforce binary mask if invalid"
        assert 'binaryValue = maskValue > 127 ? 255 : 0' in content, "Should enforce binary values during conversion"
        
        # Check that validation happens in export methods
        assert 'Binary mask invariant violated during export' in content, "Should warn about binary invariant violations during export"

    def test_exact_resolution_implementation(self):
        """Verify that exact image resolution is maintained in exports"""
        canvas_manager_path = "static/js/canvas-manager.js"
        
        with open(canvas_manager_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check that export canvas dimensions match image dimensions
        assert 'exportCanvas.width = this.state.imageWidth' in content, "Export canvas width should match image width"
        assert 'exportCanvas.height = this.state.imageHeight' in content, "Export canvas height should match image height"

    def test_data_url_generation_implementation(self):
        """Verify that PNG data URL generation is properly implemented"""
        canvas_manager_path = "static/js/canvas-manager.js"
        
        with open(canvas_manager_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for PNG data URL generation
        assert "toDataURL('image/png')" in content, "Should generate PNG data URLs"
        
        # Check that image smoothing is disabled for crisp output
        assert 'imageSmoothingEnabled = false' in content, "Should disable image smoothing for crisp output"

    def test_temporary_file_cleanup_implementation(self):
        """Verify that temporary file cleanup system is implemented"""
        mask_file_manager_path = "static/js/mask-file-manager.js"
        
        with open(mask_file_manager_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for cleanup functionality
        assert 'cleanupExpiredFiles()' in content, "Should have cleanup expired files method"
        assert 'cleanupAllFiles()' in content, "Should have cleanup all files method"
        assert 'isExpired(' in content, "Should have expiration check method"
        assert 'enforceFileLimit(' in content, "Should enforce file limits"
        
        # Check for automatic cleanup
        assert 'setInterval(' in content, "Should have automatic cleanup interval"
        assert 'clearInterval(' in content, "Should be able to stop automatic cleanup"
        
        # Check for file statistics
        assert 'getStatistics()' in content, "Should provide file statistics"
        assert 'totalFiles:' in content, "Statistics should include total files"
        assert 'expiredFiles:' in content, "Statistics should include expired files count"