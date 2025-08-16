#!/usr/bin/env python3
"""
Example demonstrating the dynamic prompt system functionality.

This script shows how the make_prompt_dynamic function works with various
syntax patterns and user-specific prompt files.
"""

import tempfile
import os
from dynamic_prompts import make_prompt_dynamic, GridDynamicPromptInfo

def create_example_prompt_files(temp_dir: str, username: str):
    """Create example prompt files for demonstration."""
    prompts_dir = os.path.join(temp_dir, "prompts", username)
    os.makedirs(prompts_dir, exist_ok=True)
    
    # Create colors.txt
    with open(os.path.join(prompts_dir, "colors.txt"), "w") as f:
        f.write("red\nblue\ngreen\nyellow\npurple\n")
    
    # Create animals.txt
    with open(os.path.join(prompts_dir, "animals.txt"), "w") as f:
        f.write("cat\ndog\nbird\nfish\nrabbit\n")
    
    # Create styles.txt
    with open(os.path.join(prompts_dir, "styles.txt"), "w") as f:
        f.write("anime\nrealistic\ncartoon\noil painting\nwatercolor\n")
    
    # Create nested.txt (demonstrates nested dynamic prompts)
    with open(os.path.join(prompts_dir, "nested.txt"), "w") as f:
        f.write("a __colors__ __animals__\na {beautiful:2} __animals__\na [ugly:1-2] creature\n")

def demonstrate_basic_usage():
    """Demonstrate basic dynamic prompt functionality."""
    print("=== Basic Dynamic Prompt Examples ===\n")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        username = "demo_user"
        create_example_prompt_files(temp_dir, username)
        
        examples = [
            "A __colors__ __animals__ in the forest",
            "A {beautiful:2} __animals__ with __colors__ fur",
            "A __styles__ portrait of a __animals__",
            "[ugly:1-3] __animals__ in {dramatic:2} lighting",
            "A __colors__|silver|golden __animals__",  # Choice within dynamic prompt
            "__nested__",  # Nested dynamic prompt
        ]
        
        for i, template in enumerate(examples, 1):
            print(f"Example {i}:")
            print(f"Template: {template}")
            
            # Generate 3 variations with different seeds
            for seed in [42, 123, 456]:
                result = make_prompt_dynamic(template, username, temp_dir, seed)
                print(f"  Seed {seed}: {result}")
            print()

def demonstrate_grid_generation():
    """Demonstrate grid generation with controlled variation."""
    print("=== Grid Generation Example ===\n")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        username = "demo_user"
        create_example_prompt_files(temp_dir, username)
        
        template = "A __colors__ __animals__ in {__styles__:2} style"
        print(f"Template: {template}")
        print("Grid varying colors while keeping other elements consistent:\n")
        
        # Simulate grid generation by overriding colors
        colors = ["red", "blue", "green", "yellow"]
        seed = 42  # Same seed for consistency in non-overridden elements
        
        for color in colors:
            grid_info = GridDynamicPromptInfo(str_to_replace_with=color, prompt_file="colors")
            result = make_prompt_dynamic(template, username, temp_dir, seed, grid_info)
            print(f"  {color}: {result}")

def demonstrate_emphasis_brackets():
    """Demonstrate emphasis bracket functionality."""
    print("\n=== Emphasis Bracket Examples ===\n")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        username = "demo_user"
        create_example_prompt_files(temp_dir, username)
        
        examples = [
            "{beautiful:1} __animals__",
            "{beautiful:3} __animals__", 
            "{beautiful:1-4} __animals__",  # Random 1-4 brackets
            "[ugly:2] and {beautiful:2} __animals__",
            "{red|blue|green:2} __animals__",  # Choice with emphasis
        ]
        
        for template in examples:
            print(f"Template: {template}")
            for seed in [42, 123]:
                result = make_prompt_dynamic(template, username, temp_dir, seed)
                print(f"  Seed {seed}: {result}")
            print()

if __name__ == "__main__":
    print("Dynamic Prompt System Demonstration")
    print("=" * 50)
    
    demonstrate_basic_usage()
    demonstrate_grid_generation()
    demonstrate_emphasis_brackets()
    
    print("\nKey Features Demonstrated:")
    print("- Dynamic prompt file replacement (__filename__)")
    print("- Emphasis brackets for AI attention control {content:count}")
    print("- Negative emphasis brackets [content:count]")
    print("- Range notation for random bracket counts (1-3)")
    print("- Choice options within content (option1|option2)")
    print("- Nested dynamic prompts (files referencing other files)")
    print("- Grid generation with controlled variation")
    print("- Deterministic randomization with seeds")