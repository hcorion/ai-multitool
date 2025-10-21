"""Tests for model metadata enhancement in agent instructions."""

import time
from datetime import datetime
from unittest.mock import patch

import pytest

from app import AgentPreset, ResponsesAPIClient


class TestModelMetadata:
    """Test model metadata enhancement functionality."""

    @pytest.fixture
    def responses_client(self):
        """Create a ResponsesAPIClient for testing."""
        # Mock the OpenAI client since we don't need real API calls
        with patch('openai.OpenAI') as mock_client:
            return ResponsesAPIClient(mock_client)

    def test_model_knowledge_cutoffs_defined(self, responses_client):
        """Test that all valid models have knowledge cutoff dates defined."""
        for model in responses_client.VALID_MODELS:
            assert model in responses_client.MODEL_KNOWLEDGE_CUTOFFS
            cutoff = responses_client.MODEL_KNOWLEDGE_CUTOFFS[model]
            assert isinstance(cutoff, str)
            assert len(cutoff) == 10  # YYYY-MM-DD format
            assert cutoff.count('-') == 2

    def test_get_model_metadata(self, responses_client):
        """Test _get_model_metadata method returns correct format."""
        metadata = responses_client._get_model_metadata("gpt-5")
        
        # Check format
        assert "Knowledge cutoff:" in metadata
        assert "Current date:" in metadata
        
        # Check that it contains expected cutoff date
        assert "2024-09-30" in metadata
        
        # Check that it contains today's date
        today = datetime.today().strftime("%Y-%m-%d")
        assert today in metadata

    def test_get_model_metadata_unknown_model(self, responses_client):
        """Test _get_model_metadata with unknown model falls back to default."""
        metadata = responses_client._get_model_metadata("unknown-model")
        
        # Should fall back to default cutoff
        assert "2024-09-30" in metadata
        assert "Knowledge cutoff:" in metadata
        assert "Current date:" in metadata

    def test_enhance_instructions_with_metadata_new_instructions(self, responses_client):
        """Test enhancing instructions that don't have metadata."""
        original_instructions = "You are a helpful assistant."
        enhanced = responses_client._enhance_instructions_with_metadata(original_instructions, "gpt-5")
        
        # Should add metadata at the beginning
        assert "Knowledge cutoff: 2024-09-30" in enhanced
        assert "Current date:" in enhanced
        assert "You are a helpful assistant." in enhanced
        
        # Metadata should come first
        lines = enhanced.split('\n')
        assert "Knowledge cutoff:" in lines[0]

    def test_enhance_instructions_with_metadata_existing_metadata(self, responses_client):
        """Test that existing metadata is not duplicated."""
        original_instructions = """You are a helpful assistant.
Knowledge cutoff: 2024-09-30. Current date: 2024-10-20.
Provide helpful responses."""
        
        enhanced = responses_client._enhance_instructions_with_metadata(original_instructions, "gpt-5")
        
        # Should return unchanged since metadata already exists
        assert enhanced == original_instructions
        
        # Should not have duplicate metadata
        assert enhanced.count("Knowledge cutoff:") == 1
        assert enhanced.count("Current date:") == 1

    def test_enhance_instructions_with_model_identification(self, responses_client):
        """Test enhancing instructions that start with model identification."""
        original_instructions = """You are CodeGPT, a large language model.
You write clean code and provide helpful responses."""
        
        enhanced = responses_client._enhance_instructions_with_metadata(original_instructions, "gpt-5-mini")
        
        lines = enhanced.split('\n')
        # First line should be the model identification
        assert "CodeGPT" in lines[0]
        # Second line should be the metadata
        assert "Knowledge cutoff:" in lines[1]
        # Third line should be the rest of the instructions
        assert "You write clean code" in lines[2]

    def test_agent_preset_instructions_enhanced_in_create_response(self, responses_client):
        """Test that agent preset instructions are enhanced with metadata."""
        # Create a test agent preset
        test_preset = AgentPreset(
            id="test-preset",
            name="Test Assistant",
            instructions="You are a test assistant. Be helpful and accurate.",
            model="gpt-5-pro",
            default_reasoning_level="high",
            created_at=int(time.time()),
            updated_at=int(time.time()),
        )
        
        # Mock the client.responses.create method to capture the parameters
        with patch.object(responses_client.client.responses, 'create') as mock_create:
            mock_create.return_value = {"test": "response"}
            
            # Call create_response with custom instructions
            responses_client.create_response(
                input_text="Test input",
                instructions=test_preset.instructions,
                model=test_preset.model
            )
            
            # Verify that create was called with enhanced instructions
            mock_create.assert_called_once()
            call_args = mock_create.call_args
            instructions = call_args.kwargs['instructions']
            
            # Should contain original instructions
            assert "You are a test assistant" in instructions
            # Should contain metadata
            assert "Knowledge cutoff: 2024-09-30" in instructions
            assert "Current date:" in instructions

    def test_default_instructions_enhanced(self, responses_client):
        """Test that default instructions are enhanced when no custom instructions provided."""
        # Mock the client.responses.create method to capture the parameters
        with patch.object(responses_client.client.responses, 'create') as mock_create:
            mock_create.return_value = {"test": "response"}
            
            # Call create_response without custom instructions
            responses_client.create_response(
                input_text="Test input",
                model="gpt-5"
            )
            
            # Verify that create was called with enhanced default instructions
            mock_create.assert_called_once()
            call_args = mock_create.call_args
            instructions = call_args.kwargs['instructions']
            
            # Should contain default instructions
            assert "CodeGPT" in instructions
            # Should contain metadata
            assert "Knowledge cutoff: 2024-09-30" in instructions
            assert "Current date:" in instructions

    def test_different_models_get_correct_cutoffs(self, responses_client):
        """Test that different models get their specific knowledge cutoff dates."""
        for model in responses_client.VALID_MODELS:
            metadata = responses_client._get_model_metadata(model)
            expected_cutoff = responses_client.MODEL_KNOWLEDGE_CUTOFFS[model]
            assert f"Knowledge cutoff: {expected_cutoff}" in metadata