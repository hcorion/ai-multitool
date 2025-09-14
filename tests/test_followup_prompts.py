"""
Unit tests for follow-up prompt file parsing and data structures.

This module tests the follow-up prompt functionality including:
- Follow-up file parsing with column-based options
- Data structure creation and validation
- Error handling for malformed files
- Integration with existing prompt system

Requirements tested: 1.1, 1.2, 5.1, 5.2, 5.3, 5.4, 5.5
"""

import pytest
import os
import tempfile
from dynamic_prompts import (
    parse_followup_file,
    FollowUpPromptFile,
    FollowUpState,
    get_prompt_dict,
    get_prompts_for_name,
    make_prompt_dynamic
)


class TestFollowUpPromptFileParsing:
    """Test parsing of follow-up prompt files with column syntax"""
    
    def test_parse_valid_followup_file(self, temp_dir):
        """Test parsing a valid follow-up file with proper column syntax"""
        # Requirement 1.1: Should recognize files with # columns: header
        file_path = os.path.join(temp_dir, "test_colors.txt")
        with open(file_path, "w") as f:
            f.write("# columns: primary, secondary, tertiary\n")
            f.write("red||green||blue\n")
            f.write("yellow||purple||orange\n")
        
        result = parse_followup_file(file_path)
        
        assert result is not None
        assert isinstance(result, FollowUpPromptFile)
        assert result.name == "test_colors"
        assert result.column_count == 3
        assert len(result.rows) == 2
        assert result.rows[0] == ["red", "green", "blue"]
        assert result.rows[1] == ["yellow", "purple", "orange"]
    
    def test_parse_followup_file_with_spaces(self, temp_dir):
        """Test parsing follow-up file with spaces in options"""
        # Requirement 1.2: Should handle spaces in column options
        file_path = os.path.join(temp_dir, "test_styles.txt")
        with open(file_path, "w") as f:
            f.write("# columns: style one, style two\n")
            f.write("modern art||classic painting\n")
            f.write("digital design||traditional sketch\n")
        
        result = parse_followup_file(file_path)
        
        assert result is not None
        assert result.column_count == 2
        assert result.rows[0] == ["modern art", "classic painting"]
        assert result.rows[1] == ["digital design", "traditional sketch"]
    
    def test_parse_followup_file_single_column(self, temp_dir):
        """Test parsing follow-up file with single column"""
        file_path = os.path.join(temp_dir, "test_single.txt")
        with open(file_path, "w") as f:
            f.write("# columns: single\n")
            f.write("option1\n")
            f.write("option2\n")
        
        result = parse_followup_file(file_path)
        
        assert result is not None
        assert result.column_count == 1
        assert result.rows[0] == ["option1"]
        assert result.rows[1] == ["option2"]
    
    def test_parse_followup_file_with_empty_lines(self, temp_dir):
        """Test parsing follow-up file with empty lines and comments"""
        file_path = os.path.join(temp_dir, "test_empty.txt")
        with open(file_path, "w") as f:
            f.write("# columns: col1, col2\n")
            f.write("\n")  # Empty line
            f.write("# This is a comment\n")
            f.write("red||blue\n")
            f.write("\n")  # Another empty line
            f.write("green||yellow\n")
        
        result = parse_followup_file(file_path)
        
        assert result is not None
        assert result.column_count == 2
        assert len(result.rows) == 2
        assert result.rows[0] == ["red", "blue"]
        assert result.rows[1] == ["green", "yellow"]
    
    def test_parse_followup_file_with_empty_columns(self, temp_dir):
        """Test parsing follow-up file with empty column values"""
        # Requirement 5.2: Should handle empty columns gracefully
        file_path = os.path.join(temp_dir, "test_empty_cols.txt")
        with open(file_path, "w") as f:
            f.write("# columns: col1, col2, col3\n")
            f.write("red||||blue\n")  # Empty middle column
            f.write("||green||\n")    # Empty first and last columns
        
        result = parse_followup_file(file_path)
        
        assert result is not None
        assert result.column_count == 3
        assert result.rows[0] == ["red", "", "blue"]
        assert result.rows[1] == ["", "green", ""]


