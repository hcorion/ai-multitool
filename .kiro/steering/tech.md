# Technology Stack

## Backend
- **Python 3.13** Latest idiomatic python with Flask web framework
- **OpenAI Python SDK** for GPT-Image-1 generation, inpainting, and Responses API (gpt-5/gpt-5-nano models)
- **Pydantic** for data validation and serialization with type safety
- **Requests** library for StabilityAI and NovelAI API calls
- **NovelAI Client** custom client for text-to-image, inpainting, and img2img operations
- **Pillow (PIL)** for image processing, metadata handling, and mask processing
- **Wand (ImageMagick)** for advanced image operations and grid generation
- **Pygments** and **Markdown** for syntax highlighting and text processing

## Frontend
- **TypeScript** compiled to ES2024 with strict type checking
- **jQuery** for DOM manipulation and AJAX requests
- **Showdown.js** for Markdown rendering with syntax highlighting
- **Highlight.js** for code syntax highlighting
- **Sass** for CSS preprocessing

## Build System
- **TypeScript Compiler (tsc)** with watch mode for development
- **Sass compiler** with watch mode for CSS generation
- **npm** for frontend dependency management
- **pipenv** for Python dependency management

## Development Tools
- **Ruff** for Python linting with Python 3.13 target
- **Prettier** for code formatting (4-space tabs, 120 char width)
- **pytest** for Python testing with pytest-dotenv for environment variable loading

## Common Commands

### Setup
```powershell
# Install dependencies
npm install
pipenv sync

# Install global tools
npm install -g typescript sass
```

### Development
```powershell
# Start development server (runs TypeScript, Sass, and Flask in watch mode)
pipenv shell
.\run-user.ps1
```

### Build
```powershell
# Compile TypeScript
tsc

# Compile Sass
sass static/sass:static/css
```

### Testing
```powershell
# Run all tests
pytest

# Run tests with verbose output
pytest -v

# Run specific test file
pytest tests/test_specific_module.py

# Run tests with coverage
pytest --cov=app --cov-report=html
```

## Environment Variables
- `OPENAI_API_KEY`: Required for OpenAI GPT-Image-1 generation, inpainting, and Responses API chat functionality
- `STABILITY_API_KEY`: Required for StabilityAI image generation
- `NOVELAI_API_KEY`: Required for NovelAI text-to-image, inpainting, and img2img operations

## API Models and Endpoints

### OpenAI Integration
- **Chat Model**: gpt-5 via Responses API (`client.responses.create()`)
- **Title Generation**: gpt-5-nano for automatic conversation titles
- **Image Model**: gpt-image-1 for text-to-image and inpainting operations
- **Endpoints**: `/image` (unified), `/chat` (streaming), `/update-conversation-title`

### NovelAI Integration
- **Models**: nai-diffusion-4-5-full, nai-diffusion-4-5-full-inpainting
- **Operations**: Text-to-image, inpainting with mask processing, img2img transformations
- **Features**: Multi-character prompts, negative prompting, image upscaling

### Image Operations
- **Unified API**: Single `/image` endpoint handles all providers and operations
- **Request Types**: ImageGenerationRequest, InpaintingRequest, Img2ImgRequest
- **Response Format**: Structured JSON with success/error handling and metadata
## Testing Guidelines

### Test Structure
Tests are organized in the `tests/` directory with the following structure:
- `tests/` - Unit tests for individual modules
- `tests/integration/` - Integration tests that may use real API calls
- `conftest.py` - Shared fixtures and test configuration

### Writing Tests

#### Unit Tests
Unit tests should mock external dependencies and focus on testing individual functions:

```python
import pytest
from unittest.mock import Mock, patch
from app import generate_openai_image

def test_generate_openai_image_success(mock_openai_client):
    """Test successful image generation with mocked OpenAI client."""
    # Test implementation here
    pass

@patch('app.requests.post')
def test_api_call_with_mock(mock_post):
    """Test API calls with mocked requests."""
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {"success": True}
    # Test implementation here
    pass
```

#### Integration Tests
Integration tests can use real API keys from `.env.local` when available:

