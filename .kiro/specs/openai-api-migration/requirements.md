# Requirements Document

## Introduction

This feature involves migrating the AI Multitool's chat functionality from the deprecated OpenAI Assistants API to the new OpenAI Responses API, while also upgrading to use the o4-mini model. The migration requires implementing our own conversation thread management since the Responses API uses a stateless approach with `previous_response_id` for conversation continuity, unlike the Assistants API which provided built-in thread persistence.

The current system uses the OpenAI Assistants API with features like thread management, streaming responses, and conversation persistence. The new Responses API provides similar capabilities but with a different architecture that requires us to manage conversation state ourselves.

## Requirements

### Requirement 1: API Migration

**User Story:** As a user, I want to continue having conversations with the AI chat interface so that I can interact with the AI assistant functionality without interruption.

#### Acceptance Criteria

1. WHEN a user sends a chat message THEN the system SHALL use the OpenAI Responses API (`client.responses.create()`) instead of the Assistants API
2. WHEN a user sends a chat message THEN the system SHALL use the "o4-mini" model for generating responses
3. WHEN a user interacts with the chat interface THEN the functionality SHALL remain identical to the current experience
4. WHEN a user sends multiple messages in a conversation THEN the system SHALL maintain conversation context using the `previous_response_id` parameter
5. WHEN making API calls THEN the system SHALL use the `input` parameter to send user messages instead of the Assistants API message format
6. WHEN configuring responses THEN the system SHALL use appropriate parameters like `instructions` for system messages and `stream=True` for real-time responses

### Requirement 2: Conversation Thread Management

**User Story:** As a user, I want my conversation history to be preserved so that I can reference previous messages and maintain context in ongoing conversations.

#### Acceptance Criteria

1. WHEN a user starts a new conversation THEN the system SHALL create a new conversation thread with a unique identifier and store it locally
2. WHEN a user sends a message in an existing conversation THEN the system SHALL append the message to the local conversation history
3. WHEN the AI responds to a message THEN the system SHALL store both the response ID and content in the conversation history
4. WHEN a user selects a previous conversation THEN the system SHALL load and display the complete conversation history from local storage
5. WHEN conversation data is stored THEN it SHALL include message content, timestamps, role information (user/assistant), and OpenAI response IDs
6. WHEN continuing a conversation THEN the system SHALL use the last response ID as the `previous_response_id` parameter
7. WHEN storing conversations THEN the system SHALL maintain the existing file structure in `static/chats/{username}/` directory
8. WHEN conversation metadata is needed THEN the system SHALL store chat names, creation dates, and last update timestamps

### Requirement 3: Real-time Streaming Responses

**User Story:** As a user, I want real-time streaming responses from the AI so that I can see the response being generated in real-time rather than waiting for the complete response.

#### Acceptance Criteria

1. WHEN the AI generates a response THEN the system SHALL stream the response in real-time using `client.responses.create(stream=True)`
2. WHEN streaming a response THEN the system SHALL process `ResponseStreamEvent` objects to extract text deltas
3. WHEN streaming is active THEN the system SHALL update the UI incrementally as tokens are received via the existing streaming mechanism
4. WHEN streaming is complete THEN the system SHALL mark the message as complete and enable user input
5. WHEN streaming encounters an error THEN the system SHALL handle the error gracefully and display an appropriate message
6. WHEN processing stream events THEN the system SHALL handle different event types (text_created, text_delta, text_done) appropriately
7. WHEN a stream completes THEN the system SHALL store the final response ID for use in subsequent conversation turns

### Requirement 4: Data Format Compatibility

**User Story:** As a developer, I want the conversation storage system to be compatible with the existing chat interface so that users don't experience any breaking changes.

#### Acceptance Criteria

1. WHEN implementing the new conversation storage THEN it SHALL maintain compatibility with existing conversation list functionality
2. WHEN storing conversations THEN the data format SHALL include all necessary metadata for the chat interface (chat_name, created_at, last_update)
3. WHEN loading conversations THEN the system SHALL populate the conversation list with chat names and creation dates using the existing format
4. WHEN sharing conversations THEN the existing sharing functionality SHALL continue to work without modification
5. WHEN accessing conversation data THEN the system SHALL use the same JSON structure as the current implementation
6. WHEN displaying conversation history THEN the system SHALL use the existing message format with role and text fields
7. WHEN managing conversation metadata THEN the system SHALL preserve the existing ThreadData and ConversationData structures

### Requirement 5: Complete API Deprecation

**User Story:** As a system administrator, I want the migration to remove dependencies on deprecated APIs so that the system remains functional and maintainable.

#### Acceptance Criteria

1. WHEN the migration is complete THEN the system SHALL no longer use any OpenAI Assistants API endpoints (threads, messages, runs)
2. WHEN the migration is complete THEN all OpenAI API calls SHALL use the Responses API (`client.responses.create()`)
3. WHEN the migration is complete THEN the system SHALL use the "o4-mini" model for all chat interactions
4. WHEN the migration is complete THEN any Assistants API-specific code SHALL be removed (AssistantEventHandler, thread management, run polling)
5. WHEN the migration is complete THEN imports related to Assistants API SHALL be removed from the codebase
6. WHEN the migration is complete THEN the system SHALL no longer depend on assistant IDs or thread IDs from OpenAI
7. WHEN the migration is complete THEN conversation continuity SHALL be managed entirely through local storage and response IDs

### Requirement 6: Error Handling and Resilience

**User Story:** As a user, I want error handling to work properly so that I receive appropriate feedback when something goes wrong with the chat functionality.

#### Acceptance Criteria

1. WHEN an API call fails THEN the system SHALL display a user-friendly error message without exposing technical details
2. WHEN rate limits are exceeded THEN the system SHALL handle the error gracefully and inform the user to wait before retrying
3. WHEN network connectivity issues occur THEN the system SHALL provide appropriate feedback and allow retry attempts
4. WHEN conversation loading fails THEN the system SHALL handle the error without breaking the interface
5. WHEN streaming is interrupted THEN the system SHALL handle partial responses gracefully and allow conversation continuation
6. WHEN response parsing fails THEN the system SHALL log the error and provide fallback behavior
7. WHEN local storage operations fail THEN the system SHALL handle file system errors and provide appropriate user feedback
8. WHEN the o4-mini model is unavailable THEN the system SHALL provide clear error messaging about model availability

### Requirement 7: Performance and Optimization

**User Story:** As a user, I want the chat interface to remain responsive and performant after the API migration.

#### Acceptance Criteria

1. WHEN loading conversation lists THEN the system SHALL maintain current performance levels or better
2. WHEN streaming responses THEN the system SHALL process tokens efficiently without UI lag
3. WHEN storing conversation data THEN the system SHALL optimize file I/O operations to prevent blocking
4. WHEN switching between conversations THEN the system SHALL load conversation history quickly
5. WHEN handling large conversation histories THEN the system SHALL implement appropriate pagination or truncation
6. WHEN managing multiple concurrent requests THEN the system SHALL handle them efficiently without degrading performance
7. WHEN using the o4-mini model THEN the system SHALL account for any model-specific performance characteristics