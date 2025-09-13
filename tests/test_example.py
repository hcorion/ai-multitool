"""
Example test file demonstrating testing patterns and best practices.

This file serves as a reference for developers writing tests for the AI Multitool.
"""

import pytest
from unittest.mock import Mock, patch
import os


class TestExamplePatterns:
    """Example test class demonstrating various testing patterns."""
    
    def test_basic_unit_test(self):
        """Example of a basic unit test."""
        # Arrange
        expected_result = "test"
        
        # Act
        actual_result = "test"
        
        # Assert
        assert actual_result == expected_result
    
    def test_with_mock_decorator(self, mock_openai_client):
        """Example test using the mock OpenAI client fixture."""
        # The mock_openai_client fixture is automatically available
        assert mock_openai_client is not None
        
        # You can configure the mock's behavior
        mock_openai_client.images.generate.return_value.data = [
            Mock(url="https://example.com/test.png")
        ]
        
        # Test your function that uses the OpenAI client
        result = mock_openai_client.images.generate()
        assert result.data[0].url == "https://example.com/test.png"
    
    @patch('requests.post')
    def test_with_requests_mock(self, mock_post):
        """Example test mocking HTTP requests."""
        # Configure the mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True, "data": "test"}
        mock_post.return_value = mock_response
        
        # Your test logic here
        import requests
        response = requests.post("https://api.example.com/test")
        
        assert response.status_code == 200
        assert response.json()["success"] is True
    
    def test_flask_endpoint(self, client):
        """Example test for Flask endpoints."""
        # Test GET request
        response = client.get('/')
        # The response might be 200, 302 (redirect), or 404 depending on implementation
        assert response.status_code in [200, 302, 404]
        
        # Test POST request would go here if needed for specific endpoint testing
    
    def test_with_temp_directory(self, temp_dir):
        """Example test using temporary directory for file operations."""
        import os
        
        # Create a test file in the temporary directory
        test_file = os.path.join(temp_dir, "test.txt")
        with open(test_file, 'w') as f:
            f.write("test content")
        
        # Verify the file exists
        assert os.path.exists(test_file)
        
        # Read and verify content
        with open(test_file, 'r') as f:
            content = f.read()
        assert content == "test content"
        
        # temp_dir is automatically cleaned up after the test
    
    def test_environment_variables(self, api_keys):
        """Example test checking environment variables."""
        # api_keys fixture provides a dict of available API keys
        assert isinstance(api_keys, dict)
        
        # Check if specific keys are available (they might be None)
        openai_key = api_keys.get('openai')
        if openai_key:
            assert isinstance(openai_key, str)
            assert len(openai_key) > 0
    
    @pytest.mark.integration
    def test_integration_example(self, skip_if_no_api_key):
        """Example integration test that requires real API keys."""
        # This test will be skipped if the API key is not available
        skip_if_no_api_key('openai')
        
        # If we get here, the API key is available
        api_key = os.getenv('OPENAI_API_KEY')
        assert api_key is not None
        
        # Your integration test logic here
        # This would make actual API calls
    
    def test_error_handling(self):
        """Example test for error conditions."""
        # Test that a function raises the expected exception
        with pytest.raises(ValueError, match="Invalid input"):
            raise ValueError("Invalid input")
        
        # Test that a function handles errors gracefully
        def example_function(value):
            if value < 0:
                return None
            return value * 2
        
        assert example_function(-1) is None
        assert example_function(5) == 10
    
    @pytest.mark.parametrize("input_value,expected", [
        ("test", "TEST"),
        ("hello", "HELLO"),
        ("", ""),
    ])
    def test_parametrized(self, input_value, expected):
        """Example parametrized test."""
        result = input_value.upper()
        assert result == expected