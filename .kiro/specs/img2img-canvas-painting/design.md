# Design Document: Img2Img Canvas Painting Feature

## Overview

This design extends the existing inpainting canvas system to support arbitrary color painting (img2img) alongside mask painting (inpainting). The feature enables users to paint RGB colors directly on images and combine both techniques simultaneously - painting colors on some areas while masking other areas for regeneration.

The design maintains backward compatibility with existing inpainting workflows while introducing a dual-layer architecture that manages both Color_Layer (RGB data) and Mask_Layer (binary mask data) independently.

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  InpaintingMaskCanvas                       │
│                  (Main Orchestrator)                        │
└─────────────────────────────────────────────────────────────┘
                            │
                            ├─────────────────────────────────┐
                            │                                 │
                            ▼                                 ▼
┌─────────────────────────────────────┐   ┌──────────────────────────────┐
│        Canvas_Manager                │   │     Input_Engine             │
│  - Manages Color_Layer (new)        │   │  - Pointer event handling    │
│  - Manages Mask_Layer (existing)    │   │  - Cursor preview            │
│  - Dual-layer rendering              │   │  - Mode-aware visuals        │
│  - Export both layers                │   └──────────────────────────────┘
└─────────────────────────────────────┘
            │
            ├──────────────┬──────────────┬──────────────┐
            │              │              │              │
            ▼              ▼              ▼              ▼
┌─────────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│  Brush_Engine   │ │   History   │ │   Zoom/Pan  │ │   Worker    │
│  - Color mode   │ │   Manager   │ │  Controller │ │   Manager   │
│  - Mask mode    │ │  - Dual     │ │             │ │             │
│  - Shared size  │ │    layer    │ │             │ │             │
└─────────────────┘ └─────────────┘ └─────────────┘ └─────────────┘
```

### Data Flow

```
User Input → Input_Engine → Canvas_Manager → Brush_Engine
                                    │
                                    ├─→ Color_Layer (RGB canvas)
                                    └─→ Mask_Layer (binary canvas)
                                    
Export Flow:
Canvas_Manager → Composite Color_Layer over original image → Painted Image Data URL
              → Export Mask_Layer → Mask Data URL
              → Send both to backend → Combined operation
```

## Components and Interfaces

### 1. Canvas_Manager Extensions

**New Properties:**
```typescript
interface CanvasState {
    // Existing properties
    imageWidth: number;
    imageHeight: number;
    maskData: Uint8Array;
    isDirty: boolean;
    displayWidth: number;
    displayHeight: number;
    offsetX: number;
    offsetY: number;
    scale: number;
    
    // New properties for color layer
    colorData: Uint8Array | null;  // RGB data (3 bytes per pixel)
    colorLayerDirty: boolean;
    currentMode: 'mask' | 'color';
}
```

**New Methods:**
```typescript
class CanvasManager {
    // Color layer management
    public initializeColorLayer(): void;
    public updateColorData(x: number, y: number, r: number, g: number, b: number): boolean;
    public getColorValue(x: number, y: number): { r: number; g: number; b: number };
    public clearColorLayer(): void;
    
    // Mode switching
    public setMode(mode: 'mask' | 'color'): void;
    public getMode(): 'mask' | 'color';
    
    // Export functions
    public exportPaintedImage(): string;  // Composite color layer over original
    public exportColorLayer(): string;    // Raw color layer data
    public exportBothLayers(): { paintedImage: string; mask: string };
    
    // Rendering
    private renderColorLayer(dirtyRect?: DirtyRect): void;
    private compositeColorOverImage(): void;
}
```

**Implementation Strategy:**
- Color_Layer stored as `Uint8Array` with 3 bytes per pixel (RGB)
- Separate dirty tracking for color and mask layers
- Render color layer to a dedicated canvas, then composite over image canvas
- Mask overlay renders on top of color layer for visual feedback

### 2. Brush_Engine Extensions

**New Properties:**
```typescript
interface BrushSettings {
    size: number;
    mode: 'paint' | 'erase';
    spacing: number;
    
