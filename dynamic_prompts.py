"""
Dynamic Prompt System for AI Image Generation

This module implements a template-based prompt system that allows users to create
reusable, randomizable prompts for AI image generation. The system supports:

- User-specific prompt files with random selection
- Follow-up prompt files with column-based sequential options
- Emphasis control through decimal range notation
- Nested dynamic prompts for complex templates
- Deterministic randomization for reproducible results
- Grid generation with controlled variation

The system is designed to enhance prompt engineering workflows by enabling:
1. Reusable prompt components stored in text files
2. Sequential progression through related prompt options
3. Consistent randomization across multiple generations
4. Fine-grained control over AI model attention through decimal emphasis ranges
5. Systematic variation for comparative image generation

File Structure:
static/prompts/{username}/
├── colors.txt          # Regular file: "red\nblue\ngreen"
├── styles.txt          # Regular file: "anime\nrealistic\ncartoon"
├── subjects.txt        # Regular file: "cat\ndog\nbird"
└── color_palette.txt   # Follow-up file with column syntax

Follow-up File Format:
# columns: primary, secondary, tertiary
warm red||cool red||deep red
bright blue||sky blue||navy blue
forest green||lime green||dark green

Usage Examples:
Regular: "A __colors__ __subjects__ in 1.5-2.0::__styles__:: style"
Result:  "A red cat in 1.73::anime:: style"

Follow-up: "A __color_palette__ theme"
First use:  "A warm red theme"     (primary column)
Second use: "A cool red theme"     (secondary column)
Third use:  "A deep red theme"     (tertiary column)
Fourth use: "A warm red theme"     (cycles back to primary)
"""

import os
import random
import re
from dataclasses import dataclass


@dataclass
class GridDynamicPromptInfo:
    """
    Configuration for grid generation with controlled prompt variation.

    Used to override specific dynamic prompt replacements during grid generation,
    allowing systematic variation of one element while keeping others consistent.

    Attributes:
        str_to_replace_with: The specific string to use instead of random selection
        prompt_file: The prompt file name (without .txt) to override
        followup_row_index: For follow-up files, specifies which row to use (optional)

    Example:
        To generate a grid varying colors while keeping other elements consistent:
        GridDynamicPromptInfo(str_to_replace_with="red", prompt_file="colors")

        This ensures that __colors__ is replaced with "red" instead of a random
        selection from colors.txt, while other dynamic prompts remain randomized.

        For follow-up files:
        GridDynamicPromptInfo(str_to_replace_with="", prompt_file="color_palette", followup_row_index=0)

        This ensures that __color_palette__ uses row 0 and progresses through its columns.
    """

    str_to_replace_with: str
    prompt_file: str
    followup_row_index: int | None = None


@dataclass
class FollowUpPromptFile:
    """Represents a follow-up prompt file with column-based options."""

    name: str
    column_count: int  # Number of columns (determined by row parsing)
    rows: list[list[str]]  # Each row contains options for each column


@dataclass
class FollowUpState:
    """Tracks the state of follow-up prompt progression for a user."""

    locked_seed: int  # Seed used for row selection
    current_column: int  # Current column index (0-based)
    selected_row_index: int  # Which row was selected with the locked seed


