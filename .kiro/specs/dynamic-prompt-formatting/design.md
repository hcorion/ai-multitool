# Design Document

## Overview

This design implements a new dynamic prompt formatting system that replaces the current bracket duplication logic with a more intuitive syntax. The new system will support decimal emphasis ranges and inline choice options while maintaining the existing file-based dynamic prompt functionality.

The key changes are:
1. Replace `{content:count}` and `[content:count]` with `min-max::content::` range syntax
2. Add support for inline choice options using `{option1|option2}` syntax
3. Compile decimal ranges to specific values with two decimal places
4. Maintain compatibility with existing `__filename__` dynamic prompt files

## Architecture

### Current System Analysis

The existing `dynamic_prompts.py` system uses:
- `__filename__` syntax for file-based dynamic prompts
- `{content:count}` for positive emphasis brackets
- `[content:count]` for negative emphasis brackets  
- Recursive processing for nested dynamic elements
- Seeded randomization for deterministic results

### New System Design

The new system will modify the existing architecture to:
- Remove bracket duplication logic entirely
- Add decimal range processing for emphasis
- Add inline choice option processing
- Maintain all existing functionality for file-based prompts

## Components and Interfaces

### Modified Functions

#### `make_prompt_dynamic()`
**Current Signature:**
```python
def make_prompt_dynamic(
    prompt: str,
    username: str, 
    static_folder: str,
    seed: int,
    grid_prompt: GridDynamicPromptInfo | None = None,
) -> str
```

**Changes:**
- Remove `replace_brackets_section_positive()` and `replace_brackets_section_negative()` functions
- Add `replace_emphasis_range_section()` function for new `min-max::content::` syntax
- Add `replace_choice_options()` function for new `{option1|option2}` syntax
- Update regex patterns to match new syntax

#### New Helper Functions

**`replace_emphasis_range_section(match: re.Match[str]) -> str`**
- Processes `min-max::content::` syntax
- Generates random decimal between min and max (2 decimal places)
- Returns formatted `value::content::` for backend API
- Handles single values like `2.0::content::`

**`replace_choice_options(match: re.Match[str]) -> str`**
- Processes `{option1|option2|option3}` syntax
- Randomly selects one option from pipe-separated list
- Preserves spacing and special characters in options
- Handles empty options gracefully

### Processing Order

The new processing order will be:
1. **Dynamic prompt files** (`__filename__`) - unchanged
2. **Choice options** (`{option1|option2}`) - new
3. **Emphasis ranges** (`min-max::content::`) - new
4. **Recursive processing** for nested elements - unchanged

This order ensures that:
- File-based prompts are resolved first
- Choice options within files are processed
- Emphasis is applied to final content
- Nested structures work correctly

## Data Models

### Regex Patterns

**New Patterns:**
```python
# Emphasis range pattern: 1.5-2.0::content:: or 2.0::content::
EMPHASIS_RANGE_PATTERN = r'(\d+\.?\d*)-?(\d+\.?\d*)?::(.+?)::'

# Choice options pattern: {option1|option2|option3}
CHOICE_OPTIONS_PATTERN = r'\{([^}]+\|[^}]+)\}'
```

**Removed Patterns:**
```python
# These will be completely removed:
# r'{(.+?):(\d+-?\d*)}'  # Positive emphasis brackets
# r'\[(.+?):(\d+-?\d*)\]'  # Negative emphasis brackets
```

### Data Structures

No changes to existing data structures:
- `GridDynamicPromptInfo` remains unchanged
- Character prompt processing remains unchanged
- Prompt dictionary structure remains unchanged

## Error Handling

### New Error Cases

1. **Invalid emphasis range syntax:**
   - `1.5-::content::` (missing max value)
   - `::content::` (missing emphasis value)
   - `abc::content::` (non-numeric emphasis)

2. **Invalid choice options:**
   - `{option1}` (no pipe separator)
   - `{}` (empty choices)
   - `{|}` (empty options)

### Error Messages

```python
# Example error messages for new syntax
"Invalid emphasis range syntax: '{syntax}'. Use format: '1.5-2.0::content::' or '2.0::content::'"
"Invalid choice options syntax: '{syntax}'. Use format: '{option1|option2|option3}'"
"Empty choice options not allowed: '{syntax}'"
```

### Graceful Degradation

- Invalid emphasis syntax returns content without emphasis
- Invalid choice syntax returns the original text
- Empty choice options return empty string
- Maintains existing error handling for file-based prompts

## Testing Strategy

### Unit Tests

1. **Emphasis Range Processing:**
   - Test single values: `2.0::content::`
   - Test ranges: `1.5-2.0::content::`
   - Test decimal precision (exactly 2 places)
   - Test invalid syntax handling
   - Test edge cases (0.0, very large numbers)

2. **Choice Options Processing:**
   - Test basic choices: `{red|blue|green}`
   - Test choices with spaces: `{option one|option two}`
   - Test single option: `{only option}`
   - Test empty options: `{|}`
   - Test nested choices within other syntax

3. **Integration Testing:**
   - Test new syntax within dynamic prompt files
   - Test combination of all syntax types
   - Test recursive processing with new syntax
   - Test character prompt processing
   - Test grid generation with new syntax

4. **Regression Testing:**
   - Verify `__filename__` syntax still works
   - Verify seeded randomization consistency
   - Verify character prompt seed offsets
   - Verify grid prompt overrides

### Test Data Examples

```python
# Test cases for emphasis ranges
test_cases = [
    ("2.0::bold text::", "2.00::bold text::"),
    ("1.5-2.0::varied text::", r"\d\.\d{2}::varied text::"),  # regex match
    ("invalid::text::", "text"),  # graceful degradation
]

# Test cases for choice options  
choice_cases = [
    ("{red|blue|green}", ["red", "blue", "green"]),  # one of these
    ("{single option}", "single option"),  # no pipe, return as-is
    ("{}", ""),  # empty choices
]
```

### Performance Considerations

- New regex patterns should not significantly impact performance
- Choice option processing is O(n) where n is number of options
- Emphasis range processing is O(1)
- Overall complexity remains the same as current system

## Implementation Notes

### Backward Compatibility

Since backward compatibility is not required, the implementation will:
- Completely remove old bracket processing functions
- Remove old regex patterns
- Clean up unused code paths
- Simplify the overall codebase

### Migration Path

Users will need to update their prompt files to use new syntax:
- `{content:2}` → `2.0::content::`
- `{content:1-3}` → `1.0-3.0::content::`
- `[content:2]` → `2.0::content::` (same format, emphasis handled by backend)

### Code Organization

The refactored code will be cleaner and more maintainable:
- Fewer helper functions (remove bracket-specific functions)
- Clearer regex patterns with descriptive names
- Better separation of concerns between different syntax types
- Improved error handling with specific error messages