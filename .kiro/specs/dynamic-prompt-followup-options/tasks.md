# Implementation Plan

- [x] 1. Implement follow-up prompt file parsing and data structures





  - Create `FollowUpPromptFile` and `FollowUpState` dataclasses for managing follow-up file data and progression state
  - Implement `parse_followup_file()` function to detect `# columns:` header and parse rows with `||` separators
  - Add validation for consistent column counts across rows with graceful error handling
  - Modify `get_prompt_dict()` to return separate dictionaries for regular and follow-up prompt files
  - Add comprehensive error handling for malformed follow-up files with fallback to regular prompt file behavior
  - _Requirements: 1.1, 1.2, 5.1, 5.2, 5.3, 5.4, 5.5_

- [ ] 2. Implement follow-up state management and integrate with prompt processing system







  - Create `init_followup_state()` function to initialize empty state for each generation
  - Implement `get_followup_option()` function to handle seed locking, row selection, and column progression within a generation
  - Add logic for cycling back to first column when all columns have been used within the same generation
  - Modify `replace_dynamic_prompt_section()` to detect and handle follow-up files differently from regular files
  - Ensure follow-up files use shared locked seed while regular files continue using character-specific seed offsets
  - Update `make_prompt_dynamic()` to initialize and manage follow-up state during processing
  - Ensure state resets for each new generation and each grid image
  - Maintain backward compatibility with existing prompt files and processing logic
  - Add proper error handling to prevent follow-up file issues from breaking overall prompt generation
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 3.1, 3.2, 3.3, 3.4, 3.5_

- [ ] 3. Enhance backend API for follow-up file metadata
  - Modify existing `/prompt-files` endpoint to include follow-up file metadata (isFollowUp, totalColumns)
  - Add proper error handling and validation for follow-up file detection and parsing
  - Ensure API endpoints respect user isolation and security
  - _Requirements: 4.1, 4.2_

- [x] 4. Enhance frontend Prompts Tab for follow-up file support with integration tests





  - Update `PromptFile` interface to include follow-up file metadata (isFollowUp, totalColumns)
  - Modify `renderPromptFiles()` to visually distinguish follow-up files with special icons or badges
  - Add display of total column count in file preview
  - Update prompt file creation/editing modal to detect and validate follow-up file syntax
  - Add template suggestions and formatting guidance for follow-up file creation
  - Write integration tests for follow-up file display and visual indicators
  - Write tests for column count display in file preview
  - Write tests for file creation/editing with follow-up syntax validation
  - Write tests for error handling of malformed follow-up files in UI
  - _Requirements: 4.1, 4.2, 4.3, 4.4_

- [ ] 5. Write comprehensive unit tests for follow-up file functionality
  - Create test cases for follow-up file parsing with valid and invalid formats
  - Test state management functions (load, save, progression logic)
  - Test integration with existing prompt processing system
  - Test character prompt handling with mixed regular and follow-up files
  - Test error handling and graceful degradation for malformed files
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.2, 2.3, 2.4, 2.5, 5.1, 5.2, 5.3, 5.4, 5.5_

- [ ] 6. Write integration tests for follow-up files with character prompts
  - Test that follow-up files use shared locked seed across all characters
  - Test that regular files continue using character-specific seed offsets
  - Test mixed scenarios with both regular and follow-up files in character prompts
  - Test progression consistency within a single generation
  - Test that progression resets for each new generation and grid image
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_



- [ ] 7. Update documentation and add example follow-up files
  - Update module docstring in `dynamic_prompts.py` to document follow-up file syntax
  - Add code comments explaining follow-up file processing logic
  - Create example follow-up files for common use cases (color palettes, character development, style variations)
  - Update function docstrings to reflect new follow-up file parameters and behavior
  - Document the in-memory state management approach
  - _Requirements: 1.1, 1.2, 2.1, 4.4_