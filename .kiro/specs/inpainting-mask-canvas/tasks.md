# Implementation Plan

- [ ] 1. Set up core canvas infrastructure and basic UI
  - Create the main InpaintingMaskCanvas class with popup overlay structure
  - Implement basic HTML structure with full-screen modal and toolbar
  - Set up three-canvas system (image, overlay, mask alpha) with proper layering
  - Add basic CSS styling for full-screen popup and dark overlay
  - _Requirements: 1.1, 1.2, 6.1, 6.4_

- [ ] 2. Implement image loading and display system
  - Create CanvasManager class to handle canvas state and rendering
  - Implement image loading with proper error handling and validation
  - Add "contain" scaling with letterboxing to maintain aspect ratio
  - Create coordinate transformation system between screen and image pixels
  - Write unit tests for coordinate mapping accuracy
  - _Requirements: 6.1, 6.2, 6.3, 6.4_

- [ ] 3. Create basic brush engine with binary mask enforcement
  - Implement BrushEngine class with hard-edge circular stamp functionality
  - Create binary mask data structure using Uint8Array (0 or 255 values only)
  - Add stamp spacing logic at 0.35 × brush diameter intervals
  - Implement integer pixel positioning for crisp edges
  - Write unit tests to verify binary mask invariant is maintained
  - _Requirements: 1.4, 9.1, 9.2, 9.3, 9.5_

- [ ] 4. Implement unified pointer input handling
  - Create InputEngine class using Pointer Events API for mouse/pen/touch
  - Add pointer capture during drawing with preventDefault on pointermove
  - Implement pointercancel handling for robust input management
  - Create brush cursor preview that follows pointer position
  - Add touch-action: none styling to prevent page scrolling
  - _Requirements: 5.1, 5.2, 5.4, 2.4, 2.5_

- [ ] 5. Add paint and erase tools with brush size control
  - Implement paint tool that stamps white (255) values to mask
  - Implement erase tool that stamps black (0) values to mask
  - Create brush size slider with 1-200 pixel range
  - Add press-and-hold drag resize functionality on brush size icon
  - Update cursor preview to reflect current brush size
  - _Requirements: 1.2, 1.3, 2.1, 2.2, 2.3_

- [ ] 6. Create mask overlay visualization system
  - Implement semi-transparent white overlay (40-60% opacity) for masked areas
  - Use destination-in compositing with maskAlphaCanvas for proper transparency
  - Disable image smoothing when drawing mask to prevent soft edges
  - Add dirty rectangle optimization to only redraw changed areas
  - Write tests to verify overlay never introduces soft edges
  - _Requirements: 1.5, 9.4, 9.5, 7.3_

- [ ] 7. Implement zoom and pan navigation system
  - Create ZoomPanController class for view transformation management
  - Add pinch-to-zoom gesture support for touch devices
  - Implement wheel+modifier zoom for mouse users
  - Add two-finger pan gesture support
  - Disable drawing while zoom/pan gestures are active
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [ ] 8. Build stroke-based history system for undo/redo
  - Create HistoryManager class with stroke command storage
  - Implement StrokeCommand data structure with mode, brushSize, path, timestamp
  - Add undo functionality that reverts last stroke
  - Add redo functionality that restores previously undone stroke
  - Clear redo history when new strokes are added
  - _Requirements: 3.1, 3.2, 3.3_

- [ ] 9. Add checkpoint system for deterministic replay
  - Implement tile-based checkpoint creation at 256×256 tile resolution
  - Create replay system that restores from nearest checkpoint then applies subsequent strokes
  - Add periodic checkpoint creation during drawing sessions
  - Implement memory management with configurable limits (200-300 MB)
  - Write tests to verify deterministic replay produces identical mask bytes
  - _Requirements: 3.4, 3.5_

- [ ] 10. Implement performance optimizations for 60 FPS rendering
  - Add requestAnimationFrame batching for pointer event processing
  - Implement dirty rectangle tracking to minimize redraws
  - Use canvas context hints (desynchronized: true, willReadFrequently: true)
  - Add frame rate monitoring and performance metrics
  - Optimize overlay canvas updates to only occur when mask changes or cursor moves
  - _Requirements: 7.1, 7.2, 7.3, 7.5_

- [ ] 11. Add WebWorker support with main thread fallback
  - Create WebWorker for heavy mask processing operations
  - Implement OffscreenCanvas support for worker-based rendering
  - Add message passing system for stroke processing and checkpoint creation
  - Create graceful fallback to main thread when WebWorkers unavailable
  - Post dirty rectangles back to main thread for UI updates
  - _Requirements: 7.4, 7.5_

- [ ] 12. Create mask export functionality
  - Implement mask export as PNG grayscale with exact image resolution
  - Ensure exported mask contains only binary values (0 or 255)
  - Add data URL generation for integration with inpainting API
  - Create temporary file cleanup system for generated masks
  - Write tests to verify exported mask binary invariant
  - _Requirements: 1.4, 9.1_

- [ ] 13. Integrate with existing inpainting workflow
  - Add "Edit Mask" button to existing image generation results
  - Create integration points with current script.ts image handling
  - Implement mask canvas trigger from grid view modal
  - Connect mask completion to existing InpaintingRequest submission
  - Add proper file path handling for base images and generated masks
  - _Requirements: 1.1, 6.1_

- [ ] 14. Add comprehensive error handling and recovery
  - Implement error handling for image loading failures with retry options
  - Add canvas context creation error handling with fallbacks
  - Create memory limit exceeded handling with automatic cleanup
  - Add invalid mask data recovery that preserves user work when possible
  - Implement graceful degradation when browser features unavailable
  - _Requirements: 9.1, 9.2, 9.3, 9.4_

