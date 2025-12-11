# AI Multitool

Web frontend for AI image generation (OpenAI, StabilityAI, NovelAI) and chat (GPT-5 via Responses API).

## Features

### Image Generation
- Multi-provider support with unified `/image` API
- Text-to-image, inpainting, img2img operations
- Multi-character prompts (NovelAI)
- Dynamic prompt templates with randomization and follow-up options
- Grid generation for batch variations
- Metadata preservation and gallery browsing

### Chat
- GPT-5 streaming via Responses API
- Local conversation storage with auto-generated titles
- Web search integration and reasoning inspection modal
- Agent presets with configurable tools and reasoning levels

### Inpainting Canvas
- Full-featured mask editor with brush tools
- Zoom/pan controls and undo/redo history
- Web worker-based mask processing
- Mask save/load functionality

### UI
- Provider-specific form interfaces
- Prompt diff highlighting (original vs processed)
- Copy image metadata back to generation form
- Dynamic prompt file editor
