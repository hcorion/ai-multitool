"""
Dynamic Prompt System for AI Image Generation

This module implements a template-based prompt system that allows users to create
reusable, randomizable prompts for AI image generation. The system supports:

- User-specific prompt files with random selection
- Emphasis control through decimal range notation
- Nested dynamic prompts for complex templates
- Deterministic randomization for reproducible results
- Grid generation with controlled variation

The system is designed to enhance prompt engineering workflows by enabling:
1. Reusable prompt components stored in text files
2. Consistent randomization across multiple generations
3. Fine-grained control over AI model attention through decimal emphasis ranges
4. Systematic variation for comparative image generation

File Structure:
static/prompts/{username}/
├── colors.txt      # Color options: "red\nblue\ngreen"
├── styles.txt      # Art styles: "anime\nrealistic\ncartoon"
└── subjects.txt    # Subject matter: "cat\ndog\nbird"

Usage Example:
Template: "A __colors__ __subjects__ in 1.5-2.0::__styles__:: style"
Result:  "A red cat in 1.73::anime:: style"
"""

import os
import random
import re
from dataclasses import dataclass
from typing import Dict, List


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
    """Load user's prompt files into dictionary for dynamic replacement processing."""
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
    """Get prompt options from a specific prompt file by name."""
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

    2. Emphasis Ranges: min-max::content:: or value::content::
       - Generates random decimal value between min and max (2 decimal places)
       - Example: "1.5-2.0::emphasized text::" → "1.73::emphasized text::"
       - Example: "2.0::bold text::" → "2.00::bold text::" (single value)

    3. Choice Options: {option1|option2|option3}
       - Randomly selects one option from pipe-separated choices
       - Example: "{red|blue|green}" → "red" (randomly selected)
       - Supports any number of options and preserves spacing

    5. Nested Replacements:
       - Dynamic prompt files can contain other dynamic syntax
       - Recursively processed to support complex template hierarchies

    Returns:
    - Processed prompt string with all dynamic elements replaced

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
    dynamicRandom = random.Random(seed)

    # Load all available prompt files for this user
    prompts = get_prompt_dict(username, static_folder)

    # Track whether grid prompt override was actually used (for validation)
    used_grid_prompt = False

    # Helper functions for new syntax
    def replace_emphasis_range_section(match: re.Match[str]) -> str:
        """Handle emphasis range processing: min-max::content:: or value::content::"""
        try:
            full_match = match.group(0)
            min_val_str = match.group(1)  # First number (min value or single value)
            max_val_str = match.group(2)  # Second number (max value, may be None)
            content = match.group(3)      # The content inside emphasis markers

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
                emphasis_value = dynamicRandom.uniform(min_val, max_val)
            else:
                # Single value format: value::content::
                emphasis_value = min_val
            
            # Round to exactly 2 decimal places
            emphasis_value = round(emphasis_value, 2)
            
            # Format with exactly 2 decimal places
            return f"{emphasis_value:.2f}::{content}::"
            
        except (ValueError, TypeError):
            # Graceful degradation: return content without emphasis on invalid syntax
            return content if len(match.groups()) >= 3 and match.group(3) else match.group(0)

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
            selected_option = dynamicRandom.choice(options)
            return selected_option
            
        except (AttributeError, IndexError):
            # Graceful degradation: return original text on error
            return match.group(0)

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
        # Process choice options first
        replaced_section = re.sub(
            r"\{([^}]+\|[^}]+)\}", replace_choice_options, replaced_section
        )
        # Process emphasis ranges
        replaced_section = re.sub(
            r"(\d+(?:\.\d+)?)-?(\d+(?:\.\d+)?)?::(.+?)::", replace_emphasis_range_section, replaced_section
        )
        return replaced_section

    # Process the prompt through multiple passes to handle all dynamic elements
    # Processing order: dynamic files → choice options → emphasis ranges → recursive processing

    # Pass 1: Replace dynamic prompt files (__filename__)
    revised_prompt = re.sub(r"__(.+?)__", replace_dynamic_prompt_section, prompt)

    # Pass 2: Replace choice options {option1|option2|option3}
    revised_prompt = re.sub(
        r"\{([^}]+\|[^}]+)\}", replace_choice_options, revised_prompt
    )

    # Pass 3: Replace emphasis ranges min-max::content:: or value::content::
    revised_prompt = re.sub(
        r"(\d+(?:\.\d+)?)-?(\d+(?:\.\d+)?)?::(.+?)::", replace_emphasis_range_section, revised_prompt
    )

    return revised_prompt


def make_character_prompts_dynamic(
    character_prompts: List[Dict[str, str]],
    username: str,
    static_folder: str,
    seed: int,
    grid_prompt: GridDynamicPromptInfo | None = None,
) -> List[Dict[str, str]]:
    """Process dynamic prompts for character prompts with unique seeds for variety."""
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
