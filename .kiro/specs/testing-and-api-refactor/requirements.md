# Requirements Document

## Introduction

This feature focuses on establishing proper testing infrastructure for the AI Multitool application and refactoring the NovelAI API integration to support advanced image generation capabilities. The work includes setting up pytest-based testing, abstracting NovelAI functionality into a dedicated client class, adding support for inpainting and img2img operations, and restructuring the Flask endpoints to be more modular and extensible.

## Requirements

### Requirement 1

**User Story:** As a developer, I want updated steering documentation and proper testing infrastructure so that future development follows established patterns and tests can be written consistently.

#### Acceptance Criteria

1. WHEN the project is set up THEN it SHALL include pytest as the testing framework in the pipenv dependencies
2. WHEN tests are run THEN the system SHALL automatically load environment variables from .env.local using pytest-dotenv
3. WHEN developers write tests THEN they SHALL be able to test actual API functionality using real API keys from the environment
4. WHEN the steering documentation is updated THEN it SHALL include pytest usage guidelines
5. WHEN the steering documentation is updated THEN it SHALL explain how to write tests that use actual API keys
6. WHEN the steering documentation is updated THEN it SHALL provide examples of proper test structure and organization

### Requirement 2

**User Story:** As a developer, I want the NovelAI API functionality abstracted into a separate client class so that the code is more maintainable and extensible.

#### Acceptance Criteria

1. WHEN the NovelAI functionality is refactored THEN it SHALL be moved to a separate novelai_client.py file
2. WHEN the NovelAI client is created THEN it SHALL implement a NovelAIClient class that encapsulates all API interactions
3. WHEN the NovelAI client is implemented THEN it SHALL support regular text-to-image generation
4. WHEN the NovelAI client is implemented THEN it SHALL provide backend interfaces for inpainting operations
5. WHEN the NovelAI client is implemented THEN it SHALL provide backend interfaces for img2img operations
6. WHEN the existing generate_novelai_image function is refactored THEN it SHALL use the new NovelAIClient class

### Requirement 3

**User Story:** As a developer, I want backend support for inpainting operations so that the application can support advanced image editing capabilities.

#### Acceptance Criteria

1. WHEN inpainting is implemented THEN it SHALL support both NovelAI and OpenAI providers
2. WHEN OpenAI inpainting is implemented THEN it SHALL use the client.images.edit API correctly [reference: .venv/Lib/site-packages/openai/resources/images.py]
3. WHEN inpainting operations are performed THEN they SHALL accept PNG mask and base image location parameters
4. WHEN the OpenAI image generation is updated THEN the function SHALL be renamed from generate_dalle_image to reflect the new gpt-image-1 model

### Requirement 4

**User Story:** As a developer, I want the Flask endpoints restructured so that image generation is not the primary focus of the root endpoint and all image operations are consolidated.

#### Acceptance Criteria

1. WHEN the endpoints are restructured THEN the root POST endpoint SHALL no longer handle image generation
2. WHEN the new endpoint structure is implemented THEN all image generation SHALL use the POST /image endpoint
3. WHEN the /image endpoint is created THEN it SHALL handle regular generation, inpainting, and img2img operations
4. WHEN inpainting requests are made THEN they SHALL send PNG mask and base image location data through the /image endpoint
5. WHEN the endpoint restructuring is complete THEN the frontend SHALL be updated to use the new /image endpoint

