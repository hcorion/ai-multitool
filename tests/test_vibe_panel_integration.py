"""
Integration tests for the Vibe Panel component.

Tests the integration of the vibe panel with the NovelAI generation form,
including HTML structure, CSS compilation, and JavaScript functionality.
"""

import pytest
import os
from pathlib import Path


class TestVibePanelIntegration:
    """Test vibe panel integration with the main application."""
    
    def test_vibe_panel_typescript_compilation(self):
        """Test that vibe-panel.ts compiles to JavaScript without errors."""
        # Check that the TypeScript file exists
        ts_file = Path("src/vibe-panel.ts")
        assert ts_file.exists(), "vibe-panel.ts should exist"
        
        # Check that it compiles to JavaScript
        js_file = Path("static/js/vibe-panel.js")
        assert js_file.exists(), "vibe-panel.ts should compile to vibe-panel.js"
        
        # Check that the compiled JS contains expected exports
        with open(js_file, 'r', encoding='utf-8') as f:
            js_content = f.read()
            assert 'VibePanel' in js_content, "Compiled JS should contain VibePanel class"
            assert 'vibePanel' in js_content, "Compiled JS should export vibePanel instance"
    
    def test_vibe_panel_css_compilation(self):
        """Test that vibe panel styles are compiled into CSS."""
        css_file = Path("static/css/style.css")
        assert css_file.exists(), "CSS file should exist"
        
        with open(css_file, 'r', encoding='utf-8') as f:
            css_content = f.read()
            # Check for vibe panel specific styles
            assert '.vibe-add-section' in css_content, "CSS should contain vibe add section styles"
            assert '.vibe-panel' in css_content, "CSS should contain vibe panel styles"
            assert '.vibe-item' in css_content, "CSS should contain vibe item styles"
            assert '.vibe-thumbnail' in css_content, "CSS should contain vibe thumbnail styles"
    
    def test_script_imports_vibe_panel(self):
        """Test that main script.ts imports the vibe panel."""
        script_file = Path("src/script.ts")
        assert script_file.exists(), "script.ts should exist"
        
        with open(script_file, 'r', encoding='utf-8') as f:
            script_content = f.read()
            assert "import { vibePanel } from './vibe-panel.js'" in script_content, \
                "script.ts should import vibePanel"
    
    def test_vibe_panel_provider_integration(self):
        """Test that vibe panel is integrated with provider switching."""
        script_file = Path("src/script.ts")
        
        with open(script_file, 'r', encoding='utf-8') as f:
            script_content = f.read()
            # Check that vibePanel.show() is called for NovelAI
            assert 'vibePanel.show()' in script_content, \
                "script.ts should call vibePanel.show() for NovelAI"
            # Check that vibePanel.hide() is called for other providers
            assert 'vibePanel.hide()' in script_content, \
                "script.ts should call vibePanel.hide() for other providers"
    
    @pytest.mark.integration
    def test_vibe_panel_html_structure(self, client):
        """Test that vibe panel HTML is properly structured."""
        # This would require authentication, so we'll test the TypeScript structure instead
        ts_file = Path("src/vibe-panel.ts")
        
        with open(ts_file, 'r', encoding='utf-8') as f:
            ts_content = f.read()
            # Check for HTML structure creation
            assert 'vibe-add-section' in ts_content, "Should create vibe add section"
            assert 'vibe-panel' in ts_content, "Should create vibe panel"
            assert 'Add Vibe' in ts_content, "Should have Add Vibe button"
            assert 'Selected Vibes' in ts_content, "Should have Selected Vibes header"


class TestVibePanelFunctionality:
    """Test vibe panel core functionality."""
    
    def test_vibe_panel_class_structure(self):
        """Test that VibePanel class has required methods."""
        ts_file = Path("src/vibe-panel.ts")
        
        with open(ts_file, 'r', encoding='utf-8') as f:
            ts_content = f.read()
            
            # Check for required methods
            required_methods = [
                'addVibe',
                'removeVibe', 
                'updateVibe',
                'render',
                'show',
                'hide',
                'getVibesForGeneration'
            ]
            
            for method in required_methods:
                assert f'public {method}(' in ts_content or f'private {method}(' in ts_content, \
                    f"VibePanel should have {method} method"
    
    def test_vibe_panel_validation_constants(self):
        """Test that vibe panel includes validation constants."""
        ts_file = Path("src/vibe-panel.ts")
        
        with open(ts_file, 'r', encoding='utf-8') as f:
            ts_content = f.read()
            
            # Check for validation constants
            assert 'VALID_ENCODING_STRENGTHS' in ts_content, \
                "Should define valid encoding strengths"
            assert 'maxVibes' in ts_content, \
                "Should define maximum vibe count"
            assert '[1.0, 0.85, 0.7, 0.5, 0.35]' in ts_content, \
                "Should include correct encoding strength values"
    
    def test_vibe_panel_interfaces(self):
        """Test that vibe panel defines required interfaces."""
        ts_file = Path("src/vibe-panel.ts")
        
        with open(ts_file, 'r', encoding='utf-8') as f:
            ts_content = f.read()
            
            # Check for required interfaces
            assert 'interface SelectedVibe' in ts_content, \
                "Should define SelectedVibe interface"
            assert 'interface VibeGenerationParams' in ts_content, \
                "Should define VibeGenerationParams interface"
            
            # Check interface properties
            assert 'reference_image_multiple' in ts_content, \
                "Should include reference_image_multiple in generation params"
            assert 'reference_strength_multiple' in ts_content, \
                "Should include reference_strength_multiple in generation params"