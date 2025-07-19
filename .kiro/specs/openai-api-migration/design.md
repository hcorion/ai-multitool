# Design Document

## Overview

This design document outlines the migration from the OpenAI Assistants API to the new OpenAI Responses API with the o1-mini model. The migration involves replacing the current thread-based conversation management with a stateless approach using response IDs for conversation continuity, while maintaining all existing functionality and user experience.

The current system relies on OpenAI's built-in thread persistence, but the Responses API requires us to manage conversation state locally using the `previous_response_id` parameter to maintain context between messages.

## Architecture

### Current Architecture (Assistants API)
```
User Message → Flask Route → Assistants API (Thread + Assistant) → Streaming Response → Local Storage
                                    ↓
                            OpenAI manages thread state
```

### New Architecture (Responses API)
```
User Message → Flask Route → Local Thread Management → Responses API → Streaming Response → Local Storage
                                    ↓                        ↓
                            Local conversation state    Response ID tracking
```

### Key Architectural Changes

1. **State Management**: Move from OpenAI-managed threads to local conversation storage
2. **API Interface**: Replace Assistants API calls with Responses API calls
3. **Conversation Continuity**: Use `previous_response_id` instead of thread context
4. **Model Selection**: Switch from assistant-based model to direct o1-mini model usage

## Components and Interfaces

### 1. Conversation Storage Manager

**Purpose**: Manage local conversation state and response ID tracking

**Interface**:
```python
class ConversationManager:
    def create_conversation(self, username: str, chat_name: str) -> str
    def get_conversation(self, username: str, conversation_id: str) -> dict
    def add_message(self, username: str, conversation_id: str, role: str, content: str, response_id: str = None) -> None
    def get_last_response_id(self, username: str, conversation_id: str) -> str | None
    def update_conversation_metadata(self, username: str, conversation_id: str, **kwargs) -> None
    def list_conversations(self, username: str) -> dict
```

**Implementation Details**:
- Maintains existing JSON file structure in `static/chats/{username}.json`
- Stores response IDs alongside message content
- Preserves existing metadata format for UI compatibility
- Handles conversation creation with unique IDs

### 2. Responses API Client

**Purpose**: Interface with OpenAI Responses API for chat functionality

**Interface**:
```python
class ResponsesAPIClient:
    def create_response(self, input_text: str, previous_response_id: str = None, stream: bool = True) -> Response | Stream
    def process_stream_events(self, stream: Stream) -> Generator[dict, None, None]
    def handle_api_errors(self, error: Exception) -> dict
```

**Implementation Details**:
- Uses `client.responses.create()` with o1-mini model
- Handles streaming with `ResponseStreamEvent` processing
- Manages `previous_response_id` parameter for conversation continuity
- Implements proper error handling for new API

### 3. Stream Event Processor

**Purpose**: Process streaming responses from the Responses API

**Interface**:
```python
class StreamEventProcessor:
    def __init__(self, event_queue: Queue)
    def process_stream(self, stream: Stream) -> None
    def handle_text_created(self, event: ResponseStreamEvent) -> None
    def handle_text_delta(self, event: ResponseStreamEvent) -> None
    def handle_text_done(self, event: ResponseStreamEvent) -> None
```

**Implementation Details**:
- Replaces `AssistantEventHandler` with Responses API event handling
- Maintains existing event queue mechanism for frontend compatibility
- Processes different `ResponseStreamEvent` types
- Extracts response IDs for conversation continuity

### 4. Migration Compatibility Layer

**Purpose**: Ensure existing frontend and data structures continue to work

**Interface**:
```python
class CompatibilityLayer:
    def format_message_list(self, conversation_data: dict) -> list[dict]
    def format_conversation_metadata(self, conversation_data: dict) -> dict
    def migrate_existing_conversations(self, username: str) -> None
```

**Implementation Details**:
- Maintains existing JSON structure for frontend compatibility
- Provides data format translation between old and new systems
- Handles migration of existing conversation data if needed

## Data Models

### Conversation Data Structure

