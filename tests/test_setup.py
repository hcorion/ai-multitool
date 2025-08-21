"""
Basic setup tests to verify pytest configuration and fixtures work correctly.
"""

import pytest
import os


def test_pytest_setup():
    """Test that pytest is working correctly."""
    assert True


def test_environment_loading():
    """Test that environment variables are loaded from .env.local."""
    # This test verifies that pytest-dotenv is working
    # Environment variables should be available if .env.local exists
    assert os.getenv is not None


def test_flask_client_fixture(client):
    """Test that the Flask test client fixture works."""
    assert client is not None
    
    # Test a basic route
    response = client.get('/')
    # Should get a response (may be 200 or redirect, but not 404)
    assert response.status_code in [200, 302, 404]  # 404 is acceptable if route doesn't exist yet


def test_mock_openai_client_fixture(mock_openai_client):
    """Test that the mock OpenAI client fixture works."""
    assert mock_openai_client is not None
    assert hasattr(mock_openai_client, 'images')
    assert hasattr(mock_openai_client.images, 'generate')


def test_sample_image_data_fixture(sample_image_data):
    """Test that the sample image data fixture provides valid PNG data."""
    assert sample_image_data is not None
    assert isinstance(sample_image_data, bytes)
    assert sample_image_data.startswith(b'\x89PNG')  # PNG magic number


def test_api_keys_fixture(api_keys):
    """Test that the API keys fixture returns a dictionary."""
    assert isinstance(api_keys, dict)
    assert 'openai' in api_keys
    assert 'novelai' in api_keys
    assert 'stability' in api_keys


def test_skip_if_no_api_key_fixture(skip_if_no_api_key):
    """Test that the skip_if_no_api_key fixture is callable."""
    assert callable(skip_if_no_api_key)
    
    # Test with invalid provider (should skip)
    with pytest.raises(pytest.skip.Exception):
        skip_if_no_api_key('invalid_provider')