# Requirements Document

## Introduction

This feature extends the existing inpainting canvas system to support arbitrary color painting (img2img) in addition to mask painting (inpainting). Users will be able to paint colors directly on images and combine both techniques simultaneously - painting colors on some areas while masking other areas for regeneration. The feature integrates with the existing canvas infrastructure and maintains compatibility with the unified `/image` API endpoint.

## Glossary

- **Canvas_System**: The existing inpainting canvas infrastructure including brush tools, zoom/pan, undo/redo
- **Color_Layer**: A new canvas layer that stores RGB color data painted by the user
- **Mask_Layer**: The existing canvas layer that stores binary mask data (0 or 255)
- **Img2Img_Operation**: Backend operation that uses a painted image as input for generation
- **Inpainting_Operation**: Backend operation that regenerates masked areas of an image
- **Combined_Operation**: An operation that uses both color painting and masking simultaneously
- **Paint_Button**: UI button that opens the canvas editor for an image
- **Brush_Engine**: The existing brush stamping system that handles drawing
- **Canvas_Manager**: The existing canvas state and rendering orchestrator

## Requirements

### Requirement 1: Color Painting Canvas Layer

**User Story:** As a user, I want to paint arbitrary colors on an image, so that I can modify the image before regeneration.

#### Acceptance Criteria

1. THE Canvas_System SHALL maintain a separate Color_Layer with RGB data alongside the existing Mask_Layer
2. WHEN the user paints in color mode, THE Brush_Engine SHALL apply color stamps to the Color_Layer
3. THE Color_Layer SHALL preserve the original image data in unpainted areas
4. WHEN exporting, THE Canvas_System SHALL composite the Color_Layer over the original image to produce the painted image
5. THE Canvas_System SHALL export both the painted image and mask as separate data URLs

### Requirement 2: Dual-Mode Brush System

**User Story:** As a user, I want to switch between painting colors and painting masks, so that I can use both techniques on the same image.

#### Acceptance Criteria

1. THE Canvas_System SHALL support a color painting mode in addition to the existing mask painting mode
2. WHEN in color mode, THE Brush_Engine SHALL paint with a user-selected color
3. WHEN in mask mode, THE Brush_Engine SHALL paint binary mask values (0 or 255) as it currently does
4. THE Canvas_System SHALL allow switching between color mode and mask mode without losing painted data
5. THE Canvas_System SHALL provide a color picker UI element for selecting paint colors

### Requirement 3: Canvas Entry Points

**User Story:** As a user, I want to access the painting canvas from both the generated image page and the grid view, so that I can edit any image.

#### Acceptance Criteria

1. WHEN viewing a generated image, THE UI SHALL display a paint button
2. WHEN viewing the grid modal, THE UI SHALL display a paint button for each image
3. WHEN the user clicks a paint button, THE Canvas_System SHALL open with the selected image loaded
4. THE Canvas_System SHALL extract and preserve the original prompt metadata when opening an image
5. WHEN the user completes painting, THE Canvas_System SHALL populate the generation form with the painted image and mask data

### Requirement 4: Combined Operation Support

**User Story:** As a user, I want to use both color painting and masking simultaneously, so that I can paint some areas and regenerate other areas in a single operation.

#### Acceptance Criteria

1. WHEN both Color_Layer and Mask_Layer contain data, THE Canvas_System SHALL export both layers
2. THE Canvas_System SHALL send both the painted image and mask to the backend
3. THE Backend SHALL perform a Combined_Operation using both the painted image (img2img) and mask (inpainting)
4. WHEN only Color_Layer contains data, THE Backend SHALL perform an Img2Img_Operation
5. WHEN only Mask_Layer contains data, THE Backend SHALL perform an Inpainting_Operation as it currently does

### Requirement 5: Undo/Redo for Color Painting

**User Story:** As a user, I want undo/redo to work with color painting, so that I can experiment without fear of mistakes.

#### Acceptance Criteria

