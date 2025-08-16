# Requirements Document

## Introduction

This feature adds support for NovelAI's multiple character prompt functionality to the AI Multitool. NovelAI's image generation API supports defining multiple characters within a single prompt using char_captions arrays, allowing for more complex scene generation with multiple distinct characters. This enhancement will extend both the backend API integration and frontend user interface to support creating, managing, and generating images with multiple character definitions.

## Requirements

### Requirement 1

**User Story:** As a user generating images with NovelAI, I want to define multiple characters in a single prompt, so that I can create complex scenes with multiple distinct characters.

#### Acceptance Criteria

1. WHEN a user selects NovelAI as the image generation provider THEN the system SHALL display a character prompt interface
2. WHEN a user adds a character prompt THEN the system SHALL allow defining both positive and negative prompts for that character
3. WHEN a user submits a multi-character prompt THEN the backend SHALL format the request using NovelAI's char_captions array structure
4. WHEN an image is generated with character prompts THEN the system SHALL preserve character prompt metadata in the generated image
5. WHEN a user enters dynamic prompt syntax in character prompts THEN the system SHALL process the dynamic prompts for each character independently

### Requirement 2

**User Story:** As a user managing character prompts, I want to add and remove character definitions dynamically, so that I can experiment with different character combinations.

#### Acceptance Criteria

1. WHEN a user clicks "Add Character" THEN the system SHALL create a new character prompt input section
2. WHEN a user clicks "Remove Character" on a character section THEN the system SHALL remove that character's prompt inputs
3. WHEN a user has multiple characters defined THEN the system SHALL maintain separate positive and negative prompts for each character
4. WHEN a user removes all characters THEN the system SHALL fall back to the standard single prompt interface

### Requirement 3

**User Story:** As a user working with character prompts, I want to toggle the visibility of positive and negative prompt sections, so that I can optimize screen space and focus on the prompts I'm actively editing.

#### Acceptance Criteria

1. WHEN a user views character prompt sections THEN the system SHALL provide toggle controls for positive and negative prompt visibility
2. WHEN a user toggles negative prompt visibility THEN the system SHALL show or hide negative prompt inputs while preserving their values
3. WHEN negative prompts are hidden THEN the system SHALL indicate their presence with a visual indicator if they contain content
4. WHEN a user toggles prompt visibility THEN the system SHALL remember the visibility state during the session

### Requirement 4

**User Story:** As a user copying prompts from generated images, I want the copy functionality to transfer character data to the image prompt interface, so that I can regenerate images with the same multi-character configuration.

#### Acceptance Criteria

1. WHEN a user clicks "Copy Prompt" on an image with character data THEN the system SHALL populate the image prompt interface with all character prompt information
2. WHEN character prompts are copied to the interface THEN the system SHALL recreate the same number of character sections with their respective positive and negative prompts
3. WHEN copying prompts with both main and character prompts THEN the system SHALL populate both the main prompt fields and character prompt sections
4. WHEN character prompt data is copied THEN the system SHALL maintain the original structure and content of each character's prompts

### Requirement 5

**User Story:** As a user viewing generated images, I want to see character prompt metadata preserved in image details, so that I can understand how multi-character images were created.

#### Acceptance Criteria

1. WHEN an image is generated with character prompts THEN the system SHALL store character prompt data in the image metadata
2. WHEN a user views image details THEN the system SHALL display character prompt information alongside standard prompt metadata
3. WHEN character metadata is displayed THEN the system SHALL clearly distinguish between different characters and their respective prompts
4. WHEN sharing images with character prompts THEN the system SHALL include character prompt information in the shared metadata

### Requirement 6

**User Story:** As a developer integrating with NovelAI's API, I want the backend to properly format multi-character requests, so that the API calls are structured correctly for NovelAI's char_captions format.

#### Acceptance Criteria

1. WHEN the backend receives a multi-character prompt request THEN the system SHALL format it using NovelAI's char_captions array structure
2. WHEN character prompts are empty or undefined THEN the system SHALL omit them from the API request
3. WHEN both main prompts and character prompts are provided THEN the system SHALL include both in the properly structured API call
4. WHEN the NovelAI API returns an error for character prompts THEN the system SHALL provide meaningful error messages to the user

