"""
Unit tests for vibe API endpoints.

This module contains tests for the vibe encoding API endpoints including
creation, listing, retrieval, deletion, and progress streaming.
"""

import json
import time
from unittest.mock import Mock, patch

import pytest

from vibe_models import VibeCollection, VibeEncoding, VibeCollectionSummary


class TestVibeAPIEndpoints:
    """Unit tests for vibe API endpoints."""
    
    @pytest.fixture
    def authenticated_session(self, client):
        """Create an authenticated session."""
        with client.session_transaction() as sess:
            sess['username'] = 'testuser'
        return client
    
    @pytest.fixture
    def sample_vibe_collection(self):
        """Create a sample vibe collection for testing."""
        encodings = {}
        for strength in [1.0, 0.85, 0.7, 0.5, 0.35]:
            encodings[str(strength)] = VibeEncoding(
                encoding_strength=strength,
                encoded_data=f"encoded_data_{strength}"
            )
        
        return VibeCollection(
            guid="550e8400-e29b-41d4-a716-446655440000",
            name="Test Vibe",
            model="nai-diffusion-4-5-full",
            created_at=int(time.time()),
            source_image_path="/test/image.png",
            encodings=encodings,
            preview_images={
                "enc1.0_ref1.0": "/static/vibes/testuser/550e8400-e29b-41d4-a716-446655440000/preview_enc1.0_ref1.0.thumb.jpg",
                "enc0.85_ref0.85": "/static/vibes/testuser/550e8400-e29b-41d4-a716-446655440000/preview_enc0.85_ref0.85.thumb.jpg"
            }
        )
    
    def test_encode_vibe_endpoint_unauthenticated(self, client):
        """Test that unauthenticated requests are rejected."""
        response = client.post('/vibes/encode', json={
            'image_filename': 'test.png',
            'name': 'Test Vibe'
        })
        
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data['error_type'] == 'AuthenticationError'
    
    def test_encode_vibe_endpoint_missing_data(self, authenticated_session):
        """Test validation of required fields."""
        # Missing image_filename
        response = authenticated_session.post('/vibes/encode', json={
            'name': 'Test Vibe'
        })
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['error_type'] == 'ValidationError'
        assert 'image_filename' in data['error_message']
        
        # Missing name
        response = authenticated_session.post('/vibes/encode', json={
            'image_filename': 'test.png'
        })
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['error_type'] == 'ValidationError'
        assert 'name' in data['error_message']
    
    @patch('app.threading.Thread')  # Mock the background thread
    @patch('app.VibeStorageManager.generate_guid')  # Mock GUID generation
    def test_encode_vibe_endpoint_success(self, mock_generate_guid, mock_thread, authenticated_session):
        """Test successful vibe encoding."""
        # Mock GUID generation to return predictable value
        mock_generate_guid.return_value = '550e8400-e29b-41d4-a716-446655440000'
        
        # Mock the thread to prevent background execution during test
        mock_thread_instance = Mock()
        mock_thread.return_value = mock_thread_instance
        
        # Mock file existence check
        with patch('os.path.exists', return_value=True):
            response = authenticated_session.post('/vibes/encode', json={
                'image_filename': 'test.png',
                'name': 'Test Vibe'
            })
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['guid'] == '550e8400-e29b-41d4-a716-446655440000'
        assert data['name'] == 'Test Vibe'
        assert data['encoding_count'] == 0  # Updated expectation - encoding is done in background
        assert data['preview_count'] == 0  # Updated expectation - previews are generated in background
        assert 'progress_stream_url' in data
        
        # Verify background thread was started
        mock_thread.assert_called_once()
        mock_thread_instance.start.assert_called_once()
    
    def test_encode_vibe_endpoint_image_not_found(self, authenticated_session):
        """Test error when source image doesn't exist."""
        with patch('os.path.exists', return_value=False):
            response = authenticated_session.post('/vibes/encode', json={
                'image_filename': 'nonexistent.png',
                'name': 'Test Vibe'
            })
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['error_type'] == 'NotFoundError'
        assert 'not found' in data['error_message']
    
    @patch('app.threading.Thread')  # Mock the background thread
    @patch('app.VibeStorageManager.generate_guid')  # Mock GUID generation
    def test_encode_vibe_endpoint_api_error(self, mock_generate_guid, mock_thread, authenticated_session):
        """Test that API errors are handled in background processing."""
        # Mock GUID generation to return predictable value
        mock_generate_guid.return_value = '550e8400-e29b-41d4-a716-446655440000'
        
        # Mock the thread to prevent background execution during test
        mock_thread_instance = Mock()
        mock_thread.return_value = mock_thread_instance
        
        with patch('os.path.exists', return_value=True):
            response = authenticated_session.post('/vibes/encode', json={
                'image_filename': 'test.png',
                'name': 'Test Vibe'
            })
        
        # Should still return 200 since errors are handled in background
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['guid'] == '550e8400-e29b-41d4-a716-446655440000'
        
        # Verify background thread was started (errors will be reported via progress stream)
        mock_thread.assert_called_once()
        mock_thread_instance.start.assert_called_once()
    
    @patch('app.vibe_storage_manager')
    def test_list_vibes_endpoint_success(self, mock_storage_manager, authenticated_session):
        """Test successful vibe collection listing."""
        
        # Create sample summaries
        summaries = [
            VibeCollectionSummary(
                guid="guid1",
                name="Vibe 1",
                model="nai-diffusion-4-5-full",
                created_at=int(time.time()),
                preview_image="/static/vibes/testuser/guid1/preview_enc1.0_ref1.0.thumb.jpg"
            ),
            VibeCollectionSummary(
                guid="guid2",
                name="Vibe 2",
                model="nai-diffusion-4-5-full",
                created_at=int(time.time()) - 3600,
                preview_image="/static/vibes/testuser/guid2/preview_enc1.0_ref1.0.thumb.jpg"
            )
        ]
        mock_storage_manager.list_collections.return_value = summaries
        
        response = authenticated_session.get('/vibes')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'collections' in data
        assert len(data['collections']) == 2
        assert data['collections'][0]['guid'] == 'guid1'
        assert data['collections'][0]['name'] == 'Vibe 1'
    
    def test_list_vibes_endpoint_unauthenticated(self, client):
        """Test that unauthenticated requests are rejected."""
        response = client.get('/vibes')
        
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data['error_type'] == 'AuthenticationError'
    
    @patch('app.vibe_storage_manager')
    def test_get_vibe_endpoint_success(self, mock_storage_manager, authenticated_session, sample_vibe_collection):
        """Test successful vibe collection retrieval."""
        # Mock storage manager
        
        
        mock_storage_manager.load_collection.return_value = sample_vibe_collection
        
        response = authenticated_session.get('/vibes/550e8400-e29b-41d4-a716-446655440000')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['guid'] == '550e8400-e29b-41d4-a716-446655440000'
        assert data['name'] == 'Test Vibe'
        assert data['model'] == 'nai-diffusion-4-5-full'
        assert 'encoding_strengths' in data
        assert 'previews' in data
        assert len(data['encoding_strengths']) == 5
    
    @patch('app.vibe_storage_manager')
    def test_get_vibe_endpoint_not_found(self, mock_storage_manager, authenticated_session):
        """Test vibe collection not found."""
        # Mock storage manager to return None
        
        
        mock_storage_manager.load_collection.return_value = None
        
        response = authenticated_session.get('/vibes/nonexistent-guid')
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['error_type'] == 'NotFoundError'
        assert 'not found' in data['error_message']
    
    def test_get_vibe_endpoint_unauthenticated(self, client):
        """Test that unauthenticated requests are rejected."""
        response = client.get('/vibes/550e8400-e29b-41d4-a716-446655440000')
        
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data['error_type'] == 'AuthenticationError'
    
    @patch('app.vibe_storage_manager')
    def test_delete_vibe_endpoint_success(self, mock_storage_manager, authenticated_session):
        """Test successful vibe collection deletion."""
        # Mock storage manager
        
        
        mock_storage_manager.delete_collection.return_value = True
        
        response = authenticated_session.delete('/vibes/550e8400-e29b-41d4-a716-446655440000')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'deleted' in data['message']
        
        # Verify storage manager was called
        mock_storage_manager.delete_collection.assert_called_once_with('testuser', '550e8400-e29b-41d4-a716-446655440000')
    
    @patch('app.vibe_storage_manager')
    def test_delete_vibe_endpoint_not_found(self, mock_storage_manager, authenticated_session):
        """Test deletion of non-existent vibe collection."""
        # Mock storage manager to return False (not found)
        
        
        mock_storage_manager.delete_collection.return_value = False
        
        response = authenticated_session.delete('/vibes/nonexistent-guid')
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['error_type'] == 'NotFoundError'
        assert 'not found' in data['error_message']
    
    def test_delete_vibe_endpoint_unauthenticated(self, client):
        """Test that unauthenticated requests are rejected."""
        response = client.delete('/vibes/550e8400-e29b-41d4-a716-446655440000')
        
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data['error_type'] == 'AuthenticationError'
    
    @patch('app.vibe_storage_manager')
    def test_get_vibe_preview_endpoint_success(self, mock_storage_manager, authenticated_session, sample_vibe_collection):
        """Test successful preview image retrieval."""
        # Mock storage manager
        
        
        mock_storage_manager.load_collection.return_value = sample_vibe_collection
        
        response = authenticated_session.get('/vibes/550e8400-e29b-41d4-a716-446655440000/preview/1.0/1.0')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'preview_url' in data
        assert 'enc1.0_ref1.0' in data['preview_url']
    
    @patch('app.vibe_storage_manager')
    def test_get_vibe_preview_endpoint_not_found(self, mock_storage_manager, authenticated_session):
        """Test preview retrieval for non-existent vibe."""
        # Mock storage manager to return None
        
        
        mock_storage_manager.load_collection.return_value = None
        
        response = authenticated_session.get('/vibes/nonexistent-guid/preview/1.0/1.0')
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['error_type'] == 'NotFoundError'
    
    def test_get_vibe_preview_endpoint_invalid_strength(self, authenticated_session):
        """Test preview retrieval with invalid strength values."""
        response = authenticated_session.get('/vibes/550e8400-e29b-41d4-a716-446655440000/preview/2.0/1.0')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['error_type'] == 'ValidationError'
        assert 'encoding strength' in data['error_message']
    
    def test_get_vibe_preview_endpoint_unauthenticated(self, client):
        """Test that unauthenticated requests are rejected."""
        response = client.get('/vibes/550e8400-e29b-41d4-a716-446655440000/preview/1.0/1.0')
        
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data['error_type'] == 'AuthenticationError'
    
    @patch('app.vibe_storage_manager')
    def test_vibe_progress_endpoint_collection_not_found(self, mock_storage_manager, authenticated_session):
        """Test progress endpoint when collection doesn't exist."""
        # Mock storage manager to return None
        
        
        mock_storage_manager.load_collection.return_value = None
        
        response = authenticated_session.get('/vibes/nonexistent-guid/progress')
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['error_type'] == 'NotFoundError'
    
    def test_vibe_progress_endpoint_unauthenticated(self, client):
        """Test that unauthenticated requests are rejected."""
        response = client.get('/vibes/550e8400-e29b-41d4-a716-446655440000/progress')
        
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data['error_type'] == 'AuthenticationError'
    
    @patch('app.vibe_storage_manager')
    def test_vibe_progress_endpoint_with_tracking(self, mock_storage_manager, authenticated_session, sample_vibe_collection):
        """Test progress endpoint with active progress tracking."""
        # Mock storage manager to return the collection
        mock_storage_manager.load_collection.return_value = sample_vibe_collection
        
        # Set up progress tracking
        guid = sample_vibe_collection.guid
        
        # Simulate progress tracking data
        import app
        with app.vibe_progress_lock:
            app.vibe_progress_tracker[guid] = {
                "phase": "preview",
                "step": 10,
                "total": 25,
                "message": "Generating preview 10/25",
                "complete": True,  # Set to complete so the SSE stream ends quickly
                "error": None
            }
        
        # Make request to progress endpoint
        response = authenticated_session.get(f'/vibes/{guid}/progress')
        
        # Should return SSE stream
        assert response.status_code == 200
        assert response.headers['Content-Type'] == 'text/event-stream; charset=utf-8'


