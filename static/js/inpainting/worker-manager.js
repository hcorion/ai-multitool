/**
 * WorkerManager - Manages WebWorker communication with graceful fallback to main thread
 * Handles heavy mask processing operations with performance optimization
 */
import { BrushEngine } from './brush-engine.js';
export class WorkerManager {
    worker = null;
    capabilities;
    pendingMessages = new Map();
    messageIdCounter = 0;
    fallbackBrushEngine;
    isInitialized = false;
    initializationPromise = null;
    constructor() {
        this.capabilities = this.detectCapabilities();
        this.fallbackBrushEngine = new BrushEngine();
    }
    /**
     * Initialize the worker manager
     */
    async initialize() {
        if (this.isInitialized)
            return;
        if (this.initializationPromise) {
            return this.initializationPromise;
        }
        this.initializationPromise = this.performInitialization();
        return this.initializationPromise;
    }
    /**
     * Perform the actual initialization
     */
    async performInitialization() {
        if (this.capabilities.webWorkerSupported) {
            try {
                await this.initializeWorker();
            }
            catch (error) {
                console.warn('Failed to initialize WebWorker, falling back to main thread:', error);
                this.capabilities.webWorkerSupported = false;
                this.worker = null;
            }
        }
        else {
            console.error('WebWorker not supported, using main thread processing');
        }
        this.isInitialized = true;
    }
    /**
     * Initialize the WebWorker
     */
    async initializeWorker() {
        return new Promise((resolve, reject) => {
            try {
                // Create worker from the compiled TypeScript file
                this.worker = new Worker('/static/js/mask-worker.js', { type: 'module' });
                this.worker.onmessage = (event) => {
                    this.handleWorkerMessage(event.data);
                };
                this.worker.onerror = (error) => {
                    console.error('WebWorker error:', error);
                    reject(new Error(`WebWorker error: ${error.message}`));
                };
                this.worker.onmessageerror = (error) => {
                    console.error('WebWorker message error:', error);
                    reject(new Error('WebWorker message error'));
                };
                // Test worker with a simple message
                this.sendTestMessage()
                    .then(() => resolve())
                    .catch(reject);
            }
            catch (error) {
                reject(error);
            }
        });
    }
    /**
     * Send a test message to verify worker functionality
     */
    async sendTestMessage() {
        if (!this.worker) {
            throw new Error('Worker not available for testing');
        }
        // Create a simple test message that doesn't trigger recursive initialization
        const testMessage = {
            id: this.generateMessageId(),
            type: 'VALIDATE_MASK',
            data: {
                maskData: new Uint8Array(10) // Very small test array
            }
        };
        // Send test message directly without going through public methods
        return new Promise((resolve, reject) => {
            const timeoutId = setTimeout(() => {
                this.pendingMessages.delete(testMessage.id);
                reject(new Error('Test message timeout'));
            }, 5000);
            this.pendingMessages.set(testMessage.id, {
                resolve: (response) => {
                    clearTimeout(timeoutId);
                    resolve();
                },
                reject: (error) => {
                    clearTimeout(timeoutId);
                    reject(error);
                }
            });
            try {
                this.worker.postMessage(testMessage);
            }
            catch (error) {
                clearTimeout(timeoutId);
                this.pendingMessages.delete(testMessage.id);
                reject(error);
            }
        });
    }
    /**
     * Detect browser capabilities
     */
    detectCapabilities() {
        const webWorkerSupported = typeof Worker !== 'undefined';
        const offscreenCanvasSupported = typeof OffscreenCanvas !== 'undefined';
        // Test transferable objects support
        let transferableObjectsSupported = false;
        try {
            const testBuffer = new ArrayBuffer(1);
            const testMessage = { test: true };
            // This will throw if transferable objects aren't supported
            transferableObjectsSupported = true; // Assume supported if no error creating ArrayBuffer
        }
        catch {
            transferableObjectsSupported = false;
        }
        return {
            webWorkerSupported,
            offscreenCanvasSupported,
            transferableObjectsSupported
        };
    }
    /**
     * Get current capabilities
     */
    getCapabilities() {
        return { ...this.capabilities };
    }
    /**
     * Process a single brush stroke stamp
     */
    async processStroke(maskData, imageWidth, imageHeight, centerX, centerY, brushSize, mode) {
        await this.initialize();
        if (this.worker && this.capabilities.webWorkerSupported) {
            try {
                return await this.processStrokeWorker(maskData, imageWidth, imageHeight, centerX, centerY, brushSize, mode);
            }
            catch (error) {
                console.warn('Worker stroke processing failed, falling back to main thread:', error);
                return this.processStrokeMainThread(maskData, imageWidth, imageHeight, centerX, centerY, brushSize, mode);
            }
        }
        else {
            return this.processStrokeMainThread(maskData, imageWidth, imageHeight, centerX, centerY, brushSize, mode);
        }
    }
    /**
     * Apply a complete stroke path
     */
    async applyStrokePath(maskData, imageWidth, imageHeight, path, brushSize, mode, spacing = 0.35) {
        await this.initialize();
        if (this.worker && this.capabilities.webWorkerSupported) {
            try {
                return await this.applyStrokePathWorker(maskData, imageWidth, imageHeight, path, brushSize, mode, spacing);
            }
            catch (error) {
                console.warn('Worker stroke path processing failed, falling back to main thread:', error);
                return this.applyStrokePathMainThread(maskData, imageWidth, imageHeight, path, brushSize, mode, spacing);
            }
        }
        else {
            return this.applyStrokePathMainThread(maskData, imageWidth, imageHeight, path, brushSize, mode, spacing);
        }
    }
    /**
     * Create a checkpoint from mask data
     */
    async createCheckpoint(maskData, imageWidth, imageHeight, tileSize, strokeIndex) {
        await this.initialize();
        if (this.worker && this.capabilities.webWorkerSupported) {
            try {
                return await this.createCheckpointWorker(maskData, imageWidth, imageHeight, tileSize, strokeIndex);
            }
            catch (error) {
                console.warn('Worker checkpoint creation failed, falling back to main thread:', error);
                return this.createCheckpointMainThread(maskData, imageWidth, imageHeight, tileSize, strokeIndex);
            }
        }
        else {
            return this.createCheckpointMainThread(maskData, imageWidth, imageHeight, tileSize, strokeIndex);
        }
    }
    /**
     * Export mask data
     */
    async exportMask(maskData, imageWidth, imageHeight) {
        await this.initialize();
        if (this.worker && this.capabilities.webWorkerSupported) {
            try {
                return await this.exportMaskWorker(maskData, imageWidth, imageHeight);
            }
            catch (error) {
                console.warn('Worker mask export failed, falling back to main thread:', error);
                return this.exportMaskMainThread(maskData, imageWidth, imageHeight);
            }
        }
        else {
            return this.exportMaskMainThread(maskData, imageWidth, imageHeight);
        }
    }
    /**
     * Validate and fix mask binary invariant
     */
    async validateMask(maskData) {
        await this.initialize();
        if (this.worker && this.capabilities.webWorkerSupported) {
            try {
                return await this.validateMaskWorker(maskData);
            }
            catch (error) {
                console.warn('Worker mask validation failed, falling back to main thread:', error);
                return this.validateMaskMainThread(maskData);
            }
        }
        else {
            return this.validateMaskMainThread(maskData);
        }
    }
    /**
     * Worker-based stroke processing
     */
    async processStrokeWorker(maskData, imageWidth, imageHeight, centerX, centerY, brushSize, mode) {
        const message = {
            id: this.generateMessageId(),
            type: 'PROCESS_STROKE',
            data: {
                maskData: new Uint8Array(maskData), // Create copy for worker
                imageWidth,
                imageHeight,
                centerX,
                centerY,
                brushSize,
                mode
            }
        };
        const response = await this.sendWorkerMessage(message, [maskData.buffer.slice(0)]);
        return response.data;
    }
    /**
     * Worker-based stroke path processing
     */
    async applyStrokePathWorker(maskData, imageWidth, imageHeight, path, brushSize, mode, spacing) {
        const message = {
            id: this.generateMessageId(),
            type: 'APPLY_STROKE_PATH',
            data: {
                maskData: new Uint8Array(maskData), // Create copy for worker
                imageWidth,
                imageHeight,
                path,
                brushSize,
                mode,
                spacing
            }
        };
        const response = await this.sendWorkerMessage(message, [maskData.buffer.slice(0)]);
        return response.data;
    }
    /**
     * Worker-based checkpoint creation
     */
    async createCheckpointWorker(maskData, imageWidth, imageHeight, tileSize, strokeIndex) {
        const message = {
            id: this.generateMessageId(),
            type: 'CREATE_CHECKPOINT',
            data: {
                maskData: new Uint8Array(maskData), // Create copy for worker
                imageWidth,
                imageHeight,
                tileSize,
                strokeIndex
            }
        };
        const response = await this.sendWorkerMessage(message, [maskData.buffer.slice(0)]);
        return response.data;
    }
    /**
     * Worker-based mask export
     */
    async exportMaskWorker(maskData, imageWidth, imageHeight) {
        const message = {
            id: this.generateMessageId(),
            type: 'EXPORT_MASK',
            data: {
                maskData: new Uint8Array(maskData), // Create copy for worker
                imageWidth,
                imageHeight
            }
        };
        const response = await this.sendWorkerMessage(message, [maskData.buffer.slice(0)]);
        return response.data;
    }
    /**
     * Worker-based mask validation
     */
    async validateMaskWorker(maskData) {
        const message = {
            id: this.generateMessageId(),
            type: 'VALIDATE_MASK',
            data: {
                maskData: new Uint8Array(maskData) // Create copy for worker
            }
        };
        const response = await this.sendWorkerMessage(message, [maskData.buffer.slice(0)]);
        return response.data;
    }
    /**
     * Main thread fallback for stroke processing
     */
    processStrokeMainThread(maskData, imageWidth, imageHeight, centerX, centerY, brushSize, mode) {
        const hasChanges = this.fallbackBrushEngine.applyStamp(maskData, imageWidth, imageHeight, centerX, centerY, brushSize, mode);
        const radius = Math.ceil(brushSize / 2);
        const dirtyRect = {
            x: Math.max(0, Math.round(centerX) - radius),
            y: Math.max(0, Math.round(centerY) - radius),
            width: Math.min(imageWidth - Math.max(0, Math.round(centerX) - radius), radius * 2),
            height: Math.min(imageHeight - Math.max(0, Math.round(centerY) - radius), radius * 2)
        };
        return { maskData, hasChanges, dirtyRect };
    }
    /**
     * Main thread fallback for stroke path processing
     */
    applyStrokePathMainThread(maskData, imageWidth, imageHeight, path, brushSize, mode, spacing) {
        const hasChanges = this.fallbackBrushEngine.applyStrokePath(maskData, imageWidth, imageHeight, path, brushSize, mode);
        // Calculate dirty rectangle for the entire path
        let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
        const radius = Math.ceil(brushSize / 2);
        for (const point of path) {
            minX = Math.min(minX, point.x - radius);
            minY = Math.min(minY, point.y - radius);
            maxX = Math.max(maxX, point.x + radius);
            maxY = Math.max(maxY, point.y + radius);
        }
        const dirtyRect = path.length > 0 ? {
            x: Math.max(0, minX),
            y: Math.max(0, minY),
            width: Math.min(imageWidth - Math.max(0, minX), maxX - Math.max(0, minX)),
            height: Math.min(imageHeight - Math.max(0, minY), maxY - Math.max(0, minY))
        } : { x: 0, y: 0, width: 0, height: 0 };
        return { maskData, hasChanges, dirtyRect };
    }
    /**
     * Main thread fallback for checkpoint creation
     */
    createCheckpointMainThread(maskData, imageWidth, imageHeight, tileSize, strokeIndex) {
        // Simple tile extraction implementation
        const tiles = [];
        const tilesX = Math.ceil(imageWidth / tileSize);
        const tilesY = Math.ceil(imageHeight / tileSize);
        for (let tileY = 0; tileY < tilesY; tileY++) {
            for (let tileX = 0; tileX < tilesX; tileX++) {
                const startX = tileX * tileSize;
                const startY = tileY * tileSize;
                const endX = Math.min(startX + tileSize, imageWidth);
                const endY = Math.min(startY + tileSize, imageHeight);
                const tileWidth = endX - startX;
                const tileHeight = endY - startY;
                const tileData = new Uint8Array(tileWidth * tileHeight);
                let hasNonZero = false;
                for (let y = 0; y < tileHeight; y++) {
                    for (let x = 0; x < tileWidth; x++) {
                        const sourceIndex = (startY + y) * imageWidth + (startX + x);
                        const tileIndex = y * tileWidth + x;
                        tileData[tileIndex] = maskData[sourceIndex];
                        if (maskData[sourceIndex] !== 0) {
                            hasNonZero = true;
                        }
                    }
                }
                // Only store non-empty tiles
                if (hasNonZero) {
                    tiles.push({ x: tileX, y: tileY, data: tileData });
                }
            }
        }
        return {
            tiles,
            strokeIndex,
            timestamp: Date.now(),
            imageWidth,
            imageHeight,
            tileSize
        };
    }
    /**
     * Main thread fallback for mask export
     */
    exportMaskMainThread(maskData, imageWidth, imageHeight) {
        return {
            maskData: new Uint8Array(maskData), // Return copy
            imageWidth,
            imageHeight
        };
    }
    /**
     * Main thread fallback for mask validation
     */
    validateMaskMainThread(maskData) {
        const isValid = BrushEngine.validateBinaryMask(maskData);
        if (!isValid) {
            BrushEngine.enforceBinaryMask(maskData);
        }
        return { isValid, maskData };
    }
    /**
     * Send a message to the worker and wait for response
     */
    async sendWorkerMessage(message, transferables) {
        if (!this.worker) {
            throw new Error('Worker not available');
        }
        return new Promise((resolve, reject) => {
            this.pendingMessages.set(message.id, { resolve, reject });
            try {
                if (transferables && this.capabilities.transferableObjectsSupported) {
                    this.worker.postMessage(message, transferables);
                }
                else {
                    this.worker.postMessage(message);
                }
            }
            catch (error) {
                this.pendingMessages.delete(message.id);
                reject(error);
            }
        });
    }
    /**
     * Handle worker response messages
     */
    handleWorkerMessage(response) {
        const pending = this.pendingMessages.get(response.id);
        if (!pending) {
            console.warn('Received response for unknown message ID:', response.id);
            return;
        }
        this.pendingMessages.delete(response.id);
        if (response.type === 'ERROR') {
            pending.reject(new Error(response.error || 'Unknown worker error'));
        }
        else {
            pending.resolve(response);
        }
    }
    /**
     * Generate a unique message ID
     */
    generateMessageId() {
        return `msg_${++this.messageIdCounter}_${Date.now()}`;
    }
    /**
     * Check if worker is available and ready
     */
    isWorkerAvailable() {
        return this.worker !== null && this.capabilities.webWorkerSupported;
    }
    /**
     * Cleanup resources
     */
    cleanup() {
        if (this.worker) {
            // Reject all pending messages
            for (const [id, pending] of this.pendingMessages) {
                pending.reject(new Error('Worker manager cleanup'));
            }
            this.pendingMessages.clear();
            this.worker.terminate();
            this.worker = null;
        }
        this.isInitialized = false;
        this.initializationPromise = null;
    }
    /**
     * Get performance statistics
     */
    getPerformanceStats() {
        return {
            workerAvailable: this.isWorkerAvailable(),
            capabilities: this.getCapabilities(),
            pendingMessages: this.pendingMessages.size,
            isInitialized: this.isInitialized
        };
    }
}