```python
import pytest
import os

@pytest.mark.integration
def test_real_openai_api(skip_if_no_api_key):
    """Test actual OpenAI API integration."""
    skip_if_no_api_key('openai')
    
    # This test will be skipped if OPENAI_API_KEY is not set
    # Test implementation using real API here
    pass
```

#### Flask Endpoint Tests
Test Flask routes using the test client fixture:

```python
def test_image_endpoint(client):
    """Test the image generation endpoint."""
    response = client.post('/image', data={
        'prompt': 'test prompt',
        'provider': 'openai'
    })
    assert response.status_code == 200
```

### Test Configuration

#### Environment Variables
- Tests automatically load environment variables from `.env.local` via pytest-dotenv
- Use the `skip_if_no_api_key` fixture to skip integration tests when API keys are unavailable
- Never commit API keys to version control

#### Fixtures
Common fixtures are available in `conftest.py`:
- `client` - Flask test client
- `mock_openai_client` - Mocked OpenAI client
- `api_keys` - Dictionary of available API keys
- `skip_if_no_api_key` - Function to skip tests when API keys are missing
- `sample_image_data` - Sample PNG data for image processing tests

### Best Practices

1. **Test Isolation**: Each test should be independent and not rely on other tests
2. **Mock External APIs**: Use mocks for unit tests, real APIs only for integration tests
3. **Descriptive Names**: Test function names should clearly describe what is being tested
4. **Arrange-Act-Assert**: Structure tests with clear setup, execution, and verification phases
5. **Error Testing**: Include tests for error conditions and edge cases
6. **Environment Safety**: Never make destructive API calls in tests

### Running Tests

#### Basic Test Execution
```powershell
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_app.py

# Run tests matching a pattern
pytest -k "test_image"
```

#### Integration Test Control
```powershell
# Run only unit tests (skip integration)
pytest -m "not integration"

# Run only integration tests
pytest -m integration

# Run with real API keys (ensure .env.local is configured)
pytest tests/integration/
```

#### Test Coverage
```powershell
# Install coverage plugin
pipenv install pytest-cov --dev

# Run tests with coverage report
pytest --cov=app --cov-report=html

# View coverage report
# Open htmlcov/index.html in browser
```

### JavaScript Testing with Selenium

This project uses Selenium WebDriver to test JavaScript functionality in a real browser environment. This approach allows testing of complex frontend interactions, canvas operations, and DOM manipulation.

#### JavaScript Test Pattern
```python
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class TestJavaScriptFeature:
    @pytest.fixture
    def driver(self):
        """Set up Chrome driver for testing"""
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        driver = webdriver.Chrome(options=options)
        driver.implicitly_wait(10)
        yield driver
        driver.quit()
    
    def test_javascript_functionality(self, driver):
        """Test JavaScript functionality in browser"""
        driver.get("http://localhost:5000/test-page")
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "test-element"))
        )
        
        # Execute JavaScript test code
        result = driver.execute_script("""
            return new Promise((resolve) => {
                import('/static/js/module.js').then(({ ClassName }) => {
                    try {
                        // Test JavaScript functionality
                        const instance = new ClassName();
                        const testResult = instance.testMethod();
                        
                        resolve({
                            success: true,
                            result: testResult
                        });
                    } catch (error) {
                        resolve({ success: false, error: error.message });
                    }
                });
            });
        """)
        
        assert result['success'], f"Test failed: {result.get('error', 'Unknown error')}"
```

#### Key Testing Principles
- **Real Browser Environment**: Tests run in actual Chrome browser for authentic behavior
- **ES Module Imports**: Use dynamic imports to load TypeScript-compiled modules
- **Promise-based Testing**: JavaScript tests return promises for async operations
- **Canvas and DOM Testing**: Full access to Canvas API, DOM manipulation, and browser APIs
- **Error Handling**: Comprehensive error catching and reporting from JavaScript
- **Headless Execution**: Tests run in headless mode for CI/CD compatibility

#### Test File Organization
- Python test files generate and execute JavaScript test code
- Tests verify complex interactions like canvas rendering, input handling, and state management
- Each test focuses on specific functionality (binary mask enforcement, coordinate mapping, etc.)
- Results are validated in Python with detailed assertion messages