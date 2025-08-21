# Design Document

## Overview

This design outlines the implementation of proper testing infrastructure using pytest and the refactoring of NovelAI API functionality into a dedicated client class. The design also includes adding support for inpainting operations across both NovelAI and OpenAI providers, and restructuring Flask endpoints to be more modular and focused.

## Architecture

### Testing Infrastructure

The testing infrastructure will be built around pytest with the following components:

- **pytest Configuration**: Standard pytest setup with test discovery and configuration
- **Environment Integration**: pytest-dotenv plugin to load .env.local for API testing
- **Test Organization**: Tests organized in a `tests/` directory with logical groupings
- **API Testing**: Real API integration tests using actual API keys from environment

### NovelAI Client Abstraction

The NovelAI functionality will be abstracted into a dedicated client class:

- **NovelAIClient Class**: Encapsulates all NovelAI API interactions
- **Method Separation**: Distinct methods for generation, inpainting, and img2img
- **Error Handling**: Consistent error handling across all operations
- **Configuration Management**: Centralized API key and endpoint management

### Flask Endpoint Restructuring

The Flask application will be restructured to separate concerns:

- **Dedicated Image Endpoint**: New `/image` POST endpoint for all image operations
- **Operation Type Detection**: Request payload determines operation type (generation, inpainting, img2img)
- **Provider Routing**: Logic to route requests to appropriate provider (OpenAI, NovelAI, StabilityAI)
- **Unified Response Format**: Consistent response structure across all operations

## Components and Interfaces

### Testing Components

#### pytest Configuration (`pytest.ini`)
```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = --verbose --tb=short
env_files = .env.local
```

#### Test Directory Structure
```
tests/
├── __init__.py
├── conftest.py              # Shared fixtures and configuration
├── test_novelai_client.py   # NovelAI client tests
├── test_image_endpoints.py  # Flask endpoint tests
├── test_inpainting.py       # Inpainting functionality tests
└── integration/
    ├── __init__.py
    └── test_api_integration.py  # Full API integration tests
```

### NovelAI Client Interface

#### NovelAIClient Class Structure
```python
class NovelAIClient:
    def __init__(self, api_key: str, base_url: str = "https://api.novelai.net"):
        self.api_key = api_key
        self.base_url = base_url
        self.session = requests.Session()
    
    def generate_image(self, prompt: str, negative_prompt: str = None, **kwargs) -> dict:
        """Generate image from text prompt"""
        pass
    
    def generate_inpaint_image(self, base_image: bytes, mask: bytes, prompt: str, **kwargs) -> dict:
        """Perform inpainting on existing image"""
        pass
    
    def generate_img2img_image(self, base_image: bytes, prompt: str, strength: float = 0.7, **kwargs) -> dict:
        """Generate image based on existing image"""
        pass
    
    def _make_request(self, endpoint: str, payload: dict) -> dict:
        """Internal method for API requests"""
        pass
```

### Flask Endpoint Design

#### New Image Endpoint Structure
```python
@app.route("/image", methods=["POST"])
def handle_image_request():
    """Unified endpoint for all image operations"""
    operation_type = request.form.get("operation", "generate")
    provider = request.form.get("provider", "openai")
    
    if operation_type == "generate":
        return handle_generation(provider)
    elif operation_type == "inpaint":
        return handle_inpainting(provider)
    elif operation_type == "img2img":
        return handle_img2img(provider)
    else:
        return jsonify({"error": "Invalid operation type"}), 400
```

### OpenAI Integration Updates

#### Renamed Generation Functions
```python
def generate_openai_image(prompt: str, username: str, **kwargs) -> GeneratedImageData:
    """Generate image using OpenAI's gpt-image-1 model"""
    # Updated to use gpt-image-1 instead of DALL-E 3
    pass

def generate_openai_inpaint_image(base_image_path: str, mask_path: str, prompt: str, **kwargs) -> GeneratedImageData:
    """Perform inpainting using OpenAI's images.edit API"""
    # Implementation using client.images.edit
    pass
```

## Data Models

### Request/Response Models

#### Image Generation Request
```python
from enum import Enum
from typing import Literal

class Provider(str, Enum):
    OPENAI = "openai"
    NOVELAI = "novelai"
    STABILITY = "stability"

class Operation(str, Enum):
    GENERATE = "generate"
    INPAINT = "inpaint"
    IMG2IMG = "img2img"

class Quality(str, Enum):
    STANDARD = "standard"
    HD = "hd"

@dataclass
class ImageGenerationRequest:
    prompt: str
    provider: Provider = Provider.OPENAI
    operation: Operation = Operation.GENERATE
    negative_prompt: Optional[str] = None
    width: int = 1024
    height: int = 1024
    quality: Quality = Quality.STANDARD
    
@dataclass
class InpaintingRequest(ImageGenerationRequest):
    base_image_path: str
    mask_path: str
    operation: Operation = Operation.INPAINT

@dataclass
class Img2ImgRequest(ImageGenerationRequest):
    base_image_path: str
    strength: float = 0.7
    operation: Operation = Operation.IMG2IMG
```

