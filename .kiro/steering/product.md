# AI Multitool

A web-based frontend for interacting with multiple AI image generation services including OpenAI's GPT-Image-1, StabilityAI's Stable Diffusion, and NovelAI's image generation models.

## Core Features

- **Multi-provider image generation**: Supports OpenAI, StabilityAI, and NovelAI backends with unified API
- **Advanced image operations**: Text-to-image generation, inpainting, and img2img transformations
- **Multi-character prompt system**: NovelAI-specific character-based prompt management with individual positive/negative prompts
- **Dynamic prompt system**: Template-based prompts with randomization and user-specific customization
- **Grid generation**: Batch image generation with different prompt variations
- **Image gallery**: Browse and manage generated images with comprehensive metadata
- **Chat interface**: OpenAI Responses API integration with GPT-5 model for conversational AI
- **Auto-generated conversation titles**: Automatic title generation for chat conversations using gpt-5-nano
- **Image sharing**: Share generated images and conversations via URLs

## Key Capabilities

### Image Generation
- Text-to-image generation with various quality and style options
- **Inpainting operations**: Edit specific regions of images using mask-based editing (OpenAI and NovelAI)
- **Img2img transformations**: Transform existing images with new prompts (NovelAI)
- Negative prompting support for StabilityAI and NovelAI
- **Character-specific prompts**: Multi-character prompt system for NovelAI with individual character control
- Image upscaling for supported providers
- Prompt metadata preservation with character prompt tracking
- **Unified image API**: Structured request/response system with proper error handling

### Chat & Conversation Management
- **OpenAI Responses API**: Modern API integration with gpt-5 model for enhanced reasoning
- Real-time streaming chat responses with proper event handling
- **Local conversation management**: Thread-based conversation storage with response ID tracking
- **Automatic conversation titles**: AI-generated conversation titles using o3-mini model
- Conversation sharing and persistence
- User session management with personalized conversation storage

### User Experience
- **Provider-specific interfaces**: Dynamic UI adaptation based on selected image generation provider
- **Character prompt management**: Add/remove character prompts with visual indicators and validation
- **Advanced metadata display**: Comprehensive image metadata with character prompt differentiation
- **Copy prompt functionality**: Transfer image metadata back to generation interface including character prompts
- **Diff highlighting**: Visual comparison between original and processed prompts