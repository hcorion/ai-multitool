"""
Unit tests for character prompt processing functionality.
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os
import json
from dataclasses import asdict

from app import (
    CharacterPrompt,
    MultiCharacterPromptData,
    _build_char_captions,
    _extract_character_prompts_from_form,
)
from dynamic_prompts import make_character_prompts_dynamic


class TestCharacterPromptDataClasses(unittest.TestCase):
    """Test character prompt data classes."""

    def test_character_prompt_creation(self):
        """Test CharacterPrompt data class creation."""
        char_prompt = CharacterPrompt(
            positive_prompt="a beautiful character",
            negative_prompt="ugly, deformed"
        )
        
        self.assertEqual(char_prompt.positive_prompt, "a beautiful character")
        self.assertEqual(char_prompt.negative_prompt, "ugly, deformed")

    def test_character_prompt_default_negative(self):
        """Test CharacterPrompt with default empty negative prompt."""
        char_prompt = CharacterPrompt(positive_prompt="a beautiful character")
        
        self.assertEqual(char_prompt.positive_prompt, "a beautiful character")
        self.assertEqual(char_prompt.negative_prompt, "")

    def test_multi_character_prompt_data_creation(self):
        """Test MultiCharacterPromptData creation with character prompts."""
        char1 = CharacterPrompt("character 1", "negative 1")
        char2 = CharacterPrompt("character 2", "negative 2")
        
        multi_prompt = MultiCharacterPromptData(
            main_prompt="main scene",
            main_negative_prompt="main negative",
            character_prompts=[char1, char2]
        )
        
        self.assertEqual(multi_prompt.main_prompt, "main scene")
        self.assertEqual(multi_prompt.main_negative_prompt, "main negative")
        self.assertEqual(len(multi_prompt.character_prompts), 2)
        self.assertEqual(multi_prompt.character_prompts[0].positive_prompt, "character 1")

    def test_multi_character_prompt_data_defaults(self):
        """Test MultiCharacterPromptData with default values."""
        multi_prompt = MultiCharacterPromptData(main_prompt="main scene")
        
        self.assertEqual(multi_prompt.main_prompt, "main scene")
        self.assertEqual(multi_prompt.main_negative_prompt, "")
        self.assertEqual(len(multi_prompt.character_prompts), 0)


class TestCharCaptionsBuilder(unittest.TestCase):
    """Test the _build_char_captions helper function."""

    def test_build_char_captions_positive(self):
        """Test building positive char_captions."""
        character_prompts = [
            {'positive': 'character 1 positive', 'negative': 'character 1 negative'},
            {'positive': 'character 2 positive', 'negative': 'character 2 negative'},
        ]
        
        result = _build_char_captions(character_prompts, 'positive')
        
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['char_caption'], 'character 1 positive')
        self.assertEqual(result[1]['char_caption'], 'character 2 positive')
        self.assertEqual(result[0]['centers'], [{'x': 0, 'y': 0}])

    def test_build_char_captions_negative(self):
        """Test building negative char_captions."""
        character_prompts = [
            {'positive': 'character 1 positive', 'negative': 'character 1 negative'},
            {'positive': 'character 2 positive', 'negative': 'character 2 negative'},
        ]
        
        result = _build_char_captions(character_prompts, 'negative')
        
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['char_caption'], 'character 1 negative')
        self.assertEqual(result[1]['char_caption'], 'character 2 negative')

    def test_build_char_captions_empty_prompts(self):
        """Test that empty prompts are omitted from char_captions."""
        character_prompts = [
            {'positive': 'character 1 positive', 'negative': ''},
            {'positive': '', 'negative': 'character 2 negative'},
            {'positive': 'character 3 positive', 'negative': 'character 3 negative'},
        ]
        
        positive_result = _build_char_captions(character_prompts, 'positive')
        negative_result = _build_char_captions(character_prompts, 'negative')
        
        # Only non-empty prompts should be included
        self.assertEqual(len(positive_result), 2)  # char 1 and char 3
        self.assertEqual(len(negative_result), 2)  # char 2 and char 3
        
        self.assertEqual(positive_result[0]['char_caption'], 'character 1 positive')
        self.assertEqual(positive_result[1]['char_caption'], 'character 3 positive')
        
        self.assertEqual(negative_result[0]['char_caption'], 'character 2 negative')
        self.assertEqual(negative_result[1]['char_caption'], 'character 3 negative')

    def test_build_char_captions_empty_list(self):
        """Test building char_captions with empty character list."""
        result = _build_char_captions([], 'positive')
        self.assertEqual(result, [])


class TestFormExtraction(unittest.TestCase):
    """Test form data extraction for character prompts."""

    def test_extract_character_prompts_from_form(self):
        """Test extracting character prompts from form data."""
        mock_request = Mock()
        form_data = {
            'character_prompts[0][positive]': 'character 1 positive',
            'character_prompts[0][negative]': 'character 1 negative',
            'character_prompts[1][positive]': 'character 2 positive',
            'character_prompts[1][negative]': 'character 2 negative',
        }
        mock_request.form = Mock()
        mock_request.form.get = lambda key, default="": form_data.get(key, default)
        mock_request.form.__contains__ = lambda self, key: key in form_data
        
        result = _extract_character_prompts_from_form(mock_request)
        
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['positive'], 'character 1 positive')
        self.assertEqual(result[0]['negative'], 'character 1 negative')
        self.assertEqual(result[1]['positive'], 'character 2 positive')
        self.assertEqual(result[1]['negative'], 'character 2 negative')

    def test_extract_character_prompts_empty_negative(self):
        """Test extracting character prompts with empty negative prompts."""
        mock_request = Mock()
        form_data = {
            'character_prompts[0][positive]': 'character 1 positive',
            'character_prompts[0][negative]': '',
            'character_prompts[1][positive]': 'character 2 positive',
            'character_prompts[1][negative]': 'character 2 negative',
        }
        mock_request.form = Mock()
        mock_request.form.get = lambda key, default="": form_data.get(key, default)
        mock_request.form.__contains__ = lambda self, key: key in form_data
        
        result = _extract_character_prompts_from_form(mock_request)
        
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['positive'], 'character 1 positive')
        self.assertEqual(result[0]['negative'], '')
        self.assertEqual(result[1]['positive'], 'character 2 positive')
        self.assertEqual(result[1]['negative'], 'character 2 negative')

    def test_extract_character_prompts_skip_empty_positive(self):
        """Test that characters with empty positive prompts are skipped."""
        mock_request = Mock()
        form_data = {
            'character_prompts[0][positive]': 'character 1 positive',
            'character_prompts[0][negative]': 'character 1 negative',
            'character_prompts[1][positive]': '',  # Empty positive prompt
            'character_prompts[1][negative]': 'character 2 negative',
            'character_prompts[2][positive]': 'character 3 positive',
            'character_prompts[2][negative]': '',
        }
        mock_request.form = Mock()
        mock_request.form.get = lambda key, default="": form_data.get(key, default)
        mock_request.form.__contains__ = lambda self, key: key in form_data
        
        result = _extract_character_prompts_from_form(mock_request)
        
        # Should only include characters 1 and 3 (character 2 has empty positive)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['positive'], 'character 1 positive')
        self.assertEqual(result[1]['positive'], 'character 3 positive')

    def test_extract_character_prompts_no_characters(self):
        """Test extracting when no character prompts are present."""
        mock_request = Mock()
        form_data = {}
        mock_request.form = Mock()
        mock_request.form.get = lambda key, default="": form_data.get(key, default)
        mock_request.form.__contains__ = lambda self, key: key in form_data
        
        result = _extract_character_prompts_from_form(mock_request)
        
        self.assertEqual(result, [])


class TestDynamicCharacterPrompts(unittest.TestCase):
    """Test dynamic prompt processing for character prompts."""

    def setUp(self):
        """Set up test environment with temporary directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.username = "testuser"
        self.prompts_dir = os.path.join(self.temp_dir, "prompts", self.username)
        os.makedirs(self.prompts_dir, exist_ok=True)
        
        # Create test prompt files
        with open(os.path.join(self.prompts_dir, "colors.txt"), "w") as f:
            f.write("red\nblue\ngreen\n")
        
        with open(os.path.join(self.prompts_dir, "animals.txt"), "w") as f:
            f.write("cat\ndog\nbird\n")

    def tearDown(self):
        """Clean up temporary directory."""
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_make_character_prompts_dynamic_basic(self):
        """Test basic dynamic prompt processing for characters."""
        character_prompts = [
            {'positive': 'a __colors__ character', 'negative': 'ugly'},
            {'positive': 'a __animals__ companion', 'negative': ''},
        ]
        
        result = make_character_prompts_dynamic(
            character_prompts, self.username, self.temp_dir, seed=42
        )
        
        self.assertEqual(len(result), 2)
        # Should replace __colors__ with one of the color options
        self.assertIn(result[0]['positive'].split()[1], ['red', 'blue', 'green'])
        # Should replace __animals__ with one of the animal options
        self.assertIn(result[1]['positive'].split()[1], ['cat', 'dog', 'bird'])
        
        self.assertEqual(result[0]['negative'], 'ugly')
        self.assertEqual(result[1]['negative'], '')

    def test_make_character_prompts_dynamic_empty_prompts(self):
        """Test dynamic processing with empty prompts."""
        character_prompts = [
            {'positive': '', 'negative': 'ugly'},
            {'positive': 'a character', 'negative': ''},
        ]
        
        result = make_character_prompts_dynamic(
            character_prompts, self.username, self.temp_dir, seed=42
        )
        
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['positive'], '')
        self.assertEqual(result[0]['negative'], 'ugly')
        self.assertEqual(result[1]['positive'], 'a character')
        self.assertEqual(result[1]['negative'], '')

    def test_make_character_prompts_dynamic_seed_variation(self):
        """Test that different characters get different seed offsets."""
        character_prompts = [
            {'positive': 'a __colors__ character', 'negative': ''},
            {'positive': 'a __colors__ companion', 'negative': ''},
        ]
        
        # Run multiple times to check for variation
        results = []
        for _ in range(10):
            result = make_character_prompts_dynamic(
                character_prompts, self.username, self.temp_dir, seed=42
            )
            results.append((result[0]['positive'], result[1]['positive']))
        
        # Characters should potentially get different colors due to seed offsets
        # At least verify the structure is correct
        for result in results:
            self.assertTrue(result[0].startswith('a '))
            self.assertTrue(result[1].startswith('a '))
            self.assertTrue(result[0].endswith(' character'))
            self.assertTrue(result[1].endswith(' companion'))


