# Project Structure

## Code Organization Principles

### Separation of Concerns
- **Keep route handlers thin**: Delegate business logic to service functions
- **Separate data access**: Use manager classes for file operations and data persistence
- **Isolate presentation**: Keep data transformation separate from HTTP response construction
- **Modular frontend**: Separate DOM manipulation from business logic

### Abstraction Guidelines
- **Prefer duplication over wrong abstraction**: Don't extract until you have 3+ identical use cases
- **Flat over deep**: Avoid deep inheritance hierarchies; prefer composition
- **Explicit over clever**: Clear, straightforward code beats clever abstractions
- **Measure by cognitive load**: Code should be easy to understand, not just follow rules

### Function Design
- **Tell a clear story**: A long function with clear flow is better than artificially split functions
- **Single responsibility**: But don't over-split - jumping between files increases cognitive load
- **Synchronous by default**: Only use async when genuinely needed for performance
- **Avoid premature generalization**: Solve specific problems; generalize only when needed

## Root Level
- `app.py` - Main Flask application with unified image API and Responses API chat integration
- `image_models.py` - Pydantic data models for unified image generation API
- `novelai_client.py` - Dedicated NovelAI API client for all image operations
- `dynamic_prompts.py` - Dynamic prompt system with multi-character prompt support
- `utils.py` - Utility functions (stop word removal, text processing)
- `secret-key.txt` - Auto-generated Flask session secret (gitignored)

## Frontend Source (`src/`)
- `chat.ts` - Chat functionality and message handling
- `script.ts` - Main frontend logic, event handlers, and UI interactions
- `share.ts` - Sharing functionality
- `utils.ts` - Frontend utility functions

## Templates (`templates/`)
- `index.html` - Main application interface
- `login.html` - User login page
- `result-section.html` - Image generation results partial
- `share.html` - Shared content display

## Static Assets (`static/`)
- `css/` - Compiled CSS from Sass with character prompt styling
- `sass/` - Sass source files with responsive design for multi-character interface
- `js/` - Compiled TypeScript output with unified image API integration
- `images/` - User-generated images with comprehensive metadata including character prompts
- `prompts/` - User-specific dynamic prompt files
- `chats/` - Local conversation storage with response ID tracking and auto-generated titles
- `assets/` - Static assets and resources

## Testing Structure (`tests/`)
- `tests/` - Unit tests for core functionality
- `tests/integration/` - Integration tests with real API calls
- `conftest.py` - Shared fixtures and test configuration
- Test files organized by module: `test_app.py`, `test_novelai_client.py`, `test_image_models.py`

### JavaScript Testing Pattern
- **Selenium-based Testing**: JavaScript functionality tested using Selenium WebDriver in real Chrome browser
- **Python Test Generators**: Python test files generate and execute JavaScript test code dynamically
- **Canvas and DOM Testing**: Full browser environment for testing complex frontend interactions
- **Module Import Testing**: Tests use ES module dynamic imports to load compiled TypeScript modules
- **Promise-based Execution**: JavaScript tests return promises for async validation in Python
- **Examples**: `test_brush_engine.py`, `test_canvas_manager.py`, `test_input_engine.py`, `test_mask_overlay.py`

## Configuration Files
- `tsconfig.json` - TypeScript compiler configuration
- `package.json` - Frontend dependencies
- `Pipfile` - Python dependencies
- `ruff.toml` - Python linting configuration
- `.prettierrc` - Code formatting rules
- `.env` / `.env.local` - Environment variables (gitignored)

## Conventions

### File Organization
- User-specific content stored under `static/{type}/{username}/`
- Generated images include metadata and thumbnails
- Chat conversations stored as JSON files

### Naming Patterns
- Python files use snake_case
- TypeScript files use camelCase for functions, PascalCase for types
- Generated images: `{sequence}-{cleaned_prompt}.png`
- Thumbnails: `{sequence}-{cleaned_prompt}.thumb.jpg`

### Code Organization
- **Flask routes**: Unified `/image` endpoint for all image operations, `/chat` for streaming responses
- **TypeScript modules**: Provider-specific UI logic with character prompt management
- **Image processing**: Structured request/response objects with comprehensive error handling
- **API clients**: Dedicated client classes (NovelAIClient, ResponsesAPIClient) with proper abstraction
- **Data models**: Pydantic models for type safety and validation across all operations
- **Conversation management**: Local thread storage with ConversationManager class and response ID tracking

### Advanced Features
- **Multi-character prompts**: Character-specific positive/negative prompts for NovelAI
- **Inpainting operations**: Mask-based image editing with provider-specific processing
- **Img2img transformations**: Image-to-image generation with strength parameters
- **Auto-generated titles**: AI-powered conversation title generation using gpt-5-nano
- **Diff highlighting**: Visual comparison between original and processed prompts
- **Metadata preservation**: Comprehensive image metadata including character prompt tracking