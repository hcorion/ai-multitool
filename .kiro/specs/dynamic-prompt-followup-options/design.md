# Design Document

## Overview

This design implements follow-up options for the dynamic prompting system, allowing users to create prompt files with multiple columns of related options that progress sequentially. The system will maintain seed consistency for row selection while advancing through columns on subsequent uses, enabling coherent prompt progressions like color palettes, character development stages, or style variations.

Key features:
1. Column-based prompt files with header syntax: `# columns:` (column names are decorative)
2. Row format with double-pipe separators: `option1||option2||option3`
3. Seed locking mechanism for consistent row selection across uses
4. Column progression tracking per user per file
5. Shared progression across character prompts for thematic consistency
6. Frontend support in the Prompts Tab for managing follow-up files

## Architecture

### Current System Analysis

The existing `dynamic_prompts.py` system:
- Uses `get_prompt_dict()` to load all prompt files into memory
- Processes `__filename__` syntax through `replace_dynamic_prompt_section()`
- Uses seeded randomization for deterministic results
- Supports character-specific seed offsets in `make_character_prompts_dynamic()`
- Maintains grid prompt overrides through `GridDynamicPromptInfo`

### New System Design

The enhanced system will add:
- Follow-up file detection and parsing logic
- Persistent storage for seed locks and column progression
- Modified prompt selection logic for follow-up files
- Frontend enhancements for follow-up file management
- Backward compatibility with existing prompt files

## Components and Interfaces

### Data Models

#### New Data Structures

```python
@dataclass
class FollowUpPromptFile:
    """Represents a follow-up prompt file with column-based options."""
    name: str
    column_count: int  # Number of columns (determined by row parsing)
    rows: List[List[str]]  # Each row contains options for each column
    
@dataclass
class FollowUpState:
    """Tracks the state of follow-up prompt progression for a user."""
    locked_seed: int  # Seed used for row selection
    current_column: int  # Current column index (0-based)
    selected_row_index: int  # Which row was selected with the locked seed
```

#### Storage Structure

Follow-up state will be tracked in memory during generation (no persistent storage needed):
```
static/prompts/{username}/
├── colors.txt           # Regular prompt file
└── color_palette.txt    # Follow-up prompt file
```

In-memory state structure:
```python
# Tracked per generation, resets for each new generation/grid image
generation_followup_state: dict[str, FollowUpState] = {
  "color_palette": FollowUpState(
    locked_seed=12345,
    current_column=1,
    selected_row_index=2
  )
}
```

### Modified Functions

#### `get_prompt_dict()` Enhancement

```python
def get_prompt_dict(username: str, static_folder: str) -> tuple[dict[str, list[str]], dict[str, FollowUpPromptFile]]:
    """Load user's prompt files, separating regular and follow-up files."""
    # Returns: (regular_prompts, followup_prompts)
```

**Changes:**
- Parse file headers to detect follow-up files
- Separate regular and follow-up files into different dictionaries
- Parse column headers and row data for follow-up files
- Validate follow-up file format and handle errors gracefully

#### New Helper Functions

**`parse_followup_file(file_path: str) -> FollowUpPromptFile | None`**
- Reads file and checks for `# columns:` header (column names are ignored)
- Splits rows by `||` separator to determine column count
- Validates column count consistency across all rows
- Returns None for malformed files (graceful degradation)

**`init_followup_state() -> dict[str, FollowUpState]`**
- Initializes empty follow-up state for a new generation
- Returns empty dictionary to track state during generation

**`get_followup_option(file_name: str, followup_file: FollowUpPromptFile, state: dict[str, FollowUpState], base_seed: int) -> str`**
- Manages follow-up file progression logic
- Creates new state entry if file hasn't been used
- Uses locked seed for consistent row selection
- Advances column progression
- Handles cycling back to first column when all columns used

#### Modified `replace_dynamic_prompt_section()`

The function will be enhanced to handle follow-up files:

