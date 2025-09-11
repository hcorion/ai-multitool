/**
 * PerformanceMonitor - Tracks frame rate and performance metrics for the inpainting mask canvas
 */
export class PerformanceMonitor {
    config;
    frameTimes = [];
    renderTimes = [];
    lastFrameTime = 0;
    frameCount = 0;
    droppedFrames = 0;
    isRunning = false;
    animationFrameId = null;
    lastRenderStart = 0;
    // Frame time constants
    TARGET_FRAME_TIME_60FPS = 16.67; // 60 FPS target in milliseconds
    // Performance warning callbacks
    onPerformanceWarning = null;
    onMetricsUpdate = null;
    constructor(config = {}) {
        this.config = {
            targetFps: 60,
            sampleSize: 60, // Track last 60 frames
            enableMemoryTracking: true,
            warningThreshold: 45, // Warn if FPS drops below 45
            ...config
        };
    }
    /**
     * Start monitoring performance
     */
    start() {
        if (this.isRunning)
            return;
        this.isRunning = true;
        this.lastFrameTime = performance.now();
        this.scheduleNextFrame();
    }
    /**
     * Stop monitoring performance
     */
    stop() {
        if (!this.isRunning)
            return;
        this.isRunning = false;
        if (this.animationFrameId !== null) {
            cancelAnimationFrame(this.animationFrameId);
            this.animationFrameId = null;
        }
    }
    /**
     * Mark the start of a render operation
     */
    startRender() {
        this.lastRenderStart = performance.now();
    }
    /**
     * Mark the end of a render operation
     */
    endRender() {
        if (this.lastRenderStart > 0) {
            const renderTime = performance.now() - this.lastRenderStart;
            this.recordRenderTime(renderTime);
            this.lastRenderStart = 0;
        }
    }
    /**
     * Get current performance metrics
     */
    getMetrics() {
        const currentTime = performance.now();
        const frameTime = this.frameTimes.length > 0 ? this.frameTimes[this.frameTimes.length - 1] : 0;
        const averageFrameTime = this.frameTimes.length > 0
            ? this.frameTimes.reduce((sum, time) => sum + time, 0) / this.frameTimes.length
            : 0;
        const fps = frameTime > 0 ? 1000 / frameTime : 0;
        const averageFps = averageFrameTime > 0 ? 1000 / averageFrameTime : 0;
        const renderTime = this.renderTimes.length > 0 ? this.renderTimes[this.renderTimes.length - 1] : 0;
        const averageRenderTime = this.renderTimes.length > 0
            ? this.renderTimes.reduce((sum, time) => sum + time, 0) / this.renderTimes.length
            : 0;
        const metrics = {
            fps,
            averageFps,
            frameTime,
            averageFrameTime,
            droppedFrames: this.droppedFrames,
            totalFrames: this.frameCount,
            renderTime,
            averageRenderTime
        };
        // Add memory usage if available and enabled
        if (this.config.enableMemoryTracking && 'memory' in performance) {
            const memory = performance.memory;
            if (memory && memory.usedJSHeapSize) {
                metrics.memoryUsage = memory.usedJSHeapSize / (1024 * 1024); // MB
            }
        }
        return metrics;
    }
    /**
     * Set callback for performance warnings
     */
    setPerformanceWarningCallback(callback) {
        this.onPerformanceWarning = callback;
    }
    /**
     * Set callback for metrics updates
     */
    setMetricsUpdateCallback(callback) {
        this.onMetricsUpdate = callback;
    }
    /**
     * Reset all metrics
     */
    reset() {
        this.frameTimes = [];
        this.renderTimes = [];
        this.frameCount = 0;
        this.droppedFrames = 0;
        this.lastFrameTime = performance.now();
    }
    /**
     * Schedule the next frame for monitoring
     */
    scheduleNextFrame() {
        if (!this.isRunning)
            return;
        this.animationFrameId = requestAnimationFrame((currentTime) => {
            this.recordFrame(currentTime);
            this.scheduleNextFrame();
        });
    }
    /**
     * Record a frame timing
     */
    recordFrame(currentTime) {
        if (this.lastFrameTime > 0) {
            const frameTime = currentTime - this.lastFrameTime;
            this.recordFrameTime(frameTime);
            // Check for dropped frames (frame time significantly longer than target)
            const targetFrameTime = 1000 / this.config.targetFps; // Convert FPS to ms
            if (frameTime > targetFrameTime * 1.5) {
                this.droppedFrames++;
            }
        }
        this.lastFrameTime = currentTime;
        this.frameCount++;
        // Notify callbacks
        const metrics = this.getMetrics();
        if (this.onMetricsUpdate) {
            this.onMetricsUpdate(metrics);
        }
        // Check for performance warnings
        if (this.onPerformanceWarning && metrics.fps < this.config.warningThreshold) {
            this.onPerformanceWarning(metrics);
        }
    }
    /**
     * Record a frame time measurement
     */
    recordFrameTime(frameTime) {
        this.frameTimes.push(frameTime);
        // Keep only the last N samples
        if (this.frameTimes.length > this.config.sampleSize) {
            this.frameTimes.shift();
        }
    }
    /**
     * Record a render time measurement
     */
    recordRenderTime(renderTime) {
        this.renderTimes.push(renderTime);
        // Keep only the last N samples
        if (this.renderTimes.length > this.config.sampleSize) {
            this.renderTimes.shift();
        }
    }
    /**
     * Check if performance is currently good
     */
    isPerformanceGood() {
        const metrics = this.getMetrics();
        return metrics.fps >= this.config.warningThreshold;
    }
    /**
     * Get performance summary as a string
     */
    getPerformanceSummary() {
        const metrics = this.getMetrics();
        const memoryStr = metrics.memoryUsage ? ` | Memory: ${metrics.memoryUsage.toFixed(1)}MB` : '';
        return `FPS: ${metrics.fps.toFixed(1)} (avg: ${metrics.averageFps.toFixed(1)}) | ` +
            `Frame: ${metrics.frameTime.toFixed(1)}ms | ` +
            `Render: ${metrics.renderTime.toFixed(1)}ms | ` +
            `Dropped: ${metrics.droppedFrames}/${metrics.totalFrames}${memoryStr}`;
    }
}
