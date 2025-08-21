"""
Shared pytest fixtures and configuration for the AI Multitool test suite.

This module provides common fixtures for testing Flask endpoints, API clients,
and image processing functionality with proper environment variable loading.
"""

import pytest
import os
import tempfile
from unittest.mock import Mock, patch
from flask import Flask

# Mock OpenAI client before importing app to avoid initialization errors
with patch('openai.OpenAI'):
    from app import app


@pytest.fixture
def client():
    """Flask test client fixture for testing endpoints."""
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.test_client() as client:
        with app.app_context():
            yield client


@pytest.fixture
def temp_dir():
    """Temporary directory fixture for file operations during tests."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing without making actual API calls."""
    with patch('openai.OpenAI') as mock_client:
        mock_instance = Mock()
        mock_client.return_value = mock_instance
        
        # Mock image generation response
        mock_response = Mock()
        mock_response.data = [Mock(url="https://example.com/test-image.png")]
        mock_instance.images.generate.return_value = mock_response
        
        yield mock_instance


@pytest.fixture
def sample_image_data():
    """Sample image data for testing image processing functions."""
    # Create a minimal PNG image data (1x1 pixel transparent PNG)
    png_data = (
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
        b'\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\x0f'
        b'\x00\x00\x01\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00IEND\xaeB`\x82'
    )
    return png_data


@pytest.fixture
def api_keys():
    """Fixture providing API keys from environment variables."""
    return {
        'openai': os.getenv('OPENAI_API_KEY'),
        'novelai': os.getenv('NOVELAI_API_KEY'),
        'stability': os.getenv('STABILITY_API_KEY')
    }


@pytest.fixture
def skip_if_no_api_key():
    """Fixture to skip tests if required API keys are not available."""
    def _skip_if_no_key(provider: str):
        key_map = {
            'openai': 'OPENAI_API_KEY',
            'novelai': 'NOVELAI_API_KEY',
            'stability': 'STABILITY_API_KEY'
        }
        
        if provider not in key_map:
            pytest.skip(f"Unknown provider: {provider}")
            
        if not os.getenv(key_map[provider]):
            pytest.skip(f"{key_map[provider]} not available for integration testing")
    
    return _skip_if_no_key


@pytest.fixture
def mock_requests():
    """Mock requests library for testing HTTP API calls."""
    with patch('requests.Session') as mock_session:
        mock_instance = Mock()
        mock_session.return_value = mock_instance
        
        # Default successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        mock_response.content = b"mock image data"
        mock_instance.post.return_value = mock_response
        mock_instance.get.return_value = mock_response
        
        yield mock_instance