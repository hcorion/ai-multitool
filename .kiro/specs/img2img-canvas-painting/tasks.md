# Implementation Plan: Img2Img Canvas Painting Feature

## Overview

This implementation extends the existing inpainting canvas system to support color painting (img2img) alongside mask painting. The feature enables users to paint RGB colors directly on images and combine both techniques simultaneously. Implementation follows four phases: Core Infrastructure, UI Components, History & Export, and Polish & Testing.

## Tasks

- [x] 1. Phase 1: Core Infrastructure - Canvas_Manager Extensions
  - [x] 1.1 Extend CanvasState interface with color layer properties
    - Add `colorData: Uint8Array | null`, `colorLayerDirty: boolean`, and `currentMode: 'mask' | 'color'` to CanvasState interface in `src/inpainting/canvas-manager.ts`
    - Initialize colorData as null by default for lazy allocation
    - _Requirements: 1.1, 1.4_

  - [x] 1.2 Implement color layer initialization and management methods
    - Add `initializeColorLayer()` method to allocate RGB data (3 bytes per pixel)
    - Add `updateColorData(x, y, r, g, b)` method to write color values
    - Add `getColorValue(x, y)` method to read color values
    - Add `clearColorLayer()` method to reset color data
    - _Requirements: 1.1, 1.3_

  - [x] 1.3 Implement mode switching methods
    - Add `setMode(mode)` and `getMode()` methods to Canvas_Manager
    - Ensure mode switching preserves both layer data
    - Update dirty tracking to handle both layers independently
    - _Requirements: 2.4_

  - [x] 1.4 Implement color layer rendering methods
    - Add `renderColorLayer(dirtyRect?)` private method for rendering color data to canvas
    - Add `compositeColorOverImage()` private method to composite color layer over original image
    - Integrate color layer rendering into existing render pipeline
    - Ensure mask overlay renders on top of color layer
    - _Requirements: 1.3, 6.1, 6.2_

- [x] 2. Phase 1: Core Infrastructure - Brush_Engine Extensions
  - [x] 2.1 Extend BrushSettings interface with color mode properties
    - Add `paintMode: 'mask' | 'color'` property to BrushSettings in `src/inpainting/brush-engine.ts`
    - Add `color?: { r: number; g: number; b: number }` property for color mode
    - _Requirements: 2.1, 2.2_

  - [x] 2.2 Implement color stamp application method
    - Add `applyColorStamp()` method to apply RGB color stamps to colorData array
    - Use same brush size and spacing calculations as mask stamps for consistency
    - Write RGB values (3 bytes per pixel) to colorData at stamp positions
    - _Requirements: 2.2, 10.1, 10.3_

  - [x] 2.3 Implement color stroke path method
    - Add `applyColorStrokePath()` method for continuous color strokes
    - Reuse existing path interpolation logic from mask strokes
    - Apply color stamps along the path with proper spacing
    - _Requirements: 2.2, 10.1_

- [x] 3. Checkpoint - Verify core infrastructure
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Phase 2: UI Components - Mode Switcher
  - [x] 4.1 Create mode switcher HTML structure
    - Add mode switcher buttons to canvas toolbar in `templates/index.html`
    - Include "Color Paint" and "Mask Paint" buttons with appropriate icons
    - Add active state styling to indicate current mode
    - _Requirements: 2.1, 2.4_

  - [x] 4.2 Implement mode switcher event handlers
    - Add click handlers in `src/inpainting/inpainting-mask-canvas.ts` to switch between modes
    - Call Canvas_Manager's `setMode()` method on mode change
    - Update UI to reflect active mode (button states, color picker visibility)
    - _Requirements: 2.4_

  - [x] 4.3 Add mode switcher styles
    - Create styles for mode switcher buttons in `static/sass/_inpainting-mask-canvas.scss`
    - Style active/inactive states with clear visual distinction
    - Ensure responsive layout in canvas toolbar
    - _Requirements: 2.4_

- [x] 5. Phase 2: UI Components - Color Picker
  - [x] 5.1 Create color picker HTML structure
    - Add color picker input element to canvas toolbar
    - Include hex color input field and visual color selector
    - Add current color display indicator
    - _Requirements: 8.1, 8.2, 8.3, 8.4_

  - [x] 5.2 Implement color picker event handlers
    - Add color change handler to update Brush_Engine color setting
    - Validate hex color input and convert to RGB values
    - Update cursor preview when color changes
    - _Requirements: 8.2, 8.4, 6.3_

  - [x] 5.3 Implement color picker visibility logic
    - Show color picker only when in color painting mode
    - Hide color picker when in mask mode
    - Preserve selected color when switching modes
    - _Requirements: 8.5, 2.4_

  - [x] 5.4 Add color picker styles
    - Style color picker component in `static/sass/_inpainting-mask-canvas.scss`
    - Ensure color display indicator is clearly visible
    - Match existing canvas toolbar styling
    - _Requirements: 8.4_

