"""
Unit tests for follow-up file detection functionality in the backend API.
"""

import pytest
import tempfile
import os
import shutil
from app import app, detect_followup_file


class TestFollowUpFileDetection:
    """Test follow-up file detection logic."""

    def test_detect_regular_file(self):
        """Test that regular files are not detected as follow-up files."""
        content_lines = [
            "red",
            "blue", 
            "green",
            "yellow"
        ]
        
        is_followup, total_columns = detect_followup_file(content_lines)
        assert not is_followup
        assert total_columns == 0

    def test_detect_followup_file_valid(self):
        """Test detection of valid follow-up files."""
        content_lines = [
            "# columns: primary, secondary, tertiary",
            "warm red||cool red||deep red",
            "bright blue||sky blue||navy blue",
            "forest green||lime green||dark green"
        ]
        
        is_followup, total_columns = detect_followup_file(content_lines)
        assert is_followup
        assert total_columns == 3

    def test_detect_followup_file_two_columns(self):
        """Test detection of follow-up file with two columns."""
        content_lines = [
            "# columns: primary, secondary",
            "option1||option2",
            "option3||option4"
        ]
        
        is_followup, total_columns = detect_followup_file(content_lines)
        assert is_followup
        assert total_columns == 2

    def test_detect_followup_file_header_only(self):
        """Test follow-up file with header but no data."""
        content_lines = [
            "# columns: primary, secondary, tertiary",
            "",
            "# This is a comment"
        ]
        
        is_followup, total_columns = detect_followup_file(content_lines)
        assert is_followup
        assert total_columns == 0

    def test_detect_followup_file_malformed_no_separators(self):
        """Test that files without || separators are not detected as follow-up."""
        content_lines = [
            "# columns: primary, secondary",
            "option1",
            "option2"
        ]
        
        is_followup, total_columns = detect_followup_file(content_lines)
        assert not is_followup
        assert total_columns == 0

    def test_detect_followup_file_empty(self):
        """Test empty file detection."""
        content_lines = []
        
        is_followup, total_columns = detect_followup_file(content_lines)
        assert not is_followup
        assert total_columns == 0

    def test_detect_followup_file_comments_and_whitespace(self):
        """Test follow-up file with comments and whitespace."""
        content_lines = [
            "",
            "# This is a comment",
            "# columns: primary, secondary, tertiary",
            "",
            "warm red||cool red||deep red",
            "# Another comment",
            "bright blue||sky blue||navy blue",
            ""
        ]
        
        is_followup, total_columns = detect_followup_file(content_lines)
        assert is_followup
        assert total_columns == 3


class TestFollowUpFileAPI:
    """Test the prompt files API with follow-up file support."""

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
        
        # Create test user directory and files
        user_dir = os.path.join(temp_dir, "prompts", "testuser")
        os.makedirs(user_dir, exist_ok=True)
        
        # Regular file
        with open(os.path.join(user_dir, "colors.txt"), "w", encoding="utf-8") as f:
            f.write("red\nblue\ngreen\nyellow")
        
        # Follow-up file
        with open(os.path.join(user_dir, "color_palette.txt"), "w", encoding="utf-8") as f:
            f.write("# columns: primary, secondary, tertiary\n")
            f.write("warm red||cool red||deep red\n")
            f.write("bright blue||sky blue||navy blue\n")
            f.write("forest green||lime green||dark green")
        
        yield temp_dir
        
        app.static_folder = original_static
        shutil.rmtree(temp_dir)

    def test_get_prompt_files_with_followup_metadata(self, client, temp_static_folder):
        """Test that API returns follow-up file metadata."""
        # Login as test user
        with client.session_transaction() as sess:
            sess['username'] = 'testuser'
        
        response = client.get('/prompt-files')
        assert response.status_code == 200
        
        files = response.get_json()
        assert len(files) == 2
        
        # Find the files
        regular_file = next(f for f in files if f['name'] == 'colors')
        followup_file = next(f for f in files if f['name'] == 'color_palette')
        
        # Check regular file
        assert not regular_file['isFollowUp']
        assert 'totalColumns' not in regular_file
        
        # Check follow-up file
        assert followup_file['isFollowUp']
        assert followup_file['totalColumns'] == 3

    def test_get_prompt_files_malformed_followup(self, client, temp_static_folder):
        """Test handling of malformed follow-up files."""
        # Create malformed follow-up file
        user_dir = os.path.join(temp_static_folder, "prompts", "testuser")
        with open(os.path.join(user_dir, "malformed.txt"), "w", encoding="utf-8") as f:
            f.write("# columns: primary, secondary\n")
            f.write("option1||option2||option3\n")  # Too many columns
            f.write("option4||option5")  # Correct columns
        
        # Login as test user
        with client.session_transaction() as sess:
            sess['username'] = 'testuser'
        
        response = client.get('/prompt-files')
        assert response.status_code == 200
        
        files = response.get_json()
        malformed_file = next(f for f in files if f['name'] == 'malformed')
        
        # Should still be detected as follow-up based on first line
        assert malformed_file['isFollowUp']
        assert malformed_file['totalColumns'] == 3  # Based on first data line

    def test_get_prompt_files_unauthenticated(self, client, temp_static_folder):
        """Test that unauthenticated requests are rejected."""
        response = client.get('/prompt-files')
        assert response.status_code == 401
        
        data = response.get_json()
        assert 'error_message' in data
        assert 'Authentication required' in data['error_message']