def parse_followup_file(file_path: str) -> FollowUpPromptFile | None:
    """
    Parse a follow-up prompt file with column-based options.

    Follow-up files have the format:
    # columns: primary, secondary, tertiary
    option1||option2||option3
    choice1||choice2||choice3

    Args:
        file_path: Path to the prompt file to parse

    Returns:
        FollowUpPromptFile if valid follow-up file, None if regular file or malformed

    Requirements: 1.1, 1.2, 5.1, 5.2, 5.3, 5.4, 5.5
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()

        if not lines:
            return None

        # Check for follow-up file header
        first_line = lines[0].strip()
        if not first_line.startswith("# columns:"):
            return None

        # Parse data rows (skip header)
        data_rows = []
        column_count = None

        for line_num, line in enumerate(lines[1:], start=2):
            line = line.strip()

            # Skip empty lines
            if not line:
                continue

            # Skip comment lines
            if line.startswith("#"):
                continue

            # Split by || separator
            if "||" not in line:
                # Single column or malformed - treat as single column
                columns = [line]
            else:
                columns = line.split("||")

            # Determine column count from first data row
            if column_count is None:
                column_count = len(columns)
            elif len(columns) != column_count:
                # Inconsistent column count - log warning but continue
                # Pad with empty strings or truncate to match expected count
                if len(columns) < column_count:
                    columns.extend([""] * (column_count - len(columns)))
                else:
                    columns = columns[:column_count]

            data_rows.append(columns)

        # Must have at least one data row
        if not data_rows or column_count is None:
            return None

        # Extract filename without extension
        filename = os.path.splitext(os.path.basename(file_path))[0]

        return FollowUpPromptFile(
            name=filename, column_count=column_count, rows=data_rows
        )

    except (IOError, OSError, UnicodeDecodeError):
        # File reading errors - graceful degradation
        return None
    except Exception:
        # Any other parsing errors - graceful degradation
        return None


def get_prompt_dict(
    username: str, static_folder: str
) -> tuple[dict[str, list[str]], dict[str, FollowUpPromptFile]]:
    """
    Load user's prompt files, separating regular and follow-up files.

    Args:
        username: Username for prompt file directory
        static_folder: Base static folder path

    Returns:
        Tuple of (regular_prompts, followup_prompts) dictionaries

    Requirements: 1.1, 1.2, 5.1, 5.2, 5.3, 5.4, 5.5
    """
    dynamic_prompts_path = os.path.join(static_folder, "prompts", username)
    os.makedirs(dynamic_prompts_path, exist_ok=True)

    regular_prompts: dict[str, list[str]] = {}
    followup_prompts: dict[str, FollowUpPromptFile] = {}

    # TODO: Cache this if this gets slow
    for dirpath, _, filenames in os.walk(dynamic_prompts_path):
        for file in filenames:
            if file.endswith(".txt"):
                file_path = os.path.join(dirpath, file)
                filename_without_ext = os.path.splitext(file)[0]

                # Try to parse as follow-up file first
                followup_file = parse_followup_file(file_path)

                if followup_file is not None:
                    # It's a follow-up file
                    followup_prompts[filename_without_ext] = followup_file
                else:
                    # It's a regular prompt file
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            regular_prompts[filename_without_ext] = (
                                f.read().splitlines()
                            )
                    except (IOError, OSError, UnicodeDecodeError):
                        # Skip files that can't be read
                        continue

    return regular_prompts, followup_prompts


def init_followup_state() -> dict[str, FollowUpState]:
    """
    Initialize empty follow-up state for a new generation.

    Returns:
        Empty dictionary to track follow-up state during generation

    Requirements: 2.1, 2.2, 2.3, 2.4, 2.5
    """
    return {}


def get_followup_option(
    file_name: str,
    followup_file: FollowUpPromptFile,
    state: dict[str, FollowUpState],
    base_seed: int,
) -> str:
    """
    Handle follow-up file progression logic with seed locking and column advancement.

    For follow-up files, the seed is locked per file to ensure consistent row selection
    across multiple uses within the same generation. The column progression advances
    sequentially and cycles back to the first column when all columns are used.

    Args:
        file_name: Name of the follow-up file
        followup_file: The parsed follow-up file data
        state: Current follow-up state dictionary (modified in-place)
        base_seed: Base seed for deterministic row selection (shared across characters)

    Returns:
        Selected option from the appropriate column

    Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 3.1, 3.2, 3.3, 3.4, 3.5
    """
    try:
        # Ensure we have valid rows
        if not followup_file.rows:
            return file_name

        # Check if we have state for this file
        if file_name not in state:
            # First use - create new state with locked seed
            # Use a file-specific seed based on base seed and filename for consistency
            file_seed = hash(f"{base_seed}_{file_name}") & 0x7FFFFFFF  # Ensure positive

            # Use locked seed to select row deterministically
            row_random = random.Random(file_seed)
            selected_row_index = row_random.randint(0, len(followup_file.rows) - 1)

            # Initialize state starting at first column
            state[file_name] = FollowUpState(
                locked_seed=file_seed,
                current_column=0,
                selected_row_index=selected_row_index,
            )

        # Get current state
        current_state = state[file_name]

        # Validate row index is still valid
        if current_state.selected_row_index >= len(followup_file.rows):
            # Row index out of bounds - reset to first row
            current_state.selected_row_index = 0

        # Get the selected row
        selected_row = followup_file.rows[current_state.selected_row_index]

        # Ensure row has content
        if not selected_row:
            return file_name

        # Validate column index
        if current_state.current_column >= len(selected_row):
            # Column index out of bounds - cycle back to first column
            current_state.current_column = 0

        # Get the option from current column
        selected_option = selected_row[current_state.current_column]

        # Advance to next column for next use
        current_state.current_column += 1

        # If we've used all columns, cycle back to first column
        if current_state.current_column >= len(selected_row):
            current_state.current_column = 0

        return selected_option if selected_option is not None else ""

    except (IndexError, ValueError, AttributeError, TypeError):
        # Error handling - return first available option or filename as fallback
        try:
            if followup_file.rows and followup_file.rows[0]:
                return (
                    followup_file.rows[0][0]
                    if followup_file.rows[0][0] is not None
                    else ""
                )
        except (IndexError, TypeError):
            pass
        return file_name


def get_prompts_for_name(username: str, static_folder: str, name: str) -> list[str]:
    """Get prompt options from a specific prompt file by name."""
    regular_prompts, followup_prompts = get_prompt_dict(username, static_folder)

    # Check regular prompts first
    if name in regular_prompts:
        return regular_prompts[name]

    # Check follow-up prompts - return row identifiers for grid generation
    if name in followup_prompts:
        followup_file = followup_prompts[name]
        row_options = []
        for i, row in enumerate(followup_file.rows):
            if row:  # Ensure row is not empty
                # Use the first column as display name but encode the row index
                display_name = row[0] if row[0] else f"Row_{i}"
                row_options.append(f"__FOLLOWUP_ROW_{i}:{display_name}__")
        return row_options

    # Return empty list if not found
    return []


def make_prompt_dynamic(
    prompt: str,
    username: str,
    static_folder: str,
    seed: int,
    grid_prompt: GridDynamicPromptInfo | None = None,
    followup_state: dict[str, FollowUpState] | None = None,
    followup_base_seed: int | None = None,
) -> str:
    """
    Transform a prompt string with dynamic placeholders into a concrete prompt using user-specific prompt files.

    This function implements a template-based prompt system that allows users to create reusable, randomized prompts
    for AI image generation. It supports multiple types of dynamic replacements and maintains deterministic behavior
    through seeded randomization.

    Design Intent:
    - Enable users to create reusable prompt templates with randomizable elements
    - Provide deterministic randomization for reproducible results when using the same seed
    - Support nested dynamic prompts for complex template hierarchies
    - Allow emphasis control through bracket notation for fine-tuning AI model attention
    - Enable grid generation with controlled variation through grid prompt overrides
    - Support follow-up files with sequential column progression and shared seed locking

    Supported Syntax:
    1. Dynamic Prompt Files: __filename__
       - Replaced with random line from static/prompts/{username}/{filename}.txt
       - Example: "__colors__" → "red" (from colors.txt containing "red\nblue\ngreen")

    2. Follow-up Prompt Files: __filename__
       - Files with "# columns:" header and "||" separators
       - Progress through columns sequentially with locked seed for row selection
       - Example: "__color_palette__" → "warm red" (first use), "cool red" (second use)

    3. Emphasis Ranges: min-max::content:: or value::content::
       - Generates random decimal value between min and max (2 decimal places)
       - Example: "1.5-2.0::emphasized text::" → "1.73::emphasized text::"
       - Example: "2.0::bold text::" → "2.00::bold text::" (single value)

    4. Choice Options: {option1|option2|option3}
       - Randomly selects one option from pipe-separated choices
       - Example: "{red|blue|green}" → "red" (randomly selected)
       - Supports any number of options and preserves spacing

    5. Nested Replacements:
       - Dynamic prompt files can contain other dynamic syntax
       - Recursively processed to support complex template hierarchies

    Args:
        prompt: Template prompt string with dynamic placeholders
        username: Username for prompt file directory
        static_folder: Base static folder path
        seed: Seed for deterministic randomization
        grid_prompt: Optional grid generation override
        followup_state: Optional follow-up state dictionary (modified in-place)
        followup_base_seed: Optional base seed for follow-up files (defaults to seed)

    Returns:
        Processed prompt string with all dynamic elements replaced

    Example Usage:
    ```python
    # Template: "A __colors__ __animals__ in 1.5-2.0::artistic:: style with {modern|classic|vintage} elements"
    # With colors.txt: "red\nblue\ngreen"
    # With animals.txt: "cat\ndog\nbird"
    # Result: "A red cat in 1.73::artistic:: style with modern elements"
    ```

    Grid Generation:
    When grid_prompt is provided, it allows overriding specific prompt file replacements
    while maintaining consistent randomization for other elements. This enables generating
    image grids where one element varies systematically while others remain consistent.
    """
    # Initialize seeded random generator for deterministic behavior
    dynamic_random = random.Random(seed)

    # Load all available prompt files for this user
    regular_prompts, followup_prompts = get_prompt_dict(username, static_folder)

    # Initialize follow-up state if not provided
    if followup_state is None:
        followup_state = init_followup_state()

    # Use provided followup_base_seed or default to regular seed
    if followup_base_seed is None:
        followup_base_seed = seed

    # Track whether grid prompt override was actually used (for validation)
    used_grid_prompt = False

    # Helper functions for new syntax
    def replace_emphasis_range_section(match: re.Match[str]) -> str:
        """Handle emphasis range processing: min-max::content:: or value::content::"""
        try:
            min_val_str = match.group(1)  # First number (min value or single value)
            max_val_str = match.group(2)  # Second number (max value, may be None)
            content = match.group(3)  # The content inside emphasis markers

            # Validate that min_val_str is a valid number
            if not min_val_str:
                return content

            # Convert to float values
            min_val = float(min_val_str)

            if max_val_str and max_val_str.strip():
                # Range format: min-max::content::
                max_val = float(max_val_str)
                if min_val > max_val:
                    # Swap if min > max for graceful handling
                    min_val, max_val = max_val, min_val
                # Generate random decimal between min and max
                emphasis_value = dynamic_random.uniform(min_val, max_val)
            else:
                # Single value format: value::content::
                emphasis_value = min_val

            # Round to exactly 2 decimal places
            emphasis_value = round(emphasis_value, 2)

            # Format with minimal decimal places needed
            # If it's a whole number, show .0
            # If it has 1 decimal place, show that
            # If it has 2 decimal places, show both
            if emphasis_value == int(emphasis_value):
                # Whole number - show .0
                formatted_value = f"{int(emphasis_value)}.0"
            elif emphasis_value * 10 == int(emphasis_value * 10):
                # One decimal place - show as is
                formatted_value = f"{emphasis_value:.1f}"
            else:
                # Two decimal places - show both
                formatted_value = f"{emphasis_value:.2f}"

            return f"{formatted_value}::{content}::"

        except (ValueError, TypeError):
            # Graceful degradation: return content without emphasis on invalid syntax
            return (
                content
                if len(match.groups()) >= 3 and match.group(3)
                else match.group(0)
            )

    def replace_choice_options(match: re.Match[str]) -> str:
        """Handle choice option processing: {option1|option2|option3}"""
        try:
            choices_str = match.group(1)  # The content inside curly braces

            # Check if there's actually a pipe character (required for choice syntax)
            if "|" not in choices_str:
                # Not a choice option, return original text
                return match.group(0)

            # Split by pipe character to get individual options
            options = choices_str.split("|")

            # Keep all options, including empty ones for graceful handling
            if not options:
                # Return empty string for completely empty choices
                return ""

            # Randomly select one option (may be empty string)
            selected_option = dynamic_random.choice(options)
            return selected_option

        except (AttributeError, IndexError):
            # Graceful degradation: return original text on error
            return match.group(0)

    def replace_dynamic_prompt_section(match: re.Match[str]) -> str:
        """Handle dynamic prompt file replacement with support for nested processing."""
        nonlocal used_grid_prompt  # Declare at function start
        content = match.group(1)  # The filename inside __filename__

        # Check if this is a follow-up file
        if content in followup_prompts:
            # Handle follow-up files with state management
            followup_file = followup_prompts[content]

            # Check for grid override for follow-up files
            if (
                grid_prompt
                and content == grid_prompt.prompt_file
                and grid_prompt.followup_row_index is not None
            ):
                used_grid_prompt = True
                # Use the specified row index for grid generation
                if 0 <= grid_prompt.followup_row_index < len(followup_file.rows):
                    selected_row = followup_file.rows[grid_prompt.followup_row_index]
                    if selected_row:
                        # For grid generation, create a temporary state that uses the specified row
                        # and progresses through columns normally
                        temp_state = followup_state.copy() if followup_state else {}
                        if content not in temp_state:
                            temp_state[content] = FollowUpState(
                                locked_seed=followup_base_seed,
                                current_column=0,
                                selected_row_index=grid_prompt.followup_row_index,
                            )
                        prompt_text = get_followup_option(
                            content, followup_file, temp_state, followup_base_seed
                        )
                        # Update the main state with the temp state progression
                        followup_state.update(temp_state)
                    else:
                        prompt_text = content  # Fallback if row is empty
                else:
                    prompt_text = content  # Fallback if row index is out of bounds
            else:
                # Normal follow-up file processing
                prompt_text = get_followup_option(
                    content, followup_file, followup_state, followup_base_seed
                )
        elif content in regular_prompts:
            # Handle regular prompt files
            # Select random prompt from the file
            # Note: We always call choice() even if using grid override to maintain RNG consistency
            # This ensures that the same seed produces the same results for non-overridden elements
            prompt_text = dynamic_random.choice(regular_prompts[content])

            # Override with grid-specific value if this is the target file for grid generation
            if grid_prompt and content == grid_prompt.prompt_file:
                used_grid_prompt = True
                prompt_text = grid_prompt.str_to_replace_with
        else:
            # File not found - check if no files exist at all for graceful degradation
            if len(regular_prompts) <= 0 and len(followup_prompts) <= 0:
                return content

            # Files exist but this specific file wasn't found
            raise ValueError(
                f"Error: Could not find matching dynamic prompt file for keyword: {content}"
            )

        # Recursively process the selected prompt text for nested dynamic elements
        # This enables complex template hierarchies where prompt files reference other prompt files
        replaced_section = re.sub(
            r"__(.+?)__", replace_dynamic_prompt_section, prompt_text
        )
        # Process choice options first
        replaced_section = re.sub(
            r"\{([^}]*\|[^}]*)\}", replace_choice_options, replaced_section
        )
        # Process emphasis ranges
        replaced_section = re.sub(
            r"(\d+(?:\.\d+)?)-?(\d+(?:\.\d+)?)?::(.+?)::",
            replace_emphasis_range_section,
            replaced_section,
        )
        return replaced_section

    # Process the prompt through multiple passes to handle all dynamic elements
    # Processing order: dynamic files → choice options → emphasis ranges → recursive processing

    # Pass 1: Replace dynamic prompt files (__filename__)
    revised_prompt = re.sub(r"__(.+?)__", replace_dynamic_prompt_section, prompt)

    # Pass 2: Replace choice options {option1|option2|option3}
    revised_prompt = re.sub(
        r"\{([^}]*\|[^}]*)\}", replace_choice_options, revised_prompt
    )

    # Pass 3: Replace emphasis ranges min-max::content:: or value::content::
    revised_prompt = re.sub(
        r"(\d+(?:\.\d+)?)-?(\d+(?:\.\d+)?)?::(.+?)::",
        replace_emphasis_range_section,
        revised_prompt,
    )

    return revised_prompt


def make_character_prompts_dynamic(
    character_prompts: list[dict[str, str]],
    username: str,
    static_folder: str,
    seed: int,
    grid_prompt: GridDynamicPromptInfo | None = None,
    followup_state: dict[str, FollowUpState] | None = None,
) -> list[dict[str, str]]:
    """
    Process dynamic prompts for character prompts with unique seeds for variety.

    Follow-up files use shared locked seed across all characters for consistency,
    while regular files use character-specific seed offsets for variety.

    If followup_state is provided, it will be used and modified in-place to continue
    the follow-up progression from where the base prompt left off.

    Requirements: 3.1, 3.2, 3.3, 3.4, 3.5
    """
    processed_character_prompts: list[dict[str, str]] = []

    # Use provided follow-up state or initialize new state
    if followup_state is None:
        followup_state = init_followup_state()

    for i, char_prompt in enumerate(character_prompts):
        # Use seed offset for each character to ensure variety for regular files
        char_seed = seed + i + 1

        processed_char: dict[str, str] = {}

        # Process positive prompt
        if char_prompt.get("positive", "").strip():
            processed_char["positive"] = make_prompt_dynamic(
                char_prompt["positive"],
                username,
                static_folder,
                char_seed,  # Character-specific seed for regular files
                grid_prompt,
                followup_state,  # Continue follow-up progression from base prompt
                seed,  # Original seed for follow-up files (shared across characters)
            )
        else:
            processed_char["positive"] = ""

        # Process negative prompt
        if char_prompt.get("negative", "").strip():
            processed_char["negative"] = make_prompt_dynamic(
                char_prompt["negative"],
                username,
                static_folder,
                char_seed,  # Character-specific seed for regular files
                grid_prompt,
                followup_state,  # Continue follow-up progression from base prompt
                seed,  # Original seed for follow-up files (shared across characters)
            )
        else:
            processed_char["negative"] = ""

        processed_character_prompts.append(processed_char)

    return processed_character_prompts