```python
def replace_dynamic_prompt_section(match: re.Match[str]) -> str:
    """Handle both regular and follow-up prompt file replacement."""
    content = match.group(1)  # The filename inside __filename__
    
    # Check if this is a follow-up file
    if content in followup_prompts:
        return get_followup_option(content, followup_prompts[content], followup_state, base_seed)
    
    # Handle regular prompt files (existing logic)
    # ...
```

### Processing Flow

#### Follow-Up File Processing Flow

1. **File Loading Phase:**
   - `get_prompt_dict()` scans all `.txt` files
   - Files with `# columns:` header are parsed as follow-up files
   - Regular files are loaded as before
   - Follow-up state is loaded from `.followup_state.json`

2. **Prompt Processing Phase:**
   - When `__filename__` is encountered, check if it's a follow-up file
   - For follow-up files:
     - Check if state exists for this file
     - If not, create new state with locked seed and select row
     - Use current column index to get option from selected row
     - Advance column index for next use
     - Save updated state
   - For regular files: use existing logic

3. **Character Prompt Handling:**
   - Follow-up files use the shared locked seed (no character offset)
   - Regular files continue to use character-specific seed offsets
   - This ensures follow-up files progress consistently across characters

### Frontend Integration

#### Prompts Tab Enhancements

**Visual Indicators:**
- Follow-up files will be marked with a special icon or badge
- Number of columns will be displayed in the file preview

**File Management:**
- Create/Edit modal will detect follow-up syntax
- Template suggestions for follow-up file format
- Validation for column header format and row consistency
- Option to reset progression state

**Enhanced File Display:**
```typescript
interface PromptFile {
    name: string;
    content: string[];
    size: number;
    isFollowUp: boolean;
    totalColumns?: number;
}
```

#### Modified API Endpoints

**`GET /prompt-files`**
- Enhanced to include follow-up file metadata (isFollowUp, totalColumns)
- No progression state needed since it resets per generation

## Error Handling

### File Format Validation

1. **Invalid Column Header:**
   - Missing `# columns:` prefix
   - **Fallback:** Treat as regular prompt file

2. **Row Format Issues:**
   - Inconsistent column counts between rows
   - Missing `||` separators
   - Empty rows
   - **Fallback:** Skip malformed rows, log warnings

### Runtime Error Handling

1. **State Inconsistencies:**
   - Column index out of bounds
   - Referenced row doesn't exist
   - **Fallback:** Reset file state, select new row

## Testing Strategy

### Unit Tests

1. **Follow-Up File Parsing:**
   - Valid column headers and row formats
   - Invalid formats and graceful degradation
   - Edge cases (empty columns, special characters)

2. **State Management:**
   - State creation, loading, and saving
   - Column progression logic
   - Cycling behavior when all columns used

3. **Integration with Existing System:**
   - Mixed regular and follow-up files
   - Character prompt processing
   - Grid generation compatibility

### Test Data Examples

**Valid Follow-Up File:**
```
# columns: primary, secondary, tertiary
warm red||cool red||deep red
bright blue||sky blue||navy blue
forest green||lime green||dark green
```

Note: The column names "primary, secondary, tertiary" are decorative and ignored by the system. The functionality is determined by the `||` separators in the data rows.

**Test Cases:**
```python
# Test progression through columns
test_cases = [
    # First use: primary column
    ("__color_palette__", "warm red"),  # Assuming row 0 selected
    # Second use: secondary column  
    ("__color_palette__", "cool red"),
    # Third use: tertiary column
    ("__color_palette__", "deep red"),
    # Fourth use: cycles back to primary
    ("__color_palette__", "warm red"),
]
```

## Implementation Notes

### Backward Compatibility

- Existing prompt files continue to work unchanged
- No breaking changes to existing API
- Follow-up files are opt-in through header syntax

### Performance Considerations

- State file I/O only occurs when follow-up files are used
- State is cached in memory during prompt processing
- File parsing happens once during loading phase

### Security Considerations

- State files are stored within user's prompt directory
- No cross-user access to follow-up states
- File path validation to prevent directory traversal

### Migration Path

Users can convert existing prompt files to follow-up format by:
1. Adding `# columns:` header (any text after the colon is decorative)
2. Converting lines to `value1||value2||value3` format
3. The system will automatically detect and handle the new format