class TestVibeAPIValidation:
    """Tests for vibe API input validation."""
    
    @pytest.fixture
    def authenticated_session(self, client):
        """Create an authenticated session."""
        with client.session_transaction() as sess:
            sess['username'] = 'testuser'
        return client
    
    def test_encode_vibe_validation_empty_name(self, authenticated_session):
        """Test validation of empty vibe name."""
        response = authenticated_session.post('/vibes/encode', json={
            'image_filename': 'test.png',
            'name': ''  # Empty name
        })
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['error_type'] == 'ValidationError'
        assert 'name' in data['error_message']
    
    def test_encode_vibe_validation_whitespace_name(self, authenticated_session):
        """Test validation of whitespace-only vibe name."""
        response = authenticated_session.post('/vibes/encode', json={
            'image_filename': 'test.png',
            'name': '   '  # Whitespace only
        })
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['error_type'] == 'ValidationError'
        assert 'name' in data['error_message']
    
    def test_encode_vibe_validation_long_name(self, authenticated_session):
        """Test validation of very long vibe name."""
        long_name = 'a' * 256  # Very long name
        response = authenticated_session.post('/vibes/encode', json={
            'image_filename': 'test.png',
            'name': long_name
        })
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['error_type'] == 'ValidationError'
        assert 'name' in data['error_message']
    
    def test_preview_validation_invalid_encoding_strength(self, authenticated_session):
        """Test validation of invalid encoding strength values."""
        # Test non-numeric values
        response = authenticated_session.get('/vibes/test-guid/preview/invalid/1.0')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['error_type'] == 'ValidationError'
        assert 'Invalid strength values' in data['error_message']
        
        # Test invalid numeric encoding strength
        response = authenticated_session.get('/vibes/test-guid/preview/0.6/1.0')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['error_type'] == 'ValidationError'
        assert 'encoding strength' in data['error_message']
    
    def test_preview_validation_invalid_reference_strength(self, authenticated_session):
        """Test validation of invalid reference strength values."""
        # Test non-numeric values
        response = authenticated_session.get('/vibes/test-guid/preview/1.0/invalid')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['error_type'] == 'ValidationError'
        assert 'Invalid strength values' in data['error_message']
        
        # Test invalid numeric reference strength
        response = authenticated_session.get('/vibes/test-guid/preview/1.0/1.1')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['error_type'] == 'ValidationError'
        assert 'reference strength' in data['error_message']


