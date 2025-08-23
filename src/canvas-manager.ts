/**
 * CanvasManager - Handles canvas state, rendering, and coordinate transformations
 * for the inpainting mask canvas system.
 */

export interface CanvasState {
    imageWidth: number;
    imageHeight: number;
    maskData: Uint8Array;
    isDirty: boolean;
    displayWidth: number;
    displayHeight: number;
    offsetX: number;
    offsetY: number;
    scale: number;
}

export interface CoordinateTransform {
    screenToImage(screenX: number, screenY: number): { x: number; y: number } | null;
    imageToScreen(imageX: number, imageY: number): { x: number; y: number };
}

export class CanvasManager implements CoordinateTransform {
    private imageCanvas: HTMLCanvasElement;
    private overlayCanvas: HTMLCanvasElement;
    private maskAlphaCanvas: OffscreenCanvas | HTMLCanvasElement;
    private state: CanvasState | null = null;
    private loadedImage: HTMLImageElement | null = null;

    constructor(
        imageCanvas: HTMLCanvasElement,
        overlayCanvas: HTMLCanvasElement,
        maskAlphaCanvas: OffscreenCanvas | HTMLCanvasElement
    ) {
        this.imageCanvas = imageCanvas;
        this.overlayCanvas = overlayCanvas;
        this.maskAlphaCanvas = maskAlphaCanvas;
    }

