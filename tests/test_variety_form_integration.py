"""Integration test for variety toggle form parameter."""

import pytest
from unittest.mock import Mock, patch


class TestVarietyFormIntegration:
    """Test variety parameter extraction from form data."""

    @patch('app.session', {'username': 'testuser'})
    @patch('app.generate_novelai_image')
    def test_variety_parameter_extracted_from_form(self, mock_generate):
        """Test that variety parameter is extracted from form and passed to generation function."""
        from app import app
        
        mock_generate.return_value = Mock(
            local_image_path="test.png",
            revised_prompt="test prompt",
            original_prompt="test prompt",
            image_name="test.png",
            metadata={}
        )
        
        with app.test_client() as client:
            # Test with variety enabled
            response = client.post('/', data={
                'provider': 'novelai',
                'prompt': 'test prompt',
                'size': '1024x1024',
                'seed': '42',
                'variety': 'true'
            })
            
            # Verify the function was called with variety=True
            mock_generate.assert_called_once()
            call_args = mock_generate.call_args
            assert call_args.kwargs['variety'] is True
            
            # Reset mock for next test
            mock_generate.reset_mock()
            
            # Test with variety disabled
            response = client.post('/', data={
                'provider': 'novelai',
                'prompt': 'test prompt',
                'size': '1024x1024',
                'seed': '42',
                'variety': 'false'
            })
            
            # Verify the function was called with variety=False
            mock_generate.assert_called_once()
            call_args = mock_generate.call_args
            assert call_args.kwargs['variety'] is False
            
            # Reset mock for next test
            mock_generate.reset_mock()
            
            # Test with variety parameter missing (should default to False)
            response = client.post('/', data={
                'provider': 'novelai',
                'prompt': 'test prompt',
                'size': '1024x1024',
                'seed': '42'
            })
            
            # Verify the function was called with variety=False (default)
            mock_generate.assert_called_once()
            call_args = mock_generate.call_args
            assert call_args.kwargs['variety'] is False