1. THE History_Manager SHALL track color painting strokes in addition to mask strokes
2. WHEN the user undoes a color stroke, THE Canvas_System SHALL restore the previous Color_Layer state
3. WHEN the user redoes a color stroke, THE Canvas_System SHALL reapply the color stroke
4. THE History_Manager SHALL maintain separate undo stacks for Color_Layer and Mask_Layer operations
5. THE History_Manager SHALL support undo/redo across mode switches (color to mask and vice versa)

### Requirement 6: Visual Feedback for Dual Layers

**User Story:** As a user, I want to see both my color painting and mask overlay simultaneously, so that I understand what will be painted and what will be regenerated.

#### Acceptance Criteria

1. THE Canvas_System SHALL render the Color_Layer composited over the original image
2. THE Canvas_System SHALL render the Mask_Layer as a semi-transparent overlay on top of the Color_Layer
3. WHEN in color mode, THE Cursor_Preview SHALL display the selected color
4. WHEN in mask mode, THE Cursor_Preview SHALL display the mask color (white/red) as it currently does
5. THE Canvas_System SHALL update both layer visualizations in real-time during painting

### Requirement 7: Backward Compatibility

**User Story:** As a user, I want existing inpainting functionality to continue working unchanged, so that my workflow is not disrupted.

#### Acceptance Criteria

1. WHEN only mask painting is used, THE Canvas_System SHALL behave identically to the current implementation
2. THE existing inpainting buttons SHALL continue to work for mask-only operations
3. THE Backend SHALL accept requests with only mask data (no painted image) as it currently does
4. THE Canvas_System SHALL not require color painting for mask-only workflows
5. THE existing mask export format SHALL remain unchanged for mask-only operations

### Requirement 8: Color Picker UI

**User Story:** As a user, I want an intuitive color picker, so that I can easily select colors for painting.

#### Acceptance Criteria

1. THE Canvas_System SHALL provide a color picker UI element in the toolbar
2. THE Color_Picker SHALL support hex color input
3. THE Color_Picker SHALL provide a visual color selection interface
4. THE Color_Picker SHALL display the currently selected color
5. THE Color_Picker SHALL be visible only when in color painting mode

### Requirement 9: Export Format for Combined Operations

**User Story:** As a developer, I want a clear export format for combined operations, so that the backend can process both layers correctly.

#### Acceptance Criteria

1. THE Canvas_System SHALL export the painted image as a PNG data URL
2. THE Canvas_System SHALL export the mask as a PNG data URL (existing format)
3. THE Canvas_System SHALL include both data URLs in the form submission when both layers have data
4. THE Backend SHALL detect combined operations by the presence of both painted image and mask data
5. THE Backend SHALL validate that painted image and mask dimensions match

### Requirement 10: Brush Size and Opacity Consistency

**User Story:** As a user, I want brush size to work consistently across both color and mask modes, so that I have a predictable painting experience.

#### Acceptance Criteria

1. THE Brush_Engine SHALL use the same brush size for both color and mask painting
2. WHEN switching between modes, THE Brush_Engine SHALL preserve the current brush size
3. THE Brush_Engine SHALL apply color with full opacity (no transparency)
4. THE Brush_Engine SHALL maintain the existing binary mask behavior (0 or 255 values)
5. THE Cursor_Preview SHALL display the correct size in both modes

### Requirement 11: Create Blank Canvas

**User Story:** As a user, I want to create a blank canvas at my selected resolution, so that I can paint an img2img image from scratch without needing a generated image first.

#### Acceptance Criteria

1. THE UI SHALL display a "Create Blank Canvas" button in the generation form area
2. WHEN the user clicks the button, THE Canvas_System SHALL open with a blank white canvas
3. THE blank canvas dimensions SHALL match the currently selected width and height from the generation form
4. THE Canvas_System SHALL support all painting features on blank canvases including color painting and masking
5. WHEN the user completes painting on a blank canvas, THE Canvas_System SHALL populate the generation form with the painted image data
