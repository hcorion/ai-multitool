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
        console.log('Event listeners attached');
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
        console.log('Pointer down event received:', event.type, 'enabled:', this.isEnabled, 'enableDrawing:', this.settings.enableDrawing);
        if (!this.isEnabled || !this.settings.enableDrawing)
            return;
        // Prevent default behavior
        event.preventDefault();
        // Only handle primary pointer for drawing (ignore secondary touches/clicks)
        if (!event.isPrimary)
            return;
        // Capture the pointer for reliable tracking
        if (this.settings.capturePointer) {
            this.canvas.setPointerCapture(event.pointerId);
        }
        // Create pointer state
        const pointerState = {
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
    handlePointerMove(event) {
        if (!this.isEnabled)
            return;
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
        }
        else if (event.pointerType === 'mouse') {
            // Handle cursor preview for mouse (non-drawing movement)
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
    handlePointerCancel(event) {
        if (!this.isEnabled)
            return;
        const pointerState = this.activePointers.get(event.pointerId);
        if (!pointerState)
            return;
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
    handleMouseLeave(event) {
        this.hideCursorPreview();
    }
    /**
     * Update cursor preview position
     */
    updateCursorPreview(screenX, screenY) {
        if (this.cursorElement) {
            this.cursorElement.style.left = `${screenX}px`;
            this.cursorElement.style.top = `${screenY}px`;
        }
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
            this.cursorElement.style.width = `${size}px`;
            this.cursorElement.style.height = `${size}px`;
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
    cleanup() {
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