    // New property for color mode
    paintMode: 'mask' | 'color';
    color?: { r: number; g: number; b: number };  // Only used in color mode
}
```

**New Methods:**
```typescript
class BrushEngine {
    // Color painting
    public applyColorStamp(
        colorData: Uint8Array,
        imageWidth: number,
        imageHeight: number,
        centerX: number,
        centerY: number,
        brushSize: number,
        color: { r: number; g: number; b: number }
    ): boolean;
    
    public applyColorStrokePath(
        colorData: Uint8Array,
        imageWidth: number,
        imageHeight: number,
        path: { x: number; y: number }[],
        brushSize: number,
        color: { r: number; g: number; b: number }
    ): boolean;
}
```

**Implementation Strategy:**
- Extend existing stamp logic to support RGB color application
- Maintain same brush size and spacing calculations for consistency
- Color stamps write RGB values to colorData array (3 bytes per pixel)
- Mask stamps continue to write binary values (0 or 255) to maskData array

### 3. History_Manager Extensions

**New Interfaces:**
```typescript
interface ColorStrokeCommand extends StrokeCommand {
    color: { r: number; g: number; b: number };
    layerType: 'color';
}

interface MaskStrokeCommand extends StrokeCommand {
    layerType: 'mask';
}

type DualLayerStrokeCommand = ColorStrokeCommand | MaskStrokeCommand;
```

**New Methods:**
```typescript
class HistoryManager {
    // Dual-layer checkpoint support
    public createDualLayerCheckpoint(
        maskData: Uint8Array,
        colorData: Uint8Array | null
    ): Checkpoint;
    
    public reconstructDualLayerFromCheckpoint(
        checkpoint: Checkpoint
    ): { maskData: Uint8Array; colorData: Uint8Array | null };
    
    // Layer-specific replay
    public replayColorStrokes(
        strokes: ColorStrokeCommand[],
        colorData: Uint8Array,
        imageWidth: number,
        imageHeight: number
    ): void;
}
```

**Implementation Strategy:**
- Extend checkpoint structure to include optional colorData tiles
- Store layer type with each stroke command
- Replay strokes to appropriate layer based on layerType
- Maintain separate dirty tracking for each layer during replay

### 4. UI Components

**Color Picker Component:**
```typescript
interface ColorPickerConfig {
    initialColor: { r: number; g: number; b: number };
    onColorChange: (color: { r: number; g: number; b: number }) => void;
}

class ColorPicker {
    private currentColor: { r: number; g: number; b: number };
    private pickerElement: HTMLElement;
    
    public show(): void;
    public hide(): void;
    public getColor(): { r: number; g: number; b: number };
    public setColor(color: { r: number; g: number; b: number }): void;
}
```

**Mode Switcher Component:**
```html
<div class="mode-switcher">
    <button class="mode-btn color-mode-btn">
        🎨 Color Paint
    </button>
    <button class="mode-btn mask-mode-btn active">
        ⬜ Mask Paint
    </button>
</div>
```

**Blank Canvas Button:**
```html
<button id="create-blank-canvas-btn" class="primary-button">
    📄 Create Blank Canvas
</button>
```

### 5. Input_Engine Extensions

**Cursor Preview Updates:**
```typescript
class InputEngine {
    // Update cursor to show color in color mode
    public updateCursorColor(color: { r: number; g: number; b: number }): void;
    
    // Existing method extended
    public updateCursorMode(mode: 'paint' | 'erase', paintMode?: 'mask' | 'color'): void;
}
```

**Implementation:**
- In color mode, cursor preview shows selected color as fill
- In mask mode, cursor preview shows white/red as before
- Cursor size remains consistent across modes

## Data Models

### Color Layer Storage

```typescript
// RGB storage: 3 bytes per pixel
// Index calculation: (y * imageWidth + x) * 3
// [R, G, B, R, G, B, ...]

interface ColorLayerData {
    width: number;
    height: number;
    data: Uint8Array;  // length = width * height * 3
}
```

### Export Format

```typescript
interface CanvasExportData {
    hasPaintedImage: boolean;
    paintedImageDataUrl: string | null;
    hasMask: boolean;
    maskDataUrl: string | null;
    operation: 'generate' | 'inpaint' | 'img2img' | 'combined';
}
```

### Backend Request Format

```python
class CombinedOperationRequest(BaseModel):
    """Request for combined img2img + inpainting operation"""
    prompt: str
    negative_prompt: Optional[str] = None
    base_image_data: str  # Data URL of painted image
    mask_data: str        # Data URL of mask
    provider: Provider
    # ... other generation parameters
    
    @field_validator('base_image_data', 'mask_data')
    @classmethod
    def validate_dimensions_match(cls, v, info):
        """Ensure painted image and mask have matching dimensions"""
        # Validation logic
        pass
