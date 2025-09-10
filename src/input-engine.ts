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
    clientX: number;
    clientY: number;
    // kept for backward compatibility with existing code
    screenX: number;
    screenY: number;
    pointerId: number;
    pointerType: string;
    isPrimary: boolean;
    pressure?: number;
}) => void;

export interface CoordinateTransformer {
    (screenX: number, screenY: number): { x: number; y: number } | null;
    getTransform?: () => { scale: number; translateX: number; translateY: number };
    imageToScreen?: (imageX: number, imageY: number) => { x: number; y: number };
}

export class InputEngine {
    private canvas: HTMLCanvasElement;
    private settings: InputSettings;
    private activePointers: Map<number, PointerState> = new Map();
    private eventHandler: InputEventHandler | null = null;
    private isEnabled: boolean = false;
    private cursorElement: HTMLElement | null = null;
    private coordinateTransformer: CoordinateTransformer | null = null;

    private bound = {
        pointerDown: (e: PointerEvent) => this.handlePointerDown(e),
        pointerMove: (e: PointerEvent) => this.handlePointerMove(e),
        pointerUp: (e: PointerEvent) => this.handlePointerUp(e),
        pointerCancel: (e: PointerEvent) => this.handlePointerCancel(e),
        pointerLeave: (e: PointerEvent) => this.handlePointerLeave(e),
        contextMenu: (e: Event) => this.handleContextMenu(e),
        mouseEnter: (e: MouseEvent) => this.handleMouseEnter(e),
        mouseLeave: (e: MouseEvent) => this.handleMouseLeave(e),
    };

    constructor(canvas: HTMLCanvasElement, settings: Partial<InputSettings> = {}) {
        console.log('InputEngine constructor called with canvas:', canvas);
        this.canvas = canvas;
        this.settings = {
            enableDrawing: true,
            preventScrolling: true,
            capturePointer: true,
            ...settings
        };
        console.log('InputEngine settings:', this.settings);

        this.setupEventListeners();
        this.setupTouchAction();
        console.log('InputEngine initialization complete');
    }

    /**
     * Set up pointer event listeners
     */
    private setupEventListeners(): void {
        console.log('Setting up event listeners on canvas:', this.canvas);

        // Pointer Events API handlers
        this.canvas.addEventListener('pointerdown', this.bound.pointerDown);
        this.canvas.addEventListener('pointermove', this.bound.pointerMove);
        this.canvas.addEventListener('pointerup', this.bound.pointerUp);
        this.canvas.addEventListener('pointercancel', this.bound.pointerCancel);
        this.canvas.addEventListener('pointerleave', this.bound.pointerLeave);
        this.canvas.addEventListener('contextmenu', this.bound.contextMenu);
        this.canvas.addEventListener('mouseenter', this.bound.mouseEnter);
        this.canvas.addEventListener('mouseleave', this.bound.mouseLeave);
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
        event.preventDefault();
        if (!event.isPrimary) return;
        if (this.settings.capturePointer) this.canvas.setPointerCapture(event.pointerId);

        this.activePointers.set(event.pointerId, {
            pointerId: event.pointerId,
            pointerType: event.pointerType,
            isPrimary: event.isPrimary,
            isDrawing: true,
            lastPosition: { x: event.clientX, y: event.clientY },
            startTime: Date.now()
        });

        this.eventHandler?.({
            type: 'start',
            clientX: event.clientX,
            clientY: event.clientY,
            screenX: event.clientX,
            screenY: event.clientY,
            pointerId: event.pointerId,
            pointerType: event.pointerType,
            isPrimary: event.isPrimary,
            pressure: event.pressure
        });
    }

