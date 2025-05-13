from dataclasses import dataclass
import os
import re
import random
from typing import List

@dataclass
class GridDynamicPromptInfo:
    str_to_replace_with: str
    prompt_file: str

def get_prompt_dict(username: str, static_folder: str) -> dict[str, list[str]]:
    dynamic_prompts_path = os.path.join(static_folder, "prompts", username)
    os.makedirs(dynamic_prompts_path, exist_ok=True)

    prompts: dict[str, list[str]] = dict()
    # TODO: Cache this if this gets slow
    for (dirpath, _, filenames) in os.walk(dynamic_prompts_path):
        for file in filenames:
            if file.endswith(".txt"):
                with open(os.path.join(dirpath, file)) as f:
                    prompts[os.path.splitext(file)[0]] = f.read().splitlines()
    return prompts

def get_prompts_for_name(username: str, static_folder: str, name: str) -> List[str]:
    return get_prompt_dict(username, static_folder)[name]

def make_prompt_dynamic(prompt: str, username: str, static_folder: str, seed: int, grid_prompt: GridDynamicPromptInfo | None = None) -> str:
    dynamicRandom = random.Random(seed)
    prompts = get_prompt_dict(username, static_folder)
    used_grid_prompt = False
    
    def replace_brackets_section_positive(match: re.Match[str]) -> str:
        return replace_brackets_section(match, "{", "}")
    
    def replace_brackets_section_negative(match: re.Match[str]) -> str:
        return replace_brackets_section(match, "[", "]")

    def replace_brackets_section(match: re.Match[str], bracket_left: str, bracket_right: str) -> str:
        content = match.group(1)
        bracket_count = match.group(2)

        if "-" in bracket_count:
            range = bracket_count.split('-')
            bracket_count = dynamicRandom.randrange(int(range[0]), int(range[1])+1)
        
        left_brackets = bracket_left*int(bracket_count)
        right_brackets = bracket_right*int(bracket_count)

        if "|" in content:
            rand_options = content.split('|')
            content = dynamicRandom.choice(rand_options)

        replaced_section = f"{left_brackets}{content}{right_brackets}"
        return replaced_section
    
    def replace_dynamic_prompt_section(match: re.Match[str]) -> str:

        content = match.group(1)
        if len(prompts) <= 0:
            return content

        # Define custom replacements based on the captured content
        
        if content not in prompts:
            raise ValueError(f"Error: Could not find matching dynamic prompt file for keyword: {content}")
        
        # We actually still iterate the RNG here even if it gets replaced in the grid
        # This is to keep prompt consistency when generating grids
        prompt_text = dynamicRandom.choice(prompts[content])
        if grid_prompt and content == grid_prompt.prompt_file:
            nonlocal used_grid_prompt
            used_grid_prompt = True
            prompt_text = grid_prompt.str_to_replace_with
        
        replaced_section = re.sub(r'__(.+?)__', replace_dynamic_prompt_section, prompt_text)
        replaced_section = re.sub(r'{(.+?):(\d+-?\d*)}', replace_brackets_section_positive, replaced_section)
        replaced_section = re.sub(r'\[(.+?):(\d+-?\d*)\]', replace_brackets_section_negative, replaced_section)
        return replaced_section
    
    revised_prompt = re.sub(r'__(.+?)__', replace_dynamic_prompt_section, prompt)
    revised_prompt = re.sub(r'{(.+?):(\d+-?\d*)}', replace_brackets_section_positive, revised_prompt)
    revised_prompt = re.sub(r'\[(.+?):(\d+-?\d*)\]', replace_brackets_section_negative, revised_prompt)

    if grid_prompt and not used_grid_prompt:
        raise LookupError(f"Tried to use grid prompt but no prompt file matching {grid_prompt.prompt_file} was found in the prompt!")

    return revised_prompt