```

## Error Handling

### Validation Errors

```typescript
class CanvasValidationError extends Error {
    constructor(message: string, public code: string) {
        super(message);
        this.name = 'CanvasValidationError';
    }
}

// Error codes:
// - DIMENSION_MISMATCH: Color layer and mask dimensions don't match
// - INVALID_COLOR: Color values out of range (0-255)
// - NO_LAYERS: Attempting to export with no painted data
// - MODE_CONFLICT: Operation not valid in current mode
```

### Backend Validation

```python
def validate_combined_operation(
    painted_image: PILImage.Image,
    mask: PILImage.Image
) -> None:
    """Validate combined operation inputs"""
    if painted_image.size != mask.size:
        raise ValidationError(
            "Painted image and mask dimensions must match",
            field="dimensions"
        )
    
    if mask.mode != 'L':
        raise ValidationError(
            "Mask must be grayscale",
            field="mask_mode"
        )
```

## Testing Strategy

### Unit Tests

**Canvas_Manager Tests:**
- Test color layer initialization
- Test color data updates at various coordinates
- Test mode switching preserves both layers
- Test export functions produce valid data URLs
- Test compositing color layer over original image

**Brush_Engine Tests:**
- Test color stamp application
- Test color stroke path rendering
- Test brush size consistency across modes
- Test color values are correctly applied

**History_Manager Tests:**
- Test dual-layer checkpoint creation
- Test undo/redo across mode switches
- Test replay of color strokes
- Test replay of mask strokes
- Test mixed stroke replay (color then mask then color)

**Integration Tests:**
- Test complete painting workflow (color + mask)
- Test export with both layers
- Test export with only color layer
- Test export with only mask layer (backward compatibility)
- Test blank canvas creation and painting

### Frontend Tests

```typescript
describe('Dual-Mode Canvas', () => {
    it('should switch between color and mask modes', () => {
        // Test mode switching
    });
    
    it('should preserve painted data when switching modes', () => {
        // Paint in color mode, switch to mask, verify color data intact
    });
    
    it('should export both layers correctly', () => {
        // Paint both layers, export, verify data URLs
    });
    
    it('should handle undo/redo across modes', () => {
        // Paint color, paint mask, undo, redo, verify state
    });
});
```

### Backend Tests

```python
def test_combined_operation():
    """Test combined img2img + inpainting operation"""
    # Create test painted image and mask
    # Submit to /image endpoint
    # Verify correct operation type detected
    # Verify both inputs used in generation

def test_img2img_only():
    """Test img2img operation without mask"""
    # Create test painted image, no mask
    # Submit to /image endpoint
    # Verify img2img operation performed

def test_backward_compatibility():
    """Test existing inpainting still works"""
    # Submit mask-only request
    # Verify inpainting operation performed
    # Verify no breaking changes
