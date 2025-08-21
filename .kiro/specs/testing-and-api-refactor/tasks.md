# Implementation Plan

- [x] 1. Set up testing infrastructure and update steering documentation





  - Create pytest configuration files and test directory structure
  - Add pytest and pytest-dotenv to Pipfile dependencies
  - Update steering documentation with pytest usage guidelines and examples
  - Create basic test fixtures and configuration in conftest.py
  - _Requirements: 1.1, 1.2, 1.4, 1.5, 1.6_

- [x] 2. Create NovelAI client abstraction with core functionality




- [x] 2.1 Create NovelAIClient class with basic image generation and tests


  - Create novelai_client.py file with NovelAIClient class
  - Define NovelAIModel, NovelAIAction, and related enums
  - Implement __init__ method with API key and session management
  - Create _make_request method for handling API calls
  - Implement generate_image method in NovelAIClient
  - Create NovelAIGenerationPayload dataclass with proper typing
  - Add error handling for API responses and network issues
  - Write unit tests for generate_image functionality with mocked responses
  - Write integration test using actual API key from .env.local
  - _Requirements: 2.1, 2.2, 2.3, 1.3_



- [x] 2.2 Refactor existing generate_novelai_image function with tests





  - Update generate_novelai_image function to use NovelAIClient
  - Maintain backward compatibility with existing function signature
  - Update error handling to use new client error classes
  - Write tests for the refactored function integration
  - Test integration with existing Flask routes
  - _Requirements: 2.6, 1.3_

- [x] 3. Add inpainting support for both providers




- [x] 3.1 Implement NovelAI inpainting functionality with tests


  - Add generate_inpaint_image method to NovelAIClient
  - Create NovelAIInpaintPayload dataclass with mask and image fields
  - Implement base64 encoding for image and mask data
  - Write unit tests for inpainting functionality with mocked responses
  - Write integration test using sample images and actual API key
  - _Requirements: 2.4, 3.1, 1.3_



- [x] 3.2 Implement OpenAI inpainting functionality with tests





  - Create generate_openai_inpaint_image function using client.images.edit API
  - Reference .venv/Lib/site-packages/openai/resources/images.py for API structure
  - Handle PNG mask and base image file processing
  - Add error handling for OpenAI inpainting API responses
  - Write unit tests with mocked OpenAI responses
  - Write integration test using actual OpenAI API key


  - _Requirements: 3.1, 3.2, 3.3, 1.3_

- [x] 3.3 Rename OpenAI generation function with tests


  - Rename generate_dalle_image function to generate_openai_image
  - Update function to reflect gpt-image-1 model usage
  - Update all references to the renamed function throughout the codebase
  - Write tests to ensure existing functionality remains intact
  - Test integration with existing Flask routes
  - _Requirements: 3.4, 1.3_

- [x] 4. Add img2img support for NovelAI




- [x] 4.1 Implement img2img functionality in NovelAI client with tests


  - Add generate_img2img_image method to NovelAIClient
  - Create appropriate payload structure for img2img operations
  - Handle strength parameter and base image processing
  - Write unit tests for img2img functionality with mocked responses
  - Write integration test using sample images and actual API key
  - _Requirements: 2.5, 1.3_

- [x] 5. Create unified image endpoint and request models





- [x] 5.1 Create request/response data models with strict typing


  - Create Provider, Operation, Quality, and other enums
  - Implement ImageGenerationRequest, InpaintingRequest, and Img2ImgRequest dataclasses
  - Create ImageOperationResponse dataclass for unified responses
  - Add validation logic for request parameters
  - _Requirements: 4.3_

- [x] 5.2 Implement new /image POST endpoint and update frontend with tests


  - Create handle_image_request function for the new /image endpoint
  - Implement operation routing logic (generate, inpaint, img2img)
  - Add provider routing to appropriate generation functions
  - Handle request validation and error responses
  - Modify existing root POST route to redirect or deprecate
  - Ensure backward compatibility during transition period
  - Update frontend JavaScript to send requests to /image endpoint
  - Update request payload structure to match new data models
  - Handle new response format and error structures in frontend
  - Write Flask endpoint tests for all operation types and providers
  - Write frontend integration tests for end-to-end workflows
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 1.3_

- [ ] 6. Add error handling and custom exceptions with tests
- [ ] 6.1 Create custom exception classes with tests
  - Implement NovelAIClientError, NovelAIAPIError, and ImageProcessingError classes
  - Add proper error message formatting and status code handling
  - Create create_error_response utility function
  - Write tests for error handling scenarios and exception behavior
  - _Requirements: 2.2, 3.1, 3.2, 1.3_

- [ ] 7. Final validation and testing
  - Run comprehensive test suite across all providers and operations
  - Validate that all requirements are met and functionality works correctly
  - Test end-to-end workflows to ensure complete integration
  - _Requirements: 1.3, 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 3.1, 3.2, 3.3, 3.4, 4.1, 4.2, 4.3, 4.4, 4.5_