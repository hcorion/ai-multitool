# Design Document

## Overview

This design implements agent presets and reasoning level controls for the AI Multitool chat interface. The solution extends the existing chat system to support multiple agent configurations with custom instructions and reasoning levels, while maintaining backward compatibility with the current OpenAI Responses API integration.

## Architecture

### Backend Components

#### Agent Preset Management
- **AgentPreset Model**: Pydantic model for agent configuration data
- **AgentPresetManager**: Service class for CRUD operations on agent presets
- **Storage**: JSON file-based storage in `static/agents/{username}/` directory
- **API Endpoints**: RESTful endpoints for agent preset management

#### Reasoning Level Integration
- **ResponsesAPIClient Enhancement**: Extend existing client to accept model and reasoning level parameters
- **Chat Endpoint Modification**: Update `/chat` endpoint to handle agent preset and reasoning level selection
- **Message Storage**: Extend ChatMessage model to store reasoning level metadata

### Frontend Components

#### Agent Preset Interface
- **Agent Selector**: Dropdown/selector for choosing active agent preset
- **Agent Management Modal**: Interface for creating, editing, and deleting agent presets
- **Preset Configuration Form**: Form for setting agent instructions and default reasoning level

#### Reasoning Level Controls
- **Message-Level Override**: Per-message reasoning level selector in chat input area
- **Visual Indicators**: Display current agent and reasoning level in chat interface
- **Status Display**: Show active agent preset and reasoning level in chat header

## Components and Interfaces

### Data Models

```python
class AgentPreset(BaseModel):
    """Pydantic model for agent preset configuration."""
    id: str = Field(..., description="Unique identifier for the preset")
    name: str = Field(..., description="User-friendly name for the preset")
    instructions: str = Field(..., description="System instructions for the agent")
    model: str = Field(
        default="gpt-5", 
        description="Model to use (gpt-5, gpt-5-mini, gpt-5-pro)"
    )
    default_reasoning_level: str = Field(
        default="medium", 
        description="Default reasoning level (high, medium, low)"
    )
    created_at: int = Field(..., description="Unix timestamp of creation")
    updated_at: int = Field(..., description="Unix timestamp of last update")

class ChatMessage(BaseModel):
    """Extended ChatMessage model with agent and reasoning tracking."""
    # ... existing fields ...
    agent_preset_id: str | None = Field(
        None, description="ID of agent preset used for this message"
    )
    model: str | None = Field(
        None, description="Model used for this message"
    )
    reasoning_level: str | None = Field(
        None, description="Reasoning level used for this message"
    )
```

### Backend Services

```python
class AgentPresetManager:
    """Manages agent preset storage and operations."""
    
    def __init__(self, static_folder: str):
        self.static_folder = static_folder
        self.agents_dir = os.path.join(static_folder, "agents")
    
    def create_preset(self, username: str, preset: AgentPreset) -> str:
        """Create a new agent preset."""
        
    def get_preset(self, username: str, preset_id: str) -> AgentPreset | None:
        """Retrieve a specific agent preset."""
        
    def list_presets(self, username: str) -> List[AgentPreset]:
        """List all agent presets for a user."""
        
    def update_preset(self, username: str, preset: AgentPreset) -> bool:
        """Update an existing agent preset."""
        
    def delete_preset(self, username: str, preset_id: str) -> bool:
        """Delete an agent preset."""
```

### API Endpoints

```python
@app.route("/agents", methods=["GET", "POST"])
def manage_agent_presets():
    """Handle agent preset CRUD operations."""

@app.route("/agents/<preset_id>", methods=["GET", "PUT", "DELETE"])
def handle_agent_preset(preset_id: str):
    """Handle individual agent preset operations."""
```

### Frontend TypeScript Interfaces

```typescript
interface AgentPreset {
    id: string;
    name: string;
    instructions: string;
    model: 'gpt-5' | 'gpt-5-mini' | 'gpt-5-pro';
    default_reasoning_level: 'high' | 'medium' | 'low';
    created_at: number;
    updated_at: number;
}

interface ChatState {
    activeAgentPreset: AgentPreset | null;
    messageReasoningLevel: 'high' | 'medium' | 'low' | null;
}
```

## Data Models

### Agent Preset Storage Structure
```json
{
    "presets": {
        "preset-id-1": {
            "id": "preset-id-1",
            "name": "Code Assistant",
            "instructions": "You are a helpful coding assistant...",
            "model": "gpt-5-pro",
            "default_reasoning_level": "high",
            "created_at": 1640995200,
            "updated_at": 1640995200
        }
    }
}
```

### Enhanced Chat Message Format
```json
{
    "role": "assistant",
    "text": "Response text...",
    "timestamp": 1640995200,
    "response_id": "resp_123",
    "agent_preset_id": "preset-id-1",
    "model": "gpt-5-pro",
    "reasoning_level": "high",
    "reasoning_data": { ... }
}
```

## Error Handling

### Backend Error Scenarios
- **Invalid Agent Preset**: Return 404 for non-existent presets
- **Storage Failures**: Graceful degradation with default agent
- **Invalid Reasoning Level**: Fallback to preset default or system default
- **Concurrent Access**: File locking for agent preset modifications

### Frontend Error Handling
- **Network Failures**: Retry logic for agent preset operations
- **Invalid Selections**: Validation before sending chat requests
- **Missing Presets**: Fallback to default agent with user notification

## Testing Strategy

### Backend Tests
- **Unit Tests**: AgentPresetManager CRUD operations
- **Integration Tests**: Agent preset API endpoints
- **Chat Integration**: Reasoning level parameter passing
- **Storage Tests**: File-based persistence and concurrent access

### Frontend Tests
- **Component Tests**: Agent selector and management modal
- **Integration Tests**: Chat flow with agent presets and reasoning levels
- **User Interaction Tests**: Preset creation, editing, and deletion workflows
- **State Management Tests**: Agent preset and reasoning level state handling

### Test Data
- **Sample Presets**: Various agent configurations for testing
- **Edge Cases**: Empty instructions, invalid reasoning levels
- **Performance Tests**: Large numbers of agent presets
- **Concurrent Usage**: Multiple users managing presets simultaneously

## Implementation Notes

### Default Agent Preset
The system will include a built-in "Default Assistant" preset that:
- Cannot be deleted or modified
- Uses the current system instructions
- Uses "gpt-5" as the default model
- Has "medium" as default reasoning level
- Serves as fallback when no preset is selected

### Model Selection
Each agent preset can specify one of three available models:
- **gpt-5**: Standard model for general conversations
- **gpt-5-mini**: Faster, more cost-effective model for simple tasks
- **gpt-5-pro**: Advanced model for complex reasoning and analysis

### Reasoning Level Mapping
- **High**: `{"effort": "high", "summary": "detailed"}`
- **Medium**: `{"effort": "medium", "summary": "detailed"}`
- **Low**: `{"effort": "low", "summary": "concise"}`

### Migration Strategy
- Existing conversations continue to work without agent preset data
- New conversations automatically use selected agent preset
- Gradual rollout with feature flags for testing

### Performance Considerations
- Agent presets cached in memory with TTL
- Lazy loading of preset data in frontend
- Minimal impact on existing chat performance
- Efficient storage format for quick access