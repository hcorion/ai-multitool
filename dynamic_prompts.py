import os
import re
import random

def make_prompt_dynamic(prompt: str, username: str, static_folder: str, seed: int) -> str:
    dyanamicRandom = random.Random(seed)
    prompts: dict[str, list[str]] = dict()
    dynamic_prompts_path = os.path.join(static_folder, "prompts", username)
    os.makedirs(dynamic_prompts_path, exist_ok=True)
    for (dirpath, _, filenames) in os.walk(dynamic_prompts_path):
        for file in filenames:
            if file.endswith(".txt"):
                with open(os.path.join(dirpath, file)) as f:
                    prompts[os.path.splitext(file)[0]] = f.read().splitlines()
    
    def replace_brackets_section_positive(match: re.Match[str]) -> str:
        return replace_brackets_section(match, "{", "}")
    
    def replace_brackets_section_negative(match: re.Match[str]) -> str:
        return replace_brackets_section(match, "[", "]")

    def replace_brackets_section(match: re.Match[str], bracket_left: str, bracket_right: str) -> str:
        content = match.group(1)
        bracket_count = match.group(2)

        if "-" in bracket_count:
            range = bracket_count.split('-')
            bracket_count = dyanamicRandom.randrange(int(range[0]), int(range[1])+1)
        
        left_brackets = bracket_left*int(bracket_count)
        right_brackets = bracket_right*int(bracket_count)

        replaced_section = f"{left_brackets}{content}{right_brackets}"
        return replaced_section
    
    def replace_dynamic_prompt_section(match: re.Match[str]) -> str:

        content = match.group(1)
        if len(prompts) <= 0:
            return content

        # Define custom replacements based on the captured content
        
        if content not in prompts:
            raise ValueError(f"Error: Could not find matching dynamic prompt file for keyword: {content}")
        replaced_section = re.sub(r'__(.+?)__', replace_dynamic_prompt_section, dyanamicRandom.choice(prompts[content]))
        replaced_section = re.sub(r'{(.+?):(\d+-?\d*)}', replace_brackets_section_positive, replaced_section)
        replaced_section = re.sub(r'\[(.+?):(\d+-?\d*)\]', replace_brackets_section_negative, replaced_section)
        return replaced_section
    
    revised_prompt = re.sub(r'__(.+?)__', replace_dynamic_prompt_section, prompt)
    revised_prompt = re.sub(r'{(.+?):(\d+-?\d*)}', replace_brackets_section_positive, revised_prompt)
    revised_prompt = re.sub(r'\[(.+?):(\d+-?\d*)\]', replace_brackets_section_negative, revised_prompt)
    

    return revised_prompt