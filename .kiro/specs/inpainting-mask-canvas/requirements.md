# Requirements Document

## Introduction

This feature implements a sophisticated 2D inpainting mask canvas that allows users to create precise binary masks for image inpainting operations. The system provides a full-screen popup interface with professional-grade painting tools, zoom/pan capabilities, and robust undo/redo functionality. The mask canvas integrates with the existing inpainting backend to enable users to selectively edit regions of their generated images with pixel-perfect precision.

## Requirements

### Requirement 1

**User Story:** As a user, I want to paint inpainting masks on my images, so that I can precisely control which areas get modified during inpainting operations.

#### Acceptance Criteria

1. WHEN the user opens the mask canvas THEN the system SHALL display a full-screen popup overlay with the selected image as background
2. WHEN the user selects the paint tool THEN the system SHALL allow painting white mask areas with a circular brush
3. WHEN the user selects the erase tool THEN the system SHALL allow erasing mask areas (painting black) with a circular brush
4. WHEN the user paints or erases THEN the system SHALL maintain a strictly binary mask (0 or 255 values only) in the underlying data
5. WHEN the user paints or erases THEN the system SHALL display a semi-transparent white overlay (40-60% opacity) to visualize masked areas

### Requirement 2

**User Story:** As a user, I want to adjust brush size dynamically, so that I can paint both fine details and broad areas efficiently.

#### Acceptance Criteria

1. WHEN the user interacts with the brush size slider THEN the system SHALL adjust brush size between 1-200 pixels
2. WHEN the user press-and-holds the brush size icon THEN the system SHALL enable drag-to-resize functionality
3. WHEN the brush size changes THEN the system SHALL update the circular cursor preview to reflect the new size
4. WHEN the user moves the pointer THEN the system SHALL display a circular brush cursor preview at the pointer position
5. IF the user is in touch mode THEN the system SHALL hide the cursor preview

### Requirement 3

**User Story:** As a user, I want undo and redo functionality, so that I can experiment with mask painting without fear of making irreversible mistakes.

#### Acceptance Criteria

1. WHEN the user clicks the undo button THEN the system SHALL revert the last painting stroke
2. WHEN the user clicks the redo button THEN the system SHALL restore the previously undone stroke
3. WHEN the user performs a new painting action THEN the system SHALL clear the redo history
4. WHEN restoring from history THEN the system SHALL ensure deterministic replay that yields identical mask bytes
5. WHEN history memory exceeds limits THEN the system SHALL manage memory by coalescing or dropping oldest entries

### Requirement 4

**User Story:** As a user, I want to zoom and pan the canvas, so that I can work on fine details and navigate large images efficiently.

#### Acceptance Criteria

1. WHEN the user performs pinch-to-zoom gesture THEN the system SHALL zoom the canvas in/out while maintaining aspect ratio
2. WHEN the user uses wheel+modifier or on-screen controls THEN the system SHALL provide zoom functionality for mouse users
3. WHEN the user performs two-finger pan gesture THEN the system SHALL pan the canvas view
4. WHEN a zoom or pan gesture is active THEN the system SHALL disable drawing functionality
5. WHEN zooming or panning THEN the system SHALL maintain brush size definition in image pixels rather than screen pixels

### Requirement 5

**User Story:** As a user, I want responsive touch, pen, and mouse input, so that I can use the canvas effectively across different devices and input methods.

#### Acceptance Criteria

1. WHEN the user interacts with the canvas THEN the system SHALL use Pointer Events API for unified input handling
2. WHEN the user starts drawing THEN the system SHALL capture pointer events and prevent default behaviors appropriately
3. WHEN the user draws on touch devices THEN the system SHALL prevent page scrolling and zooming behind the popup
4. WHEN pointer events are cancelled THEN the system SHALL handle pointercancel events gracefully
5. WHEN drawing strokes THEN the system SHALL achieve 60 FPS performance through optimized rendering

### Requirement 6

**User Story:** As a user, I want the background image to display correctly regardless of aspect ratio, so that I can see the full context while painting masks.

#### Acceptance Criteria

1. WHEN an image is loaded THEN the system SHALL render it using "contain" scaling with letterboxing
2. WHEN the image aspect ratio differs from canvas THEN the system SHALL maintain the original image aspect ratio
3. WHEN coordinate mapping is needed THEN the system SHALL accurately transform between view CSS pixels and image pixels
4. WHEN the canvas is resized THEN the system SHALL maintain proper image positioning and scaling
5. WHEN stamping brush strokes THEN the system SHALL perform all operations in image space for crisp edges

### Requirement 7

**User Story:** As a user, I want high-performance rendering, so that the canvas remains responsive even with large images and complex operations.

#### Acceptance Criteria

1. WHEN drawing continuously THEN the system SHALL maintain 60 FPS performance
2. WHEN processing pointer events THEN the system SHALL batch samples using requestAnimationFrame
3. WHEN the mask changes THEN the system SHALL only redraw affected areas using dirty rectangles
4. WHEN possible THEN the system SHALL utilize Web Workers with OffscreenCanvas for heavy operations
5. IF Web Workers are unsupported THEN the system SHALL gracefully fallback to main thread processing

### Requirement 8

**User Story:** As a user, I want the brush engine to produce clean, professional results, so that my masks are precise and suitable for high-quality inpainting.

#### Acceptance Criteria

1. WHEN painting strokes THEN the system SHALL use hard-edge round brush stamps
2. WHEN drawing continuous strokes THEN the system SHALL space stamps at approximately 0.35 × brush diameter
3. WHEN positioning stamps THEN the system SHALL round stamp centers to integer image pixels
4. WHEN compositing overlays THEN the system SHALL disable image smoothing to prevent soft edges
5. WHEN rendering the mask overlay THEN the system SHALL use destination-in compositing for proper transparency

### Requirement 9

**User Story:** As a user, I want the canvas to work reliably across different browsers and devices, so that I can use it consistently regardless of my platform.

#### Acceptance Criteria

1. WHEN the popup is open THEN the system SHALL disable page scroll and zoom behind the interface
2. WHEN using different browsers THEN the system SHALL provide consistent behavior across platforms
3. WHEN context creation fails THEN the system SHALL provide appropriate fallbacks and error handling
4. WHEN memory constraints are encountered THEN the system SHALL manage resources gracefully without crashes