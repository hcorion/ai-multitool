"""
Manual integration test for follow-up file functionality.
This test creates actual files and verifies the complete workflow.
"""

import pytest
import os
import tempfile
import shutil
import json
from app import app


class TestFollowUpIntegrationManual:
    """Manual integration test for follow-up file functionality."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test-secret-key'
        
        with app.test_client() as client:
            with app.app_context():
                yield client

    @pytest.fixture
    def temp_static_folder(self):
        """Create temporary static folder for testing."""
        temp_dir = tempfile.mkdtemp()
        original_static = app.static_folder
        app.static_folder = temp_dir
        
        yield temp_dir
        
        app.static_folder = original_static
        shutil.rmtree(temp_dir)

    def test_complete_followup_file_workflow(self, client, temp_static_folder):
        """Test the complete workflow of creating and managing follow-up files."""
        # Login as test user
        with client.session_transaction() as sess:
            sess['username'] = 'testuser'
        
        # 1. Initially no files
        response = client.get('/prompt-files')
        assert response.status_code == 200
        files = response.get_json()
        assert len(files) == 0
        
        # 2. Create a regular file
        regular_content = "red\nblue\ngreen\nyellow"
        response = client.post('/prompt-files', 
                             json={
                                 'name': 'colors',
                                 'content': regular_content
                             },
                             content_type='application/json')
        assert response.status_code == 200
        
        # 3. Create a follow-up file
        followup_content = """# columns: primary, secondary, tertiary
warm red||cool red||deep red
bright blue||sky blue||navy blue
forest green||lime green||dark green"""
        
        response = client.post('/prompt-files', 
                             json={
                                 'name': 'color_palette',
                                 'content': followup_content
                             },
                             content_type='application/json')
        assert response.status_code == 200
        
        # 4. Verify both files are returned with correct metadata
        response = client.get('/prompt-files')
        assert response.status_code == 200
        files = response.get_json()
        assert len(files) == 2
        
        # Sort files by name for consistent testing
        files.sort(key=lambda x: x['name'])
        
        # Find files by name
        colors_file = next(f for f in files if f['name'] == 'colors')
        palette_file = next(f for f in files if f['name'] == 'color_palette')
        
        # Check regular file
        assert colors_file['name'] == 'colors'
        assert not colors_file['isFollowUp']
        assert 'totalColumns' not in colors_file
        assert len(colors_file['content']) == 4
        
        # Check follow-up file
        assert palette_file['name'] == 'color_palette'
        assert palette_file['isFollowUp']
        assert palette_file['totalColumns'] == 3
        assert len(palette_file['content']) == 4  # Header + 3 data lines
        
        # 5. Test file retrieval
        response = client.get('/prompt-files/color_palette')
        assert response.status_code == 200
        file_data = response.get_json()
        assert file_data['name'] == 'color_palette'
        assert file_data['isFollowUp']
        assert file_data['totalColumns'] == 3
        
        # 6. Test file deletion
        response = client.delete('/prompt-files/colors')
        assert response.status_code == 200
        
        # Verify only follow-up file remains
        response = client.get('/prompt-files')
        files = response.get_json()
        assert len(files) == 1
        assert files[0]['name'] == 'color_palette'
        assert files[0]['isFollowUp']

    def test_followup_file_edge_cases(self, client, temp_static_folder):
        """Test edge cases for follow-up file detection."""
        # Login as test user
        with client.session_transaction() as sess:
            sess['username'] = 'testuser'
        
        # Test 1: Follow-up file with only header
        header_only = "# columns: primary, secondary"
        response = client.post('/prompt-files', 
                             json={
                                 'name': 'header_only',
                                 'content': header_only
                             },
                             content_type='application/json')
        assert response.status_code == 200
        
        # Test 2: Follow-up file with comments and whitespace
        with_comments = """# This is a comment
# columns: mood, intensity
# Another comment

happy||ecstatic
# More comments
sad||depressed

calm||serene"""
        
        response = client.post('/prompt-files', 
                             json={
                                 'name': 'with_comments',
                                 'content': with_comments
                             },
                             content_type='application/json')
        assert response.status_code == 200
        
        # Test 3: File that looks like follow-up but isn't (no || separators)
        fake_followup = """# columns: primary, secondary