    /**
     * Handle pointer move events
     */
    private handlePointerMove(event: PointerEvent): void {
        if (!this.isEnabled) return;
        const pointerState = this.activePointers.get(event.pointerId);

        if (pointerState && pointerState.isDrawing && this.settings.enableDrawing) {
            event.preventDefault();
            pointerState.lastPosition = { x: event.clientX, y: event.clientY };
            this.eventHandler?.({
                type: 'move',
                clientX: event.clientX,
                clientY: event.clientY,
                screenX: event.clientX,
                screenY: event.clientY,
                pointerId: event.pointerId,
                pointerType: event.pointerType,
                isPrimary: event.isPrimary,
                pressure: event.pressure
            });
        } else if (event.pointerType === 'mouse') {
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
        if (this.settings.capturePointer && this.canvas.hasPointerCapture(event.pointerId)) {
            this.canvas.releasePointerCapture(event.pointerId);
        }

        if (pointerState.isDrawing) {
            this.eventHandler?.({
                type: 'end',
                clientX: event.clientX,
                clientY: event.clientY,
                screenX: event.clientX,
                screenY: event.clientY,
                pointerId: event.pointerId,
                pointerType: event.pointerType,
                isPrimary: event.isPrimary,
                pressure: event.pressure
            });
        }
        this.activePointers.delete(event.pointerId);
    }

    /**
     * Handle pointer cancel events (important for robust input handling)
     */
    private handlePointerCancel(event: PointerEvent): void {
        if (!this.isEnabled) return;
        const pointerState = this.activePointers.get(event.pointerId);
        if (!pointerState) return;

        if (this.settings.capturePointer && this.canvas.hasPointerCapture(event.pointerId)) {
            this.canvas.releasePointerCapture(event.pointerId);
        }

        if (pointerState.isDrawing) {
            this.eventHandler?.({
                type: 'cancel',
                clientX: event.clientX,
                clientY: event.clientY,
                screenX: event.clientX,
                screenY: event.clientY,
                pointerId: event.pointerId,
                pointerType: event.pointerType,
                isPrimary: event.isPrimary,
                pressure: event.pressure
            });
        }
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
    private handleMouseLeave(_event: MouseEvent): void {
        this.hideCursorPreview();
    }

    /**
     * Update cursor preview position
     */
    private updateCursorPreview(clientX: number, clientY: number): void {
        if (!this.cursorElement) return;

        let cursorX = clientX;
        let cursorY = clientY;

        if (this.coordinateTransformer) {
            const img = this.coordinateTransformer(clientX, clientY);
            if (!img) { this.cursorElement.style.display = 'none'; return; }

            if (this.coordinateTransformer.imageToScreen) {
                const p = this.coordinateTransformer.imageToScreen(img.x, img.y);
                cursorX = p.x;
                cursorY = p.y;
            }
        }

        this.cursorElement.style.left = `${cursorX}px`;
        this.cursorElement.style.top = `${cursorY}px`;
        this.cursorElement.style.display = 'block';
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
            let displaySize = size;
            if (this.coordinateTransformer?.getTransform) {
                const t = this.coordinateTransformer.getTransform() as any;
                const baseScale = t.baseScale ?? 1;
                displaySize = size * baseScale * t.scale; // exact on-screen brush diameter
            }
            this.cursorElement.style.width = `${displaySize}px`;
            this.cursorElement.style.height = `${displaySize}px`;
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
     * Set coordinate transformer for cursor preview positioning
     */
    public setCoordinateTransformer(transformer: CoordinateTransformer | null): void {
        this.coordinateTransformer = transformer;
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
        for (const [pointerId, pointerState] of Array.from(this.activePointers.entries())) {
            if (this.settings.capturePointer && this.canvas.hasPointerCapture(pointerId)) {
                this.canvas.releasePointerCapture(pointerId);
            }

            if (pointerState.isDrawing && this.eventHandler) {
                this.eventHandler({
                    type: 'cancel',
                    clientX: pointerState.lastPosition?.x || 0,
                    clientY: pointerState.lastPosition?.y || 0,
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
        for (const [pointerId, pointerState] of Array.from(this.activePointers.entries())) {
            if (this.settings.capturePointer && this.canvas.hasPointerCapture(pointerId)) {
                this.canvas.releasePointerCapture(pointerId);
            }

            if (pointerState.isDrawing && this.eventHandler) {
                this.eventHandler({
                    type: 'cancel',
                    clientX: pointerState.lastPosition?.x || 0,
                    clientY: pointerState.lastPosition?.y || 0,
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
        this.canvas.removeEventListener('pointerdown', this.bound.pointerDown);
        this.canvas.removeEventListener('pointermove', this.bound.pointerMove);
        this.canvas.removeEventListener('pointerup', this.bound.pointerUp);
        this.canvas.removeEventListener('pointercancel', this.bound.pointerCancel);
        this.canvas.removeEventListener('pointerleave', this.bound.pointerLeave);
        this.canvas.removeEventListener('contextmenu', this.bound.contextMenu);
        this.canvas.removeEventListener('mouseenter', this.bound.mouseEnter);
        this.canvas.removeEventListener('mouseleave', this.bound.mouseLeave);
        if (this.cursorElement) { this.cursorElement.remove(); this.cursorElement = null; }
        this.canvas.style.touchAction = '';
        this.canvas.style.cursor = '';
        this.eventHandler = null;
    }
}