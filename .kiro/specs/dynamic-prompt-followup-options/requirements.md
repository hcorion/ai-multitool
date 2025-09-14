# Requirements Document

## Introduction

This feature adds follow-up options to the dynamic prompting system, allowing users to create prompt files with multiple columns of related options that progress sequentially. When a prompt file is used multiple times, it will advance through the columns (primary → secondary → tertiary) while maintaining seed consistency for the selected row. This enables creating coherent prompt progressions like color palettes, character development stages, or style variations.

## Requirements

### Requirement 1

**User Story:** As a user creating dynamic prompts, I want to define multi-column prompt files with follow-up options so that I can create sequential progressions of related prompts that maintain thematic consistency.

#### Acceptance Criteria

1. WHEN a user creates a prompt file with `# columns: primary, secondary, tertiary` header THEN the system SHALL recognize it as a follow-up options file
2. WHEN the file contains rows like `primary color1||secondary color1||tertiary color1` THEN the system SHALL parse each row into column-based options
3. WHEN the prompt file is first used THEN the system SHALL select a random row and use the first column option
4. WHEN the same prompt file is used again THEN the system SHALL use the next column option from the same row
5. WHEN all columns have been used THEN the system SHALL cycle back to the first column

### Requirement 2

**User Story:** As a user generating images with follow-up prompts, I want the system to lock the seed for each prompt file within a single generation so that the same row is consistently selected across multiple uses within that generation.

#### Acceptance Criteria

1. WHEN a follow-up prompt file is first used in a generation THEN the system SHALL generate a seed specific to that file and lock it for the duration of that generation
2. WHEN the same prompt file is used again within the same generation THEN the system SHALL use the locked seed to select the same row
3. WHEN the seed is locked for a file THEN the row selection SHALL be deterministic and consistent within that generation
4. WHEN a new generation starts THEN the system SHALL reset column progression for all follow-up files back to the first column
5. WHEN grid generation occurs THEN each grid image SHALL reset follow-up file progression independently

### Requirement 3

**User Story:** As a user working with character prompts, I want follow-up options to work consistently across all characters so that they progress through the same thematic sequence together.

#### Acceptance Criteria

1. WHEN follow-up prompt files are used in character prompts THEN they SHALL use the same locked seed for all characters
2. WHEN multiple characters use the same follow-up file THEN they SHALL select the same row and progress through columns together
3. WHEN character prompts combine regular and follow-up files THEN regular files SHALL use character-specific seed offsets while follow-up files SHALL use the shared locked seed
4. WHEN follow-up files are used across character prompts THEN the column progression SHALL be shared across all characters
5. WHEN character prompts use follow-up files THEN the progression SHALL persist across sessions for all characters

### Requirement 4

**User Story:** As a user managing prompt files, I want to see follow-up options in the Prompts Tab interface so that I can create, edit, and monitor the progression of these special prompt files.

#### Acceptance Criteria

1. WHEN the Prompts Tab displays prompt files THEN it SHALL visually distinguish follow-up option files from regular files
2. WHEN viewing a follow-up option file THEN the interface SHALL show the column headers and current progression state
3. WHEN editing a follow-up option file THEN the interface SHALL provide appropriate formatting guidance for the column syntax
4. WHEN creating a new follow-up option file THEN the interface SHALL offer templates or examples for the column header format
5. WHEN managing follow-up files THEN users SHALL be able to reset progression state if needed

### Requirement 5

**User Story:** As a developer implementing follow-up options, I want the system to handle edge cases and errors gracefully so that malformed files don't break the dynamic prompt processing.

#### Acceptance Criteria

1. WHEN a follow-up file has mismatched column counts between header and rows THEN the system SHALL handle gracefully with appropriate warnings
2. WHEN a follow-up file has empty columns THEN the system SHALL treat them as empty strings and continue processing
3. WHEN a follow-up file header is malformed THEN the system SHALL fall back to treating it as a regular prompt file
4. WHEN column separators (`||`) are missing or inconsistent THEN the system SHALL provide clear error messages
5. WHEN follow-up file processing fails THEN the system SHALL not break overall prompt generation