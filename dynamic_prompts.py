"""
Dynamic Prompt System for AI Image Generation

This module implements a template-based prompt system that allows users to create
reusable, randomizable prompts for AI image generation. The system supports:

- User-specific prompt files with random selection
- Emphasis control through bracket notation
- Nested dynamic prompts for complex templates
- Deterministic randomization for reproducible results
- Grid generation with controlled variation

The system is designed to enhance prompt engineering workflows by enabling:
1. Reusable prompt components stored in text files
2. Consistent randomization across multiple generations
3. Fine-grained control over AI model attention through emphasis
4. Systematic variation for comparative image generation

File Structure:
static/prompts/{username}/
├── colors.txt      # Color options: "red\nblue\ngreen"
├── styles.txt      # Art styles: "anime\nrealistic\ncartoon"
└── subjects.txt    # Subject matter: "cat\ndog\nbird"

Usage Example:
Template: "A __colors__ __subjects__ in {__styles__:2} style"
Result:  "A red cat in {{anime}} style"
"""

import os
import random
import re
from dataclasses import dataclass
from typing import List, Dict


@dataclass
class GridDynamicPromptInfo:
    """
    Configuration for grid generation with controlled prompt variation.

    Used to override specific dynamic prompt replacements during grid generation,
    allowing systematic variation of one element while keeping others consistent.

    Attributes:
        str_to_replace_with: The specific string to use instead of random selection
        prompt_file: The prompt file name (without .txt) to override

    Example:
        To generate a grid varying colors while keeping other elements consistent:
        GridDynamicPromptInfo(str_to_replace_with="red", prompt_file="colors")

        This ensures that __colors__ is replaced with "red" instead of a random
        selection from colors.txt, while other dynamic prompts remain randomized.
    """

    str_to_replace_with: str
    prompt_file: str


def get_prompt_dict(username: str, static_folder: str) -> dict[str, list[str]]:
    """
    Load all user-specific prompt files into a dictionary for dynamic prompt processing.

    Scans the user's prompt directory for .txt files and loads each file's lines as
    a list of prompt options. The filename (without extension) becomes the key that
    can be referenced in dynamic prompts using __filename__ syntax.

    Directory Structure:
    static_folder/prompts/{username}/
    ├── colors.txt      # Referenced as __colors__
    ├── animals.txt     # Referenced as __animals__
    └── styles.txt      # Referenced as __styles__

    Args:
        username: User identifier for locating prompt files
        static_folder: Base path to static files directory

    Returns:
        Dictionary mapping filename (without .txt) to list of lines from that file

    Example:
        If colors.txt contains "red\nblue\ngreen", returns:
        {"colors": ["red", "blue", "green"]}
    """
    dynamic_prompts_path = os.path.join(static_folder, "prompts", username)
    os.makedirs(dynamic_prompts_path, exist_ok=True)

    prompts: dict[str, list[str]] = dict()
    # TODO: Cache this if this gets slow
    for dirpath, _, filenames in os.walk(dynamic_prompts_path):
        for file in filenames:
            if file.endswith(".txt"):
                with open(os.path.join(dirpath, file)) as f:
                    prompts[os.path.splitext(file)[0]] = f.read().splitlines()
    return prompts


def get_prompts_for_name(username: str, static_folder: str, name: str) -> List[str]:
    """
    Get the list of prompt options for a specific prompt file name.

    Convenience function to retrieve prompts from a single file without
    loading the entire prompt dictionary.

    Args:
        username: User identifier for locating prompt files
        static_folder: Base path to static files directory
        name: Prompt file name (without .txt extension)

    Returns:
        List of prompt options from the specified file

    Raises:
        KeyError: If the specified prompt file doesn't exist
    """
    return get_prompt_dict(username, static_folder)[name]