#### Unified Response Model
```python
@dataclass
class ImageOperationResponse:
    success: bool
    image_path: Optional[str] = None
    image_name: Optional[str] = None
    revised_prompt: Optional[str] = None
    error_message: Optional[str] = None
    provider: Optional[str] = None
    operation: Optional[str] = None
```

### NovelAI API Models

#### NovelAI Request Payloads
```python
class NovelAIModel(str, Enum):
    DIFFUSION_4_5_FULL = "nai-diffusion-4-5-full"
    DIFFUSION_4_5_FULL_INPAINTING = "nai-diffusion-4-5-full-inpainting"
    DIFFUSION_3 = "nai-diffusion-3"

class NovelAIAction(str, Enum):
    GENERATE = "generate"
    INPAINT = "infill"
    IMG2IMG = "img2img"

@dataclass
class NovelAIGenerationPayload:
    input: str
    model: NovelAIModel = NovelAIModel.DIFFUSION_4_5_FULL
    action: NovelAIAction = NovelAIAction.GENERATE
    parameters: dict = field(default_factory=dict)

@dataclass
class NovelAIInpaintPayload(NovelAIGenerationPayload):
    model: NovelAIModel = NovelAIModel.DIFFUSION_4_5_FULL_INPAINTING
    action: NovelAIAction = NovelAIAction.INPAINT
    mask: str  # Base64 encoded mask
    image: str  # Base64 encoded base image
```

## Error Handling

### Centralized Error Management

#### Custom Exception Classes
```python
class NovelAIClientError(Exception):
    """Base exception for NovelAI client errors"""
    pass

class NovelAIAPIError(NovelAIClientError):
    """API-specific errors from NovelAI"""
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"NovelAI API Error {status_code}: {message}")

class ImageProcessingError(Exception):
    """Errors related to image processing operations"""
    pass
```

#### Error Response Format
```python
def create_error_response(error: Exception, operation: str, provider: str) -> dict:
    """Create standardized error response"""
    return {
        "success": False,
        "error_type": type(error).__name__,
        "error_message": str(error),
        "operation": operation,
        "provider": provider,
        "timestamp": int(time.time())
    }
```

## Testing Strategy

### Test Categories

#### Unit Tests
- **NovelAI Client Methods**: Test each method in isolation with mocked API responses
- **Request/Response Models**: Validate data model serialization and validation
- **Error Handling**: Test exception handling and error response generation
- **Utility Functions**: Test helper functions and data processing

#### Integration Tests
- **API Connectivity**: Test actual API calls with real credentials (when available)
- **End-to-End Workflows**: Test complete image generation workflows
- **Cross-Provider Compatibility**: Ensure consistent behavior across providers
- **File Operations**: Test image saving, loading, and processing

#### Flask Endpoint Tests
- **Route Testing**: Test all endpoint routes and HTTP methods
- **Request Validation**: Test request parameter validation and error handling
- **Response Format**: Validate response structure and content
- **Authentication**: Test session management and user authentication

### Test Configuration

#### Environment Setup
```python
# conftest.py
import pytest
import os
from app import app
from novelai_client import NovelAIClient

@pytest.fixture
def client():
    """Flask test client"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

@pytest.fixture
def novelai_client():
    """NovelAI client for testing"""
    api_key = os.getenv('NOVELAI_API_KEY')
    if not api_key:
        pytest.skip("NovelAI API key not available")
    return NovelAIClient(api_key)

@pytest.fixture
def sample_image():
    """Sample image for testing"""
    # Create or load a sample image for testing
    pass
```

#### Test Data Management
- **Mock Responses**: Predefined API responses for consistent testing
- **Sample Images**: Test images for inpainting and img2img operations
- **Environment Variables**: Secure handling of API keys in test environment

### Performance Considerations

#### Caching Strategy
- **Response Caching**: Cache API responses for repeated test runs
- **Image Caching**: Reuse generated images for subsequent tests
- **Mock Prioritization**: Use mocks for unit tests, real APIs for integration tests

#### Test Isolation
- **Database Cleanup**: Ensure tests don't interfere with each other
- **File System Management**: Clean up generated files after tests
- **Session Management**: Isolate user sessions between tests

## Implementation Phases

### Phase 1: Testing Infrastructure
1. Set up pytest configuration and directory structure
2. Add pytest and pytest-dotenv to Pipfile
3. Create basic test fixtures and configuration
4. Update steering documentation with testing guidelines

### Phase 2: NovelAI Client Refactoring
1. Create NovelAIClient class with basic structure
2. Implement generate_image method
3. Add error handling and request management
4. Write unit tests for client functionality

### Phase 3: Inpainting Support
1. Implement NovelAI inpainting method
2. Implement OpenAI inpainting using client.images.edit
3. Create unified inpainting interface
4. Add integration tests for inpainting operations

### Phase 4: Endpoint Restructuring
1. Create new /image POST endpoint
2. Implement operation routing logic
3. Update existing generation functions
4. Migrate frontend to use new endpoint

### Phase 5: Integration and Testing
1. Comprehensive integration testing
2. Performance optimization
3. Documentation updates
4. Final validation and cleanup