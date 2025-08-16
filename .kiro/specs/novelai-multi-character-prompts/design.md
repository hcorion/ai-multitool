# Design Document

## Overview

This design implements support for NovelAI's multiple character prompt functionality by extending both the backend API integration and frontend user interface. The feature leverages NovelAI's existing `char_captions` array structure to allow users to define multiple characters with individual positive and negative prompts within a single image generation request.

The implementation focuses on maintaining backward compatibility with existing single-prompt functionality while adding an intuitive character management interface that appears only when NovelAI is selected as the provider.

## Architecture

### Backend Architecture

The backend extends the existing `generate_novelai_image()` function to accept and process character prompt data. The current implementation already has placeholder `char_captions` arrays in the API request structure, which will be populated with actual character data.

**Key Components:**
- **Character Data Processing**: New data structures to handle multiple character prompts
- **Dynamic Prompt Integration**: Extension of existing dynamic prompt system to work with character prompts
- **Metadata Enhancement**: Updated image metadata storage to include character prompt information
- **API Request Formatting**: Enhanced NovelAI API request builder to populate char_captions arrays

### Frontend Architecture

The frontend adds a character management interface that dynamically shows/hides based on the selected provider. The interface allows users to add, remove, and manage multiple character prompts with visibility toggles for space optimization.

**Key Components:**
- **Character Prompt Manager**: TypeScript module for managing character prompt UI
- **Dynamic UI Elements**: Character prompt sections that can be added/removed
- **Visibility Controls**: Toggle system for positive/negative prompt sections
- **Copy Functionality Enhancement**: Extended prompt copying to handle character data
- **Form Data Processing**: Enhanced form serialization to include character prompt data

## Components and Interfaces

### Backend Data Models

```python
@dataclass
class CharacterPrompt:
    positive_prompt: str
    negative_prompt: str = ""
    
@dataclass
class MultiCharacterPromptData:
    main_prompt: str
    main_negative_prompt: str = ""
    character_prompts: List[CharacterPrompt] = field(default_factory=list)
```

### Frontend Interface Components

**Character Prompt Section:**
- Character index/label
- Positive prompt textarea
- Negative prompt textarea (with visibility toggle)
- Remove character button

**Character Management Controls:**
- Add Character button
- Visibility toggle controls for positive/negative sections
- Character count indicator

### API Integration

**Enhanced NovelAI Request Structure:**
```python
"v4_prompt": {
    "caption": {
        "base_caption": main_prompt,
        "char_captions": [
            {
                "centers": [{"x": 0, "y": 0}],
                "char_caption": character_positive_prompt,
            }
            # ... additional characters
        ],
    },
    "use_coords": False,
    "use_order": True,
},
"v4_negative_prompt": {
    "caption": {
        "base_caption": main_negative_prompt,
        "char_captions": [
            {
                "centers": [{"x": 0, "y": 0}],
                "char_caption": character_negative_prompt,
            }
            # ... additional characters
        ],
    },
    "use_coords": False,
    "use_order": True,
}
```

## Data Models

### Character Prompt Data Structure

The system will use a structured approach to handle character prompt data:

**Form Data Format:**
```
character_prompts[0][positive]: "character 1 positive prompt"
character_prompts[0][negative]: "character 1 negative prompt"
character_prompts[1][positive]: "character 2 positive prompt"
character_prompts[1][negative]: "character 2 negative prompt"
```

**Internal Processing Format:**
```python
{
    "main_prompt": "main scene description",
    "main_negative_prompt": "main negative elements",
    "character_prompts": [
        {
            "positive": "character 1 description",
            "negative": "character 1 negative elements"
        },
        {
            "positive": "character 2 description", 
            "negative": "character 2 negative elements"
        }
    ]
}
```

### Metadata Storage Format

Character prompt metadata will be stored in the image metadata using a structured format. Empty negative prompts will be omitted from the metadata to keep it clean:

```python
{
    "Prompt": "main scene prompt",
    "Negative Prompt": "main negative prompt",  # Only if not empty
    "Character 1 Prompt": "character 1 positive prompt",
    "Character 1 Negative": "character 1 negative prompt",  # Only if not empty
    "Character 2 Prompt": "character 2 positive prompt",
    # Character 2 Negative omitted if empty
    # ... additional characters
}
```

## Error Handling

### Backend Error Handling

**Character Prompt Validation:**
- Validate character prompt data structure
- Handle empty character prompts gracefully
- Omit empty negative prompts from API requests and metadata
- Provide meaningful error messages for malformed character data

**API Error Handling:**
- Enhanced NovelAI API error messages for character-specific issues
- Fallback to single prompt mode if character processing fails
- Detailed logging for character prompt processing errors

### Frontend Error Handling

**UI State Management:**
- Graceful handling of character section addition/removal
- Preservation of character data during provider switches
- Recovery from invalid character prompt states

**Form Validation:**
- Character prompt length validation
- Warning for excessive character count
- Validation of character prompt structure before submission

## Testing Strategy

### Backend Testing

**Unit Tests:**
- Character prompt data structure validation
- Dynamic prompt processing with character prompts
- NovelAI API request formatting with character data
- Metadata storage and retrieval with character information

**Integration Tests:**
- End-to-end character prompt processing
- Dynamic prompt integration with character prompts
- Image generation with multiple character configurations
- Copy prompt functionality with character data

### Frontend Testing

**UI Component Tests:**
- Character section addition/removal
- Visibility toggle functionality
- Form data serialization with character prompts
- Provider switching behavior with character data

**User Interaction Tests:**
- Character prompt input and validation
- Copy prompt functionality with character data
- Dynamic character management workflows
- Responsive behavior with multiple characters

### Manual Testing Scenarios

**Basic Character Functionality:**
1. Add single character prompt and generate image
2. Add multiple character prompts and generate image
3. Toggle visibility of positive/negative sections
4. Remove character prompts and verify cleanup

**Dynamic Prompt Integration:**
1. Use dynamic prompts in character sections
2. Verify independent processing of character dynamic prompts
3. Test grid generation with character dynamic prompts

**Copy and Metadata Functionality:**
1. Generate image with character prompts
2. Verify character metadata in image details
3. Copy prompt from generated image
4. Verify character data populates correctly in interface

**Error Scenarios:**
1. Test with empty character prompts
2. Test with malformed character data
3. Test provider switching with character data
4. Test character prompt length limits