- [x] 6. Phase 2: UI Components - Blank Canvas Button
  - [x] 6.1 Add blank canvas button to generation form
    - Add "Create Blank Canvas" button to main generation form in `templates/index.html`
    - Position button near other canvas-related controls
    - _Requirements: 11.1_

  - [x] 6.2 Implement blank canvas creation logic
    - Add click handler in `src/script.ts` to create blank canvas
    - Read current width/height from generation form
    - Create blank white image data at specified dimensions
    - Open canvas editor with blank image
    - _Requirements: 11.2, 11.3_

  - [x] 6.3 Ensure blank canvas supports all features
    - Verify color painting works on blank canvas
    - Verify mask painting works on blank canvas
    - Verify export populates generation form correctly
    - _Requirements: 11.4, 11.5_

- [x] 7. Phase 2: UI Components - Cursor Preview Updates
  - [x] 7.1 Extend cursor preview for color mode
    - Add `updateCursorColor(color)` method to Input_Engine in `src/inpainting/input-engine.ts`
    - Update cursor preview to show selected color as fill in color mode
    - Maintain existing white/red cursor in mask mode
    - _Requirements: 6.3, 6.4, 10.5_

  - [x] 7.2 Update cursor preview rendering
    - Modify cursor rendering logic to use color fill when in color mode
    - Ensure cursor size remains consistent across modes
    - Update cursor preview in real-time when color changes
    - _Requirements: 6.3, 10.5_

- [x] 8. Checkpoint - Verify UI components
  - Ensure all tests pass, ask the user if questions arise.

- [x] 9. Phase 3: History & Export - History_Manager Extensions
  - [x] 9.1 Extend stroke command interfaces for dual layers
    - Add `ColorStrokeCommand` and `MaskStrokeCommand` types in `src/inpainting/history-manager.ts`
    - Add `layerType: 'color' | 'mask'` property to stroke commands
    - Add `color` property to ColorStrokeCommand
    - _Requirements: 5.1, 5.5_

  - [x] 9.2 Implement dual-layer checkpoint support
    - Add `createDualLayerCheckpoint()` method to include both maskData and colorData
    - Extend checkpoint structure to store optional colorData tiles
    - Add `reconstructDualLayerFromCheckpoint()` method to restore both layers
    - _Requirements: 5.2, 5.3_

  - [x] 9.3 Implement layer-specific stroke replay
    - Add `replayColorStrokes()` method to replay color strokes to colorData
    - Update existing replay logic to check layerType and route to appropriate layer
    - Ensure undo/redo works correctly across mode switches
    - _Requirements: 5.4, 5.5_

  - [x] 9.4 Write unit tests for dual-layer history
    - Test checkpoint creation with both layers
    - Test undo/redo across mode switches
    - Test replay of mixed stroke sequences (color then mask then color)
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [x] 10. Phase 3: History & Export - Export Functions
  - [x] 10.1 Implement painted image export method
    - Add `exportPaintedImage()` method to Canvas_Manager
    - Composite color layer over original image
    - Return PNG data URL of composited result
    - _Requirements: 1.4, 9.1_

  - [x] 10.2 Implement combined export method
    - Add `exportBothLayers()` method to return both painted image and mask
    - Return object with `{ paintedImage: string, mask: string }`
    - Handle cases where only one layer has data
    - _Requirements: 4.1, 4.2, 9.3_

  - [x] 10.3 Update canvas close handler to populate form
    - Modify canvas close logic in `src/inpainting/inpainting-mask-canvas.ts` to call export methods
    - Populate generation form with painted image data URL when color layer exists
    - Populate generation form with mask data URL when mask layer exists
    - Include both when both layers have data
    - _Requirements: 3.5, 4.1, 4.2_

  - [x] 10.4 Add export validation
    - Validate color layer and mask dimensions match before export
    - Throw CanvasValidationError for dimension mismatches
    - Validate color values are in range [0, 255]
    - _Requirements: 9.5_