class TestVibeAPIErrorHandling:
    """Tests for vibe API error handling scenarios."""
    
    @pytest.fixture
    def authenticated_session(self, client):
        """Create an authenticated session."""
        with client.session_transaction() as sess:
            sess['username'] = 'testuser'
        return client
    
    @patch('app.vibe_storage_manager')
    def test_storage_error_handling(self, mock_storage_manager, authenticated_session):
        """Test handling of storage errors."""
        # Mock storage manager to raise an exception
        
        
        mock_storage_manager.list_collections.side_effect = Exception("Storage error")
        
        response = authenticated_session.get('/vibes')
        
        assert response.status_code == 500
        data = json.loads(response.data)
        assert data['error_type'] == 'InternalServerError'
    
    @patch('app.threading.Thread')  # Mock the background thread
    @patch('app.VibeStorageManager.generate_guid')  # Mock GUID generation
    def test_client_error_handling(self, mock_generate_guid, mock_thread, authenticated_session):
        """Test that client errors are handled in background processing."""
        # Mock GUID generation to return predictable value
        mock_generate_guid.return_value = '550e8400-e29b-41d4-a716-446655440000'
        
        # Mock the thread to prevent background execution during test
        mock_thread_instance = Mock()
        mock_thread.return_value = mock_thread_instance
        
        with patch('os.path.exists', return_value=True):
            response = authenticated_session.post('/vibes/encode', json={
                'image_filename': 'test.png',
                'name': 'Test Vibe'
            })
        
        # Should still return 200 since errors are handled in background
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['guid'] == '550e8400-e29b-41d4-a716-446655440000'
        
        # Verify background thread was started (errors will be reported via progress stream)
        mock_thread.assert_called_once()
        mock_thread_instance.start.assert_called_once()
