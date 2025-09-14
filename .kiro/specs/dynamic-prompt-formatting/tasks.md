# Implementation Plan

- [x] 1. Refactor prompt processing with new syntax implementation





  - Remove old `replace_brackets_section_positive()` and `replace_brackets_section_negative()` functions
  - Remove old regex patterns for `{content:count}` and `[content:count]` syntax
  - Define new regex patterns for emphasis ranges (`min-max::content::`) and choice options (`{option1|option2}`)
  - Implement `replace_emphasis_range_section()` function to handle decimal range processing with 2 decimal places
  - Implement `replace_choice_options()` function to handle pipe-separated option selection
  - Update `make_prompt_dynamic()` processing order: dynamic files → choice options → emphasis ranges → recursive processing
  - Replace old regex substitution calls with new pattern matching
  - Ensure seeded randomization works correctly with new syntax
  - Add comprehensive error handling for invalid syntax patterns
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.2, 2.3, 2.4, 2.5, 3.1, 3.2, 3.4, 4.1, 4.2, 4.3_

- [ ] 2. Enhance error handling with specific validation messages
  - Implement specific error messages for invalid emphasis range syntax
  - Implement specific error messages for invalid choice option syntax  
  - Add graceful degradation for malformed syntax (return content without processing)
  - Ensure error messages guide users to correct new format
  - _Requirements: 3.3, 3.5_

- [x] 3. Write comprehensive unit tests for new syntax processing





  - Create test cases for emphasis range processing (single values, ranges, decimal precision)
  - Create test cases for choice option processing (basic choices, spaces, edge cases)
  - Create test cases for error handling and invalid syntax
  - Create test cases for empty and malformed input handling
  - _Requirements: 1.1, 1.2, 1.4, 1.5, 2.1, 2.2, 2.3, 2.4, 2.5_

- [ ] 4. Write integration tests for combined syntax functionality
  - Test new syntax within dynamic prompt files (`__filename__` containing new syntax)
  - Test combination of emphasis ranges and choice options in same prompt
  - Test recursive processing with nested new syntax elements
  - Test character prompt processing with new syntax and seed offsets
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [ ] 5. Write regression tests to ensure existing functionality works
  - Test that `__filename__` dynamic prompt file processing still works correctly
  - Test that seeded randomization produces consistent results
  - Test that grid generation with `GridDynamicPromptInfo` overrides work correctly
  - Test that character prompt processing maintains seed variety
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [ ] 6. Update function documentation and code comments
  - Update docstrings to reflect new syntax and remove references to old bracket syntax
  - Update code comments to explain new processing logic
  - Update module-level documentation with new syntax examples
  - Remove outdated documentation about bracket duplication logic
  - _Requirements: 3.4, 3.5_