**New Enhanced Structure**:
```python
{
    "conversation_id": {
        "data": {
            "id": "conversation_id",
            "created_at": timestamp,
            "metadata": {},
            "object": "conversation"
        },
        "chat_name": "User Chat Name",
        "last_update": timestamp,
        "messages": [
            {
                "role": "user",
                "text": "User message content",
                "timestamp": timestamp,
                "response_id": None
            },
            {
                "role": "assistant", 
                "text": "Assistant response content",
                "timestamp": timestamp,
                "response_id": "resp_abc123"
            }
        ],
        "last_response_id": "resp_abc123"
    }
}
```

**Key Changes**:
- Added `messages` array to store full conversation history locally
- Added `response_id` field to track OpenAI response IDs
- Added `last_response_id` for conversation continuity
- Maintained existing metadata structure for compatibility

### Response Stream Event Mapping

**Current Assistants API Events** → **New Responses API Events**:
- `on_text_created` → Handle `text_created` event type
- `on_text_delta` → Handle `text_delta` event type  
- `on_text_done` → Handle `text_done` event type
- Tool calls → Handle function calling events (if needed)

## Error Handling

### API Error Management

1. **Rate Limiting**: Implement exponential backoff and user notification
2. **Network Errors**: Provide retry mechanisms and offline indicators
3. **Model Unavailability**: Handle o1-mini specific errors gracefully
4. **Streaming Interruptions**: Recover partial responses and allow continuation

### Data Consistency

1. **File System Errors**: Handle JSON file corruption and backup/recovery
2. **Conversation State**: Ensure atomic updates to conversation data
3. **Response ID Tracking**: Handle missing or invalid response IDs

## Testing Strategy

### Unit Tests

1. **ConversationManager**: Test all CRUD operations and edge cases
2. **ResponsesAPIClient**: Mock API responses and test error handling
3. **StreamEventProcessor**: Test event processing and queue management
4. **CompatibilityLayer**: Test data format conversions

### Integration Tests

1. **End-to-End Chat Flow**: Test complete conversation lifecycle
2. **Streaming Functionality**: Test real-time response streaming
3. **Conversation Persistence**: Test data storage and retrieval
4. **Error Scenarios**: Test various failure modes and recovery

### Migration Testing

1. **Backward Compatibility**: Ensure existing conversations still work
2. **Data Migration**: Test conversion of existing conversation data
3. **Frontend Compatibility**: Verify UI continues to function correctly

## Implementation Phases

### Phase 1: Core Infrastructure
- Implement `ConversationManager` class
- Create `ResponsesAPIClient` wrapper
- Set up basic Responses API integration
- Implement local conversation storage

### Phase 2: Streaming and Events
- Implement `StreamEventProcessor`
- Replace `AssistantEventHandler` with new event handling
- Ensure streaming functionality works with new API
- Test real-time response processing

### Phase 3: API Migration
- Replace all Assistants API calls with Responses API calls
- Update chat route to use new conversation management
- Implement o1-mini model integration
- Remove deprecated API dependencies

### Phase 4: Compatibility and Testing
- Implement `CompatibilityLayer` for existing data
- Comprehensive testing of all functionality
- Performance optimization and error handling
- Documentation and cleanup

## Security Considerations

1. **API Key Management**: Ensure secure handling of OpenAI API keys
2. **User Data Protection**: Maintain existing user data isolation
3. **Input Validation**: Validate all user inputs before API calls
4. **Error Information**: Avoid exposing sensitive API details in error messages

## Performance Considerations

1. **Response Time**: Optimize conversation loading and message processing
2. **Memory Usage**: Efficient handling of conversation history and streaming data
3. **File I/O**: Optimize JSON file operations for conversation storage
4. **Concurrent Requests**: Handle multiple simultaneous chat requests efficiently

## Monitoring and Observability

1. **API Usage Tracking**: Monitor Responses API usage and costs
2. **Error Logging**: Comprehensive logging of API errors and system issues
3. **Performance Metrics**: Track response times and system performance
4. **User Experience**: Monitor chat functionality and user satisfaction