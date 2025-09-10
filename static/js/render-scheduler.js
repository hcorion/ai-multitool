/**
 * RenderScheduler - Batches rendering operations using requestAnimationFrame for 60 FPS performance
 */
export class RenderScheduler {
    pendingOperations = [];
    animationFrameId = null;
    isScheduled = false;
    lastFrameTime = 0;
    frameCount = 0;
    // Dirty rectangle tracking
    dirtyRects = [];
    fullRedrawPending = false;
    // Callbacks for different render operations
    renderCallbacks = new Map();
    // Performance tracking
    frameTimeTarget = 16.67; // ~60 FPS (16.67ms per frame)
    lastRenderTime = 0;
    constructor() {
        // Bind methods to preserve context
        this.processFrame = this.processFrame.bind(this);
    }
    /**
     * Schedule a render operation
     */
    scheduleRender(operation) {
        // Remove duplicate operations of the same type (keep the latest)
        this.pendingOperations = this.pendingOperations.filter(op => !(op.type === operation.type && op.priority === operation.priority));
        this.pendingOperations.push(operation);
        // Sort by priority (higher priority first)
        this.pendingOperations.sort((a, b) => b.priority - a.priority);
        this.scheduleFrame();
    }
    /**
     * Schedule a pointer event for batched processing
     */
    schedulePointerUpdate(data) {
        this.scheduleRender({
            type: 'pointer',
            priority: 100, // High priority for responsiveness
            data,
            timestamp: performance.now()
        });
    }
    /**
     * Schedule an overlay update with dirty rectangle
     */
    scheduleOverlayUpdate(dirtyRect) {
        if (dirtyRect) {
            this.addDirtyRect(dirtyRect);
        }
        else {
            this.fullRedrawPending = true;
        }
        this.scheduleRender({
            type: 'overlay',
            priority: 80,
            data: dirtyRect,
            timestamp: performance.now()
        });
    }
    /**
     * Schedule a cursor update
     */
    scheduleCursorUpdate(data) {
        this.scheduleRender({
            type: 'cursor',
            priority: 90, // High priority for smooth cursor
            data,
            timestamp: performance.now()
        });
    }
    /**
     * Schedule a full redraw
     */
    scheduleFullRedraw() {
        this.fullRedrawPending = true;
        this.dirtyRects = []; // Clear dirty rects since we're doing a full redraw
        this.scheduleRender({
            type: 'full',
            priority: 50,
            timestamp: performance.now()
        });
    }
    /**
     * Set a callback for a specific render operation type
     */
    setRenderCallback(type, callback) {
        this.renderCallbacks.set(type, callback);
    }
    /**
     * Add a dirty rectangle for optimized rendering
     */
    addDirtyRect(rect) {
        if (this.fullRedrawPending)
            return; // No need to track dirty rects if full redraw is pending
        // Merge with existing dirty rects if they overlap or are adjacent
        let merged = false;
        for (let i = 0; i < this.dirtyRects.length; i++) {
            const existing = this.dirtyRects[i];
            if (this.rectsOverlapOrAdjacent(existing, rect)) {
                this.dirtyRects[i] = this.mergeRects(existing, rect);
                merged = true;
                break;
            }
        }
        if (!merged) {
            this.dirtyRects.push(rect);
        }
        // If we have too many dirty rects, switch to full redraw for performance
        if (this.dirtyRects.length > 10) {
            this.fullRedrawPending = true;
            this.dirtyRects = [];
        }
    }
    /**
     * Get the combined dirty rectangle for optimized rendering
     */
    getCombinedDirtyRect() {
        if (this.fullRedrawPending || this.dirtyRects.length === 0) {
            return null; // Full redraw needed or no dirty areas
        }
        if (this.dirtyRects.length === 1) {
            return this.dirtyRects[0];
        }
        // Combine all dirty rects into one
        let combined = this.dirtyRects[0];
        for (let i = 1; i < this.dirtyRects.length; i++) {
            combined = this.mergeRects(combined, this.dirtyRects[i]);
        }
        return combined;
    }
    /**
     * Clear all pending operations and dirty rects
     */
    clear() {
        this.pendingOperations = [];
        this.dirtyRects = [];
        this.fullRedrawPending = false;
        if (this.animationFrameId !== null) {
            cancelAnimationFrame(this.animationFrameId);
            this.animationFrameId = null;
            this.isScheduled = false;
        }
    }
    /**
     * Check if any renders are pending
     */
    hasPendingRenders() {
        return this.pendingOperations.length > 0 || this.isScheduled;
    }
    /**
     * Get performance metrics
     */
    getPerformanceMetrics() {
        return {
            frameCount: this.frameCount,
            lastRenderTime: this.lastRenderTime,
            averageFrameTime: this.frameCount > 0 ? this.lastRenderTime / this.frameCount : 0
        };
    }
    /**
     * Schedule the next animation frame
     */
    scheduleFrame() {
        if (this.isScheduled)
            return;
        this.isScheduled = true;
        this.animationFrameId = requestAnimationFrame(this.processFrame);
    }
    /**
     * Process the current frame
     */
    processFrame(currentTime) {
        this.isScheduled = false;
        this.animationFrameId = null;
        const frameStartTime = performance.now();
        // Calculate frame timing
        if (this.lastFrameTime > 0) {
            const frameTime = currentTime - this.lastFrameTime;
            // Could emit frame timing events here if needed
        }
        this.lastFrameTime = currentTime;
        this.frameCount++;
        // Process operations by type and priority
        const operationsByType = new Map();
        for (const operation of this.pendingOperations) {
            if (!operationsByType.has(operation.type)) {
                operationsByType.set(operation.type, []);
            }
            operationsByType.get(operation.type).push(operation);
        }
        // Get combined dirty rectangle for optimized rendering
        const combinedDirtyRect = this.getCombinedDirtyRect();
        // Execute render callbacks
        for (const [type, operations] of operationsByType) {
            const callback = this.renderCallbacks.get(type);
            if (callback) {
                try {
                    callback(operations, combinedDirtyRect || undefined);
                }
                catch (error) {
                    console.error(`Error in render callback for type ${type}:`, error);
                }
            }
        }
        // Clear processed operations and dirty state
        this.pendingOperations = [];
        this.dirtyRects = [];
        this.fullRedrawPending = false;
        // Track render time
        this.lastRenderTime = performance.now() - frameStartTime;
        // If we took too long, log a warning
        if (this.lastRenderTime > this.frameTimeTarget) {
            console.warn(`Frame render took ${this.lastRenderTime.toFixed(2)}ms (target: ${this.frameTimeTarget.toFixed(2)}ms)`);
        }
    }
    /**
     * Check if two rectangles overlap or are adjacent
     */
    rectsOverlapOrAdjacent(rect1, rect2) {
        const padding = 1; // Consider rects adjacent if within 1 pixel
        return !(rect1.x > rect2.x + rect2.width + padding ||
            rect2.x > rect1.x + rect1.width + padding ||
            rect1.y > rect2.y + rect2.height + padding ||
            rect2.y > rect1.y + rect1.height + padding);
    }
    /**
     * Merge two rectangles into one that contains both
     */
    mergeRects(rect1, rect2) {
        const left = Math.min(rect1.x, rect2.x);
        const top = Math.min(rect1.y, rect2.y);
        const right = Math.max(rect1.x + rect1.width, rect2.x + rect2.width);
        const bottom = Math.max(rect1.y + rect1.height, rect2.y + rect2.height);
        return {
            x: left,
            y: top,
            width: right - left,
            height: bottom - top
        };
    }
    /**
     * Cleanup resources
     */
    cleanup() {
        this.clear();
        this.renderCallbacks.clear();
    }
}
