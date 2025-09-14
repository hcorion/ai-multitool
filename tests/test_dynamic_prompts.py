"""
Unit tests for dynamic prompt processing functionality.

This module tests the new dynamic prompt syntax including:
- Emphasis range processing (min-max::content:: and value::content::)
- Choice option processing ({option1|option2|option3})
- Error handling for invalid syntax
- Empty and malformed input handling

Requirements tested: 1.1, 1.2, 1.4, 1.5, 2.1, 2.2, 2.3, 2.4, 2.5
"""

import pytest
import os
import tempfile
import re
from unittest.mock import patch, Mock
from dynamic_prompts import (
    make_prompt_dynamic,
    make_character_prompts_dynamic,
    get_prompt_dict,
    GridDynamicPromptInfo
)


class TestEmphasisRangeProcessing:
    """Test emphasis range syntax: min-max::content:: and value::content::"""
    
    def test_single_value_emphasis(self, temp_dir):
        """Test single value emphasis: 2.0::content::"""
        # Requirement 1.2: Single value format should pass through unchanged
        prompt = "2.0::bold text::"
        result = make_prompt_dynamic(prompt, "testuser", temp_dir, seed=42)
        assert result == "2.00::bold text::"
    
    def test_range_emphasis_generates_decimal(self, temp_dir):
        """Test range emphasis generates decimal between min and max"""
        # Requirement 1.1: Range format should generate random decimal
        prompt = "1.5-2.0::emphasized text::"
        result = make_prompt_dynamic(prompt, "testuser", temp_dir, seed=42)
        
        # Extract the generated value
        match = re.search(r"(\d+\.\d{2})::emphasized text::", result)
        assert match is not None
        
        generated_value = float(match.group(1))
        assert 1.5 <= generated_value <= 2.0
        assert len(str(generated_value).split('.')[1]) == 2  # Exactly 2 decimal places
    
    def test_decimal_precision_two_places(self, temp_dir):
        """Test that decimal values are rounded to exactly 2 decimal places"""
        # Requirement 1.4: Values should be rounded to exactly 2 decimal places
        prompt = "1.0-2.0::test::"
        result = make_prompt_dynamic(prompt, "testuser", temp_dir, seed=123)
        
        # Extract the generated value
        match = re.search(r"(\d+\.\d{2})::test::", result)
        assert match is not None
        
        value_str = match.group(1)
        # Should have exactly 2 digits after decimal point
        assert re.match(r"\d+\.\d{2}$", value_str)
    
    def test_range_with_swapped_min_max(self, temp_dir):
        """Test that swapped min/max values are handled gracefully"""
        # Should swap internally if min > max
        prompt = "2.0-1.5::content::"
        result = make_prompt_dynamic(prompt, "testuser", temp_dir, seed=42)
        
        match = re.search(r"(\d+\.\d{2})::content::", result)
        assert match is not None
        
        generated_value = float(match.group(1))
        assert 1.5 <= generated_value <= 2.0
    
    def test_zero_values(self, temp_dir):
        """Test emphasis with zero values"""
        prompt = "0.0::zero emphasis::"
        result = make_prompt_dynamic(prompt, "testuser", temp_dir, seed=42)
        assert result == "0.00::zero emphasis::"
    
    def test_large_values(self, temp_dir):
        """Test emphasis with large decimal values"""
        prompt = "10.5-15.7::large emphasis::"
        result = make_prompt_dynamic(prompt, "testuser", temp_dir, seed=42)
        
        match = re.search(r"(\d+\.\d{2})::large emphasis::", result)
        assert match is not None
        
        generated_value = float(match.group(1))
        assert 10.5 <= generated_value <= 15.7
    
    def test_multiple_emphasis_ranges_in_prompt(self, temp_dir):
        """Test multiple emphasis ranges in same prompt"""
        prompt = "1.0-2.0::first:: and 3.0::second:: emphasis"
        result = make_prompt_dynamic(prompt, "testuser", temp_dir, seed=42)
        
        # Should have both emphasis ranges processed
        first_match = re.search(r"(\d+\.\d{2})::first::", result)
        second_match = re.search(r"(\d+\.\d{2})::second::", result)
        
        assert first_match is not None
        assert second_match is not None
        
        first_value = float(first_match.group(1))
        second_value = float(second_match.group(1))
        
        assert 1.0 <= first_value <= 2.0
        assert second_value == 3.0
    
    def test_emphasis_with_special_characters(self, temp_dir):
        """Test emphasis content with special characters"""
        prompt = "1.5::text with spaces and symbols!@#::"
        result = make_prompt_dynamic(prompt, "testuser", temp_dir, seed=42)
        assert result == "1.50::text with spaces and symbols!@#::"


