/**
 * InpaintingMaskCanvas - A sophisticated 2D painting interface for creating binary masks
 * for image inpainting operations with full-screen popup overlay.
 */
import { CanvasManager } from './canvas-manager.js';
import { InputEngine } from './input-engine.js';
import { ZoomPanController } from './zoom-pan-controller.js';
import { HistoryManager } from './history-manager.js';
export class InpaintingMaskCanvas {
    config;
    popupElement = null;
    imageCanvas = null;
    overlayCanvas = null;
    maskAlphaCanvas = null;
    canvasManager = null;
    inputEngine = null;
    zoomPanController = null;
    historyManager = null;
    isVisible = false;
    currentBrushSize = 20;
    isZoomPanActive = false;
    coordinateTransformer = null;
    boundResizeHandler = () => this.handleResize();
    boundKeydownHandler = (e) => this.handleKeyDown(e);
    currentStroke = null;
    constructor(config) {
        this.config = config;
    }
    async show() {
        if (this.isVisible)
            return;
        this.createPopupStructure();
        this.setupCanvases();
        this.attachEventListeners();
        this.isVisible = true;
        // Load the image using CanvasManager
        try {
            await this.loadImage(this.config.imageUrl);
        }
        catch (error) {
            console.error('Failed to load image:', error);
            this.showError(`Failed to load image: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
    }
    hide() {
        if (!this.isVisible)
            return;
        this.cleanup();
        this.isVisible = false;
    }
    exportMask() {
        if (!this.canvasManager) {
            throw new Error('Canvas not initialized');
        }
        const state = this.canvasManager.getState();
        if (!state) {
            throw new Error('No image loaded');
        }
        // Create a temporary canvas for export
        const exportCanvas = document.createElement('canvas');
        exportCanvas.width = state.imageWidth;
        exportCanvas.height = state.imageHeight;
        const ctx = exportCanvas.getContext('2d');
        if (!ctx) {
            throw new Error('Failed to get export canvas context');
        }
        // Get mask image data from canvas manager
        const imageData = this.canvasManager.exportMaskImageData();
        if (!imageData) {
            throw new Error('Failed to export mask image data');
        }
        ctx.putImageData(imageData, 0, 0);
        return exportCanvas.toDataURL('image/png');
    }
    createPopupStructure() {
        // Create the main popup overlay
        this.popupElement = document.createElement('div');
        this.popupElement.className = 'inpainting-mask-popup';
        // Create the popup content container
        const contentContainer = document.createElement('div');
        contentContainer.className = 'inpainting-mask-content';
        // Create the toolbar
        const toolbar = document.createElement('div');
        toolbar.className = 'inpainting-mask-toolbar';
        // Add toolbar buttons
        const paintButton = document.createElement('button');
        paintButton.className = 'toolbar-btn paint-btn active';
        paintButton.innerHTML = '🖌️ Paint';
        paintButton.title = 'Paint mask areas';
        const eraseButton = document.createElement('button');
        eraseButton.className = 'toolbar-btn erase-btn';
        eraseButton.innerHTML = '🧽 Erase';
        eraseButton.title = 'Erase mask areas';
        const brushSizeContainer = document.createElement('div');
        brushSizeContainer.className = 'brush-size-container';
        const brushSizeLabel = document.createElement('label');
        brushSizeLabel.textContent = 'Size:';
        const brushSizeSlider = document.createElement('input');
        brushSizeSlider.type = 'range';
        brushSizeSlider.min = '1';
        brushSizeSlider.max = '200';
        brushSizeSlider.value = '20';
        brushSizeSlider.className = 'brush-size-slider';
        const brushSizeValue = document.createElement('span');
        brushSizeValue.className = 'brush-size-value';
        brushSizeValue.textContent = '20px';
        // Create drag handle for press-and-hold resize
        const brushSizeDragHandle = document.createElement('div');
        brushSizeDragHandle.className = 'brush-size-drag-handle';
        brushSizeDragHandle.innerHTML = '⟷';
        brushSizeDragHandle.title = 'Press and hold to drag resize';
        brushSizeContainer.appendChild(brushSizeLabel);
        brushSizeContainer.appendChild(brushSizeSlider);
        brushSizeContainer.appendChild(brushSizeValue);
        brushSizeContainer.appendChild(brushSizeDragHandle);
        const undoButton = document.createElement('button');
        undoButton.className = 'toolbar-btn undo-btn';
        undoButton.innerHTML = '↶ Undo';
        undoButton.title = 'Undo last stroke';
        const redoButton = document.createElement('button');
        redoButton.className = 'toolbar-btn redo-btn';
        redoButton.innerHTML = '↷ Redo';
        redoButton.title = 'Redo last undone stroke';
        const completeButton = document.createElement('button');
        completeButton.className = 'toolbar-btn complete-btn';
        completeButton.innerHTML = '✓ Complete';
        completeButton.title = 'Complete mask and proceed';
        const cancelButton = document.createElement('button');
        cancelButton.className = 'toolbar-btn cancel-btn';
        cancelButton.innerHTML = '✕ Cancel';
        cancelButton.title = 'Cancel mask editing';
        // Create zoom controls
        const zoomContainer = document.createElement('div');
        zoomContainer.className = 'zoom-controls-container';
        const zoomInButton = document.createElement('button');
        zoomInButton.className = 'toolbar-btn zoom-in-btn';
        zoomInButton.innerHTML = '🔍+';
        zoomInButton.title = 'Zoom in';
        const zoomOutButton = document.createElement('button');
        zoomOutButton.className = 'toolbar-btn zoom-out-btn';
        zoomOutButton.innerHTML = '🔍-';
        zoomOutButton.title = 'Zoom out';
        const zoomResetButton = document.createElement('button');
        zoomResetButton.className = 'toolbar-btn zoom-reset-btn';
        zoomResetButton.innerHTML = '🔍⌂';
        zoomResetButton.title = 'Reset zoom (Ctrl+wheel to zoom)';
        zoomContainer.appendChild(zoomInButton);
        zoomContainer.appendChild(zoomOutButton);
        zoomContainer.appendChild(zoomResetButton);
        // Add all buttons to toolbar
        toolbar.appendChild(paintButton);
        toolbar.appendChild(eraseButton);
        toolbar.appendChild(brushSizeContainer);
        toolbar.appendChild(zoomContainer);
        toolbar.appendChild(undoButton);
        toolbar.appendChild(redoButton);
        toolbar.appendChild(completeButton);
        toolbar.appendChild(cancelButton);
        // Create the canvas container
        const canvasContainer = document.createElement('div');
        canvasContainer.className = 'inpainting-mask-canvas-container';
        // Create the three canvases
        this.imageCanvas = document.createElement('canvas');
        this.imageCanvas.className = 'inpainting-canvas image-canvas';
        this.overlayCanvas = document.createElement('canvas');
        this.overlayCanvas.className = 'inpainting-canvas overlay-canvas';
        // Create OffscreenCanvas for mask alpha (fallback to regular canvas if not supported)
        try {
            this.maskAlphaCanvas = new OffscreenCanvas(1, 1);
        }
        catch (e) {
            // Fallback for browsers that don't support OffscreenCanvas
            const fallbackCanvas = document.createElement('canvas');
            fallbackCanvas.style.display = 'none';
            this.maskAlphaCanvas = fallbackCanvas;
        }
        canvasContainer.appendChild(this.imageCanvas);
        canvasContainer.appendChild(this.overlayCanvas);
        // Assemble the popup structure
        contentContainer.appendChild(toolbar);
        contentContainer.appendChild(canvasContainer);
        this.popupElement.appendChild(contentContainer);
        // Add to container
        this.config.containerElement.appendChild(this.popupElement);
    }
    setupCanvases() {
        if (!this.imageCanvas || !this.overlayCanvas || !this.maskAlphaCanvas) {
            throw new Error('Canvases not created');
        }
        // Create canvas manager
        this.canvasManager = new CanvasManager(this.imageCanvas, this.overlayCanvas, this.maskAlphaCanvas);
        // Create history manager
        this.historyManager = new HistoryManager(250); // 250MB memory limit
        // Create input engine for the overlay canvas (drawing surface)
        console.log('Creating input engine for overlay canvas:', this.overlayCanvas);
        this.inputEngine = new InputEngine(this.overlayCanvas, {
            enableDrawing: true,
            preventScrolling: true,
            capturePointer: true
        });
        console.log('Input engine created:', this.inputEngine);
        // Set up input event handler
        this.inputEngine.setEventHandler(this.handleInputEvent.bind(this));
        console.log('Input event handler set');
        // Set up coordinate transformer for cursor preview
        // IMPORTANT: This must use the SAME logic as the actual drawing system
        const coordinateTransformer = (clientX, clientY) => this.zoomPanController?.screenToImage(clientX, clientY, false) ?? null;
        // Add getTransform method to access zoom scale
        coordinateTransformer.getTransform = () => ({
            ...this.zoomPanController.getTransform(),
            baseScale: this.canvasManager.getBaseScale()
        });
        coordinateTransformer.imageToScreen = (ix, iy) => this.zoomPanController.imageToScreen(ix, iy);
        this.coordinateTransformer = coordinateTransformer;
        this.inputEngine.setCoordinateTransformer(coordinateTransformer);
        // Create zoom/pan controller for the overlay canvas
        this.zoomPanController = new ZoomPanController(this.overlayCanvas, {
            minZoom: 0.1,
            maxZoom: 10.0,
            zoomSensitivity: 0.002,
            panSensitivity: 1.0,
            enablePinchZoom: true,
            enableWheelZoom: true,
            enablePan: true,
            wheelZoomModifier: 'none' // Remove Ctrl requirement for better UX
        });
        // Set up zoom/pan event handler
        this.zoomPanController.setEventHandler(this.handleZoomPanEvent);
        // Set up performance monitoring integration
        this.setupPerformanceIntegration();
        // Debug access (development only)
        window.inpaint = {
            z: this.zoomPanController,
            cm: this.canvasManager,
            overlay: this.overlayCanvas,
            image: this.imageCanvas,
            perf: this.canvasManager.getPerformanceMonitor(),
            scheduler: this.canvasManager.getRenderScheduler()
        };
        console.log('Zoom/pan controller created');
        // Add additional event listeners to the container for better UX
        // This allows zoom/pan to work anywhere in the container, not just on the canvas
        this.setupContainerEventListeners();
        // Set up resize handler
        window.addEventListener('resize', this.boundResizeHandler);
    }
    setupContainerEventListeners() {
        const canvasContainer = this.overlayCanvas?.parentElement;
        if (!canvasContainer || !this.overlayCanvas)
            return;
        // Prevent browser zoom/scroll when interacting with the container
        canvasContainer.addEventListener('wheel', (event) => {
            // Always prevent default to stop browser zoom
            event.preventDefault();
            // Forward the event to the ZoomPanController if it's over the canvas area
            // or if the user is already in a zoom/pan gesture
            if (!this.overlayCanvas)
                return;
            const rect = this.overlayCanvas.getBoundingClientRect();
            const isOverCanvas = (event.clientX >= rect.left && event.clientX <= rect.right &&
                event.clientY >= rect.top && event.clientY <= rect.bottom);
            if (isOverCanvas || this.isZoomPanActive) {
                // Create a synthetic wheel event on the canvas
                const syntheticEvent = new WheelEvent('wheel', {
                    deltaX: event.deltaX,
                    deltaY: event.deltaY,
                    deltaZ: event.deltaZ,
                    deltaMode: event.deltaMode,
                    clientX: event.clientX,
                    clientY: event.clientY,
                    ctrlKey: event.ctrlKey,
                    shiftKey: event.shiftKey,
                    altKey: event.altKey,
                    metaKey: event.metaKey,
                    bubbles: false,
                    cancelable: true
                });
                this.overlayCanvas.dispatchEvent(syntheticEvent);
            }
        }, { passive: false });
        // Handle touch events for mobile pan/zoom
        canvasContainer.addEventListener('touchstart', (event) => {
            // Prevent default touch behavior that might cause browser zoom/scroll
            if (event.touches.length > 1) {
                event.preventDefault();
            }
        }, { passive: false });
        canvasContainer.addEventListener('touchmove', (event) => {
            // Prevent default for multi-touch (pinch zoom) and when already in gesture
            if (event.touches.length > 1 || this.isZoomPanActive) {
                event.preventDefault();
            }
        }, { passive: false });
    }
    attachEventListeners() {
        if (!this.popupElement)
            return;
        // Toolbar event listeners
        const paintBtn = this.popupElement.querySelector('.paint-btn');
        const eraseBtn = this.popupElement.querySelector('.erase-btn');
        const brushSizeSlider = this.popupElement.querySelector('.brush-size-slider');
        const brushSizeValue = this.popupElement.querySelector('.brush-size-value');
        const undoBtn = this.popupElement.querySelector('.undo-btn');
        const redoBtn = this.popupElement.querySelector('.redo-btn');
        const completeBtn = this.popupElement.querySelector('.complete-btn');
        const cancelBtn = this.popupElement.querySelector('.cancel-btn');
        const zoomInBtn = this.popupElement.querySelector('.zoom-in-btn');
        const zoomOutBtn = this.popupElement.querySelector('.zoom-out-btn');
        const zoomResetBtn = this.popupElement.querySelector('.zoom-reset-btn');
        // Tool selection
        paintBtn?.addEventListener('click', () => this.setTool('paint'));
        eraseBtn?.addEventListener('click', () => this.setTool('erase'));
        // Brush size control
        brushSizeSlider?.addEventListener('input', (e) => {
            const size = e.target.value;
            brushSizeValue.textContent = `${size}px`;
            this.setBrushSize(parseInt(size));
        });
        // Press-and-hold drag resize functionality
        const brushSizeDragHandle = this.popupElement.querySelector('.brush-size-drag-handle');
        if (brushSizeDragHandle && brushSizeSlider && brushSizeValue) {
            this.setupBrushSizeDragResize(brushSizeDragHandle, brushSizeSlider, brushSizeValue);
        }
        // History controls
        undoBtn?.addEventListener('click', () => this.undo());
        redoBtn?.addEventListener('click', () => this.redo());
        // Zoom controls
        zoomInBtn?.addEventListener('click', () => this.zoomIn());
        zoomOutBtn?.addEventListener('click', () => this.zoomOut());
        zoomResetBtn?.addEventListener('click', () => this.zoomReset());
        // Action buttons
        completeBtn?.addEventListener('click', () => this.completeMask());
        cancelBtn?.addEventListener('click', () => this.cancelMask());
        // Prevent page scroll when popup is open
        document.body.style.overflow = 'hidden';
        // Close on escape key
        document.addEventListener('keydown', this.boundKeydownHandler);
    }
    async loadImage(imageUrl) {
        if (!this.canvasManager) {
            throw new Error('Canvas manager not initialized');
        }
        try {
            await this.canvasManager.loadImage(imageUrl);
            this.hideError();
            // Set up zoom/pan controller bounds and history manager dimensions
            if (this.zoomPanController && this.canvasManager) {
                const state = this.canvasManager.getState();
                if (state) {
                    this.zoomPanController.setImageBounds(state.imageWidth, state.imageHeight);
                    // Set image dimensions for tile-based checkpoints
                    if (this.historyManager) {
                        this.historyManager.setImageDimensions(state.imageWidth, state.imageHeight);
                    }
                    // Use the actual canvas container size, not the display size
                    const canvasContainer = this.overlayCanvas?.parentElement;
                    if (canvasContainer) {
                        const containerRect = canvasContainer.getBoundingClientRect();
                        this.zoomPanController.setCanvasBounds(containerRect.width, containerRect.height);
                    }
                    else {
                        // Fallback to display size if container not found
                        this.zoomPanController.setCanvasBounds(state.displayWidth, state.displayHeight);
                    }
                    this.zoomPanController.enable();
                    console.log('Zoom/pan controller configured and enabled');
                }
            }
            // Enable input handling after image is loaded
            if (this.inputEngine) {
                console.log('Enabling input engine');
                this.inputEngine.enable();
                this.inputEngine.updateCursorSize(this.currentBrushSize);
                this.inputEngine.updateCursorMode('paint'); // Default to paint mode
                console.log('Input engine enabled and configured');
            }
            else {
                console.error('Input engine not found when trying to enable');
            }
            // Initialize history button states
            this.updateHistoryButtons();
        }
        catch (error) {
            throw error;
        }
    }
    setTool(tool) {
        if (!this.popupElement)
            return;
        const paintBtn = this.popupElement.querySelector('.paint-btn');
        const eraseBtn = this.popupElement.querySelector('.erase-btn');
        paintBtn?.classList.toggle('active', tool === 'paint');
        eraseBtn?.classList.toggle('active', tool === 'erase');
        // Update brush engine mode
        if (this.canvasManager) {
            this.canvasManager.getBrushEngine().updateSettings({ mode: tool });
        }
        // Update cursor preview
        if (this.inputEngine) {
            this.inputEngine.updateCursorMode(tool);
        }
    }
    setBrushSize(size) {
        this.currentBrushSize = size;
        if (this.canvasManager) {
            this.canvasManager.getBrushEngine().updateSettings({ size });
        }
        if (this.inputEngine) {
            this.inputEngine.updateCursorSize(size);
        }
    }
    adjustBrushSize(delta) {
        const newSize = Math.max(1, Math.min(200, this.currentBrushSize + delta));
        this.setBrushSize(newSize);
        // Update UI elements
        if (this.popupElement) {
            const slider = this.popupElement.querySelector('.brush-size-slider');
            const valueDisplay = this.popupElement.querySelector('.brush-size-value');
            if (slider) {
                slider.value = newSize.toString();
            }
            if (valueDisplay) {
                valueDisplay.textContent = `${newSize}px`;
            }
        }
    }
    setupBrushSizeDragResize(dragHandle, slider, valueDisplay) {
        let isDragging = false;
        let startX = 0;
        let startSize = 0;
        let dragTimeout = null;
        const startDrag = (clientX) => {
            isDragging = true;
            startX = clientX;
            startSize = this.currentBrushSize;
            dragHandle.classList.add('dragging');
            document.body.style.cursor = 'ew-resize';
            // Prevent text selection during drag
            document.body.style.userSelect = 'none';
        };
        const updateDrag = (clientX) => {
            if (!isDragging)
                return;
            const deltaX = clientX - startX;
            const sensitivity = 0.5; // Pixels per pixel of mouse movement
            const newSize = Math.max(1, Math.min(200, startSize + deltaX * sensitivity));
            // Update slider and display
            slider.value = newSize.toString();
            valueDisplay.textContent = `${Math.round(newSize)}px`;
            this.setBrushSize(Math.round(newSize));
        };
        const endDrag = () => {
            if (!isDragging)
                return;
            isDragging = false;
            dragHandle.classList.remove('dragging');
            document.body.style.cursor = '';
            document.body.style.userSelect = '';
        };
        // Mouse events for drag handle
        dragHandle.addEventListener('mousedown', (e) => {
            e.preventDefault();
            // Start drag immediately on mouse down
            startDrag(e.clientX);
            // Add global mouse move and up listeners
            const handleMouseMove = (e) => updateDrag(e.clientX);
            const handleMouseUp = () => {
                endDrag();
                document.removeEventListener('mousemove', handleMouseMove);
                document.removeEventListener('mouseup', handleMouseUp);
            };
            document.addEventListener('mousemove', handleMouseMove);
            document.addEventListener('mouseup', handleMouseUp);
        });
        // Touch events for drag handle
        dragHandle.addEventListener('touchstart', (e) => {
            e.preventDefault();
            if (e.touches.length === 1) {
                startDrag(e.touches[0].clientX);
                const handleTouchMove = (e) => {
                    e.preventDefault();
                    if (e.touches.length === 1) {
                        updateDrag(e.touches[0].clientX);
                    }
                };
                const handleTouchEnd = () => {
                    endDrag();
                    document.removeEventListener('touchmove', handleTouchMove);
                    document.removeEventListener('touchend', handleTouchEnd);
                    document.removeEventListener('touchcancel', handleTouchEnd);
                };
                document.addEventListener('touchmove', handleTouchMove, { passive: false });
                document.addEventListener('touchend', handleTouchEnd);
                document.addEventListener('touchcancel', handleTouchEnd);
            }
        });
        // Prevent context menu on drag handle
        dragHandle.addEventListener('contextmenu', (e) => e.preventDefault());
    }
    undo() {
        if (!this.historyManager || !this.canvasManager) {
            console.warn('History manager or canvas manager not initialized');
            return;
        }
        const undoneStroke = this.historyManager.undo();
        if (undoneStroke) {
            console.log('Undoing stroke:', undoneStroke.id);
            this.replayHistoryToCurrentState();
            this.updateHistoryButtons();
        }
        else {
            console.log('Nothing to undo');
        }
    }
    redo() {
        if (!this.historyManager || !this.canvasManager) {
            console.warn('History manager or canvas manager not initialized');
            return;
        }
        const redoneStroke = this.historyManager.redo();
        if (redoneStroke) {
            console.log('Redoing stroke:', redoneStroke.id);
            this.replayHistoryToCurrentState();
            this.updateHistoryButtons();
        }
        else {
            console.log('Nothing to redo');
        }
    }
    zoomIn() {
        if (this.zoomPanController) {
            const currentTransform = this.zoomPanController.getTransform();
            const newScale = Math.min(10.0, currentTransform.scale * 1.5);
            this.zoomPanController.setTransform({ scale: newScale });
        }
    }
    zoomOut() {
        if (this.zoomPanController) {
            const currentTransform = this.zoomPanController.getTransform();
            const newScale = Math.max(0.1, currentTransform.scale / 1.5);
            this.zoomPanController.setTransform({ scale: newScale });
        }
    }
    zoomReset() {
        if (this.zoomPanController) {
            this.zoomPanController.resetTransform();
        }
    }
    completeMask() {
        try {
            const maskDataUrl = this.exportMask();
            this.config.onMaskComplete(maskDataUrl);
            this.hide();
        }
        catch (error) {
            console.error('Failed to complete mask:', error);
        }
    }
    cancelMask() {
        this.config.onCancel();
        this.hide();
    }
    handleKeyDown(event) {
        if (!this.isVisible)
            return;
        switch (event.key) {
            case 'Escape':
                this.cancelMask();
                break;
            case 'z':
                if (event.ctrlKey || event.metaKey) {
                    if (event.shiftKey) {
                        this.redo();
                    }
                    else {
                        this.undo();
                    }
                    event.preventDefault();
                }
                break;
            case 'p':
            case 'P':
                // Switch to paint tool
                this.setTool('paint');
                event.preventDefault();
                break;
            case 'e':
            case 'E':
                // Switch to erase tool
                this.setTool('erase');
                event.preventDefault();
                break;
            case '[':
                // Decrease brush size
                this.adjustBrushSize(-5);
                event.preventDefault();
                break;
            case ']':
                // Increase brush size
                this.adjustBrushSize(5);
                event.preventDefault();
                break;
            case '=':
            case '+':
                // Zoom in
                if (event.ctrlKey || event.metaKey) {
                    this.zoomIn();
                    event.preventDefault();
                }
                break;
            case '-':
            case '_':
                // Zoom out
                if (event.ctrlKey || event.metaKey) {
                    this.zoomOut();
                    event.preventDefault();
                }
                break;
            case '0':
                // Reset zoom
                if (event.ctrlKey || event.metaKey) {
                    this.zoomReset();
                    event.preventDefault();
                }
                break;
        }
    }
    handleResize() {
        if (this.canvasManager) {
            this.canvasManager.handleResize();
            // Update zoom/pan controller bounds after resize
            if (this.zoomPanController) {
                const canvasContainer = this.overlayCanvas?.parentElement;
                if (canvasContainer) {
                    const containerRect = canvasContainer.getBoundingClientRect();
                    this.zoomPanController.setCanvasBounds(containerRect.width, containerRect.height);
                }
                else {
                    // Fallback to display size
                    const state = this.canvasManager.getState();
                    if (state) {
                        this.zoomPanController.setCanvasBounds(state.displayWidth, state.displayHeight);
                    }
                }
            }
        }
    }
    /**
     * Handle input events from the InputEngine
     */
    handleInputEvent = (evt) => {
        if (!this.canvasManager || this.isZoomPanActive)
            return;
        const cx = evt.clientX ?? evt.screenX;
        const cy = evt.clientY ?? evt.screenY;
        const debugNow = evt.type === 'start' || evt.type === 'end';
        const img = this.zoomPanController.screenToImage(cx, cy, debugNow);
        if (!img)
            return;
        // Optional: log the exact on-screen stamp location
        if (debugNow) {
            const back = this.zoomPanController.imageToScreen(img.x, img.y);
            console.log('hit-test delta(px):', {
                dx: Math.round(back.x - cx),
                dy: Math.round(back.y - cy),
                transform: this.zoomPanController.getTransform()
            });
        }
        const brush = this.canvasManager.getBrushEngine();
        const settings = brush.getSettings();
        if (evt.type === 'start') {
            this.currentStroke = this.canvasManager.startBrushStroke(img.x, img.y, this.currentBrushSize, settings.mode);
        }
        else if (evt.type === 'move') {
            this.canvasManager.continueBrushStroke(img.x, img.y);
        }
        else if (evt.type === 'end') {
            const completedStroke = this.canvasManager.endBrushStroke();
            if (completedStroke && this.historyManager) {
                // Get current mask data for periodic checkpoints
                const state = this.canvasManager.getState();
                // Add the completed stroke to history (with mask data for periodic checkpoints)
                const strokeCommand = this.historyManager.addStroke(completedStroke, state?.maskData);
                console.log('Added stroke to history:', strokeCommand.id);
                // Update history button states
                this.updateHistoryButtons();
                // Create checkpoint periodically for better performance (legacy - now handled automatically)
                if (state && this.historyManager.getState().strokeCount % 10 === 0) {
                    this.historyManager.createCheckpoint(state.maskData);
                    console.log(`Created checkpoint after ${this.historyManager.getState().strokeCount} strokes`);
                }
            }
            this.currentStroke = null;
        }
    };
    /**
     * Set up performance monitoring integration
     */
    setupPerformanceIntegration() {
        if (!this.canvasManager)
            return;
        const performanceMonitor = this.canvasManager.getPerformanceMonitor();
        // Set up performance warning handler
        performanceMonitor.setPerformanceWarningCallback((metrics) => {
            console.warn('Inpainting canvas performance warning:', {
                fps: metrics.fps.toFixed(1),
                averageFps: metrics.averageFps.toFixed(1),
                droppedFrames: metrics.droppedFrames,
                renderTime: metrics.renderTime.toFixed(2) + 'ms'
            });
            // Could show a performance warning to the user here
            // this.showPerformanceWarning(metrics);
        });
        // Set up periodic performance logging (debug mode)
        if (console.debug) {
            performanceMonitor.setMetricsUpdateCallback((metrics) => {
                if (metrics.totalFrames % 300 === 0) { // Every 5 seconds at 60 FPS
                    console.debug('Canvas performance:', performanceMonitor.getPerformanceSummary());
                }
            });
        }
    }
    /**
     * Handle zoom/pan events from the ZoomPanController
     */
    handleZoomPanEvent = {
        onTransformStart: () => {
            console.log('Zoom/pan gesture started - disabling drawing');
            this.isZoomPanActive = true;
            // Disable drawing in input engine
            if (this.inputEngine) {
                this.inputEngine.updateSettings({ enableDrawing: false });
            }
        },
        onTransformUpdate: (transform) => {
            console.log('Zoom/pan transform updated:', transform);
            // Apply transform to canvases
            if (this.canvasManager) {
                this.canvasManager.applyTransform(transform);
            }
            // Update cursor size to account for zoom level
            if (this.inputEngine) {
                this.inputEngine.updateCursorSize(this.currentBrushSize);
            }
        },
        onTransformEnd: () => {
            console.log('Zoom/pan gesture ended - re-enabling drawing');
            this.isZoomPanActive = false;
            // Re-enable drawing in input engine
            if (this.inputEngine) {
                this.inputEngine.updateSettings({ enableDrawing: true });
            }
        }
    };
    showError(message) {
        if (!this.popupElement)
            return;
        const canvasContainer = this.popupElement.querySelector('.inpainting-mask-canvas-container');
        if (!canvasContainer)
            return;
        // Create or update error message
        let errorElement = canvasContainer.querySelector('.error-message');
        if (!errorElement) {
            errorElement = document.createElement('div');
            errorElement.className = 'error-message';
            errorElement.style.cssText = `
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                background-color: #ff4444;
                color: white;
                padding: 20px;
                border-radius: 8px;
                text-align: center;
                max-width: 400px;
                z-index: 10;
            `;
            canvasContainer.appendChild(errorElement);
        }
        errorElement.innerHTML = `
            <div style="font-size: 18px; margin-bottom: 10px;">⚠️ Error</div>
            <div>${message}</div>
            <button onclick="this.parentElement.remove()" style="
                margin-top: 15px;
                padding: 8px 16px;
                background-color: rgba(255,255,255,0.2);
                border: 1px solid rgba(255,255,255,0.3);
                color: white;
                border-radius: 4px;
                cursor: pointer;
            ">Dismiss</button>
        `;
    }
    hideError() {
        if (!this.popupElement)
            return;
        const errorElement = this.popupElement.querySelector('.error-message');
        if (errorElement) {
            errorElement.remove();
        }
    }
    /**
     * Replay history from the nearest checkpoint to the current state
     */
    replayHistoryToCurrentState() {
        if (!this.historyManager || !this.canvasManager)
            return;
        const state = this.canvasManager.getState();
        if (!state)
            return;
        const currentStrokes = this.historyManager.getCurrentStrokes();
        const historyState = this.historyManager.getState();
        // Find the nearest checkpoint
        const nearestCheckpoint = this.historyManager.getNearestCheckpoint(historyState.currentIndex);
        if (nearestCheckpoint) {
            // Restore from checkpoint
            console.log(`Restoring from checkpoint at stroke ${nearestCheckpoint.strokeIndex}`);
            const reconstructedMask = this.historyManager.reconstructMaskFromCheckpoint(nearestCheckpoint);
            state.maskData.set(reconstructedMask);
            // Replay strokes from checkpoint to current state
            const strokesToReplay = this.historyManager.getStrokesFromCheckpoint(nearestCheckpoint, historyState.currentIndex);
            console.log(`Replaying ${strokesToReplay.length} strokes from checkpoint`);
            for (const stroke of strokesToReplay) {
                this.canvasManager.applyBrushStroke(stroke);
            }
        }
        else {
            // No checkpoint available, replay all strokes from empty mask
            console.log(`No checkpoint found, replaying all ${currentStrokes.length} strokes from empty mask`);
            state.maskData.fill(0); // Clear mask
            for (const stroke of currentStrokes) {
                this.canvasManager.applyBrushStroke(stroke);
            }
        }
        // Update the overlay to reflect the new state
        this.canvasManager.updateMaskOverlay();
        // Create a new checkpoint periodically for performance
        if (currentStrokes.length > 0 && currentStrokes.length % 20 === 0) {
            this.historyManager.createCheckpoint(state.maskData);
            console.log(`Created checkpoint at stroke ${historyState.currentIndex}`);
        }
    }
    /**
     * Update the enabled/disabled state of history buttons
     */
    updateHistoryButtons() {
        if (!this.historyManager || !this.popupElement)
            return;
        const historyState = this.historyManager.getState();
        const undoBtn = this.popupElement.querySelector('.undo-btn');
        const redoBtn = this.popupElement.querySelector('.redo-btn');
        if (undoBtn) {
            undoBtn.disabled = !historyState.canUndo;
            undoBtn.title = historyState.canUndo ? 'Undo last stroke' : 'Nothing to undo';
        }
        if (redoBtn) {
            redoBtn.disabled = !historyState.canRedo;
            redoBtn.title = historyState.canRedo ? 'Redo last undone stroke' : 'Nothing to redo';
        }
    }
    cleanup() {
        // Cleanup history manager
        if (this.historyManager) {
            this.historyManager.clear();
            this.historyManager = null;
        }
        // Cleanup input engine
        if (this.inputEngine) {
            this.inputEngine.setCoordinateTransformer(null);
            this.inputEngine.cleanup();
            this.inputEngine = null;
        }
        // Cleanup zoom/pan controller
        if (this.zoomPanController) {
            this.zoomPanController.cleanup();
            this.zoomPanController = null;
        }
        if (this.popupElement) {
            this.popupElement.remove();
            this.popupElement = null;
        }
        // Restore page scroll
        document.body.style.overflow = '';
        // Remove event listeners
        window.removeEventListener('resize', this.boundResizeHandler);
        document.removeEventListener('keydown', this.boundKeydownHandler);
        // Cleanup canvas manager
        if (this.canvasManager) {
            this.canvasManager.cleanup();
            this.canvasManager = null;
        }
        // Reset references
        this.imageCanvas = null;
        this.overlayCanvas = null;
        this.maskAlphaCanvas = null;
    }
}
