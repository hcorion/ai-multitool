/**
 * CanvasManager - Handles canvas state, rendering, and coordinate transformations
 * for the inpainting mask canvas system.
 */
import { BrushEngine } from './brush-engine.js';
export class CanvasManager {
    imageCanvas;
    overlayCanvas;
    maskAlphaCanvas;
    state = null;
    loadedImage = null;
    brushEngine;
    constructor(imageCanvas, overlayCanvas, maskAlphaCanvas) {
        this.imageCanvas = imageCanvas;
        this.overlayCanvas = overlayCanvas;
        this.maskAlphaCanvas = maskAlphaCanvas;
        this.brushEngine = new BrushEngine();
    }
    /**
     * Load and display an image with proper scaling and letterboxing
     */
    async loadImage(imageUrl) {
        return new Promise((resolve, reject) => {
            const img = new Image();
            // Set up error handling
            img.onerror = () => {
                reject(new Error(`Failed to load image: ${imageUrl}`));
            };
            // Set up success handling
            img.onload = () => {
                try {
                    this.processLoadedImage(img);
                    this.loadedImage = img;
                    resolve();
                }
                catch (error) {
                    reject(error);
                }
            };
            // Handle CORS for cross-origin images
            img.crossOrigin = 'anonymous';
            img.src = imageUrl;
        });
    }
    /**
     * Process the loaded image and set up canvas state
     */
    processLoadedImage(img) {
        if (!img.complete || img.naturalWidth === 0) {
            throw new Error('Image failed to load properly');
        }
        // Validate image dimensions
        if (img.naturalWidth > 8192 || img.naturalHeight > 8192) {
            throw new Error('Image dimensions too large (max 8192x8192)');
        }
        if (img.naturalWidth < 1 || img.naturalHeight < 1) {
            throw new Error('Image dimensions too small (min 1x1)');
        }
        // Calculate display dimensions with letterboxing
        const containerRect = this.imageCanvas.parentElement?.getBoundingClientRect();
        if (!containerRect) {
            throw new Error('Canvas container not found');
        }
        const containerWidth = containerRect.width;
        const containerHeight = containerRect.height;
        const { displayWidth, displayHeight, scale } = this.calculateContainScaling(img.naturalWidth, img.naturalHeight, containerWidth, containerHeight);
        // Update canvas sizes
        this.updateCanvasSizes(img.naturalWidth, img.naturalHeight);
        // Initialize state (no offsets needed - CSS centering handles positioning)
        this.state = {
            imageWidth: img.naturalWidth,
            imageHeight: img.naturalHeight,
            maskData: new Uint8Array(img.naturalWidth * img.naturalHeight),
            isDirty: true,
            displayWidth,
            displayHeight,
            offsetX: 0, // Not used with CSS centering
            offsetY: 0, // Not used with CSS centering
            scale
        };
        // Initialize mask data to all zeros (transparent)
        this.state.maskData.fill(0);
        // Render the image
        this.renderImage(img);
        // Initialize the mask overlay (empty initially)
        this.updateMaskOverlay();
    }
    getBaseScale() {
        return this.state?.scale ?? 1; // CSS px per image px when interactive scale=1
    }
    /**
     * Calculate "contain" scaling with letterboxing to maintain aspect ratio
     */
    calculateContainScaling(imageWidth, imageHeight, containerWidth, containerHeight) {
        const imageAspect = imageWidth / imageHeight;
        const containerAspect = containerWidth / containerHeight;
        let displayWidth;
        let displayHeight;
        let scale;
        if (imageAspect > containerAspect) {
            // Image is wider than container - fit to width
            displayWidth = containerWidth;
            displayHeight = containerWidth / imageAspect;
            scale = containerWidth / imageWidth;
        }
        else {
            // Image is taller than container - fit to height
            displayWidth = containerHeight * imageAspect;
            displayHeight = containerHeight;
            scale = containerHeight / imageHeight;
        }
        return { displayWidth, displayHeight, scale };
    }
    /**
     * Update canvas sizes to match image dimensions
     */
    updateCanvasSizes(width, height) {
        // Set canvas internal dimensions to match image
        this.imageCanvas.width = width;
        this.imageCanvas.height = height;
        this.overlayCanvas.width = width;
        this.overlayCanvas.height = height;
        this.maskAlphaCanvas.width = width;
        this.maskAlphaCanvas.height = height;
        // Get contexts and configure them
        const imageCtx = this.imageCanvas.getContext('2d');
        const overlayCtx = this.overlayCanvas.getContext('2d');
        const maskAlphaCtx = this.maskAlphaCanvas.getContext('2d');
        if (!imageCtx || !overlayCtx || !maskAlphaCtx) {
            throw new Error('Failed to get canvas contexts');
        }
        // Disable image smoothing for crisp pixel rendering
        imageCtx.imageSmoothingEnabled = false;
        overlayCtx.imageSmoothingEnabled = false;
        maskAlphaCtx.imageSmoothingEnabled = false;
        // Set overlay to semi-transparent
        overlayCtx.globalAlpha = 0.5;
    }
    /**
     * Render the image to the image canvas
     */
    renderImage(img) {
        const ctx = this.imageCanvas.getContext('2d');
        if (!ctx || !this.state)
            return;
        ctx.clearRect(0, 0, this.state.imageWidth, this.state.imageHeight);
        ctx.drawImage(img, 0, 0);
        this.updateCanvasDisplay();
        this.resetTransform(); // ensure we start from centered state
    }
    /**
     * Update canvas display size and position for letterboxing
     */
    updateCanvasDisplay() {
        if (!this.state)
            return;
        const canvases = [this.imageCanvas, this.overlayCanvas];
        canvases.forEach(canvas => {
            canvas.style.width = `${this.state.displayWidth}px`;
            canvas.style.height = `${this.state.displayHeight}px`;
            // Do NOT touch canvas.style.transform here.
            // Centering/zoom/pan is handled solely by resetTransform/applyTransform.
        });
    }
    /**
     * Update mask overlay visualization with dirty rectangle optimization
     */
    updateMaskOverlay(dirtyRect) {
        if (!this.state)
            return;
        const overlayCtx = this.overlayCanvas.getContext('2d');
        if (!overlayCtx)
            return;
        // Disable image smoothing to prevent soft edges
        overlayCtx.imageSmoothingEnabled = false;
        // Determine the area to update
        const updateRect = dirtyRect || {
            x: 0,
            y: 0,
            width: this.state.imageWidth,
            height: this.state.imageHeight
        };
        // Clear the update area
        overlayCtx.clearRect(updateRect.x, updateRect.y, updateRect.width, updateRect.height);
        // Render the mask overlay directly
        this.renderMaskOverlay(updateRect);
    }
    /**
     * Render the semi-transparent mask overlay using destination-in compositing
     */
    renderMaskOverlay(rect) {
        if (!this.state)
            return;
        const overlayCtx = this.overlayCanvas.getContext('2d');
        if (!overlayCtx)
            return;
        // Disable image smoothing to prevent soft edges
        overlayCtx.imageSmoothingEnabled = false;
        // Create ImageData directly for pixel-perfect control
        const imageData = overlayCtx.createImageData(rect.width, rect.height);
        const data = imageData.data;
        // Fill the ImageData with semi-transparent white where mask is 255
        for (let y = 0; y < rect.height; y++) {
            for (let x = 0; x < rect.width; x++) {
                const maskX = rect.x + x;
                const maskY = rect.y + y;
                // Check bounds
                if (maskX >= 0 && maskX < this.state.imageWidth &&
                    maskY >= 0 && maskY < this.state.imageHeight) {
                    const maskIndex = maskY * this.state.imageWidth + maskX;
                    const maskValue = this.state.maskData[maskIndex];
                    // Convert to RGBA - only show overlay where mask is 255
                    const pixelIndex = (y * rect.width + x) * 4;
                    if (maskValue === 255) {
                        data[pixelIndex] = 255; // R - white
                        data[pixelIndex + 1] = 255; // G - white  
                        data[pixelIndex + 2] = 255; // B - white
                        data[pixelIndex + 3] = 128; // A - 50% opacity (128/255 ≈ 0.5)
                    }
                    else {
                        data[pixelIndex] = 0; // R
                        data[pixelIndex + 1] = 0; // G
                        data[pixelIndex + 2] = 0; // B
                        data[pixelIndex + 3] = 0; // A - fully transparent
                    }
                }
                else {
                    // Out of bounds - transparent
                    const pixelIndex = (y * rect.width + x) * 4;
                    data[pixelIndex] = 0; // R
                    data[pixelIndex + 1] = 0; // G
                    data[pixelIndex + 2] = 0; // B
                    data[pixelIndex + 3] = 0; // A
                }
            }
        }
        // Put the image data directly to the overlay canvas
        overlayCtx.putImageData(imageData, rect.x, rect.y);
    }
    /**
     * Convert screen coordinates to image pixel coordinates
     */
    screenToImage(screenX, screenY, debug = false) {
        if (debug)
            console.log('🔍 CanvasManager.screenToImage called:', { screenX, screenY });
        if (!this.state) {
            if (debug)
                console.log('❌ CanvasManager: No state available');
            return null;
        }
        const canvasRect = this.imageCanvas.getBoundingClientRect();
        // Convert to canvas-relative coordinates
        const canvasX = screenX - canvasRect.left;
        const canvasY = screenY - canvasRect.top;
        if (debug)
            console.log('📐 CanvasManager: Canvas rect and relative coords', {
                rect: { left: canvasRect.left, top: canvasRect.top, width: canvasRect.width, height: canvasRect.height },
                canvasX,
                canvasY,
                state: {
                    scale: this.state.scale,
                    imageWidth: this.state.imageWidth,
                    imageHeight: this.state.imageHeight
                }
            });
        // Check if point is within canvas bounds (using actual displayed canvas size)
        if (canvasX < 0 || canvasY < 0 || canvasX >= canvasRect.width || canvasY >= canvasRect.height) {
            if (debug)
                console.log('❌ CanvasManager: Point outside canvas bounds');
            return null;
        }
        // Convert to image coordinates using the scale factor
        const imageX = Math.floor(canvasX / this.state.scale);
        const imageY = Math.floor(canvasY / this.state.scale);
        // Clamp to image bounds
        const clampedX = Math.max(0, Math.min(this.state.imageWidth - 1, imageX));
        const clampedY = Math.max(0, Math.min(this.state.imageHeight - 1, imageY));
        if (debug)
            console.log('📊 CanvasManager calculation:', {
                rawImageX: imageX,
                rawImageY: imageY,
                clampedX,
                clampedY
            });
        const result = { x: clampedX, y: clampedY };
        if (debug)
            console.log('✅ CanvasManager result:', result);
        return result;
    }
    /**
     * Convert image pixel coordinates to screen coordinates
     */
    imageToScreen(imageX, imageY) {
        if (!this.state) {
            return { x: 0, y: 0 };
        }
        const canvasRect = this.imageCanvas.getBoundingClientRect();
        const screenX = canvasRect.left + (imageX * this.state.scale);
        const screenY = canvasRect.top + (imageY * this.state.scale);
        return { x: screenX, y: screenY };
    }
    /**
     * Get current canvas state
     */
    getState() {
        return this.state;
    }
    /**
     * Get the loaded image
     */
    getLoadedImage() {
        return this.loadedImage;
    }
    /**
     * Update mask data at specific coordinates
     */
    updateMaskData(x, y, value) {
        if (!this.state)
            return false;
        // Validate coordinates
        if (x < 0 || x >= this.state.imageWidth || y < 0 || y >= this.state.imageHeight) {
            return false;
        }
        // Ensure binary values only (0 or 255)
        const binaryValue = value > 127 ? 255 : 0;
        const index = y * this.state.imageWidth + x;
        if (this.state.maskData[index] !== binaryValue) {
            this.state.maskData[index] = binaryValue;
            this.state.isDirty = true;
            // Update overlay for the single pixel (with small dirty rect for brush effects)
            this.updateMaskOverlay({ x: x - 1, y: y - 1, width: 3, height: 3 });
            return true;
        }
        return false;
    }
    /**
     * Get mask value at specific coordinates
     */
    getMaskValue(x, y) {
        if (!this.state)
            return 0;
        // Validate coordinates
        if (x < 0 || x >= this.state.imageWidth || y < 0 || y >= this.state.imageHeight) {
            return 0;
        }
        const index = y * this.state.imageWidth + x;
        return this.state.maskData[index];
    }
    /**
     * Clear all mask data
     */
    clearMask() {
        if (!this.state)
            return;
        this.state.maskData.fill(0);
        this.state.isDirty = true;
        // Update entire overlay
        this.updateMaskOverlay();
    }
    /**
     * Fill entire mask
     */
    fillMask() {
        if (!this.state)
            return;
        this.state.maskData.fill(255);
        this.state.isDirty = true;
        // Update entire overlay
        this.updateMaskOverlay();
    }
    /**
     * Check if mask data is dirty and needs redraw
     */
    isDirty() {
        return this.state?.isDirty ?? false;
    }
    /**
     * Mark mask data as clean (after redraw)
     */
    markClean() {
        if (this.state) {
            this.state.isDirty = false;
        }
    }
    /**
     * Resize canvases when container size changes
     */
    handleResize() {
        if (!this.state || !this.loadedImage)
            return;
        // Recalculate display dimensions
        const containerRect = this.imageCanvas.parentElement?.getBoundingClientRect();
        if (!containerRect)
            return;
        const containerWidth = containerRect.width;
        const containerHeight = containerRect.height;
        const { displayWidth, displayHeight, scale } = this.calculateContainScaling(this.state.imageWidth, this.state.imageHeight, containerWidth, containerHeight);
        // Update state (no offsets needed with CSS centering)
        this.state.displayWidth = displayWidth;
        this.state.displayHeight = displayHeight;
        this.state.scale = scale;
        this.state.offsetX = 0; // Not used with CSS centering
        this.state.offsetY = 0; // Not used with CSS centering
        // Update display
        this.updateCanvasDisplay();
    }
    /**
     * Export mask as ImageData for rendering
     */
    exportMaskImageData() {
        if (!this.state)
            return null;
        const canvas = document.createElement('canvas');
        canvas.width = this.state.imageWidth;
        canvas.height = this.state.imageHeight;
        const ctx = canvas.getContext('2d');
        if (!ctx)
            return null;
        const imageData = ctx.createImageData(this.state.imageWidth, this.state.imageHeight);
        // Convert mask data to RGBA
        for (let i = 0; i < this.state.maskData.length; i++) {
            const pixelIndex = i * 4;
            const maskValue = this.state.maskData[i];
            imageData.data[pixelIndex] = maskValue; // R
            imageData.data[pixelIndex + 1] = maskValue; // G
            imageData.data[pixelIndex + 2] = maskValue; // B
            imageData.data[pixelIndex + 3] = 255; // A
        }
        return imageData;
    }
    /**
     * Start a brush stroke at the given image coordinates
     */
    startBrushStroke(imageX, imageY, brushSize, mode) {
        if (!this.state)
            return null;
        // Update brush engine settings
        this.brushEngine.updateSettings({ size: brushSize, mode });
        // Start the stroke
        const stroke = this.brushEngine.startStroke(imageX, imageY);
        // Apply initial stamp
        const hasChanges = this.brushEngine.applyStamp(this.state.maskData, this.state.imageWidth, this.state.imageHeight, imageX, imageY, brushSize, mode);
        if (hasChanges) {
            this.state.isDirty = true;
            // Calculate dirty rectangle for the brush stamp
            const radius = Math.ceil(brushSize / 2);
            const dirtyRect = {
                x: Math.max(0, imageX - radius),
                y: Math.max(0, imageY - radius),
                width: Math.min(this.state.imageWidth - Math.max(0, imageX - radius), radius * 2),
                height: Math.min(this.state.imageHeight - Math.max(0, imageY - radius), radius * 2)
            };
            this.updateMaskOverlay(dirtyRect);
        }
        return stroke;
    }
    /**
     * Continue a brush stroke to the given image coordinates
     */
    continueBrushStroke(imageX, imageY) {
        if (!this.state)
            return false;
        try {
            // Get stamp positions along the path
            const stampPositions = this.brushEngine.continueStroke(imageX, imageY);
            if (stampPositions.length === 0)
                return false;
            const settings = this.brushEngine.getSettings();
            let hasChanges = false;
            let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
            // Apply each stamp and track dirty rectangle bounds
            for (const pos of stampPositions) {
                if (this.brushEngine.applyStamp(this.state.maskData, this.state.imageWidth, this.state.imageHeight, pos.x, pos.y, settings.size, settings.mode)) {
                    hasChanges = true;
                    // Track bounds for dirty rectangle
                    const radius = Math.ceil(settings.size / 2);
                    minX = Math.min(minX, pos.x - radius);
                    minY = Math.min(minY, pos.y - radius);
                    maxX = Math.max(maxX, pos.x + radius);
                    maxY = Math.max(maxY, pos.y + radius);
                }
            }
            if (hasChanges) {
                this.state.isDirty = true;
                // Calculate optimized dirty rectangle
                const dirtyRect = {
                    x: Math.max(0, minX),
                    y: Math.max(0, minY),
                    width: Math.min(this.state.imageWidth - Math.max(0, minX), maxX - Math.max(0, minX)),
                    height: Math.min(this.state.imageHeight - Math.max(0, minY), maxY - Math.max(0, minY))
                };
                this.updateMaskOverlay(dirtyRect);
            }
            return hasChanges;
        }
        catch (error) {
            console.error('Error continuing brush stroke:', error);
            return false;
        }
    }
    /**
     * End the current brush stroke
     */
    endBrushStroke() {
        return this.brushEngine.endStroke();
    }
    /**
     * Apply a complete brush stroke path
     */
    applyBrushStroke(stroke) {
        if (!this.state)
            return false;
        const hasChanges = this.brushEngine.applyStrokePath(this.state.maskData, this.state.imageWidth, this.state.imageHeight, stroke.points, stroke.brushSize, stroke.mode);
        if (hasChanges) {
            this.state.isDirty = true;
            // Calculate dirty rectangle for the entire stroke
            if (stroke.points.length > 0) {
                const radius = Math.ceil(stroke.brushSize / 2);
                let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
                for (const point of stroke.points) {
                    minX = Math.min(minX, point.x - radius);
                    minY = Math.min(minY, point.y - radius);
                    maxX = Math.max(maxX, point.x + radius);
                    maxY = Math.max(maxY, point.y + radius);
                }
                const dirtyRect = {
                    x: Math.max(0, minX),
                    y: Math.max(0, minY),
                    width: Math.min(this.state.imageWidth - Math.max(0, minX), maxX - Math.max(0, minX)),
                    height: Math.min(this.state.imageHeight - Math.max(0, minY), maxY - Math.max(0, minY))
                };
                this.updateMaskOverlay(dirtyRect);
            }
            // Validate binary invariant
            if (!BrushEngine.validateBinaryMask(this.state.maskData)) {
                console.warn('Binary mask invariant violated, enforcing binary values');
                BrushEngine.enforceBinaryMask(this.state.maskData);
                // Re-render overlay after enforcing binary values
                this.updateMaskOverlay();
            }
        }
        return hasChanges;
    }
    /**
     * Get the brush engine instance
     */
    getBrushEngine() {
        return this.brushEngine;
    }
    /**
     * Validate that the current mask maintains binary invariant
     */
    validateMaskBinary() {
        if (!this.state)
            return true;
        return BrushEngine.validateBinaryMask(this.state.maskData);
    }
    /**
     * Enforce binary values in the current mask
     */
    enforceMaskBinary() {
        if (!this.state)
            return;
        BrushEngine.enforceBinaryMask(this.state.maskData);
        this.state.isDirty = true;
    }
    /**
     * Apply zoom/pan transform to canvases
     */
    applyTransform({ scale, translateX, translateY }) {
        if (!this.state)
            return;
        const value = `translate(-50%, -50%) ` +
            `translate(${translateX}px, ${translateY}px) ` + // translate in screen px (applies after scale)
            `scale(${scale})`;
        const canvases = [this.imageCanvas, this.overlayCanvas];
        canvases.forEach(canvas => {
            // Force override any CSS that might re-apply centering later
            canvas.style.setProperty('transform', value, 'important');
            canvas.style.setProperty('transform-origin', '50% 50%', 'important');
        });
    }
    /**
     * Reset canvas transforms
     */
    resetTransform() {
        const value = 'translate(-50%, -50%)';
        const canvases = [this.imageCanvas, this.overlayCanvas];
        canvases.forEach(canvas => {
            canvas.style.setProperty('transform', value, 'important');
            canvas.style.setProperty('transform-origin', '50% 50%', 'important');
        });
    }
    /**
     * Cleanup resources
     */
    cleanup() {
        this.resetTransform();
        this.state = null;
        this.loadedImage = null;
    }
}
