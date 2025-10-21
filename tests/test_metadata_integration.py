"""Integration test to demonstrate metadata enhancement in agent presets."""

import time
from unittest.mock import patch

import pytest

from app import AgentPreset, ResponsesAPIClient


def test_agent_preset_metadata_enhancement_integration():
    """Integration test showing that agent presets get enhanced with model metadata."""
    
    # Create a test agent preset without metadata
    test_preset = AgentPreset(
        id="coding-assistant",
        name="Coding Assistant", 
        instructions="You are a coding assistant. Help users write clean, efficient code.",
        model="gpt-5-mini",
        default_reasoning_level="high",
        created_at=int(time.time()),
        updated_at=int(time.time()),
    )
    
    # Create ResponsesAPIClient
    with patch('openai.OpenAI') as mock_openai:
        client = ResponsesAPIClient(mock_openai)
        
        # Mock the responses.create method to capture what gets sent
        with patch.object(client.client.responses, 'create') as mock_create:
            mock_create.return_value = {"test": "response"}
            
            # Call create_response with the agent preset instructions
            client.create_response(
                input_text="Write a Python function to sort a list",
                instructions=test_preset.instructions,
                model=test_preset.model,
                reasoning_level="low"  # Override the preset's default
            )
            
            # Verify the call was made
            mock_create.assert_called_once()
            call_kwargs = mock_create.call_args.kwargs
            
            # Check that the instructions were enhanced with metadata
            enhanced_instructions = call_kwargs['instructions']
            
            # Should contain original instructions
            assert "You are a coding assistant" in enhanced_instructions
            assert "Help users write clean, efficient code" in enhanced_instructions
            
            # Should contain model-specific metadata
            assert "Knowledge cutoff: 2024-09-30" in enhanced_instructions
            assert "Current date:" in enhanced_instructions
            
            # Should use the correct model
            assert call_kwargs['model'] == 'gpt-5-mini'
            
            # Should use the overridden reasoning level
            assert 'reasoning' in call_kwargs
            reasoning_config = call_kwargs['reasoning']
            assert reasoning_config['effort'] == 'low'
            
            print("✅ Agent preset instructions successfully enhanced with metadata:")
            print(f"Original: {test_preset.instructions}")
            print(f"Enhanced: {enhanced_instructions}")


def test_default_preset_metadata_enhancement():
    """Test that default preset gets enhanced with metadata."""
    
    with patch('openai.OpenAI') as mock_openai:
        client = ResponsesAPIClient(mock_openai)
        
        # Mock the responses.create method
        with patch.object(client.client.responses, 'create') as mock_create:
            mock_create.return_value = {"test": "response"}
            
            # Call create_response without custom instructions (uses default)
            client.create_response(
                input_text="Hello, how are you?",
                model="gpt-5"
            )
            
            # Verify the call was made
            mock_create.assert_called_once()
            call_kwargs = mock_create.call_args.kwargs
            
            # Check that the default instructions were enhanced
            enhanced_instructions = call_kwargs['instructions']
            
            # Should contain default CodeGPT instructions
            assert "CodeGPT" in enhanced_instructions
            assert "professional software engineer" in enhanced_instructions
            
            # Should contain metadata
            assert "Knowledge cutoff: 2024-09-30" in enhanced_instructions
            assert "Current date:" in enhanced_instructions
            
            print("✅ Default instructions successfully enhanced with metadata:")
            print(f"Enhanced: {enhanced_instructions}")


if __name__ == "__main__":
    test_agent_preset_metadata_enhancement_integration()
    test_default_preset_metadata_enhancement()
    print("🎉 All metadata enhancement tests passed!")