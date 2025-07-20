# Design Document

## Overview

This feature will automatically generate conversation titles on the server side using OpenAI's o3-mini model with minimal reasoning to keep costs low. The system will analyze the user's initial message and create a concise, descriptive title that helps users identify conversations in their chat history.

The implementation will integrate seamlessly with the existing chat flow by adding a title generation step after the first user message is processed, without blocking the conversation flow or significantly impacting response times.

## Architecture

### High-Level Flow

1. User sends first message in a new conversation
2. System creates conversation with temporary title
3. System processes user message and generates AI response (existing flow)
4. System asynchronously generates conversation title using o3-mini
5. System updates conversation with generated title
6. Frontend receives title update and refreshes display

### Integration Points

- **ResponsesAPIClient**: Add new method for title generation using o3-mini
- **ConversationManager**: Add method to update conversation titles
- **Chat Route**: Add title generation call after conversation creation
- **Frontend**: Remove manual title prompt, add title update handling

## Components and Interfaces

### TitleGenerator Class

```python
class TitleGenerator:
    """Generates conversation titles using o3-mini model."""
    
    def __init__(self, openai_client: openai.OpenAI):
        self.client = openai_client
        self.model = "o3-mini"
    
    def generate_title(self, user_message: str) -> str:
        """Generate a conversation title from the user's first message."""
        
    def _create_title_prompt(self, user_message: str) -> str:
        """Create optimized prompt for title generation."""
        
    def _sanitize_title(self, title: str) -> str:
        """Ensure title meets length and content requirements."""
```

### ResponsesAPIClient Enhancement

```python
class ResponsesAPIClient:
    # Existing methods...
    
    def generate_conversation_title(self, user_message: str) -> str:
        """Generate a conversation title using o3-mini with minimal reasoning."""
```

### ConversationManager Enhancement

```python
class ConversationManager:
    # Existing methods...
    
    def update_conversation_title(self, username: str, conversation_id: str, title: str) -> bool:
        """Update the title of an existing conversation."""
```

### Frontend API Enhancement

New endpoint for title updates:
```python
@app.route("/update-conversation-title", methods=["POST"])
def update_conversation_title():
    """Update conversation title and return updated conversation list."""
```

## Data Models

### Title Generation Request

```python
class TitleGenerationRequest(BaseModel):
    user_message: str = Field(..., max_length=4000, description="User's first message")
    max_length: int = Field(default=30, description="Maximum title length")
```

### Title Generation Response

```python
class TitleGenerationResponse(BaseModel):
    title: str = Field(..., max_length=30, description="Generated conversation title")
    fallback_used: bool = Field(default=False, description="Whether fallback title was used")
```

## Error Handling

### Title Generation Failures

1. **API Errors**: Fall back to timestamp-based title format
2. **Rate Limiting**: Use fallback title, retry in background
3. **Invalid Response**: Sanitize and truncate, or use fallback
4. **Timeout**: Use fallback title immediately

### Fallback Title Strategy

```python
def generate_fallback_title(timestamp: int) -> str:
    """Generate fallback title when AI generation fails."""
    date_str = datetime.fromtimestamp(timestamp).strftime("%m/%d %H:%M")
    return f"Chat - {date_str}"
```

### Error Recovery

- Title generation failures should not impact conversation functionality
- Failed title generations should be logged for monitoring
- System should gracefully degrade to fallback titles
- Background retry mechanism for temporary failures

## Testing Strategy

### Unit Tests

1. **TitleGenerator Tests**
   - Test title generation with various message types
   - Test prompt creation and sanitization
   - Test error handling and fallbacks
   - Test title length constraints

2. **Integration Tests**
   - Test title generation in conversation flow
   - Test frontend title updates
   - Test error scenarios and fallbacks
   - Test concurrent title generation

3. **Performance Tests**
   - Measure title generation latency
   - Test impact on conversation creation time
   - Test system behavior under load

### Test Scenarios

```python
# Test cases for different message types
test_messages = [
    "How do I implement a binary search algorithm?",  # Technical question
    "Hello, can you help me?",  # Generic greeting
    "What's the weather like?",  # Simple question
    "I need help with my Python project that involves...",  # Long message
    "Hi",  # Very short message
    "🤔 Can you explain machine learning?",  # With emojis
]
```

## Implementation Considerations

### Performance Optimization

- Use o3-mini model for cost efficiency
- Set minimal reasoning effort to reduce latency
- Implement async title generation to avoid blocking
- Cache common title patterns

### Security and Privacy

- Sanitize user input before sending to AI model
- Avoid exposing sensitive information in titles
- Implement rate limiting for title generation
- Log title generation for abuse monitoring

### Cost Management

- Use o3-mini model (cheapest option)
- Set minimal reasoning effort
- Implement request batching if needed
- Monitor API usage and costs

### Prompt Engineering

Optimized prompt for title generation:
```
Create a concise title (max 30 chars) for this conversation based on the user's message. Focus on the main topic or question. Avoid generic words like "help" or "question".

User message: {user_message}

Title:
```

## Migration Strategy

### Phase 1: Backend Implementation
- Add TitleGenerator class
- Enhance ResponsesAPIClient
- Update ConversationManager
- Add title generation to chat route

### Phase 2: Frontend Updates
- Remove manual title prompt
- Add title update handling
- Update conversation list refresh
- Handle loading states

### Phase 3: Testing and Rollout
- Comprehensive testing
- Monitor title generation performance
- Gradual rollout with fallback monitoring
- Performance optimization based on usage