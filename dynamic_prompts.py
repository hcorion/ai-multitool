import os
import re
import random

def make_prompt_dynamic(prompt: str, username: str, static_folder: str, seed: int) -> str:
    dyanamicRandom = random.Random(seed)
    prompts = dict()
    dynamic_prompts_path = os.path.join(static_folder, "prompts", username)
    os.makedirs(dynamic_prompts_path, exist_ok=True)
    for (dirpath, dirnames, filenames) in os.walk(dynamic_prompts_path):
        for file in filenames:
            if file.endswith(".txt"):
                with open(os.path.join(dirpath, file)) as f:
                    prompts[os.path.splitext(file)[0]] = f.read().splitlines()
    if len(prompts) <= 0:
        return prompt
    
    def replace_section(match: re.Match[str]) -> str:
        content = match.group(1)
        # Define custom replacements based on the captured content
        
        if content not in prompts:
            raise ValueError(f"Error: Could not find matching dynamic prompt file for keyword: {content}")
        replaced_section = re.sub(r'__(.+?)__', replace_section, dyanamicRandom.choice(prompts[content]))
        return replaced_section
    
    revised_prompt = re.sub(r'__(.+?)__', replace_section, prompt)
    return revised_prompt