```

## Backward Compatibility

### Existing Inpainting Workflows

**Preserved Behavior:**
- Mask-only operations continue to work unchanged
- Existing inpainting buttons function identically
- Mask export format remains the same
- Backend accepts mask-only requests as before

**Implementation Strategy:**
- Color layer is optional (null by default)
- Export functions check for color layer existence
- Backend detects operation type based on presence of painted image and mask
- UI shows color controls only when explicitly enabled

### Migration Path

1. **Phase 1:** Add color layer support without UI changes
2. **Phase 2:** Add mode switcher and color picker to toolbar
3. **Phase 3:** Add blank canvas button to generation form
4. **Phase 4:** Update backend to handle combined operations

Each phase maintains full backward compatibility with previous phases.

## Performance Considerations

### Memory Management

**Color Layer Memory:**
- RGB data: 3 bytes per pixel
- 1024x1024 image: ~3MB
- 2048x2048 image: ~12MB

**Optimization Strategies:**
- Lazy initialization: Only allocate color layer when first used
- Tile-based checkpoints: Store only modified tiles
- Compression: Use PNG compression for checkpoint storage
- Memory limits: Reuse existing 250MB history limit

### Rendering Performance

**Optimization Strategies:**
- Dirty rectangle tracking for both layers
- Separate render scheduling for color and mask layers
- Batch updates during active strokes
- Use OffscreenCanvas for color layer compositing
- Throttle overlay updates to 60 FPS

### Export Performance

**Optimization Strategies:**
- Use Web Workers for image compositing
- Cache composited result until color layer changes
- Async export with progress feedback for large images
- Reuse existing worker pool from mask processing

## Security Considerations

### Input Validation

- Validate color values are in range [0, 255]
- Validate image dimensions match between layers
- Sanitize data URLs before sending to backend
- Limit maximum canvas dimensions (8192x8192)

### Backend Validation

- Verify painted image and mask dimensions match
- Validate image formats (PNG only)
- Check file sizes within limits
- Verify mask is grayscale binary

## Future Enhancements

### Potential Extensions

1. **Opacity Control:** Add opacity slider for color painting
2. **Blend Modes:** Support different blend modes for color layer
3. **Layer Management:** Multiple color layers with visibility toggle
4. **Brush Presets:** Save/load brush configurations
5. **Color Palette:** Quick access to recently used colors
6. **Eyedropper Tool:** Sample colors from original image
7. **Gradient Tool:** Paint with gradients instead of solid colors
8. **Texture Brushes:** Apply textures while painting

### API Extensions

```typescript
// Future API for advanced features
interface AdvancedCanvasConfig {
    enableOpacity: boolean;
    enableBlendModes: boolean;
    enableMultipleLayers: boolean;
    maxLayers: number;
}
```

## Implementation Phases

### Phase 1: Core Infrastructure (Week 1)
- Extend Canvas_Manager with color layer support
- Extend Brush_Engine with color painting
- Add mode switching logic
- Unit tests for core functionality

### Phase 2: UI Components (Week 1)
- Add mode switcher to toolbar
- Implement color picker component
- Update cursor preview for color mode
- Add blank canvas button

### Phase 3: History & Export (Week 2)
- Extend History_Manager for dual layers
- Implement export functions
- Add backend support for combined operations
- Integration tests

### Phase 4: Polish & Testing (Week 2)
- Performance optimization
- Error handling improvements
- Comprehensive testing
- Documentation updates

## Dependencies

### External Libraries
- No new external dependencies required
- Uses existing canvas APIs
- Leverages existing Web Worker infrastructure

### Internal Dependencies
- Extends existing Canvas_Manager
- Extends existing Brush_Engine
- Extends existing History_Manager
- Uses existing Input_Engine
- Uses existing Worker_Manager

## Deployment Considerations

### Frontend Deployment
- Compile TypeScript: `tsc`
- No breaking changes to existing code
- Feature flag for gradual rollout (optional)

### Backend Deployment
- Add combined operation handler to `/image` endpoint
- Update image_models.py with new request types
- Backward compatible with existing requests
- No database migrations required

### Rollback Plan
- Feature can be disabled via UI flag
- Backend falls back to existing operation detection
- No data migration required
- Safe to rollback without data loss

## Monitoring & Metrics

### Performance Metrics
- Canvas initialization time
- Brush stroke latency
- Export operation duration
- Memory usage per session

### Usage Metrics
- Color mode vs mask mode usage ratio
- Combined operations vs single-layer operations
- Blank canvas creation frequency
- Average session duration

### Error Metrics
- Validation errors by type
- Export failures
- Backend operation failures
- Browser compatibility issues

## Documentation Updates

### User Documentation
- Tutorial: "Painting Colors on Images"
- Tutorial: "Combining Color Painting and Masking"
- Tutorial: "Creating Images from Blank Canvas"
- FAQ: "When to use color painting vs masking"

### Developer Documentation
- API reference for Canvas_Manager extensions
- API reference for Brush_Engine extensions
- Integration guide for backend operations
- Testing guide for dual-layer features

---

## Summary

This design extends the existing inpainting canvas system with color painting capabilities while maintaining full backward compatibility. The dual-layer architecture cleanly separates color and mask data, allowing users to leverage both techniques simultaneously or independently. The implementation follows existing patterns in the codebase, reuses infrastructure where possible, and provides a clear migration path for gradual rollout.
