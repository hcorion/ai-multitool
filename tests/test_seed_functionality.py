"""
Test seed functionality to ensure seeds from UI are properly passed through.
"""

import pytest
from unittest.mock import Mock, patch
from image_models import create_request_from_form_data, Provider, Operation


class TestSeedFunctionality:
    """Test that seeds are properly extracted and used."""

    def test_seed_extraction_from_form_data(self):
        """Test that seed is correctly extracted from form data."""
        
        # Test with valid seed
        form_data = {
            "prompt": "test prompt",
            "provider": "novelai",
            "operation": "generate",
            "seed": "12345",
            "size": "1024x1024"
        }
        
        request = create_request_from_form_data(form_data)
        assert request.seed == 12345
        
        # Test with zero seed (should remain 0)
        form_data["seed"] = "0"
        request = create_request_from_form_data(form_data)
        assert request.seed == 0
        
        # Test with missing seed (should default to 0)
        form_data_no_seed = {
            "prompt": "test prompt",
            "provider": "novelai",
            "operation": "generate",
            "size": "1024x1024"
        }
        request = create_request_from_form_data(form_data_no_seed)
        assert request.seed == 0
        
        # Test with invalid seed (should default to 0)
        form_data["seed"] = "invalid"
        request = create_request_from_form_data(form_data)
        assert request.seed == 0

    def test_variety_extraction_from_form_data(self):
        """Test that variety flag is correctly extracted from form data."""
        
        form_data = {
            "prompt": "test prompt",
            "provider": "novelai",
            "operation": "generate",
            "seed": "42",
            "variety": "true",
            "size": "1024x1024"
        }
        
        request = create_request_from_form_data(form_data)
        assert request.variety == True
        assert request.seed == 42
        
        # Test variety false
        form_data["variety"] = "false"
        request = create_request_from_form_data(form_data)
        assert request.variety == False
        
        # Test missing variety (should default to False)
        del form_data["variety"]
        request = create_request_from_form_data(form_data)
        assert request.variety == False

    def test_seed_in_all_operation_types(self):
        """Test that seed is included in all operation types."""
        
        base_form_data = {
            "prompt": "test prompt",
            "provider": "novelai",
            "seed": "9999",
            "size": "1024x1024"
        }
        
        # Test generate operation
        form_data = {**base_form_data, "operation": "generate"}
        request = create_request_from_form_data(form_data)
        assert request.seed == 9999
        assert request.operation == Operation.GENERATE
        
        # Test inpaint operation
        form_data = {
            **base_form_data, 
            "operation": "inpaint",
            "base_image_path": "/path/to/base.png",
            "mask_path": "/path/to/mask.png"
        }
        request = create_request_from_form_data(form_data)
        assert request.seed == 9999
        assert request.operation == Operation.INPAINT
        
        # Test img2img operation
        form_data = {
            **base_form_data, 
            "operation": "img2img",
            "base_image_path": "/path/to/base.png",
            "strength": "0.7"
        }
        request = create_request_from_form_data(form_data)
        assert request.seed == 9999
        assert request.operation == Operation.IMG2IMG

    @patch('app.generate_seed_for_provider')
    def test_seed_generation_when_zero_or_missing(self, mock_generate_seed):
        """Test that seed generation is called when seed is 0 or missing."""
        from app import _handle_generation_request
        from image_models import ImageGenerationRequest, Provider, Operation
        
        mock_generate_seed.return_value = 54321
        
        # Test with seed = 0 (should generate new seed)
        request = ImageGenerationRequest(
            prompt="test",
            provider=Provider.NOVELAI,
            operation=Operation.GENERATE,
            seed=0
        )
        
        # Mock the session and generation function
        with patch('app.session', {'username': 'testuser'}):
            with patch('app.generate_novelai_image') as mock_generate:
                mock_generated_data = Mock()
                mock_generated_data.local_image_path = '/path/to/image.png'
                mock_generated_data.image_name = 'image.png'
                mock_generated_data.revised_prompt = 'revised prompt'
                mock_generate.return_value = mock_generated_data
                
                response = _handle_generation_request(request)
                
                # Verify that generate_seed_for_provider was called
                mock_generate_seed.assert_called_once_with('novelai')
                
                # Verify that the generated seed was passed to the generation function
                mock_generate.assert_called_once()
                call_args = mock_generate.call_args
                assert call_args[1]['seed'] == 54321

    @patch('app.generate_seed_for_provider')
    def test_seed_not_generated_when_provided(self, mock_generate_seed):
        """Test that seed generation is NOT called when a valid seed is provided."""
        from app import _handle_generation_request
        from image_models import ImageGenerationRequest, Provider, Operation
        
        # Test with valid seed (should NOT generate new seed)
        request = ImageGenerationRequest(
            prompt="test",
            provider=Provider.NOVELAI,
            operation=Operation.GENERATE,
            seed=12345
        )
        
        # Mock the session and generation function
        with patch('app.session', {'username': 'testuser'}):
            with patch('app.generate_novelai_image') as mock_generate:
                mock_generated_data = Mock()
                mock_generated_data.local_image_path = '/path/to/image.png'
                mock_generated_data.image_name = 'image.png'
                mock_generated_data.revised_prompt = 'revised prompt'
                mock_generate.return_value = mock_generated_data
                
                response = _handle_generation_request(request)
                
                # Verify that generate_seed_for_provider was NOT called
                mock_generate_seed.assert_not_called()
                
                # Verify that the original seed was passed to the generation function
                mock_generate.assert_called_once()
                call_args = mock_generate.call_args
                assert call_args[1]['seed'] == 12345