class TestChoiceOptionProcessing:
    """Test choice option syntax: {option1|option2|option3}"""
    
    def test_basic_choice_selection(self, temp_dir):
        """Test basic choice option selection"""
        # Requirement 2.1: Should randomly select one option
        prompt = "{red|blue|green}"
        result = make_prompt_dynamic(prompt, "testuser", temp_dir, seed=42)
        assert result in ["red", "blue", "green"]
    
    def test_choice_with_spaces(self, temp_dir):
        """Test choice options with spaces are preserved"""
        # Requirement 2.3: Spaces should be preserved
        prompt = "{option one|option two|option three}"
        result = make_prompt_dynamic(prompt, "testuser", temp_dir, seed=42)
        assert result in ["option one", "option two", "option three"]
    
    def test_choice_deterministic_with_seed(self, temp_dir):
        """Test that same seed produces same choice"""
        prompt = "{red|blue|green}"
        result1 = make_prompt_dynamic(prompt, "testuser", temp_dir, seed=42)
        result2 = make_prompt_dynamic(prompt, "testuser", temp_dir, seed=42)
        assert result1 == result2
    
    def test_choice_different_seeds_different_results(self, temp_dir):
        """Test that different seeds can produce different results"""
        prompt = "{red|blue|green|yellow|purple|orange}"  # More options for variety
        results = set()
        for seed in range(10):
            result = make_prompt_dynamic(prompt, "testuser", temp_dir, seed=seed)
            results.add(result)
        
        # With 6 options and 10 different seeds, we should get some variety
        assert len(results) > 1
    
    def test_multiple_choices_in_prompt(self, temp_dir):
        """Test multiple choice options in same prompt"""
        prompt = "A {red|blue} {cat|dog} in the {park|house}"
        result = make_prompt_dynamic(prompt, "testuser", temp_dir, seed=42)
        
        # Should contain valid combinations
        colors = ["red", "blue"]
        animals = ["cat", "dog"]
        locations = ["park", "house"]
        
        # Check that result contains one of each category
        has_color = any(color in result for color in colors)
        has_animal = any(animal in result for animal in animals)
        has_location = any(location in result for location in locations)
        
        assert has_color and has_animal and has_location
    
    def test_choice_with_special_characters(self, temp_dir):
        """Test choice options with special characters"""
        prompt = "{option!@#|option$%^|option&*()}"
        result = make_prompt_dynamic(prompt, "testuser", temp_dir, seed=42)
        assert result in ["option!@#", "option$%^", "option&*()"]
    
    def test_choice_with_numbers(self, temp_dir):
        """Test choice options with numbers"""
        prompt = "{123|456|789}"
        result = make_prompt_dynamic(prompt, "testuser", temp_dir, seed=42)
        assert result in ["123", "456", "789"]
    
    def test_single_option_no_pipe(self, temp_dir):
        """Test that single option without pipe returns original text"""
        # Requirement 2.1: Should handle gracefully when no pipe separator
        prompt = "{single option}"
        result = make_prompt_dynamic(prompt, "testuser", temp_dir, seed=42)
        assert result == "{single option}"  # Should return unchanged
    
    def test_nested_choice_with_emphasis(self, temp_dir):
        """Test choice options combined with emphasis ranges"""
        # Requirement 2.4: Should work with other dynamic syntax
        prompt = "1.5-2.0::{red|blue} text::"
        result = make_prompt_dynamic(prompt, "testuser", temp_dir, seed=42)
        
        # Should have emphasis value and one of the color choices
        match = re.search(r"(\d+\.\d{2})::(red|blue) text::", result)
        assert match is not None
        
        emphasis_value = float(match.group(1))
        color = match.group(2)
        
        assert 1.5 <= emphasis_value <= 2.0
        assert color in ["red", "blue"]