- [x] 11. Phase 3: History & Export - Backend Support
  - [x] 11.1 Extend image_models.py for combined operations
    - Add support for detecting combined operations (painted image + mask) in request validation
    - Add validation to ensure painted image and mask dimensions match
    - Update operation type detection logic
    - _Requirements: 4.3, 9.5_

  - [x] 11.2 Update /image endpoint for combined operations
    - Modify `/image` endpoint in `app.py` to handle requests with both painted image and mask
    - Detect operation type: 'img2img' (color only), 'inpaint' (mask only), or 'combined' (both)
    - Pass both inputs to generation logic when both present
    - _Requirements: 4.3, 4.4, 4.5_

  - [x] 11.3 Implement combined operation processing
    - Add logic to process combined operations using both painted image and mask
    - Apply mask to painted image for inpainting operation
    - Ensure backward compatibility with mask-only requests
    - _Requirements: 4.3, 7.3_

  - [x] 11.4 Write backend tests for combined operations
    - Test combined operation detection and processing
    - Test img2img-only operation (color layer, no mask)
    - Test backward compatibility with mask-only operations
    - Test dimension validation between painted image and mask
    - _Requirements: 4.3, 4.4, 4.5, 7.1, 7.2, 7.3, 9.5_

- [x] 12. Checkpoint - Verify history and export
  - Ensure all tests pass, ask the user if questions arise.

- [-] 13. Phase 4: Polish & Testing - Performance Optimization
  - [ ] 13.1 Implement lazy color layer allocation
    - Ensure colorData is only allocated when first used in color mode
    - Add memory usage tracking for color layer
    - _Requirements: 1.1_

  - [~] 13.2 Optimize rendering with dirty rectangles
    - Implement dirty rectangle tracking for color layer
    - Update only changed regions during rendering
    - Batch updates during active strokes
    - _Requirements: 6.5_

  - [~] 13.3 Optimize export with caching
    - Cache composited painted image until color layer changes
    - Use Web Workers for image compositing on large images
    - Reuse existing worker pool from mask processing
    - _Requirements: 1.4, 9.1_

- [~] 14. Phase 4: Polish & Testing - Error Handling
  - [~] 14.1 Add frontend validation errors
    - Create CanvasValidationError class with error codes
    - Add validation for dimension mismatches, invalid colors, no layers, mode conflicts
    - Display user-friendly error messages
    - _Requirements: 9.5_

  - [~] 14.2 Add backend validation errors
    - Implement validation for painted image and mask dimension matching
    - Validate mask is grayscale binary
    - Return clear error messages for validation failures
    - _Requirements: 9.5_

  - [~] 14.3 Add error recovery mechanisms
    - Handle export failures gracefully
    - Provide fallback for compositing errors
    - Log errors for debugging
    - _Requirements: 9.5_

- [~] 15. Phase 4: Polish & Testing - Backward Compatibility Verification
  - [~] 15.1 Write integration tests for backward compatibility
    - Test existing inpainting buttons work unchanged
    - Test mask-only export format remains the same
    - Test backend accepts mask-only requests as before
    - Verify no breaking changes to existing workflows
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

  - [~] 15.2 Verify UI backward compatibility
    - Test that color controls are hidden by default
    - Test that mask-only workflows don't require color painting
    - Verify existing inpainting functionality unchanged
    - _Requirements: 7.1, 7.4_

- [~] 16. Phase 4: Polish & Testing - Comprehensive Integration Tests
  - [~] 16.1 Write frontend integration tests
    - Test complete painting workflow (color + mask)
    - Test mode switching preserves painted data
    - Test export with both layers
    - Test export with only color layer
    - Test export with only mask layer
    - Test blank canvas creation and painting
    - _Requirements: 1.1, 2.4, 4.1, 4.2, 4.4, 4.5, 11.4, 11.5_

  - [~] 16.2 Write end-to-end tests
    - Test paint button opens canvas from generated image
    - Test paint button opens canvas from grid modal
    - Test canvas extracts and preserves prompt metadata
    - Test form population after canvas close
    - Test combined operation submission to backend
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 4.1, 4.2_

- [~] 17. Final checkpoint - Complete feature verification
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation at phase boundaries
- Implementation uses TypeScript for frontend and Python for backend
- Feature maintains full backward compatibility with existing inpainting workflows
- Color layer uses lazy allocation to minimize memory usage
- Export functions handle all combinations: color-only, mask-only, and combined operations
