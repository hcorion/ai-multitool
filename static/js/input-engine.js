/**
 * InputEngine - Unified pointer input handling using Pointer Events API
 * Handles mouse, pen, and touch input with proper capture and cancellation
 */
export class InputEngine {
    canvas;
    settings;
    activePointers = new Map();
    eventHandler = null;
    isEnabled = false;
    cursorElement = null;
    coordinateTransformer = null;
    bound = {
        pointerDown: (e) => this.handlePointerDown(e),
        pointerMove: (e) => this.handlePointerMove(e),
        pointerUp: (e) => this.handlePointerUp(e),
        pointerCancel: (e) => this.handlePointerCancel(e),
        pointerLeave: (e) => this.handlePointerLeave(e),
        contextMenu: (e) => this.handleContextMenu(e),
        mouseEnter: (e) => this.handleMouseEnter(e),
        mouseLeave: (e) => this.handleMouseLeave(e),
    };
    constructor(canvas, settings = {}) {
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
    setupEventListeners() {
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
    setupTouchAction() {
        if (this.settings.preventScrolling) {
            this.canvas.style.touchAction = 'none';
        }
    }
    /**
     * Handle pointer down events
     */
    handlePointerDown(event) {
        if (!this.isEnabled || !this.settings.enableDrawing)
            return;
        event.preventDefault();
        if (!event.isPrimary)
            return;
        if (this.settings.capturePointer)
            this.canvas.setPointerCapture(event.pointerId);
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
    handlePointerMove(event) {
        if (!this.isEnabled)
            return;
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
        }
        else if (event.pointerType === 'mouse') {
            this.updateCursorPreview(event.clientX, event.clientY);
        }
    }
    /**
     * Handle pointer up events
     */
    handlePointerUp(event) {
        if (!this.isEnabled)
            return;
        const pointerState = this.activePointers.get(event.pointerId);
        if (!pointerState)
            return;
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
    handlePointerCancel(event) {
        if (!this.isEnabled)
            return;
        const pointerState = this.activePointers.get(event.pointerId);
        if (!pointerState)
            return;
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
    handlePointerLeave(event) {
        // Hide cursor preview when leaving canvas
        if (event.pointerType === 'mouse') {
            this.hideCursorPreview();
        }
    }
    /**
     * Handle context menu events (prevent right-click menu during drawing)
     */
    handleContextMenu(event) {
        if (this.isEnabled && this.activePointers.size > 0) {
            event.preventDefault();
        }
    }
    /**
     * Handle mouse enter events
     */
    handleMouseEnter(event) {
        if (this.isEnabled) {
            this.showCursorPreview(event.clientX, event.clientY);
        }
    }
    /**
     * Handle mouse leave events
     */
    handleMouseLeave(_event) {
        this.hideCursorPreview();
    }
    /**
     * Update cursor preview position
     */
    updateCursorPreview(clientX, clientY) {
        if (!this.cursorElement)
            return;
        let cursorX = clientX;
        let cursorY = clientY;
        if (this.coordinateTransformer) {
            const img = this.coordinateTransformer(clientX, clientY);
            if (!img) {
                this.cursorElement.style.display = 'none';
                return;
            }
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
    showCursorPreview(screenX, screenY) {
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
    hideCursorPreview() {
        if (this.cursorElement) {
            this.cursorElement.style.display = 'none';
        }
    }
    /**
     * Create cursor preview element
     */
    createCursorPreview() {
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
    updateCursorSize(size) {
        if (this.cursorElement) {
            let displaySize = size;
            if (this.coordinateTransformer?.getTransform) {
                const t = this.coordinateTransformer.getTransform();
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
    updateCursorMode(mode) {
        if (this.cursorElement) {
            if (mode === 'paint') {
                this.cursorElement.style.borderColor = 'rgba(255, 255, 255, 0.8)';
                this.cursorElement.style.backgroundColor = 'rgba(255, 255, 255, 0.1)';
            }
            else {
                this.cursorElement.style.borderColor = 'rgba(255, 100, 100, 0.8)';
                this.cursorElement.style.backgroundColor = 'rgba(255, 100, 100, 0.1)';
            }
        }
    }
    /**
     * Set the input event handler
     */
    setEventHandler(handler) {
        this.eventHandler = handler;
    }
    /**
     * Set coordinate transformer for cursor preview positioning
     */
    setCoordinateTransformer(transformer) {
        this.coordinateTransformer = transformer;
    }
    /**
     * Enable input handling
     */
    enable() {
        this.isEnabled = true;
        this.canvas.style.cursor = 'none'; // Hide default cursor
    }
    /**
     * Disable input handling
     */
    disable() {
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
    updateSettings(newSettings) {
        this.settings = { ...this.settings, ...newSettings };
        // Update touch-action if preventScrolling changed
        if ('preventScrolling' in newSettings) {
            this.setupTouchAction();
        }
    }
    /**
     * Get current input settings
     */
    getSettings() {
        return { ...this.settings };
    }
    /**
     * Get active pointer count
     */
    getActivePointerCount() {
        return this.activePointers.size;
    }
    /**
     * Check if a specific pointer is active
     */
    isPointerActive(pointerId) {
        return this.activePointers.has(pointerId);
    }
    /**
     * Get information about active pointers
     */
    getActivePointers() {
        return Array.from(this.activePointers.values());
    }
    /**
     * Force cancel all active pointers (useful for cleanup)
     */
    cancelAllPointers() {
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
    cleanup() {
        this.disable();
        this.canvas.removeEventListener('pointerdown', this.bound.pointerDown);
        this.canvas.removeEventListener('pointermove', this.bound.pointerMove);
        this.canvas.removeEventListener('pointerup', this.bound.pointerUp);
        this.canvas.removeEventListener('pointercancel', this.bound.pointerCancel);
        this.canvas.removeEventListener('pointerleave', this.bound.pointerLeave);
        this.canvas.removeEventListener('contextmenu', this.bound.contextMenu);
        this.canvas.removeEventListener('mouseenter', this.bound.mouseEnter);
        this.canvas.removeEventListener('mouseleave', this.bound.mouseLeave);
        if (this.cursorElement) {
            this.cursorElement.remove();
            this.cursorElement = null;
        }
        this.canvas.style.touchAction = '';
        this.canvas.style.cursor = '';
        this.eventHandler = null;
    }
}
