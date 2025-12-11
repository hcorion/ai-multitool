# Requirements Document

## Introduction

This feature implements a NovelAI vibe encoding database and frontend system. Vibe encoding allows users to extract visual style information from existing generated images and apply that style to new generations. The system will encode images at multiple strength levels, generate preview grids showing the effect of different encoding and reference strengths, and provide a UI for selecting and applying vibes during image generation.

## Glossary

- **Vibe Encoding**: A base64-encoded representation of an image's visual style extracted via NovelAI's `/ai/encode-vibe` endpoint
- **Vibe Collection**: A named set of vibe encodings for a single source image, containing encodings at multiple information extraction levels
- **Information Extracted (Encoding Strength)**: A float value (0.0-1.0) controlling how much style information is extracted from the source image during encoding
- **Reference Strength**: A float value (0.0-1.0) controlling how strongly the encoded vibe influences the generated image
- **Preview Grid**: A 5x5 matrix of images showing combinations of encoding strengths and reference strengths
- **GUID**: A globally unique identifier used to reference a vibe collection

## Requirements

### Requirement 1

**User Story:** As a user, I want to create a vibe encoding from an existing generated image, so that I can reuse its visual style in future generations.

#### Acceptance Criteria

1. WHEN a user clicks the "Generate Vibe" button on an image in the grid THEN the System SHALL display a confirmation popup warning about the high Anlas cost
2. WHEN a user confirms vibe generation THEN the System SHALL prompt for a human-readable name for the vibe collection
3. WHEN a user submits the vibe name THEN the System SHALL call the NovelAI encode-vibe endpoint with the image at five encoding strengths: 1.0, 0.85, 0.7, 0.5, 0.35
4. WHEN the System receives encoded vibe data THEN the System SHALL store each encoding with its strength level, model used, and the encoded base64 data in a JSON database file
5. WHEN the System stores a vibe collection THEN the System SHALL generate a unique GUID for the collection
6. WHEN the System stores a vibe collection THEN the System SHALL save the encoded vibe data to the JSON database

### Requirement 2

**User Story:** As a user, I want to see preview images showing how different vibe settings affect generation, so that I can choose appropriate strength values.

#### Acceptance Criteria

1. WHEN a vibe collection is created THEN the System SHALL generate 25 individual preview images covering all strength combinations
2. WHEN generating preview images THEN the System SHALL use all combinations of encoding strengths (1.0, 0.85, 0.7, 0.5, 0.35) and reference strengths (1.0, 0.85, 0.7, 0.5, 0.35)
3. WHEN generating preview images THEN the System SHALL use a fixed seed and fixed prompt stored in the code
4. WHEN generating preview images THEN the System SHALL use low resolution (512x768) for efficiency
5. WHEN preview images are generated THEN the System SHALL create compressed JPG thumbnails alongside the full PNG files
6. WHEN preview images are generated THEN the System SHALL store each image as an individual file with a filename indicating the encoding and reference strength values

### Requirement 3

**User Story:** As a user, I want to apply vibes to my NovelAI image generations, so that I can influence the visual style of new images.

#### Acceptance Criteria

1. WHEN a user generates an image with NovelAI THEN the System SHALL allow specifying one to four vibes by their GUIDs
2. WHEN a user selects a vibe THEN the System SHALL allow choosing from the pre-generated encoding strength values (1.0, 0.85, 0.7, 0.5, 0.35)
3. WHEN a user selects a vibe THEN the System SHALL allow specifying any reference strength value between 0.0 and 1.0
4. WHEN vibes are specified for generation THEN the System SHALL include `reference_strength_multiple` and `reference_image_multiple` arrays in the generation parameters
5. WHEN multiple vibes are specified THEN the System SHALL pass all vibe encodings and reference strengths as parallel arrays

### Requirement 4

**User Story:** As a user, I want to browse and select vibes through a visual interface, so that I can easily find and apply the style I want.

#### Acceptance Criteria

1. WHEN a user clicks "Add Vibe" in the NovelAI generation panel THEN the System SHALL display a vibe selection modal
2. WHEN the vibe selection modal opens THEN the System SHALL display a grid of all available vibe collections showing the user-provided name and a preview image for each
3. WHEN a user hovers over or selects a vibe THEN the System SHALL display discrete sliders for encoding strength and reference strength
4. WHEN a user adjusts the encoding strength slider THEN the System SHALL update the preview thumbnail to show the corresponding pre-generated image
5. WHEN a user adjusts the reference strength slider THEN the System SHALL update the preview thumbnail to show the closest matching pre-generated reference strength image
6. WHEN a user confirms vibe selection THEN the System SHALL add the vibe to the generation panel with the selected strength values
7. WHEN a vibe is added to the generation panel THEN the System SHALL display the vibe name and a thumbnail that updates based on the selected encoding and reference strengths

### Requirement 5

**User Story:** As a user, I want to copy the seed from a generated image, so that I can reproduce or iterate on specific generations.

#### Acceptance Criteria

1. WHEN viewing an image in the grid modal THEN the System SHALL display a "Copy Seed" button alongside existing action buttons
2. WHEN a user clicks "Copy Seed" THEN the System SHALL copy the seed value from the image metadata to the seed input field in the generation form
3. WHEN a user clicks "Copy Seed" THEN the System SHALL switch to the generation tab

### Requirement 6

**User Story:** As a user, I want vibe encodings to be validated for model compatibility, so that I don't accidentally use incompatible vibes.

#### Acceptance Criteria

1. WHEN storing a vibe encoding THEN the System SHALL record the model name used for encoding
2. WHEN a user attempts to use a vibe THEN the System SHALL verify the vibe was encoded with a compatible model
3. IF a vibe is incompatible with the current model THEN the System SHALL display a warning to the user

### Requirement 7

**User Story:** As a user, I want to manage my vibe collections, so that I can organize and remove vibes I no longer need.

#### Acceptance Criteria

1. WHEN viewing the vibe selection modal THEN the System SHALL display the name and creation date for each vibe collection
2. WHEN a user selects a vibe collection THEN the System SHALL provide an option to delete the collection
3. WHEN a user confirms deletion THEN the System SHALL remove the vibe collection data and all associated preview images

### Requirement 8

**User Story:** As a user, I want to remove vibes from my current generation settings, so that I can adjust my generation parameters.

#### Acceptance Criteria

1. WHEN a vibe is added to the generation panel THEN the System SHALL display a remove button for that vibe
2. WHEN a user clicks the remove button THEN the System SHALL remove the vibe from the generation parameters
3. WHEN all vibes are removed THEN the System SHALL hide the vibe section in the generation panel
