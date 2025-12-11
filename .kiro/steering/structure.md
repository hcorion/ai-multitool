# Project Structure

## Organization Principles

- **Thin route handlers**: Delegate to service functions
- **Flat over deep**: Prefer composition over inheritance
- **Explicit over clever**: Clear code beats clever abstractions
- **Don't over-split**: Jumping between files increases cognitive load

## Key Files

### Root
- `app.py` - Flask app with all endpoints
- `image_models.py` - Pydantic models for image API
- `novelai_client.py` - NovelAI API client
- `dynamic_prompts.py` - Template-based prompt system with follow-up state
- `tool_framework.py` - Agent tool registry and executor
- `error_handlers.py` - Standardized error response creation
- `file_manager_utils.py` - User file management utilities
- `utils.py` - Shared utilities

### Frontend (`src/`)
- `script.ts` - Main UI logic and image generation
- `chat.ts` - Chat functionality with streaming
- `agent-presets.ts` / `agent-preset-ui.ts` - Agent preset management
- `error-handler.ts` - Frontend error handling
- `share.ts` - Sharing functionality
- `dom_utils.ts` / `utils.ts` - Utility functions

### Inpainting (`src/inpainting/`)
- `inpainting-mask-canvas.ts` - Main canvas orchestrator
- `canvas-manager.ts` - Canvas rendering
- `brush-engine.ts` - Brush drawing logic
- `input-engine.ts` - Mouse/touch input handling
- `zoom-pan-controller.ts` - Zoom and pan controls
- `history-manager.ts` - Undo/redo support
- `mask-file-manager.ts` - Mask save/load
- `worker-manager.ts` / `mask-worker.ts` - Web worker processing

### Templates (`templates/`)
- `index.html` - Main application interface
- `login.html` - User login page
- `share.html` - Shared content display
- `result-section.html` - Image results partial

### Sass (`static/sass/`)
- `style.scss` - Main stylesheet
- `_inpainting-mask-canvas.scss` - Inpainting canvas styles
- Compiles to `static/css/`

### Tools (`tools/`)
- `calculator_tool.py` - Example agent tool implementation

### Static (`static/`)
- `js/` - Compiled TypeScript
- `css/` - Compiled Sass
- `images/{username}/` - Generated images with metadata
- `prompts/{username}/` - User prompt template files
- `chats/{username}.json` - Conversation storage

## Conventions

### Naming
- Python: `snake_case`
- TypeScript: `camelCase` functions, `PascalCase` types
- Images: `{sequence}-{prompt}.png` with `.thumb.jpg`

### API Endpoints
- `/image` - Unified image generation (generate, inpaint, img2img)
- `/chat` - Streaming chat with conversation management
- `/chat/reasoning/{id}/{index}` - Reasoning data retrieval
- `/agents` - Agent preset CRUD
- `/prompt-files` - Dynamic prompt file management
- `/save-mask` - Inpainting mask upload