class TestErrorHandlingAndInvalidSyntax:
    """Test error handling for invalid syntax patterns"""
    
    def test_invalid_emphasis_missing_max(self, temp_dir):
        """Test invalid emphasis range with missing max value"""
        # The regex matches but max_val_str is empty, so it treats as single value
        prompt = "1.5-::content::"
        result = make_prompt_dynamic(prompt, "testuser", temp_dir, seed=42)
        # Should treat as single value 1.5
        assert result == "1.50::content::"
    
    def test_invalid_emphasis_missing_value(self, temp_dir):
        """Test invalid emphasis with missing value entirely"""
        prompt = "::content::"
        result = make_prompt_dynamic(prompt, "testuser", temp_dir, seed=42)
        # Should return original text on invalid syntax
        assert result == "::content::"
    
    def test_invalid_emphasis_non_numeric(self, temp_dir):
        """Test invalid emphasis with non-numeric values"""
        prompt = "abc::content::"
        result = make_prompt_dynamic(prompt, "testuser", temp_dir, seed=42)
        # Regex doesn't match non-numeric patterns, so returns unchanged
        assert result == "abc::content::"
    
    def test_invalid_emphasis_non_numeric_range(self, temp_dir):
        """Test invalid emphasis range with non-numeric values"""
        prompt = "abc-def::content::"
        result = make_prompt_dynamic(prompt, "testuser", temp_dir, seed=42)
        # Regex doesn't match non-numeric patterns, so returns unchanged
        assert result == "abc-def::content::"
    
    def test_empty_choice_options(self, temp_dir):
        """Test empty choice options"""
        # Requirement 2.5: Should handle empty choices gracefully
        prompt = "{}"
        result = make_prompt_dynamic(prompt, "testuser", temp_dir, seed=42)
        assert result == "{}"  # Should return unchanged
    
    def test_choice_with_empty_options(self, temp_dir):
        """Test choice with some empty options"""
        prompt = "{red||blue}"  # Empty middle option
        result = make_prompt_dynamic(prompt, "testuser", temp_dir, seed=42)
        assert result in ["red", "", "blue"]  # Empty string is valid choice
    
    def test_choice_all_empty_options(self, temp_dir):
        """Test choice with all empty options"""
        prompt = "{||}"
        result = make_prompt_dynamic(prompt, "testuser", temp_dir, seed=42)
        # The regex pattern requires at least one non-} char before and after pipe
        # So {||} doesn't match and returns unchanged
        assert result == "{||}"
    
    def test_choice_with_actual_empty_options(self, temp_dir):
        """Test choice with empty options that match the regex"""
        prompt = "{a||b}"  # This will match and have an empty middle option
        result = make_prompt_dynamic(prompt, "testuser", temp_dir, seed=42)
        assert result in ["a", "", "b"]  # Should select one of these, including empty string
    
    def test_malformed_emphasis_unclosed(self, temp_dir):
        """Test malformed emphasis syntax without closing markers"""
        prompt = "1.5::content"  # Missing closing ::
        result = make_prompt_dynamic(prompt, "testuser", temp_dir, seed=42)
        assert result == "1.5::content"  # Should return unchanged
    
    def test_malformed_choice_unclosed(self, temp_dir):
        """Test malformed choice syntax without closing brace"""
        prompt = "{red|blue"  # Missing closing }
        result = make_prompt_dynamic(prompt, "testuser", temp_dir, seed=42)
        assert result == "{red|blue"  # Should return unchanged
    
    def test_nested_braces_in_choice(self, temp_dir):
        """Test choice options with nested braces"""
        prompt = "{option{nested}|normal}"
        result = make_prompt_dynamic(prompt, "testuser", temp_dir, seed=42)
        # Should not process nested braces as separate choice
        assert result == "{option{nested}|normal}"


