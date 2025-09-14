# Requirements Document

## Introduction

This feature updates the dynamic prompting system to use a more intuitive and streamlined syntax. The current system uses complex bracket duplication logic and range notation that can be confusing for users. The new format will simplify the syntax while maintaining all existing functionality and improving user experience.

## Requirements

### Requirement 1

**User Story:** As a user creating dynamic prompts, I want to use a simpler range notation format so that I can more easily specify emphasis ranges without complex bracket counting.

#### Acceptance Criteria

1. WHEN a user writes `1.5-1.6::emphasized text::` THEN the system SHALL randomly select a decimal value between 1.5 and 1.6 (rounded to two decimal places) and compile it to format like `1.55::emphasized text::`
2. WHEN a user writes `2.0::bold text::` THEN the system SHALL pass it through unchanged as the backend API already understands this format
3. WHEN the system processes range notation THEN it SHALL remove the old `{content:count}` and `[content:count}` bracket duplication syntax
4. WHEN the system generates random decimal values THEN it SHALL round them to exactly two decimal places (e.g., 1.55, 2.73)
5. WHEN a decimal emphasis value is compiled THEN the system SHALL output it in the `value::text::` format that the backend API expects

### Requirement 2

**User Story:** As a user creating dynamic prompts, I want to specify choice options using simple curly bracket syntax so that I can create variations without needing separate prompt files.

#### Acceptance Criteria

1. WHEN a user writes `{option1|option2|option3}` THEN the system SHALL randomly select one of the options
2. WHEN choice options are processed THEN the system SHALL support any number of options separated by pipe characters
3. WHEN choice options contain spaces THEN the system SHALL preserve the spacing in the selected option
4. WHEN choice options are nested within other dynamic syntax THEN the system SHALL process them correctly
5. WHEN choice options are empty (e.g., `{|}`) THEN the system SHALL handle gracefully without errors

### Requirement 3

**User Story:** As a developer implementing the new dynamic prompt syntax, I want to completely replace the old bracket duplication logic so that the system uses only the new, cleaner syntax.

#### Acceptance Criteria

1. WHEN the system processes prompts THEN it SHALL no longer recognize or process `{content:count}` syntax
2. WHEN the system processes prompts THEN it SHALL no longer recognize or process `[content:count]` syntax  
3. WHEN the system encounters invalid syntax THEN it SHALL provide clear error messages indicating the correct new format
4. WHEN the old bracket processing code is removed THEN it SHALL not break any existing functionality
5. WHEN users attempt to use old syntax THEN they SHALL receive helpful error messages guiding them to the new format

### Requirement 4

**User Story:** As a user creating complex prompts, I want the new syntax to work seamlessly with existing dynamic prompt features so that I can combine file-based prompts with inline choices and emphasis.

#### Acceptance Criteria

1. WHEN new choice syntax `{option1|option2}` is used within dynamic prompt files THEN it SHALL be processed correctly
2. WHEN new emphasis syntax `1.5-2.0::text::` is used within dynamic prompt files THEN it SHALL be processed correctly
3. WHEN new syntax is combined with existing `__filename__` syntax THEN both SHALL be processed in the correct order
4. WHEN nested dynamic prompts contain new syntax THEN the recursive processing SHALL handle them correctly
5. WHEN character prompts use new syntax THEN they SHALL be processed with appropriate seed offsets for variety