class TestFollowUpPromptFileErrorHandling:
    """Test error handling for malformed follow-up files"""
    
    def test_parse_regular_file_returns_none(self, temp_dir):
        """Test that regular prompt files return None"""
        # Requirement 5.3: Should fall back to regular file behavior
        file_path = os.path.join(temp_dir, "regular.txt")
        with open(file_path, "w") as f:
            f.write("red\n")
            f.write("blue\n")
            f.write("green\n")
        
        result = parse_followup_file(file_path)
        assert result is None
    
    def test_parse_file_with_malformed_header(self, temp_dir):
        """Test parsing file with malformed column header"""
        # Requirement 5.3: Should handle malformed headers gracefully
        file_path = os.path.join(temp_dir, "malformed.txt")
        with open(file_path, "w") as f:
            f.write("columns: missing hash\n")  # Missing # prefix
            f.write("red||blue\n")
        
        result = parse_followup_file(file_path)
        assert result is None
    
    def test_parse_file_inconsistent_column_counts(self, temp_dir):
        """Test parsing file with inconsistent column counts"""
        # Requirement 5.1: Should handle inconsistent column counts gracefully
        file_path = os.path.join(temp_dir, "inconsistent.txt")
        with open(file_path, "w") as f:
            f.write("# columns: col1, col2, col3\n")
            f.write("red||blue||green\n")    # 3 columns
            f.write("yellow||purple\n")      # 2 columns - should be padded
            f.write("orange||pink||cyan||magenta\n")  # 4 columns - should be truncated
        
        result = parse_followup_file(file_path)
        
        assert result is not None
        assert result.column_count == 3
        assert result.rows[0] == ["red", "blue", "green"]
        assert result.rows[1] == ["yellow", "purple", ""]  # Padded with empty string
        assert result.rows[2] == ["orange", "pink", "cyan"]  # Truncated to 3 columns
    
    def test_parse_empty_file(self, temp_dir):
        """Test parsing completely empty file"""
        # Requirement 5.4: Should handle empty files gracefully
        file_path = os.path.join(temp_dir, "empty.txt")
        with open(file_path, "w") as f:
            pass  # Create empty file
        
        result = parse_followup_file(file_path)
        assert result is None
    
    def test_parse_file_header_only(self, temp_dir):
        """Test parsing file with header but no data rows"""
        # Requirement 5.5: Should handle files with no data gracefully
        file_path = os.path.join(temp_dir, "header_only.txt")
        with open(file_path, "w") as f:
            f.write("# columns: col1, col2\n")
        
        result = parse_followup_file(file_path)
        assert result is None
    
    def test_parse_nonexistent_file(self):
        """Test parsing nonexistent file"""
        # Requirement 5.4: Should handle file errors gracefully
        result = parse_followup_file("/nonexistent/path/file.txt")
        assert result is None
    
    def test_parse_file_with_unicode_content(self, temp_dir):
        """Test parsing file with unicode characters"""
        file_path = os.path.join(temp_dir, "unicode.txt")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("# columns: français, 日本語\n")
            f.write("café||寿司\n")
            f.write("résumé||漢字\n")
        
        result = parse_followup_file(file_path)
        
        assert result is not None
        assert result.column_count == 2
        assert result.rows[0] == ["café", "寿司"]
        assert result.rows[1] == ["résumé", "漢字"]


class TestFollowUpDataStructures:
    """Test the follow-up data structure classes"""
    
    def test_followup_prompt_file_creation(self):
        """Test creating FollowUpPromptFile dataclass"""
        followup_file = FollowUpPromptFile(
            name="test_colors",
            column_count=3,
            rows=[["red", "green", "blue"], ["yellow", "purple", "orange"]]
        )
        
        assert followup_file.name == "test_colors"
        assert followup_file.column_count == 3
        assert len(followup_file.rows) == 2
        assert followup_file.rows[0] == ["red", "green", "blue"]
    
    def test_followup_state_creation(self):
        """Test creating FollowUpState dataclass"""
        state = FollowUpState(
            locked_seed=12345,
            current_column=1,
            selected_row_index=2
        )
        
        assert state.locked_seed == 12345
        assert state.current_column == 1
        assert state.selected_row_index == 2


class TestGetPromptDictSeparation:
    """Test that get_prompt_dict separates regular and follow-up files"""
    
    def test_get_prompt_dict_separates_files(self, temp_dir):
        """Test that get_prompt_dict returns separate dictionaries"""
        # Create prompts directory
        prompts_dir = os.path.join(temp_dir, "prompts", "testuser")
        os.makedirs(prompts_dir, exist_ok=True)
        
        # Create regular prompt file
        with open(os.path.join(prompts_dir, "colors.txt"), "w") as f:
            f.write("red\nblue\ngreen\n")
        
        # Create follow-up prompt file
        with open(os.path.join(prompts_dir, "palettes.txt"), "w") as f:
            f.write("# columns: primary, secondary\n")
            f.write("red||blue\n")
            f.write("green||yellow\n")
        
        regular_prompts, followup_prompts = get_prompt_dict("testuser", temp_dir)
        
        # Check regular prompts
        assert "colors" in regular_prompts
        assert "palettes" not in regular_prompts
        assert regular_prompts["colors"] == ["red", "blue", "green"]
        
        # Check follow-up prompts
        assert "palettes" in followup_prompts
        assert "colors" not in followup_prompts
        assert followup_prompts["palettes"].name == "palettes"
        assert followup_prompts["palettes"].column_count == 2
        assert followup_prompts["palettes"].rows == [["red", "blue"], ["green", "yellow"]]
    
    def test_get_prompt_dict_empty_directory(self, temp_dir):
        """Test get_prompt_dict with empty directory"""
        regular_prompts, followup_prompts = get_prompt_dict("testuser", temp_dir)
        
        assert isinstance(regular_prompts, dict)
        assert isinstance(followup_prompts, dict)
        assert len(regular_prompts) == 0
        assert len(followup_prompts) == 0
    
    def test_get_prompt_dict_handles_file_errors(self, temp_dir):
        """Test that get_prompt_dict handles file reading errors gracefully"""
        prompts_dir = os.path.join(temp_dir, "prompts", "testuser")
        os.makedirs(prompts_dir, exist_ok=True)
        
        # Create a file that will cause reading issues (we'll simulate by creating a directory with .txt extension)
        bad_file_path = os.path.join(prompts_dir, "bad_file.txt")
        os.makedirs(bad_file_path, exist_ok=True)  # Create directory instead of file
        
        # Should not crash and should return empty dictionaries
        regular_prompts, followup_prompts = get_prompt_dict("testuser", temp_dir)
        
        assert isinstance(regular_prompts, dict)
        assert isinstance(followup_prompts, dict)
        # Should not contain the bad file
        assert "bad_file" not in regular_prompts
        assert "bad_file" not in followup_prompts