class TestEmptyAndMalformedInput:
    """Test handling of empty and malformed input"""
    
    def test_empty_prompt(self, temp_dir):
        """Test processing empty prompt"""
        prompt = ""
        result = make_prompt_dynamic(prompt, "testuser", temp_dir, seed=42)
        assert result == ""
    
    def test_whitespace_only_prompt(self, temp_dir):
        """Test processing whitespace-only prompt"""
        prompt = "   \n\t  "
        result = make_prompt_dynamic(prompt, "testuser", temp_dir, seed=42)
        assert result == "   \n\t  "  # Should preserve whitespace
    
    def test_prompt_with_only_text(self, temp_dir):
        """Test prompt with no dynamic elements"""
        prompt = "This is just regular text with no dynamic elements"
        result = make_prompt_dynamic(prompt, "testuser", temp_dir, seed=42)
        assert result == prompt
    
    def test_mixed_valid_invalid_syntax(self, temp_dir):
        """Test prompt with mix of valid and invalid syntax"""
        prompt = "Valid: {red|blue} Invalid: abc::text:: Valid: 2.0::bold::"
        result = make_prompt_dynamic(prompt, "testuser", temp_dir, seed=42)
        
        # Should process valid parts and handle invalid gracefully
        assert "red" in result or "blue" in result  # Valid choice processed
        assert "text" in result  # Invalid emphasis degraded to content
        assert "2.00::bold::" in result  # Valid emphasis processed
    
    def test_unicode_characters(self, temp_dir):
        """Test handling of unicode characters in prompts"""
        prompt = "1.5::café résumé 日本語::"
        result = make_prompt_dynamic(prompt, "testuser", temp_dir, seed=42)
        assert result == "1.50::café résumé 日本語::"
    
    def test_very_long_content(self, temp_dir):
        """Test handling of very long content in emphasis"""
        long_content = "a" * 1000  # 1000 character string
        prompt = f"1.5::{long_content}::"
        result = make_prompt_dynamic(prompt, "testuser", temp_dir, seed=42)
        assert result == f"1.50::{long_content}::"


