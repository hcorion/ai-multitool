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
    // Image bounds for constraint calculations
    imageBounds = null;
    canvasBounds = null;
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
    /**
     * Set up event listeners for zoom and pan gestures
     */
    setupEventListeners() {
        // Pointer events for touch gestures
        this.canvas.addEventListener('pointerdown', this.handlePointerDown.bind(this));
        this.canvas.addEventListener('pointermove', this.handlePointerMove.bind(this));
        this.canvas.addEventListener('pointerup', this.handlePointerUp.bind(this));
        this.canvas.addEventListener('pointercancel', this.handlePointerCancel.bind(this));
        // Wheel events for mouse zoom
        this.canvas.addEventListener('wheel', this.handleWheel.bind(this), { passive: false });
        // Prevent context menu during gestures
        this.canvas.addEventListener('contextmenu', this.handleContextMenu.bind(this));
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
        // Check for required modifier key
        const hasModifier = this.checkWheelModifier(event);
        if (!hasModifier && this.settings.wheelZoomModifier !== 'none') {
            return;
        }
        event.preventDefault();
        // Calculate zoom delta
        const delta = -event.deltaY * this.settings.zoomSensitivity;
        const newScale = this.clampZoom(this.transform.scale * (1 + delta));
        if (newScale !== this.transform.scale) {
            this.startGesture();
            // Zoom towards mouse position
            const rect = this.canvas.getBoundingClientRect();
            const centerX = event.clientX - rect.left;
            const centerY = event.clientY - rect.top;
            this.zoomToPoint(newScale, centerX, centerY);
            this.notifyTransformUpdate();
        }
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
     * Clamp zoom level to valid range
     */
    clampZoom(scale) {
        return Math.max(this.settings.minZoom, Math.min(this.settings.maxZoom, scale));
    }
    /**
     * Constrain transform to keep image visible
     */
    constrainTransform() {
        if (!this.imageBounds || !this.canvasBounds)
            return;
        // Get current canvas display size
        const rect = this.canvas.getBoundingClientRect();
        const canvasWidth = rect.width;
        const canvasHeight = rect.height;
        // Calculate the scaled image size
        const scaledWidth = this.imageBounds.width * this.transform.scale;
        const scaledHeight = this.imageBounds.height * this.transform.scale;
        // Calculate maximum translation to keep image visible
        // If image is larger than canvas, allow panning within bounds
        // If image is smaller than canvas, limit movement to keep it mostly visible
        const maxTranslateX = Math.max(0, (scaledWidth - canvasWidth) / 2);
        const maxTranslateY = Math.max(0, (scaledHeight - canvasHeight) / 2);
        // Add some padding to allow slight over-panning
        const padding = 50;
        const limitX = maxTranslateX + padding;
        const limitY = maxTranslateY + padding;
        // Constrain translation
        this.transform.translateX = Math.max(-limitX, Math.min(limitX, this.transform.translateX));
        this.transform.translateY = Math.max(-limitY, Math.min(limitY, this.transform.translateY));
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
    /**
     * Convert screen coordinates to image coordinates with current transform
     */
    screenToImage(screenX, screenY, debug = false) {
        if (debug)
            console.log('🔍 ZoomPanController.screenToImage called:', { screenX, screenY });
        if (!this.imageBounds || !this.canvasBounds) {
            if (debug)
                console.log('❌ ZoomPanController: Missing bounds', { imageBounds: this.imageBounds, canvasBounds: this.canvasBounds });
            return null;
        }
        const rect = this.canvas.getBoundingClientRect();
        const canvasX = screenX - rect.left;
        const canvasY = screenY - rect.top;
        if (debug)
            console.log('📐 ZoomPanController: Canvas rect and relative coords', {
                rect: { left: rect.left, top: rect.top, width: rect.width, height: rect.height },
                canvasX,
                canvasY,
                transform: this.transform,
                imageBounds: this.imageBounds
            });
        // Check if point is within canvas bounds
        if (canvasX < 0 || canvasY < 0 || canvasX >= rect.width || canvasY >= rect.height) {
            if (debug)
                console.log('❌ ZoomPanController: Point outside canvas bounds');
            return null;
        }
        // For default transform (no zoom/pan), use the same simple logic as CanvasManager
        const isDefaultState = Math.abs(this.transform.scale - 1.0) < 0.001 &&
            Math.abs(this.transform.translateX) < 0.001 &&
            Math.abs(this.transform.translateY) < 0.001;
        if (isDefaultState) {
            if (debug)
                console.log('✅ ZoomPanController: Using DEFAULT state logic');
            // The canvas CSS size matches the display size, and canvas internal size matches image size
            // So we can use the same simple transformation as CanvasManager
            const scale = rect.width / this.imageBounds.width;
            // Convert from display coordinates to image coordinates
            const imagePixelX = canvasX / scale;
            const imagePixelY = canvasY / scale;
            if (debug)
                console.log('📊 ZoomPanController DEFAULT calculation:', {
                    scale,
                    imagePixelX,
                    imagePixelY,
                    flooredX: Math.floor(imagePixelX),
                    flooredY: Math.floor(imagePixelY)
                });
            // Check if point is within actual image bounds
            if (imagePixelX < 0 || imagePixelY < 0 || imagePixelX >= this.imageBounds.width || imagePixelY >= this.imageBounds.height) {
                if (debug)
                    console.log('❌ ZoomPanController DEFAULT: Point outside image bounds');
                return null;
            }
            const result = {
                x: Math.floor(imagePixelX),
                y: Math.floor(imagePixelY)
            };
            if (debug)
                console.log('✅ ZoomPanController DEFAULT result:', result);
            return result;
        }
        if (debug)
            console.log('🔄 ZoomPanController: Using TRANSFORMED state logic');
        // For transformed state, we need to reverse the CSS transform to find the original coordinates
        // The key insight: the browser applies CSS transforms, but we need to work backwards to find
        // what the coordinates would be in the original (non-transformed) coordinate system
        // Step 1: Find the center of the transformed canvas
        const transformedCenterX = rect.left + rect.width / 2;
        const transformedCenterY = rect.top + rect.height / 2;
        if (debug)
            console.log('📍 ZoomPanController TRANSFORMED Step 1 - Centers:', {
                transformedCenterX,
                transformedCenterY
            });
        // Step 2: Convert screen coordinates to be relative to the transformed center
        const relativeToTransformedCenterX = screenX - transformedCenterX;
        const relativeToTransformedCenterY = screenY - transformedCenterY;
        if (debug)
            console.log('📍 ZoomPanController TRANSFORMED Step 2 - Relative to transformed center:', {
                relativeToTransformedCenterX,
                relativeToTransformedCenterY
            });
        // Step 3: Reverse the CSS transform to get original coordinates
        // The CSS transform is: translate(translateX, translateY) scale(scale)
        // To reverse: first reverse scale, then reverse translation
        // Reverse the scale
        const relativeToOriginalCenterX = relativeToTransformedCenterX / this.transform.scale;
        const relativeToOriginalCenterY = relativeToTransformedCenterY / this.transform.scale;
        // Reverse the translation (subtract because CSS transform adds)
        const originalRelativeX = relativeToOriginalCenterX - this.transform.translateX;
        const originalRelativeY = relativeToOriginalCenterY - this.transform.translateY;
        if (debug)
            console.log('📍 ZoomPanController TRANSFORMED Step 3 - Reverse transform:', {
                relativeToOriginalCenterX,
                relativeToOriginalCenterY,
                originalRelativeX,
                originalRelativeY
            });
        // Step 4: Convert back to canvas coordinates using original canvas size
        const originalCanvasWidth = rect.width / this.transform.scale;
        const originalCanvasHeight = rect.height / this.transform.scale;
        const originalCanvasX = originalRelativeX + originalCanvasWidth / 2;
        const originalCanvasY = originalRelativeY + originalCanvasHeight / 2;
        if (debug)
            console.log('📍 ZoomPanController TRANSFORMED Step 4 - Original canvas coords:', {
                originalCanvasWidth,
                originalCanvasHeight,
                originalCanvasX,
                originalCanvasY
            });
        // Step 5: Convert to image coordinates using the same logic as default state
        const scale = originalCanvasWidth / this.imageBounds.width;
        const imagePixelX = originalCanvasX / scale;
        const imagePixelY = originalCanvasY / scale;
        if (debug)
            console.log('📊 ZoomPanController TRANSFORMED Step 5 - Final calculation:', {
                scale,
                imagePixelX,
                imagePixelY,
                flooredX: Math.floor(imagePixelX),
                flooredY: Math.floor(imagePixelY)
            });
        // Check if point is within actual image bounds
        if (imagePixelX < 0 || imagePixelY < 0 || imagePixelX >= this.imageBounds.width || imagePixelY >= this.imageBounds.height) {
            if (debug)
                console.log('❌ ZoomPanController TRANSFORMED: Point outside image bounds');
            return null;
        }
        const result = {
            x: Math.floor(imagePixelX),
            y: Math.floor(imagePixelY)
        };
        if (debug)
            console.log('✅ ZoomPanController TRANSFORMED result:', result);
        return result;
    }
    /**
     * Convert image coordinates to screen coordinates with current transform
     */
    imageToScreen(imageX, imageY) {
        const rect = this.canvas.getBoundingClientRect();
        // Account for CSS transforms (same logic as screenToImage)
        let canvasWidth = rect.width;
        let canvasHeight = rect.height;
        let canvasLeft = rect.left;
        let canvasTop = rect.top;
        if (Math.abs(this.transform.scale - 1.0) > 0.001 ||
            Math.abs(this.transform.translateX) > 0.001 ||
            Math.abs(this.transform.translateY) > 0.001) {
            // Reverse the CSS transform to get original bounds
            canvasWidth = rect.width / this.transform.scale;
            canvasHeight = rect.height / this.transform.scale;
            const transformedCenterX = rect.left + rect.width / 2;
            const transformedCenterY = rect.top + rect.height / 2;
            const originalCenterX = transformedCenterX - this.transform.translateX;
            const originalCenterY = transformedCenterY - this.transform.translateY;
            canvasLeft = originalCenterX - canvasWidth / 2;
            canvasTop = originalCenterY - canvasHeight / 2;
        }
        // Calculate how the image is displayed within the original canvas
        const imageAspect = this.imageBounds.width / this.imageBounds.height;
        const canvasAspect = canvasWidth / canvasHeight;
        let displayWidth;
        let displayHeight;
        let baseScale;
        if (imageAspect > canvasAspect) {
            // Image is wider than canvas - fit to width
            displayWidth = canvasWidth;
            displayHeight = canvasWidth / imageAspect;
            baseScale = canvasWidth / this.imageBounds.width;
        }
        else {
            // Image is taller than canvas - fit to height
            displayWidth = canvasHeight * imageAspect;
            displayHeight = canvasHeight;
            baseScale = canvasHeight / this.imageBounds.height;
        }
        // Calculate image position (centered in original canvas)
        const imageOffsetX = (canvasWidth - displayWidth) / 2;
        const imageOffsetY = (canvasHeight - displayHeight) / 2;
        // Convert image pixel coordinates to display coordinates
        const displayX = imageX * baseScale;
        const displayY = imageY * baseScale;
        // Convert to center-relative coordinates for transform application
        const centerX = displayWidth / 2;
        const centerY = displayHeight / 2;
        const relativeX = displayX - centerX;
        const relativeY = displayY - centerY;
        // Apply transform
        const transformedX = relativeX * this.transform.scale + this.transform.translateX;
        const transformedY = relativeY * this.transform.scale + this.transform.translateY;
        // Convert back to image-relative coordinates
        const imageRelativeX = transformedX + centerX;
        const imageRelativeY = transformedY + centerY;
        // Convert to original canvas coordinates
        const canvasX = imageRelativeX + imageOffsetX;
        const canvasY = imageRelativeY + imageOffsetY;
        // Convert to screen coordinates
        // For transformed state, we need to apply the transform to get the final screen position
        if (Math.abs(this.transform.scale - 1.0) > 0.001 ||
            Math.abs(this.transform.translateX) > 0.001 ||
            Math.abs(this.transform.translateY) > 0.001) {
            // Apply the CSS transform to get the final screen position
            const originalScreenX = canvasLeft + canvasX;
            const originalScreenY = canvasTop + canvasY;
            // The CSS transform is applied around the center of the original canvas
            const originalCenterX = canvasLeft + canvasWidth / 2;
            const originalCenterY = canvasTop + canvasHeight / 2;
            // Apply scale and translation
            const scaledX = (originalScreenX - originalCenterX) * this.transform.scale;
            const scaledY = (originalScreenY - originalCenterY) * this.transform.scale;
            const finalScreenX = originalCenterX + scaledX + this.transform.translateX;
            const finalScreenY = originalCenterY + scaledY + this.transform.translateY;
            return { x: finalScreenX, y: finalScreenY };
        }
        else {
            // No transform, simple conversion
            const screenX = canvasLeft + canvasX;
            const screenY = canvasTop + canvasY;
            return { x: screenX, y: screenY };
        }
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
        this.canvas.removeEventListener('wheel', this.handleWheel.bind(this));
        this.canvas.removeEventListener('contextmenu', this.handleContextMenu.bind(this));
        this.activePointers.clear();
        this.eventHandler = null;
        this.imageBounds = null;
        this.canvasBounds = null;
    }
}
