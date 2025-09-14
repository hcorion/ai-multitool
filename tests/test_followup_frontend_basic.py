"""
Basic tests for follow-up file frontend functionality without Selenium.
Tests the JavaScript validation and detection logic.
"""

import pytest
import tempfile
import os
import shutil
from app import app


class TestFollowUpFrontendBasic:
    """Test basic frontend functionality for follow-up files."""

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

    def test_prompt_files_page_loads(self, client, temp_static_folder):
        """Test that the main page loads with prompt files tab."""
        # Login as test user
        with client.session_transaction() as sess:
            sess['username'] = 'testuser'
        
        response = client.get('/')
        assert response.status_code == 200
        
        # Check that the page contains prompt files tab elements
        html = response.get_data(as_text=True)
        assert 'id="promptsTab"' in html
        assert 'id="PromptFiles"' in html
        assert 'id="prompt-files-content"' in html
        assert 'id="create-prompt-file-btn"' in html

    def test_prompt_files_modal_elements(self, client, temp_static_folder):
        """Test that the prompt files modal has all required elements."""
        # Login as test user
        with client.session_transaction() as sess:
            sess['username'] = 'testuser'
        
        response = client.get('/')
        assert response.status_code == 200
        
        html = response.get_data(as_text=True)
        
        # Check modal elements
        assert 'id="prompt-file-modal"' in html
        assert 'id="prompt-file-name"' in html
        assert 'id="prompt-file-content"' in html
        assert 'id="prompt-file-help"' in html
        assert 'id="prompt-file-save"' in html
        assert 'id="prompt-file-cancel"' in html

    def test_api_returns_followup_metadata(self, client, temp_static_folder):
        """Test that the API returns proper follow-up metadata for frontend consumption."""
        # Login as test user
        with client.session_transaction() as sess:
            sess['username'] = 'testuser'
        
        response = client.get('/prompt-files')
        assert response.status_code == 200
        
        files = response.get_json()
        assert len(files) == 2
        
        # Verify the structure matches what frontend expects
        for file in files:
            assert 'name' in file
            assert 'content' in file
            assert 'size' in file
            assert 'isFollowUp' in file
            
            if file['isFollowUp']:
                assert 'totalColumns' in file
                assert isinstance(file['totalColumns'], int)
                assert file['totalColumns'] > 0

    def test_create_followup_file_via_api(self, client, temp_static_folder):
        """Test creating a follow-up file through the API."""
        # Login as test user
        with client.session_transaction() as sess:
            sess['username'] = 'testuser'
        
        # Create a new follow-up file
        followup_content = """# columns: mood, intensity
happy||ecstatic
sad||depressed
calm||serene"""
        
        response = client.post('/prompt-files', 
                             json={
                                 'name': 'emotions',
                                 'content': followup_content
                             },
                             content_type='application/json')
        
        assert response.status_code == 200
        
        # Verify the file was created and is detected as follow-up
        response = client.get('/prompt-files')
        files = response.get_json()
        
        emotions_file = next(f for f in files if f['name'] == 'emotions')
        assert emotions_file['isFollowUp']
        assert emotions_file['totalColumns'] == 2

    def test_create_regular_file_via_api(self, client, temp_static_folder):
        """Test creating a regular file through the API."""
        # Login as test user
        with client.session_transaction() as sess:
            sess['username'] = 'testuser'
        
        # Create a regular file
        regular_content = """option1
option2
option3"""
        
        response = client.post('/prompt-files', 
                             json={
                                 'name': 'simple',
                                 'content': regular_content
                             },
                             content_type='application/json')
        
        assert response.status_code == 200
        
        # Verify the file was created and is NOT detected as follow-up
        response = client.get('/prompt-files')
        files = response.get_json()
        
        simple_file = next(f for f in files if f['name'] == 'simple')
        assert not simple_file['isFollowUp']
        assert 'totalColumns' not in simple_file

    def test_compiled_files_exist(self):
        """Test that compiled JavaScript and CSS files exist."""
        import os
        
        # Check JavaScript file exists
        js_path = os.path.join('static', 'js', 'script.js')
        assert os.path.exists(js_path), f"Compiled JavaScript file not found at {js_path}"
        
        # Check CSS file exists
        css_path = os.path.join('static', 'css', 'style.css')
        assert os.path.exists(css_path), f"Compiled CSS file not found at {css_path}"
        
        # Check that the compiled JS contains our new functions
        with open(js_path, 'r', encoding='utf-8') as f:
            js_content = f.read()
            assert 'detectFollowUpFile' in js_content
            assert 'validateFollowUpFile' in js_content
            assert 'updateTemplateHelp' in js_content
        
        # Check that the compiled CSS contains our new styles
        with open(css_path, 'r', encoding='utf-8') as f:
            css_content = f.read()
            assert 'followup-file' in css_content
            assert 'followup-badge' in css_content
            assert 'followup-help' in css_content