def make_prompt_dynamic(
    prompt: str,
    username: str,
    static_folder: str,
    seed: int,
    grid_prompt: GridDynamicPromptInfo | None = None,
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

    Supported Syntax:
    1. Dynamic Prompt Files: __filename__
       - Replaced with random line from static/prompts/{username}/{filename}.txt
       - Example: "__colors__" → "red" (from colors.txt containing "red\nblue\ngreen")

    2. Positive Emphasis Brackets: {content:count} or {content:min-max}
       - Adds emphasis brackets around content for AI model attention
       - Example: "{beautiful:2}" → "{{beautiful}}" (double emphasis)
       - Example: "{style:1-3}" → "{style}" or "{{style}}" or "{{{style}}}" (random 1-3 brackets)

    3. Negative Emphasis Brackets: [content:count] or [content:min-max]
       - Similar to positive but uses square brackets (typically for negative prompts)
       - Example: "[ugly:2]" → "[[ugly]]"

    4. Choice Options: content|option1|option2
       - Within any replacement, "|" separates random choices
       - Example: "red|blue|green" → randomly selects one option

    5. Nested Replacements:
       - Dynamic prompt files can contain other dynamic syntax
       - Recursively processed to support complex template hierarchies

    Parameters:
    - prompt: Template string containing dynamic placeholders
    - username: User identifier for locating user-specific prompt files
    - static_folder: Base path to static files directory
    - seed: Random seed for deterministic behavior across calls
    - grid_prompt: Optional override for specific prompt file during grid generation

    Returns:
    - Processed prompt string with all dynamic elements replaced

    Raises:
    - ValueError: When a referenced prompt file doesn't exist (only if other prompt files exist)
    - LookupError: When grid_prompt is specified but the target prompt file isn't found in the template

    Example Usage:
    ```python
    # Template: "A __colors__ __animals__ in {artistic:2} style"
    # With colors.txt: "red\nblue\ngreen"
    # With animals.txt: "cat\ndog\nbird"
    # Result: "A red cat in {{artistic}} style"
    ```

    Grid Generation:
    When grid_prompt is provided, it allows overriding specific prompt file replacements
    while maintaining consistent randomization for other elements. This enables generating
    image grids where one element varies systematically while others remain consistent.
    """
    # Initialize seeded random generator for deterministic behavior
    dynamicRandom = random.Random(seed)

    # Load all available prompt files for this user
    prompts = get_prompt_dict(username, static_folder)

    # Track whether grid prompt override was actually used (for validation)
    used_grid_prompt = False

    # Helper functions for different bracket types
    def replace_brackets_section_positive(match: re.Match[str]) -> str:
        """Handle positive emphasis brackets: {content:count}"""
        return replace_brackets_section(match, "{", "}")

    def replace_brackets_section_negative(match: re.Match[str]) -> str:
        """Handle negative emphasis brackets: [content:count]"""
        return replace_brackets_section(match, "[", "]")

    def replace_brackets_section(
        match: re.Match[str], bracket_left: str, bracket_right: str
    ) -> str:
        """Handle emphasis bracket replacement with support for ranges and choices."""
        content = match.group(1)  # The content inside brackets
        bracket_count = match.group(2)  # The count or range specification

        # Handle range notation (e.g., "1-3" becomes random number between 1 and 3)
        if "-" in bracket_count:
            range_parts = bracket_count.split("-")
            bracket_count = dynamicRandom.randrange(
                int(range_parts[0]), int(range_parts[1]) + 1
            )

        # Generate the appropriate number of brackets
        left_brackets = bracket_left * int(bracket_count)
        right_brackets = bracket_right * int(bracket_count)

        # Handle choice options within the content (e.g., "red|blue|green")
        if "|" in content:
            rand_options = content.split("|")
            content = dynamicRandom.choice(rand_options)

        replaced_section = f"{left_brackets}{content}{right_brackets}"
        return replaced_section

    def replace_dynamic_prompt_section(match: re.Match[str]) -> str:
        """Handle dynamic prompt file replacement with support for nested processing."""
        content = match.group(1)  # The filename inside __filename__

        # If no prompt files exist, return the content as-is (graceful degradation)
        if len(prompts) <= 0:
            return content

        # Validate that the requested prompt file exists
        if content not in prompts:
            raise ValueError(
                f"Error: Could not find matching dynamic prompt file for keyword: {content}"
            )

        # Select random prompt from the file
        # Note: We always call choice() even if using grid override to maintain RNG consistency
        # This ensures that the same seed produces the same results for non-overridden elements
        prompt_text = dynamicRandom.choice(prompts[content])

        # Override with grid-specific value if this is the target file for grid generation
        if grid_prompt and content == grid_prompt.prompt_file:
            nonlocal used_grid_prompt
            used_grid_prompt = True
            prompt_text = grid_prompt.str_to_replace_with

        # Recursively process the selected prompt text for nested dynamic elements
        # This enables complex template hierarchies where prompt files reference other prompt files
        replaced_section = re.sub(
            r"__(.+?)__", replace_dynamic_prompt_section, prompt_text
        )
        replaced_section = re.sub(
            r"{(.+?):(\d+-?\d*)}", replace_brackets_section_positive, replaced_section
        )
        replaced_section = re.sub(
            r"\[(.+?):(\d+-?\d*)\]", replace_brackets_section_negative, replaced_section
        )
        return replaced_section

    # Process the prompt through multiple passes to handle all dynamic elements

    # Pass 1: Replace dynamic prompt files (__filename__)
    revised_prompt = re.sub(r"__(.+?)__", replace_dynamic_prompt_section, prompt)

    # Pass 2: Replace positive emphasis brackets {content:count}
    revised_prompt = re.sub(
        r"{(.+?):(\d+-?\d*)}", replace_brackets_section_positive, revised_prompt
    )

    # Pass 3: Replace negative emphasis brackets [content:count]
    revised_prompt = re.sub(
        r"\[(.+?):(\d+-?\d*)\]", replace_brackets_section_negative, revised_prompt
    )

    # Validate that grid prompt override was actually used if specified
    if grid_prompt and not used_grid_prompt:
        raise LookupError(
            f"Tried to use grid prompt but no prompt file matching {grid_prompt.prompt_file} was found in the prompt!"
        )

    return revised_prompt


def make_character_prompts_dynamic(
    character_prompts: List[Dict[str, str]],
    username: str,
    static_folder: str,
    seed: int,
    grid_prompt: GridDynamicPromptInfo | None = None,
) -> List[Dict[str, str]]:
    """
    Process dynamic prompts for character prompts independently.
    Each character prompt gets its own seed offset to ensure variety.
    """
    processed_character_prompts: List[Dict[str, str]] = []

    for i, char_prompt in enumerate(character_prompts):
        # Use seed offset for each character to ensure variety
        char_seed = seed + i + 1

        processed_char: Dict[str, str] = {}

        # Process positive prompt
        if char_prompt.get("positive", "").strip():
            processed_char["positive"] = make_prompt_dynamic(
                char_prompt["positive"], username, static_folder, char_seed, grid_prompt
            )
        else:
            processed_char["positive"] = ""

        # Process negative prompt
        if char_prompt.get("negative", "").strip():
            processed_char["negative"] = make_prompt_dynamic(
                char_prompt["negative"], username, static_folder, char_seed, grid_prompt
            )
        else:
            processed_char["negative"] = ""

        processed_character_prompts.append(processed_char)

    return processed_character_prompts
