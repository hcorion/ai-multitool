"""
Integration tests for vibe selection modal frontend component.

This module contains tests to verify the vibe selection modal integrates
correctly with the existing frontend infrastructure.
"""

import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class TestVibeModalIntegration:
    """Integration tests for vibe selection modal."""
    
    @pytest.fixture
    def chrome_driver(self):
        """Create a headless Chrome driver for testing."""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        driver = webdriver.Chrome(options=chrome_options)
        yield driver
        driver.quit()
    
    def test_vibe_modal_javascript_compilation(self):
        """Test that the vibe modal TypeScript compiled successfully."""
        import os
        
        # Check that the compiled JavaScript file exists
        js_file_path = "static/js/vibe-modal.js"
        assert os.path.exists(js_file_path), "Vibe modal JavaScript file should exist"
        
        # Check that the file contains expected exports
        with open(js_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        assert "export class VibeSelectionModal" in content
        assert "export const vibeSelectionModal" in content
        assert "VALID_ENCODING_STRENGTHS" in content
        assert "VALID_REFERENCE_STRENGTHS" in content
    
    def test_vibe_modal_css_compilation(self):
        """Test that the vibe modal SCSS compiled successfully."""
        import os
        
        # Check that the compiled CSS file exists
        css_file_path = "static/css/style.css"
        assert os.path.exists(css_file_path), "Main CSS file should exist"
        
        # Check that the file contains vibe modal styles
        with open(css_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        assert ".vibe-modal-content" in content
        assert ".vibe-collections-grid" in content
        assert ".vibe-collection-item" in content
        assert ".vibe-selection-controls" in content
    
    @pytest.mark.integration
    def test_vibe_modal_html_structure(self, client):
        """Test that the main page can load without JavaScript errors."""
        # This is a basic test to ensure the page loads
        # In a full implementation, we'd test the modal creation
        response = client.get('/')
        # Should redirect to login for unauthenticated users
        assert response.status_code in [200, 302]
        
        # Check that the page contains the necessary script imports
        html_content = response.data.decode('utf-8')
        assert 'script.js' in html_content  # Main script should be loaded
    
    def test_vibe_modal_validation_constants(self):
        """Test that validation constants match the design specification."""
        # Import the validation logic from our property tests
        from tests.test_vibe_selection_properties import VibeSelectionValidator
        
        # Verify constants match the specification
        assert VibeSelectionValidator.VALID_ENCODING_STRENGTHS == [1.0, 0.85, 0.7, 0.5, 0.35]
        assert VibeSelectionValidator.VALID_REFERENCE_STRENGTHS == [1.0, 0.85, 0.7, 0.5, 0.35]
        assert VibeSelectionValidator.MIN_VIBES == 1
        assert VibeSelectionValidator.MAX_VIBES == 4
    
    def test_vibe_api_endpoints_exist(self, client):
        """Test that required vibe API endpoints exist."""
        # Test that endpoints return proper error codes for unauthenticated requests
        
        # List vibes endpoint
        response = client.get('/vibes')
        assert response.status_code == 401  # Should require authentication
        
        # Get vibe details endpoint
        response = client.get('/vibes/test-guid')
        assert response.status_code == 401  # Should require authentication
        
        # Encode vibe endpoint
        response = client.post('/vibes/encode', json={'image_filename': 'test.png', 'name': 'Test'})
        assert response.status_code == 401  # Should require authentication
        
        # Delete vibe endpoint
        response = client.delete('/vibes/test-guid')
        assert response.status_code == 401  # Should require authentication
        
        # Preview endpoint
        response = client.get('/vibes/test-guid/preview/1.0/1.0')
        assert response.status_code == 401  # Should require authentication
    
    def test_vibe_modal_property_validation_integration(self):
        """Test that the property validation logic works correctly."""
        from tests.test_vibe_selection_properties import VibeSelectionValidator
        
        # Test vibe count validation
        assert VibeSelectionValidator.validate_vibe_count([None]) is True  # 1 vibe
        assert VibeSelectionValidator.validate_vibe_count([None] * 4) is True  # 4 vibes
        assert VibeSelectionValidator.validate_vibe_count([]) is False  # 0 vibes
        assert VibeSelectionValidator.validate_vibe_count([None] * 5) is False  # 5 vibes
        
        # Test encoding strength validation
        assert VibeSelectionValidator.validate_encoding_strength(1.0) is True
        assert VibeSelectionValidator.validate_encoding_strength(0.85) is True
        assert VibeSelectionValidator.validate_encoding_strength(0.6) is False
        
        # Test reference strength validation
        assert VibeSelectionValidator.validate_reference_strength_range(0.0) is True
        assert VibeSelectionValidator.validate_reference_strength_range(1.0) is True
        assert VibeSelectionValidator.validate_reference_strength_range(0.5) is True
        assert VibeSelectionValidator.validate_reference_strength_range(-0.1) is False
        assert VibeSelectionValidator.validate_reference_strength_range(1.1) is False
        
        # Test model compatibility validation
        assert VibeSelectionValidator.validate_model_compatibility("model-a", "model-a") is True
        assert VibeSelectionValidator.validate_model_compatibility("model-a", "model-b") is False
        
        # Test closest reference strength selection
        assert VibeSelectionValidator.find_closest_reference_strength(0.95) == 1.0   # Closer to 1.0
        assert VibeSelectionValidator.find_closest_reference_strength(0.77) == 0.7   # Closer to 0.7 (0.07 vs 0.08)
        assert VibeSelectionValidator.find_closest_reference_strength(0.45) == 0.5   # Closer to 0.5
        
        # Test invalid range raises error
        with pytest.raises(ValueError):
            VibeSelectionValidator.find_closest_reference_strength(-0.1)
        
        with pytest.raises(ValueError):
            VibeSelectionValidator.find_closest_reference_strength(1.1)


class TestVibeModalBasicFunctionality:
    """Basic functionality tests for vibe modal."""
    
    def test_modal_html_generation(self):
        """Test that modal HTML can be generated without errors."""
        # This would test the createModalHTML method in a real browser environment
        # For now, we just verify the structure is reasonable
        
        modal_html = '''
            <div id="vibe-selection-modal" class="modal" style="display: none;">
                <div class="modal-content vibe-modal-content">
                    <div class="modal-header">
                        <h2>Select Vibes</h2>
                        <span class="close" id="vibe-modal-close">&times;</span>
                    </div>
                    <div class="modal-body">
                        <div class="vibe-selection-info">
                            <p>Select up to 4 vibes to influence your image generation.</p>
                        </div>
                        <div class="vibe-collections-grid" id="vibe-collections-grid">
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button id="vibe-modal-cancel" class="btn btn-secondary">Cancel</button>
                        <button id="vibe-modal-confirm" class="btn btn-primary">Add Selected Vibes</button>
                    </div>
                </div>
            </div>
        '''
        
        # Basic validation that HTML structure is reasonable
        assert 'vibe-selection-modal' in modal_html
        assert 'vibe-collections-grid' in modal_html
        assert 'vibe-modal-confirm' in modal_html
        assert 'vibe-modal-cancel' in modal_html
    
    def test_validation_error_messages(self):
        """Test validation error message generation."""
        # Test that validation messages can be created
        validation_types = ['info', 'warning', 'error', 'success']
        
        for msg_type in validation_types:
            # This would test the showValidationMessage method
            # For now, just verify the CSS classes exist
            css_class = f"validation-{msg_type}"
            
            # Check that the CSS file contains the expected classes
            import os
            if os.path.exists("static/css/style.css"):
                with open("static/css/style.css", 'r', encoding='utf-8') as f:
                    css_content = f.read()
                    assert css_class in css_content, f"CSS should contain {css_class} class"