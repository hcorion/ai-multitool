/**
 * ZoomPanController - Handles zoom and pan navigation for the inpainting mask canvas
 * Supports pinch-to-zoom, wheel zoom, and two-finger pan gestures
 */
export class ZoomPanController {
    canvas;
    settings;
    transform;
    eventHandler = null;
    isActive = false;
    isEnabled = false;
    // Gesture tracking
    activePointers = new Map();
    lastPinchDistance = 0;
    lastPinchCenter = { x: 0, y: 0 };
    lastPanPosition = { x: 0, y: 0 };
    gestureStartTransform = null;
    // Image/canvas bounds
    imageBounds = null;
    canvasBounds = null;
    // Wheel gesture debounce so transform end fires
    wheelGestureTimer = null;
    // Store bound handlers so cleanup actually removes them
    bound = {
        pointerDown: (e) => this.handlePointerDown(e),
        pointerMove: (e) => this.handlePointerMove(e),
        pointerUp: (e) => this.handlePointerUp(e),
        pointerCancel: (e) => this.handlePointerCancel(e),
        wheel: (e) => this.handleWheel(e),
        contextMenu: (e) => this.handleContextMenu(e),
    };
    constructor(canvas, settings = {}) {
        this.canvas = canvas;
        this.settings = {
            minZoom: 0.1,
            maxZoom: 10.0,
            zoomSensitivity: 0.001,
            panSensitivity: 1.0,
            enablePinchZoom: true,
            enableWheelZoom: true,
            enablePan: true,
            wheelZoomModifier: 'ctrl',
            ...settings
        };
        this.transform = {
            scale: 1.0,
            translateX: 0,
            translateY: 0
        };
        this.setupEventListeners();
    }
    setupEventListeners() {
        this.canvas.addEventListener('pointerdown', this.bound.pointerDown);
        this.canvas.addEventListener('pointermove', this.bound.pointerMove);
        this.canvas.addEventListener('pointerup', this.bound.pointerUp);
        this.canvas.addEventListener('pointercancel', this.bound.pointerCancel);
        this.canvas.addEventListener('wheel', this.bound.wheel, { passive: false });
        this.canvas.addEventListener('contextmenu', this.bound.contextMenu);
    }
    /**
     * Handle pointer down events for gesture detection
     */
    handlePointerDown(event) {
        if (!this.isEnabled)
            return;
        this.activePointers.set(event.pointerId, event);
        // Check for multi-touch gestures
        if (this.activePointers.size === 2) {
            this.startMultiTouchGesture();
        }
        else if (this.activePointers.size === 1 && this.settings.enablePan) {
            // Single pointer - potential pan gesture
            this.lastPanPosition = { x: event.clientX, y: event.clientY };
        }
    }
    /**
     * Handle pointer move events for gesture processing
     */
    handlePointerMove(event) {
        if (!this.isEnabled)
            return;
        // Update pointer position
        if (this.activePointers.has(event.pointerId)) {
            this.activePointers.set(event.pointerId, event);
        }
        if (this.activePointers.size === 2 && this.settings.enablePinchZoom) {
            this.handlePinchZoomGesture();
        }
        else if (this.activePointers.size === 2 && this.settings.enablePan) {
            this.handleTwoFingerPan();
        }
        else if (this.activePointers.size === 1 && this.settings.enablePan && this.isActive) {
            this.handleSingleFingerPan(event);
        }
    }
    /**
     * Handle pointer up events
     */
    handlePointerUp(event) {
        if (!this.isEnabled)
            return;
        this.activePointers.delete(event.pointerId);
        // End gesture if no more active pointers
        if (this.activePointers.size === 0) {
            this.endGesture();
        }
        else if (this.activePointers.size === 1) {
            // Switch from multi-touch to single touch
            const remainingPointer = Array.from(this.activePointers.values())[0];
            this.lastPanPosition = { x: remainingPointer.clientX, y: remainingPointer.clientY };
        }
    }
    /**
     * Handle pointer cancel events
     */
    handlePointerCancel(event) {
        if (!this.isEnabled)
            return;
        this.activePointers.delete(event.pointerId);
        if (this.activePointers.size === 0) {
            this.endGesture();
        }
    }
    /**
     * Handle wheel events for mouse zoom
     */
    handleWheel(event) {
        if (!this.isEnabled || !this.settings.enableWheelZoom)
            return;
        const hasModifier = this.checkWheelModifier(event);
        if (!hasModifier && this.settings.wheelZoomModifier !== 'none') {
            return;
        }
        event.preventDefault();
        // Treat wheel as a short gesture that ends after a brief pause
        if (!this.isActive)
            this.startGesture();
        const delta = -event.deltaY * this.settings.zoomSensitivity;
        const newScale = this.clampZoom(this.transform.scale * (1 + delta));
        if (newScale !== this.transform.scale) {
            const rect = this.canvas.getBoundingClientRect();
            const centerX = event.clientX - rect.left;
            const centerY = event.clientY - rect.top;
            this.zoomToPoint(newScale, centerX, centerY);
            this.notifyTransformUpdate();
        }
        // Debounce gesture end so rapid wheel events act as one gesture
        if (this.wheelGestureTimer) {
            window.clearTimeout(this.wheelGestureTimer);
        }
        this.wheelGestureTimer = window.setTimeout(() => {
            this.wheelGestureTimer = null;
            this.endGesture();
        }, 120);
    }
    clampZoom(scale) {
        return Math.max(this.settings.minZoom, Math.min(this.settings.maxZoom, scale));
    }
    /**
     * Check if the required modifier key is pressed for wheel zoom
     */
    checkWheelModifier(event) {
        switch (this.settings.wheelZoomModifier) {
            case 'ctrl':
                return event.ctrlKey;
            case 'shift':
                return event.shiftKey;
            case 'alt':
                return event.altKey;
            case 'none':
                return true;
            default:
                return false;
        }
    }
    /**
     * Handle context menu prevention during gestures
     */
    handleContextMenu(event) {
        if (this.isActive) {
            event.preventDefault();
        }
    }
    /**
     * Start multi-touch gesture detection
     */
    startMultiTouchGesture() {
        const pointers = Array.from(this.activePointers.values());
        if (pointers.length !== 2)
            return;
        this.startGesture();
        // Calculate initial pinch distance and center
        this.lastPinchDistance = this.calculateDistance(pointers[0], pointers[1]);
        this.lastPinchCenter = this.calculateCenter(pointers[0], pointers[1]);
    }
    /**
     * Handle pinch-to-zoom gesture
     */
    handlePinchZoomGesture() {
        const pointers = Array.from(this.activePointers.values());
        if (pointers.length !== 2)
            return;
        const currentDistance = this.calculateDistance(pointers[0], pointers[1]);
        const currentCenter = this.calculateCenter(pointers[0], pointers[1]);
        if (this.lastPinchDistance > 0) {
            // Calculate zoom factor
            const zoomFactor = currentDistance / this.lastPinchDistance;
            const newScale = this.clampZoom(this.transform.scale * zoomFactor);
            if (newScale !== this.transform.scale) {
                // Convert center to canvas coordinates
                const rect = this.canvas.getBoundingClientRect();
                const centerX = currentCenter.x - rect.left;
                const centerY = currentCenter.y - rect.top;
                this.zoomToPoint(newScale, centerX, centerY);
                this.notifyTransformUpdate();
            }
        }
        this.lastPinchDistance = currentDistance;
        this.lastPinchCenter = currentCenter;
    }
    /**
     * Handle two-finger pan gesture
     */
    handleTwoFingerPan() {
        const pointers = Array.from(this.activePointers.values());
        if (pointers.length !== 2)
            return;
        const currentCenter = this.calculateCenter(pointers[0], pointers[1]);
        if (this.lastPinchCenter) {
            const deltaX = (currentCenter.x - this.lastPinchCenter.x) * this.settings.panSensitivity;
            const deltaY = (currentCenter.y - this.lastPinchCenter.y) * this.settings.panSensitivity;
            this.pan(deltaX, deltaY);
            this.notifyTransformUpdate();
        }
        this.lastPinchCenter = currentCenter;
    }
    /**
     * Handle single finger pan gesture (when gesture is already active)
     */
    handleSingleFingerPan(event) {
        if (!this.lastPanPosition)
            return;
        const deltaX = (event.clientX - this.lastPanPosition.x) * this.settings.panSensitivity;
        const deltaY = (event.clientY - this.lastPanPosition.y) * this.settings.panSensitivity;
        this.pan(deltaX, deltaY);
        this.notifyTransformUpdate();
        this.lastPanPosition = { x: event.clientX, y: event.clientY };
    }
    /**
     * Calculate distance between two pointers
     */
    calculateDistance(pointer1, pointer2) {
        const dx = pointer2.clientX - pointer1.clientX;
        const dy = pointer2.clientY - pointer1.clientY;
        return Math.sqrt(dx * dx + dy * dy);
    }
    /**
     * Calculate center point between two pointers
     */
    calculateCenter(pointer1, pointer2) {
        return {
            x: (pointer1.clientX + pointer2.clientX) / 2,
            y: (pointer1.clientY + pointer2.clientY) / 2
        };
    }
    /**
     * Zoom to a specific point on the canvas
     */
    zoomToPoint(newScale, canvasX, canvasY) {
        if (!this.canvasBounds)
            return;
        // Get the current canvas size (displayed size)
        const rect = this.canvas.getBoundingClientRect();
        const canvasWidth = rect.width;
        const canvasHeight = rect.height;
        // Calculate the point relative to canvas center (our transform origin)
        const centerX = canvasWidth / 2;
        const centerY = canvasHeight / 2;
        const pointX = canvasX - centerX;
        const pointY = canvasY - centerY;
        // Calculate the world position of this point before scaling
        const worldX = (pointX - this.transform.translateX) / this.transform.scale;
        const worldY = (pointY - this.transform.translateY) / this.transform.scale;
        // Update scale
        this.transform.scale = newScale;
        // Calculate new translation to keep the world point under the cursor
        this.transform.translateX = pointX - worldX * newScale;
        this.transform.translateY = pointY - worldY * newScale;
        // Apply constraints
        this.constrainTransform();
    }
    /**
     * Pan the view by the given delta
     */
    pan(deltaX, deltaY) {
        this.transform.translateX += deltaX;
        this.transform.translateY += deltaY;
        // Apply constraints
        this.constrainTransform();
    }
    /**
     * Constrain transform to keep image visible
     */
    constrainTransform() {
        if (!this.imageBounds)
            return;
        const rect = this.canvas.getBoundingClientRect();
        const S = this.transform.scale;
        // Pre (unscaled) canvas dims
        const preW = rect.width / S;
        const preH = rect.height / S;
        // Base contain fit in pre space
        const imgW = this.imageBounds.width;
        const imgH = this.imageBounds.height;
        const imageAspect = imgW / imgH;
        const canvasAspect = preW / preH;
        const baseScale = imageAspect > canvasAspect
            ? preW / imgW
            : preH / imgH;
        // Displayed image size in pre space, then multiplied by interactive zoom S
        const displayW = imgW * baseScale * S;
        const displayH = imgH * baseScale * S;
        // Visible canvas size in screen space is rect.width/height.
        // Max pan beyond edges (allow slight over-pan via padding):
        const padding = 50;
        const maxTranslateX = Math.max(0, (displayW - rect.width) / 2) + padding;
        const maxTranslateY = Math.max(0, (displayH - rect.height) / 2) + padding;
        this.transform.translateX = Math.max(-maxTranslateX, Math.min(maxTranslateX, this.transform.translateX));
        this.transform.translateY = Math.max(-maxTranslateY, Math.min(maxTranslateY, this.transform.translateY));
    }
    /**
     * Start a gesture (disable drawing)
     */
    startGesture() {
        if (this.isActive)
            return;
        this.isActive = true;
        this.gestureStartTransform = { ...this.transform };
        if (this.eventHandler) {
            this.eventHandler.onTransformStart();
        }
    }
    /**
     * End a gesture (re-enable drawing)
     */
    endGesture() {
        if (!this.isActive)
            return;
        this.isActive = false;
        this.gestureStartTransform = null;
        this.lastPinchDistance = 0;
        this.lastPinchCenter = { x: 0, y: 0 };
        this.lastPanPosition = { x: 0, y: 0 };
        if (this.eventHandler) {
            this.eventHandler.onTransformEnd();
        }
    }
    /**
     * Notify handler of transform update
     */
    notifyTransformUpdate() {
        if (this.eventHandler) {
            this.eventHandler.onTransformUpdate({ ...this.transform });
        }
    }
    /**
     * Set the event handler for zoom/pan events
     */
    setEventHandler(handler) {
        this.eventHandler = handler;
    }
    /**
     * Enable zoom and pan functionality
     */
    enable() {
        this.isEnabled = true;
    }
    /**
     * Disable zoom and pan functionality
     */
    disable() {
        this.isEnabled = false;
        this.endGesture();
    }
    /**
     * Check if zoom/pan gesture is currently active
     */
    isGestureActive() {
        return this.isActive;
    }
    /**
     * Get current transform
     */
    getTransform() {
        return { ...this.transform };
    }
    /**
     * Set transform programmatically
     */
    setTransform(transform) {
        this.transform = {
            ...this.transform,
            ...transform
        };
        // Clamp scale and constrain
        this.transform.scale = this.clampZoom(this.transform.scale);
        this.constrainTransform();
        this.notifyTransformUpdate();
    }
    /**
     * Reset transform to default (fit to canvas)
     */
    resetTransform() {
        this.transform = {
            scale: 1.0,
            translateX: 0,
            translateY: 0
        };
        this.notifyTransformUpdate();
    }
    /**
     * Set image bounds for constraint calculations
     */
    setImageBounds(width, height) {
        this.imageBounds = { width, height };
    }
    /**
     * Set canvas bounds for constraint calculations
     */
    setCanvasBounds(width, height) {
        this.canvasBounds = { width, height };
    }
    /**
     * Update settings
     */
    updateSettings(newSettings) {
        this.settings = { ...this.settings, ...newSettings };
    }
    /**
     * Get current settings
     */
    getSettings() {
        return { ...this.settings };
    }
    getCanvasBorders() {
        const cs = getComputedStyle(this.canvas);
        const toN = (v) => (parseFloat(v) || 0);
        return {
            left: toN(cs.borderLeftWidth),
            right: toN(cs.borderRightWidth),
            top: toN(cs.borderTopWidth),
            bottom: toN(cs.borderBottomWidth),
        };
    }
    /**
     * Convert screen coordinates to image coordinates with current transform
     */
    screenToImage(screenX, screenY) {
        if (!this.imageBounds)
            return null;
        const rect = this.canvas.getBoundingClientRect();
        const S = this.transform.scale;
        const T = { x: this.transform.translateX, y: this.transform.translateY };
        const borders = this.getCanvasBorders();
        // Element center in SCREEN coords (includes border; matches transform-origin center)
        const cx = rect.left + rect.width / 2;
        const cy = rect.top + rect.height / 2;
        // 1) screen -> center-relative
        const srX = screenX - cx;
        const srY = screenY - cy;
        // 2) invert view: pre-relative (element border-box space)
        const prX = (srX - T.x) / S;
        const prY = (srY - T.y) / S;
        // 3) pre-relative -> pre (top-left) in border-box coords
        const preW = rect.width / S; // includes border
        const preH = rect.height / S; // includes border
        const preX = prX + preW / 2;
        const preY = prY + preH / 2;
        // 4) step into content-box coords (subtract border)
        const contentX = preX - borders.left;
        const contentY = preY - borders.top;
        const contentW = preW - (borders.left + borders.right);
        const contentH = preH - (borders.top + borders.bottom);
        // Outside canvas content area?
        if (contentX < 0 || contentY < 0 || contentX > contentW || contentY > contentH) {
            return null;
        }
        // 5) map content box -> image pixels (contain-fit inside content)
        const imgW = this.imageBounds.width;
        const imgH = this.imageBounds.height;
        const imageAspect = imgW / imgH;
        const contentAspect = contentW / contentH;
        let displayW, displayH, offX = 0, offY = 0;
        if (imageAspect > contentAspect) {
            // fit to width
            displayW = contentW;
            displayH = contentW / imageAspect;
            offY = (contentH - displayH) / 2;
        }
        else {
            // fit to height
            displayH = contentH;
            displayW = contentH * imageAspect;
            offX = (contentW - displayW) / 2;
        }
        const dX = contentX - offX;
        const dY = contentY - offY;
        if (dX < 0 || dY < 0 || dX > displayW || dY > displayH) {
            return null; // in the letterbox margins
        }
        const imageX = (dX / displayW) * imgW;
        const imageY = (dY / displayH) * imgH;
        return { x: Math.floor(imageX), y: Math.floor(imageY) };
    }
    /**
     * Convert image coordinates to screen coordinates with current transform
     */
    imageToScreen(imageX, imageY) {
        if (!this.imageBounds)
            return { x: 0, y: 0 };
        const rect = this.canvas.getBoundingClientRect();
        const S = this.transform.scale;
        const T = { x: this.transform.translateX, y: this.transform.translateY };
        const borders = this.getCanvasBorders();
        // Pre (border-box) sizes (unscaled)
        const preW = rect.width / S;
        const preH = rect.height / S;
        // Content box sizes (unscaled)
        const contentW = preW - (borders.left + borders.right);
        const contentH = preH - (borders.top + borders.bottom);
        // Contain-fit image inside content box
        const imgW = this.imageBounds.width;
        const imgH = this.imageBounds.height;
        const imageAspect = imgW / imgH;
        const contentAspect = contentW / contentH;
        let displayW, displayH, offX = 0, offY = 0, baseScale;
        if (imageAspect > contentAspect) {
            displayW = contentW;
            displayH = contentW / imageAspect;
            baseScale = displayW / imgW;
            offY = (contentH - displayH) / 2;
        }
        else {
            displayH = contentH;
            displayW = contentH * imageAspect;
            baseScale = displayH / imgH;
            offX = (contentW - displayW) / 2;
        }
        // Image px -> content box coords
        const cX = offX + imageX * baseScale;
        const cY = offY + imageY * baseScale;
        // Content -> pre (add borders)
        const preX = cX + borders.left;
        const preY = cY + borders.top;
        // Pre -> center-relative
        const prX = preX - preW / 2;
        const prY = preY - preH / 2;
        // Apply view transform
        const srX = prX * S + T.x;
        const srY = prY * S + T.y;
        // Back to absolute screen
        const cx = rect.left + rect.width / 2;
        const cy = rect.top + rect.height / 2;
        return { x: cx + srX, y: cy + srY };
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
        this.canvas.removeEventListener('wheel', this.bound.wheel);
        this.canvas.removeEventListener('contextmenu', this.bound.contextMenu);
        this.activePointers.clear();
        this.eventHandler = null;
        this.imageBounds = null;
        this.canvasBounds = null;
        if (this.wheelGestureTimer) {
            window.clearTimeout(this.wheelGestureTimer);
            this.wheelGestureTimer = null;
        }
    }
}