class TestIntegrationWithExistingFeatures:
    """Test integration with existing dynamic prompt features"""
    
    def test_with_dynamic_prompt_files(self, temp_dir):
        """Test new syntax within dynamic prompt files"""
        # Create a prompt file with new syntax
        prompts_dir = os.path.join(temp_dir, "prompts", "testuser")
        os.makedirs(prompts_dir, exist_ok=True)
        
        with open(os.path.join(prompts_dir, "colors.txt"), "w") as f:
            f.write("1.5-2.0::{red|blue}::\ngreen\nyellow")
        
        prompt = "A __colors__ flower"
        result = make_prompt_dynamic(prompt, "testuser", temp_dir, seed=42)
        
        # Should process the dynamic file and then the syntax within it
        assert "flower" in result
        # Should have either processed emphasis+choice or plain color
        assert any(word in result for word in ["red", "blue", "green", "yellow"])
    
    def test_character_prompts_with_new_syntax(self, temp_dir):
        """Test character prompts processing with new syntax"""
        character_prompts = [
            {
                "positive": "1.5-2.0::{beautiful|gorgeous}:: character",
                "negative": "{ugly|bad}:: features"
            },
            {
                "positive": "2.0::handsome:: person",
                "negative": ""
            }
        ]
        
        result = make_character_prompts_dynamic(
            character_prompts, "testuser", temp_dir, seed=42
        )
        
        assert len(result) == 2
        
        # First character should have processed emphasis and choice
        first_positive = result[0]["positive"]
        assert "character" in first_positive
        assert "beautiful" in first_positive or "gorgeous" in first_positive
        
        first_negative = result[0]["negative"]
        assert "features" in first_negative
        assert "ugly" in first_negative or "bad" in first_negative
        
        # Second character should have processed emphasis
        second_positive = result[1]["positive"]
        assert "2.00::handsome:: person" == second_positive
        
        assert result[1]["negative"] == ""
    
    def test_grid_prompt_override_with_new_syntax(self, temp_dir):
        """Test grid prompt overrides work with new syntax"""
        # Create prompt file
        prompts_dir = os.path.join(temp_dir, "prompts", "testuser")
        os.makedirs(prompts_dir, exist_ok=True)
        
        with open(os.path.join(prompts_dir, "styles.txt"), "w") as f:
            f.write("1.5-2.0::{modern|classic}::\nvintage\nretro")
        
        grid_prompt = GridDynamicPromptInfo(
            str_to_replace_with="2.0::{contemporary|traditional}::",
            prompt_file="styles"
        )
        
        prompt = "A __styles__ design"
        result = make_prompt_dynamic(prompt, "testuser", temp_dir, seed=42, grid_prompt=grid_prompt)
        
        # Should use the override value and process its syntax
        assert "design" in result
        assert "contemporary" in result or "traditional" in result
    
    def test_recursive_processing_with_new_syntax(self, temp_dir):
        """Test recursive processing handles new syntax correctly"""
        # Create nested prompt files
        prompts_dir = os.path.join(temp_dir, "prompts", "testuser")
        os.makedirs(prompts_dir, exist_ok=True)
        
        with open(os.path.join(prompts_dir, "base.txt"), "w") as f:
            f.write("A __colors__ __objects__")
        
        with open(os.path.join(prompts_dir, "colors.txt"), "w") as f:
            f.write("1.5-2.0::{red|blue}::")
        
        with open(os.path.join(prompts_dir, "objects.txt"), "w") as f:
            f.write("{car|house}")
        
        prompt = "__base__"
        result = make_prompt_dynamic(prompt, "testuser", temp_dir, seed=42)
        
        # Should recursively process all levels
        assert "A " in result
        # Should have processed emphasis and choice from colors
        # Should have processed choice from objects
        assert any(word in result for word in ["red", "blue"])
        assert any(word in result for word in ["car", "house"])


class TestSeedConsistency:
    """Test that seeded randomization works correctly with new syntax"""
    
    def test_emphasis_range_seed_consistency(self, temp_dir):
        """Test that same seed produces same emphasis values"""
        prompt = "1.0-5.0::test::"
        
        result1 = make_prompt_dynamic(prompt, "testuser", temp_dir, seed=123)
        result2 = make_prompt_dynamic(prompt, "testuser", temp_dir, seed=123)
        
        assert result1 == result2
    
    def test_choice_option_seed_consistency(self, temp_dir):
        """Test that same seed produces same choice selections"""
        prompt = "{option1|option2|option3|option4|option5}"
        
        result1 = make_prompt_dynamic(prompt, "testuser", temp_dir, seed=456)
        result2 = make_prompt_dynamic(prompt, "testuser", temp_dir, seed=456)
        
        assert result1 == result2
    
    def test_combined_syntax_seed_consistency(self, temp_dir):
        """Test seed consistency with combined syntax elements"""
        prompt = "1.0-3.0::{red|blue|green} {cat|dog}:: and {house|car}"
        
        result1 = make_prompt_dynamic(prompt, "testuser", temp_dir, seed=789)
        result2 = make_prompt_dynamic(prompt, "testuser", temp_dir, seed=789)
        
        assert result1 == result2
    
    def test_different_seeds_produce_variation(self, temp_dir):
        """Test that different seeds can produce different results"""
        prompt = "1.0-10.0::{red|blue|green|yellow|purple}::"
        
        results = set()
        for seed in range(20):
            result = make_prompt_dynamic(prompt, "testuser", temp_dir, seed=seed)
            results.add(result)
        
        # With wide range and multiple options, should get variety
        assert len(results) > 1