class TestGetPromptsForNameIntegration:
    """Test get_prompts_for_name works with both regular and follow-up files"""
    
    def test_get_prompts_for_name_regular_file(self, temp_dir):
        """Test getting prompts from regular file"""
        prompts_dir = os.path.join(temp_dir, "prompts", "testuser")
        os.makedirs(prompts_dir, exist_ok=True)
        
        with open(os.path.join(prompts_dir, "colors.txt"), "w") as f:
            f.write("red\nblue\ngreen\n")
        
        result = get_prompts_for_name("testuser", temp_dir, "colors")
        assert result == ["red", "blue", "green"]
    
    def test_get_prompts_for_name_followup_file(self, temp_dir):
        """Test getting prompts from follow-up file (returns row identifiers for grid generation)"""
        prompts_dir = os.path.join(temp_dir, "prompts", "testuser")
        os.makedirs(prompts_dir, exist_ok=True)
        
        with open(os.path.join(prompts_dir, "palettes.txt"), "w") as f:
            f.write("# columns: primary, secondary\n")
            f.write("red||blue\n")
            f.write("green||yellow\n")
        
        result = get_prompts_for_name("testuser", temp_dir, "palettes")
        # Should return row identifiers for grid generation
        assert len(result) == 2  # 2 rows
        assert all(item.startswith("__FOLLOWUP_ROW_") and item.endswith("__") for item in result)
        # Check that the display names are correct
        assert "__FOLLOWUP_ROW_0:red__" in result
        assert "__FOLLOWUP_ROW_1:green__" in result
    
    def test_get_prompts_for_name_nonexistent(self, temp_dir):
        """Test getting prompts for nonexistent file"""
        result = get_prompts_for_name("testuser", temp_dir, "nonexistent")
        assert result == []


class TestMakePromptDynamicIntegration:
    """Test make_prompt_dynamic works with follow-up files (basic fallback behavior)"""
    
    def test_make_prompt_dynamic_with_followup_file(self, temp_dir):
        """Test that make_prompt_dynamic handles follow-up files with proper state management"""
        prompts_dir = os.path.join(temp_dir, "prompts", "testuser")
        os.makedirs(prompts_dir, exist_ok=True)
        
        # Create follow-up file
        with open(os.path.join(prompts_dir, "colors.txt"), "w") as f:
            f.write("# columns: primary, secondary\n")
            f.write("red||blue\n")
            f.write("green||yellow\n")
        
        # With seed 42, should select row 1 (green||yellow) and use first column (green)
        result = make_prompt_dynamic("A __colors__ flower", "testuser", temp_dir, seed=42)
        assert "green" in result  # Should use first column from selected row
        assert "flower" in result
    
    def test_make_prompt_dynamic_mixed_files(self, temp_dir):
        """Test make_prompt_dynamic with both regular and follow-up files"""
        prompts_dir = os.path.join(temp_dir, "prompts", "testuser")
        os.makedirs(prompts_dir, exist_ok=True)
        
        # Create regular file
        with open(os.path.join(prompts_dir, "animals.txt"), "w") as f:
            f.write("cat\ndog\nbird\n")
        
        # Create follow-up file
        with open(os.path.join(prompts_dir, "colors.txt"), "w") as f:
            f.write("# columns: primary, secondary\n")
            f.write("red||blue\n")
            f.write("green||yellow\n")
        
        result = make_prompt_dynamic("A __colors__ __animals__", "testuser", temp_dir, seed=42)
        
        # Should contain proper selection from follow-up file and random from regular file
        assert "green" in result  # First column from selected row in follow-up file
        assert any(animal in result for animal in ["cat", "dog", "bird"])  # Random from regular file
    
    def test_make_prompt_dynamic_followup_file_not_found(self, temp_dir):
        """Test error handling when follow-up file is referenced but not found"""
        # Create prompts directory with at least one file so it's not empty
        prompts_dir = os.path.join(temp_dir, "prompts", "testuser")
        os.makedirs(prompts_dir, exist_ok=True)
        
        with open(os.path.join(prompts_dir, "existing.txt"), "w") as f:
            f.write("some content\n")
        
        with pytest.raises(ValueError, match="Could not find matching dynamic prompt file"):
            make_prompt_dynamic("A __nonexistent__ flower", "testuser", temp_dir, seed=42)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir