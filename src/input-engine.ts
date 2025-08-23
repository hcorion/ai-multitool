/**
 * InputEngine - Unified pointer input handling using Pointer Events API
 * Handles mouse, pen, and touch input with proper capture and cancellation
 */

export interface PointerState {
    pointerId: number;
    pointerType: string;
    isPrimary: boolean;
    isDrawing: boolean;
    lastPosition: { x: number; y: number } | null;
    startTime: number;
}

export interface InputSettings {
    enableDrawing: boolean;
    preventScrolling: boolean;
    capturePointer: boolean;
}

export type InputEventHandler = (event: {
    type: 'start' | 'move' | 'end' | 'cancel';
    screenX: number;
    screenY: number;
    pointerId: number;
    pointerType: string;
    isPrimary: boolean;
    pressure?: number;
}) => void;

export class InputEngine {
    private canvas: HTMLCanvasElement;
    private settings: InputSettings;
    private activePointers: Map<number, PointerState> = new Map();
    private eventHandler: InputEventHandler | null = null;
    private isEnabled: boolean = false;
    private cursorElement: HTMLElement | null = null;

    constructor(canvas: HTMLCanvasElement, settings: Partial<InputSettings> = {}) {
        this.canvas = canvas;
        this.settings = {
            enableDrawing: true,
            preventScrolling: true,
            capturePointer: true,
            ...settings
        };

        this.setupEventListeners();
        this.setupTouchAction();
    }

    /**
     * Set up pointer event listeners
     */
    private setupEventListeners(): void {
        // Pointer Events API handlers
        this.canvas.addEventListener('pointerdown', this.handlePointerDown.bind(this));
        this.canvas.addEventListener('pointermove', this.handlePointerMove.bind(this));
        this.canvas.addEventListener('pointerup', this.handlePointerUp.bind(this));
        this.canvas.addEventListener('pointercancel', this.handlePointerCancel.bind(this));
        this.canvas.addEventListener('pointerleave', this.handlePointerLeave.bind(this));

        // Context menu prevention for better drawing experience
        this.canvas.addEventListener('contextmenu', this.handleContextMenu.bind(this));

        // Mouse cursor tracking for brush preview
        this.canvas.addEventListener('mouseenter', this.handleMouseEnter.bind(this));
        this.canvas.addEventListener('mouseleave', this.handleMouseLeave.bind(this));
    }

    /**
     * Set up touch-action CSS property to prevent scrolling
     */
    private setupTouchAction(): void {
        if (this.settings.preventScrolling) {
            this.canvas.style.touchAction = 'none';
        }
    }

    /**
     * Handle pointer down events
     */
    private handlePointerDown(event: PointerEvent): void {
        if (!this.isEnabled || !this.settings.enableDrawing) return;

        // Prevent default behavior
        event.preventDefault();

        // Only handle primary pointer for drawing (ignore secondary touches/clicks)
        if (!event.isPrimary) return;

        // Capture the pointer for reliable tracking
        if (this.settings.capturePointer) {
            this.canvas.setPointerCapture(event.pointerId);
        }

        // Create pointer state
        const pointerState: PointerState = {
            pointerId: event.pointerId,
            pointerType: event.pointerType,
            isPrimary: event.isPrimary,
            isDrawing: true,
            lastPosition: { x: event.clientX, y: event.clientY },
            startTime: Date.now()
        };

        this.activePointers.set(event.pointerId, pointerState);

        // Notify handler
        if (this.eventHandler) {
            this.eventHandler({
                type: 'start',
                screenX: event.clientX,
                screenY: event.clientY,
                pointerId: event.pointerId,
                pointerType: event.pointerType,
                isPrimary: event.isPrimary,
                pressure: event.pressure
            });
        }
    }

    /**
     * Handle pointer move events
     */
    private handlePointerMove(event: PointerEvent): void {
        if (!this.isEnabled) return;

        const pointerState = this.activePointers.get(event.pointerId);

        // Handle drawing movement
        if (pointerState && pointerState.isDrawing && this.settings.enableDrawing) {
            event.preventDefault();

            // Update pointer state
            pointerState.lastPosition = { x: event.clientX, y: event.clientY };

            // Notify handler
            if (this.eventHandler) {
                this.eventHandler({
                    type: 'move',
                    screenX: event.clientX,
                    screenY: event.clientY,
                    pointerId: event.pointerId,
                    pointerType: event.pointerType,
                    isPrimary: event.isPrimary,
                    pressure: event.pressure
                });
            }
        } else if (event.pointerType === 'mouse') {
            // Handle cursor preview for mouse (non-drawing movement)
            this.updateCursorPreview(event.clientX, event.clientY);
        }
    }

    /**
     * Handle pointer up events
     */
    private handlePointerUp(event: PointerEvent): void {
        if (!this.isEnabled) return;

        const pointerState = this.activePointers.get(event.pointerId);
        if (!pointerState) return;

        event.preventDefault();

        // Release pointer capture
        if (this.settings.capturePointer && this.canvas.hasPointerCapture(event.pointerId)) {
            this.canvas.releasePointerCapture(event.pointerId);
        }

        // Notify handler if this was a drawing operation
        if (pointerState.isDrawing && this.eventHandler) {
            this.eventHandler({
                type: 'end',
                screenX: event.clientX,
                screenY: event.clientY,
                pointerId: event.pointerId,
                pointerType: event.pointerType,
                isPrimary: event.isPrimary,
                pressure: event.pressure
            });
        }

        // Clean up pointer state
        this.activePointers.delete(event.pointerId);
    }

    /**
     * Handle pointer cancel events (important for robust input handling)
     */
    private handlePointerCancel(event: PointerEvent): void {
        if (!this.isEnabled) return;

        const pointerState = this.activePointers.get(event.pointerId);
        if (!pointerState) return;

        // Release pointer capture
        if (this.settings.capturePointer && this.canvas.hasPointerCapture(event.pointerId)) {
            this.canvas.releasePointerCapture(event.pointerId);
        }

        // Notify handler of cancellation
        if (pointerState.isDrawing && this.eventHandler) {
            this.eventHandler({
                type: 'cancel',
                screenX: event.clientX,
                screenY: event.clientY,
                pointerId: event.pointerId,
                pointerType: event.pointerType,
                isPrimary: event.isPrimary,
                pressure: event.pressure
            });
        }

        // Clean up pointer state
        this.activePointers.delete(event.pointerId);
    }

    /**
     * Handle pointer leave events
     */
    private handlePointerLeave(event: PointerEvent): void {
        // Hide cursor preview when leaving canvas
        if (event.pointerType === 'mouse') {
            this.hideCursorPreview();
        }
    }

    /**
     * Handle context menu events (prevent right-click menu during drawing)
     */
    private handleContextMenu(event: Event): void {
        if (this.isEnabled && this.activePointers.size > 0) {
            event.preventDefault();
        }
    }

    /**
     * Handle mouse enter events
     */
    private handleMouseEnter(event: MouseEvent): void {
        if (this.isEnabled) {
            this.showCursorPreview(event.clientX, event.clientY);
        }
    }

    /**
     * Handle mouse leave events
     */
    private handleMouseLeave(event: MouseEvent): void {
        this.hideCursorPreview();
    }

    /**
     * Update cursor preview position
     */
    private updateCursorPreview(screenX: number, screenY: number): void {
        if (this.cursorElement) {
            this.cursorElement.style.left = `${screenX}px`;
            this.cursorElement.style.top = `${screenY}px`;
        }
    }

    /**
     * Show cursor preview
     */
    private showCursorPreview(screenX: number, screenY: number): void {
        if (!this.cursorElement) {
            this.createCursorPreview();
        }
        
        if (this.cursorElement) {
            this.cursorElement.style.display = 'block';
            this.updateCursorPreview(screenX, screenY);
        }
    }

    /**
     * Hide cursor preview
     */
    private hideCursorPreview(): void {
        if (this.cursorElement) {
            this.cursorElement.style.display = 'none';
        }
    }

    /**
     * Create cursor preview element
     */
    private createCursorPreview(): void {
        this.cursorElement = document.createElement('div');
        this.cursorElement.className = 'brush-cursor-preview';
        this.cursorElement.style.cssText = `
            position: fixed;
            pointer-events: none;
            z-index: 10001;
            border: 2px solid rgba(255, 255, 255, 0.8);
            border-radius: 50%;
            transform: translate(-50%, -50%);
            display: none;
            box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.5);
        `;
        
        document.body.appendChild(this.cursorElement);
        this.updateCursorSize(20); // Default size
    }

    /**
     * Update cursor preview size
     */
    public updateCursorSize(size: number): void {
        if (this.cursorElement) {
            this.cursorElement.style.width = `${size}px`;
            this.cursorElement.style.height = `${size}px`;
        }
    }

    /**
     * Update cursor preview color based on tool mode
     */
    public updateCursorMode(mode: 'paint' | 'erase'): void {
        if (this.cursorElement) {
            if (mode === 'paint') {
                this.cursorElement.style.borderColor = 'rgba(255, 255, 255, 0.8)';
                this.cursorElement.style.backgroundColor = 'rgba(255, 255, 255, 0.1)';
            } else {
                this.cursorElement.style.borderColor = 'rgba(255, 100, 100, 0.8)';
                this.cursorElement.style.backgroundColor = 'rgba(255, 100, 100, 0.1)';
            }
        }
    }

    /**
     * Set the input event handler
     */
    public setEventHandler(handler: InputEventHandler): void {
        this.eventHandler = handler;
    }

    /**
     * Enable input handling
     */
    public enable(): void {
        this.isEnabled = true;
        this.canvas.style.cursor = 'none'; // Hide default cursor
    }

    /**
     * Disable input handling
     */
    public disable(): void {
        this.isEnabled = false;
        this.canvas.style.cursor = 'default'; // Restore default cursor
        this.hideCursorPreview();
        
        // Cancel any active pointers
        for (const [pointerId, pointerState] of this.activePointers) {
            if (this.settings.capturePointer && this.canvas.hasPointerCapture(pointerId)) {
                this.canvas.releasePointerCapture(pointerId);
            }
            
            if (pointerState.isDrawing && this.eventHandler) {
                this.eventHandler({
                    type: 'cancel',
                    screenX: pointerState.lastPosition?.x || 0,
                    screenY: pointerState.lastPosition?.y || 0,
                    pointerId: pointerId,
                    pointerType: pointerState.pointerType,
                    isPrimary: pointerState.isPrimary
                });
            }
        }
        
        this.activePointers.clear();
    }

    /**
     * Update input settings
     */
    public updateSettings(newSettings: Partial<InputSettings>): void {
        this.settings = { ...this.settings, ...newSettings };
        
        // Update touch-action if preventScrolling changed
        if ('preventScrolling' in newSettings) {
            this.setupTouchAction();
        }
    }

    /**
     * Get current input settings
     */
    public getSettings(): InputSettings {
        return { ...this.settings };
    }

    /**
     * Get active pointer count
     */
    public getActivePointerCount(): number {
        return this.activePointers.size;
    }

    /**
     * Check if a specific pointer is active
     */
    public isPointerActive(pointerId: number): boolean {
        return this.activePointers.has(pointerId);
    }

    /**
     * Get information about active pointers
     */
    public getActivePointers(): PointerState[] {
        return Array.from(this.activePointers.values());
    }

    /**
     * Force cancel all active pointers (useful for cleanup)
     */
    public cancelAllPointers(): void {
        for (const [pointerId, pointerState] of this.activePointers) {
            if (this.settings.capturePointer && this.canvas.hasPointerCapture(pointerId)) {
                this.canvas.releasePointerCapture(pointerId);
            }
            
            if (pointerState.isDrawing && this.eventHandler) {
                this.eventHandler({
                    type: 'cancel',
                    screenX: pointerState.lastPosition?.x || 0,
                    screenY: pointerState.lastPosition?.y || 0,
                    pointerId: pointerId,
                    pointerType: pointerState.pointerType,
                    isPrimary: pointerState.isPrimary
                });
            }
        }
        
        this.activePointers.clear();
    }

    /**
     * Cleanup resources
     */
    public cleanup(): void {
        this.disable();
        
        // Remove event listeners
        this.canvas.removeEventListener('pointerdown', this.handlePointerDown.bind(this));
        this.canvas.removeEventListener('pointermove', this.handlePointerMove.bind(this));
        this.canvas.removeEventListener('pointerup', this.handlePointerUp.bind(this));
        this.canvas.removeEventListener('pointercancel', this.handlePointerCancel.bind(this));
        this.canvas.removeEventListener('pointerleave', this.handlePointerLeave.bind(this));
        this.canvas.removeEventListener('contextmenu', this.handleContextMenu.bind(this));
        this.canvas.removeEventListener('mouseenter', this.handleMouseEnter.bind(this));
        this.canvas.removeEventListener('mouseleave', this.handleMouseLeave.bind(this));
        
        // Remove cursor preview
        if (this.cursorElement) {
            this.cursorElement.remove();
            this.cursorElement = null;
        }
        
        // Reset canvas styles
        this.canvas.style.touchAction = '';
        this.canvas.style.cursor = '';
        
        this.eventHandler = null;
    }
}