option1
option2"""
        
        response = client.post('/prompt-files', 
                             json={
                                 'name': 'fake_followup',
                                 'content': fake_followup
                             },
                             content_type='application/json')
        assert response.status_code == 200
        
        # Verify detection results
        response = client.get('/prompt-files')
        files = response.get_json()
        files_by_name = {f['name']: f for f in files}
        
        # Header only should be detected as follow-up but with 0 columns
        assert files_by_name['header_only']['isFollowUp']
        assert files_by_name['header_only']['totalColumns'] == 0
        
        # With comments should be detected correctly
        assert files_by_name['with_comments']['isFollowUp']
        assert files_by_name['with_comments']['totalColumns'] == 2
        
        # Fake follow-up should NOT be detected as follow-up
        assert not files_by_name['fake_followup']['isFollowUp']

    def test_followup_file_validation_scenarios(self, client, temp_static_folder):
        """Test various validation scenarios for follow-up files."""
        # Login as test user
        with client.session_transaction() as sess:
            sess['username'] = 'testuser'
        
        # Test 1: Inconsistent column counts (should still work, based on first line)
        inconsistent = """# columns: primary, secondary, tertiary
option1||option2||option3
option4||option5
option6||option7||option8||option9"""
        
        response = client.post('/prompt-files', 
                             json={
                                 'name': 'inconsistent',
                                 'content': inconsistent
                             },
                             content_type='application/json')
        assert response.status_code == 200
        
        # Test 2: Empty columns
        empty_columns = """# columns: primary, secondary, tertiary
option1||||option3
||option2||
option4||option5||option6"""
        
        response = client.post('/prompt-files', 
                             json={
                                 'name': 'empty_columns',
                                 'content': empty_columns
                             },
                             content_type='application/json')
        assert response.status_code == 200
        
        # Verify both files are detected as follow-up
        response = client.get('/prompt-files')
        files = response.get_json()
        files_by_name = {f['name']: f for f in files}
        
        assert files_by_name['inconsistent']['isFollowUp']
        assert files_by_name['inconsistent']['totalColumns'] == 3  # Based on first data line
        
        assert files_by_name['empty_columns']['isFollowUp']
        assert files_by_name['empty_columns']['totalColumns'] == 3

    def test_api_error_handling(self, client, temp_static_folder):
        """Test API error handling for follow-up files."""
        # Test without authentication
        response = client.get('/prompt-files')
        assert response.status_code == 401
        
        response = client.post('/prompt-files', 
                             json={'name': 'test', 'content': 'test'},
                             content_type='application/json')
        assert response.status_code == 401
        
        # Login for remaining tests
        with client.session_transaction() as sess:
            sess['username'] = 'testuser'
        
        # Test invalid file name
        response = client.post('/prompt-files', 
                             json={
                                 'name': 'invalid name!',
                                 'content': 'test content'
                             },
                             content_type='application/json')
        assert response.status_code == 400
        
        # Test missing name
        response = client.post('/prompt-files', 
                             json={
                                 'content': 'test content'
                             },
                             content_type='application/json')
        assert response.status_code == 400
        
        # Test getting non-existent file
        response = client.get('/prompt-files/nonexistent')
        assert response.status_code == 404
        
        # Test deleting non-existent file
        response = client.delete('/prompt-files/nonexistent')
        assert response.status_code == 404

    def test_file_system_integration(self, client, temp_static_folder):
        """Test that files are actually created on the file system correctly."""
        # Login as test user
        with client.session_transaction() as sess:
            sess['username'] = 'testuser'
        
        # Create a follow-up file
        followup_content = """# columns: primary, secondary
option1||option2
option3||option4"""
        
        response = client.post('/prompt-files', 
                             json={
                                 'name': 'filesystem_test',
                                 'content': followup_content
                             },
                             content_type='application/json')
        assert response.status_code == 200
        
        # Check that the file actually exists on disk
        user_dir = os.path.join(temp_static_folder, "prompts", "testuser")
        file_path = os.path.join(user_dir, "filesystem_test.txt")
        assert os.path.exists(file_path)
        
        # Check file contents
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "# columns: primary, secondary" in content
            assert "option1||option2" in content
            assert "option3||option4" in content
        
        # Verify API still detects it correctly after file system write
        response = client.get('/prompt-files')
        files = response.get_json()
        test_file = next(f for f in files if f['name'] == 'filesystem_test')
        assert test_file['isFollowUp']
        assert test_file['totalColumns'] == 2