    /**
     * Load and display an image with proper scaling and letterboxing
     */
    public async loadImage(imageUrl: string): Promise<void> {
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
                } catch (error) {
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
    private processLoadedImage(img: HTMLImageElement): void {
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

        const containerWidth = containerRect.width - 40; // Account for padding
        const containerHeight = containerRect.height - 40;
        
        const { displayWidth, displayHeight, scale } = this.calculateContainScaling(
            img.naturalWidth,
            img.naturalHeight,
            containerWidth,
            containerHeight
        );

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
    }

    /**
     * Calculate "contain" scaling with letterboxing to maintain aspect ratio
     */
    private calculateContainScaling(
        imageWidth: number,
        imageHeight: number,
        containerWidth: number,
        containerHeight: number
    ): { displayWidth: number; displayHeight: number; scale: number } {
        const imageAspect = imageWidth / imageHeight;
        const containerAspect = containerWidth / containerHeight;

        let displayWidth: number;
        let displayHeight: number;
        let scale: number;

        if (imageAspect > containerAspect) {
            // Image is wider than container - fit to width
            displayWidth = containerWidth;
            displayHeight = containerWidth / imageAspect;
            scale = containerWidth / imageWidth;
        } else {
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
    private updateCanvasSizes(width: number, height: number): void {
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

        if (!imageCtx || !overlayCtx) {
            throw new Error('Failed to get canvas contexts');
        }

        // Disable image smoothing for crisp pixel rendering
        imageCtx.imageSmoothingEnabled = false;
        overlayCtx.imageSmoothingEnabled = false;

        // Set overlay to semi-transparent
        overlayCtx.globalAlpha = 0.5;
    }

    /**
     * Render the image to the image canvas
     */
    private renderImage(img: HTMLImageElement): void {
        const ctx = this.imageCanvas.getContext('2d');
        if (!ctx || !this.state) return;

        // Clear canvas
        ctx.clearRect(0, 0, this.state.imageWidth, this.state.imageHeight);
        
        // Draw image at full resolution
        ctx.drawImage(img, 0, 0);

        // Update canvas display size and position
        this.updateCanvasDisplay();
    }

    /**
     * Update canvas display size and position for letterboxing
     */
    private updateCanvasDisplay(): void {
        if (!this.state) return;

        const canvases = [this.imageCanvas, this.overlayCanvas];
        
        canvases.forEach(canvas => {
            canvas.style.width = `${this.state!.displayWidth}px`;
            canvas.style.height = `${this.state!.displayHeight}px`;
            // Don't set left/top - let CSS centering handle positioning
            // The CSS uses transform: translate(-50%, -50%) to center the canvas
        });
    }

    /**
     * Convert screen coordinates to image pixel coordinates
     */
    public screenToImage(screenX: number, screenY: number): { x: number; y: number } | null {
        if (!this.state) return null;

        const canvasRect = this.imageCanvas.getBoundingClientRect();
        
        // Convert to canvas-relative coordinates
        const canvasX = screenX - canvasRect.left;
        const canvasY = screenY - canvasRect.top;

        // Check if point is within canvas bounds (using actual displayed canvas size)
        if (canvasX < 0 || canvasY < 0 || canvasX >= canvasRect.width || canvasY >= canvasRect.height) {
            return null;
        }

        // Convert to image coordinates using the scale factor
        const imageX = Math.floor(canvasX / this.state.scale);
        const imageY = Math.floor(canvasY / this.state.scale);

        // Clamp to image bounds
        const clampedX = Math.max(0, Math.min(this.state.imageWidth - 1, imageX));
        const clampedY = Math.max(0, Math.min(this.state.imageHeight - 1, imageY));

        return { x: clampedX, y: clampedY };
    }

    /**
     * Convert image pixel coordinates to screen coordinates
     */
    public imageToScreen(imageX: number, imageY: number): { x: number; y: number } {
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
    public getState(): CanvasState | null {
        return this.state;
    }

    /**
     * Get the loaded image
     */
    public getLoadedImage(): HTMLImageElement | null {
        return this.loadedImage;
    }

    /**
     * Update mask data at specific coordinates
     */
    public updateMaskData(x: number, y: number, value: number): boolean {
        if (!this.state) return false;

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
            return true;
        }

        return false;
    }

    /**
     * Get mask value at specific coordinates
     */
    public getMaskValue(x: number, y: number): number {
        if (!this.state) return 0;

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
    public clearMask(): void {
        if (!this.state) return;

        this.state.maskData.fill(0);
        this.state.isDirty = true;
    }

    /**
     * Fill entire mask
     */
    public fillMask(): void {
        if (!this.state) return;

        this.state.maskData.fill(255);
        this.state.isDirty = true;
    }

    /**
     * Check if mask data is dirty and needs redraw
     */
    public isDirty(): boolean {
        return this.state?.isDirty ?? false;
    }

    /**
     * Mark mask data as clean (after redraw)
     */
    public markClean(): void {
        if (this.state) {
            this.state.isDirty = false;
        }
    }

    /**
     * Resize canvases when container size changes
     */
    public handleResize(): void {
        if (!this.state || !this.loadedImage) return;

        // Recalculate display dimensions
        const containerRect = this.imageCanvas.parentElement?.getBoundingClientRect();
        if (!containerRect) return;

        const containerWidth = containerRect.width - 40;
        const containerHeight = containerRect.height - 40;
        
        const { displayWidth, displayHeight, scale } = this.calculateContainScaling(
            this.state.imageWidth,
            this.state.imageHeight,
            containerWidth,
            containerHeight
        );

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
    public exportMaskImageData(): ImageData | null {
        if (!this.state) return null;

        const canvas = document.createElement('canvas');
        canvas.width = this.state.imageWidth;
        canvas.height = this.state.imageHeight;
        const ctx = canvas.getContext('2d');
        
        if (!ctx) return null;

        const imageData = ctx.createImageData(this.state.imageWidth, this.state.imageHeight);
        
        // Convert mask data to RGBA
        for (let i = 0; i < this.state.maskData.length; i++) {
            const pixelIndex = i * 4;
            const maskValue = this.state.maskData[i];
            
            imageData.data[pixelIndex] = maskValue;     // R
            imageData.data[pixelIndex + 1] = maskValue; // G
            imageData.data[pixelIndex + 2] = maskValue; // B
            imageData.data[pixelIndex + 3] = 255;       // A
        }

        return imageData;
    }

    /**
     * Cleanup resources
     */
    public cleanup(): void {
        this.state = null;
        this.loadedImage = null;
    }
}