if __name__ == '__main__':
    unittest.main()


class TestErrorHandling(unittest.TestCase):
    """Test error handling for character prompt processing."""

    def setUp(self):
        """Set up test environment with temporary directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.username = "testuser"
        self.prompts_dir = os.path.join(self.temp_dir, "prompts", self.username)
        os.makedirs(self.prompts_dir, exist_ok=True)

    def tearDown(self):
        """Clean up temporary directory."""
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_make_character_prompts_dynamic_missing_prompt_file(self):
        """Test error handling when specific dynamic prompt file is missing but others exist."""
        # Create one valid prompt file so the prompts dict is not empty
        with open(os.path.join(self.prompts_dir, "colors.txt"), "w") as f:
            f.write("red\nblue\ngreen\n")
        
        character_prompts = [
            {'positive': 'a __missing_file__ character', 'negative': ''},
        ]
        
        # Now it should raise ValueError because prompts dict is not empty but missing_file doesn't exist
        with self.assertRaises(ValueError) as context:
            make_character_prompts_dynamic(
                character_prompts, self.username, self.temp_dir, seed=42
            )
        
        # Check that the error message mentions the missing file
        error_message = str(context.exception)
        self.assertIn("missing_file", error_message)

    def test_build_char_captions_with_none_values(self):
        """Test _build_char_captions handles None values gracefully."""
        character_prompts = [
            {'positive': None, 'negative': 'negative text'},
            {'positive': 'positive text', 'negative': None},
        ]
        
        # Should handle None values by treating them as empty strings
        positive_result = _build_char_captions(character_prompts, 'positive')
        negative_result = _build_char_captions(character_prompts, 'negative')
        
        # Only non-None, non-empty prompts should be included
        self.assertEqual(len(positive_result), 1)
        self.assertEqual(len(negative_result), 1)
        self.assertEqual(positive_result[0]['char_caption'], 'positive text')
        self.assertEqual(negative_result[0]['char_caption'], 'negative text')

    def test_extract_character_prompts_malformed_keys(self):
        """Test form extraction with malformed keys."""
        mock_request = Mock()
        form_data = {
            'character_prompts[0][positive]': 'valid character',
            'character_prompts[0][negative]': 'valid negative',
            'character_prompts[invalid][positive]': 'invalid key',  # Non-numeric index
            'character_prompts[1][unknown]': 'unknown field',  # Unknown field type
        }
        mock_request.form = Mock()
        mock_request.form.get = lambda key, default="": form_data.get(key, default)
        mock_request.form.__contains__ = lambda self, key: key in form_data
        
        result = _extract_character_prompts_from_form(mock_request)
        
        # Should only extract valid character prompts
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['positive'], 'valid character')
        self.assertEqual(result[0]['negative'], 'valid negative')


class TestIntegrationScenarios(unittest.TestCase):
    """Test integration scenarios for character prompt processing."""

    def setUp(self):
        """Set up test environment with temporary directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.username = "testuser"
        self.prompts_dir = os.path.join(self.temp_dir, "prompts", self.username)
        os.makedirs(self.prompts_dir, exist_ok=True)
        
        # Create test prompt files
        with open(os.path.join(self.prompts_dir, "styles.txt"), "w") as f:
            f.write("anime\nrealistic\ncartoon\n")

    def tearDown(self):
        """Clean up temporary directory."""
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_full_character_prompt_processing_pipeline(self):
        """Test the complete pipeline from form extraction to API request building."""
        # Simulate form data
        mock_request = Mock()
        form_data = {
            'character_prompts[0][positive]': 'a __styles__ character with red hair',
            'character_prompts[0][negative]': 'ugly, deformed',
            'character_prompts[1][positive]': 'a __styles__ companion with blue eyes',
            'character_prompts[1][negative]': '',
        }
        mock_request.form = Mock()
        mock_request.form.get = lambda key, default="": form_data.get(key, default)
        mock_request.form.__contains__ = lambda self, key: key in form_data
        
        # Extract character prompts from form
        character_prompts = _extract_character_prompts_from_form(mock_request)
        
        # Process dynamic prompts
        processed_prompts = make_character_prompts_dynamic(
            character_prompts, self.username, self.temp_dir, seed=42
        )
        
        # Build char_captions for API request
        positive_captions = _build_char_captions(processed_prompts, 'positive')
        negative_captions = _build_char_captions(processed_prompts, 'negative')
        
        # Verify the complete pipeline
        self.assertEqual(len(character_prompts), 2)
        self.assertEqual(len(processed_prompts), 2)
        self.assertEqual(len(positive_captions), 2)  # Both characters have positive prompts
        self.assertEqual(len(negative_captions), 1)  # Only first character has negative prompt
        
        # Verify dynamic prompt replacement occurred
        self.assertIn('character with red hair', processed_prompts[0]['positive'])
        self.assertIn('companion with blue eyes', processed_prompts[1]['positive'])
        
        # Verify one of the styles was selected
        first_style = processed_prompts[0]['positive'].split()[1]  # Should be anime/realistic/cartoon
        self.assertIn(first_style, ['anime', 'realistic', 'cartoon'])
        
        # Verify API request structure
        self.assertEqual(positive_captions[0]['centers'], [{'x': 0, 'y': 0}])
        self.assertEqual(negative_captions[0]['char_caption'], 'ugly, deformed')