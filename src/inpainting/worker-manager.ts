/**
 * WorkerManager - Manages WebWorker communication with graceful fallback to main thread
 * Handles heavy mask processing operations with performance optimization
 */

import { BrushEngine, BrushStroke } from './brush-engine.js';
import type { WorkerMessage, WorkerResponse } from './mask-worker.js';

export interface WorkerCapabilities {
    webWorkerSupported: boolean;
    offscreenCanvasSupported: boolean;
    transferableObjectsSupported: boolean;
}

export interface ProcessStrokeResult {
    maskData: Uint8Array;
    hasChanges: boolean;
    dirtyRect: { x: number; y: number; width: number; height: number };
}

export interface CreateCheckpointResult {
    tiles: Array<{ x: number; y: number; data: Uint8Array }>;
    strokeIndex: number;
    timestamp: number;
    imageWidth: number;
    imageHeight: number;
    tileSize: number;
}

export interface ExportMaskResult {
    maskData: Uint8Array;
    imageWidth: number;
    imageHeight: number;
}

export interface ValidateMaskResult {
    isValid: boolean;
    maskData: Uint8Array;
}

export class WorkerManager {
    private worker: Worker | null = null;
    private capabilities: WorkerCapabilities;
    private pendingMessages: Map<string, { resolve: (value: any) => void; reject: (error: Error) => void }> = new Map();
    private messageIdCounter: number = 0;
    private fallbackBrushEngine: BrushEngine;
    private isInitialized: boolean = false;
    private initializationPromise: Promise<void> | null = null;

    constructor() {
        this.capabilities = this.detectCapabilities();
        this.fallbackBrushEngine = new BrushEngine();
    }

    /**
     * Initialize the worker manager
     */
    public async initialize(): Promise<void> {
        if (this.isInitialized) return;

        if (this.initializationPromise) {
            return this.initializationPromise;
        }

        this.initializationPromise = this.performInitialization();
        return this.initializationPromise;
    }

    /**
     * Perform the actual initialization
     */
    private async performInitialization(): Promise<void> {
        if (this.capabilities.webWorkerSupported) {
            try {
                await this.initializeWorker();
                console.log('WebWorker initialized successfully');
            } catch (error) {
                console.warn('Failed to initialize WebWorker, falling back to main thread:', error);
                this.capabilities.webWorkerSupported = false;
                this.worker = null;
            }
        } else {
            console.log('WebWorker not supported, using main thread processing');
        }

        this.isInitialized = true;
    }

    /**
     * Initialize the WebWorker
     */
    private async initializeWorker(): Promise<void> {
        return new Promise((resolve, reject) => {
            try {
                // Create worker from the compiled TypeScript file
                this.worker = new Worker('/static/js/mask-worker.js', { type: 'module' });

                this.worker.onmessage = (event: MessageEvent<WorkerResponse>) => {
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

            } catch (error) {
                reject(error);
            }
        });
    }

    /**
     * Send a test message to verify worker functionality
     */
    private async sendTestMessage(): Promise<void> {
        if (!this.worker) {
            throw new Error('Worker not available for testing');
        }

        // Create a simple test message that doesn't trigger recursive initialization
        const testMessage: WorkerMessage = {
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
                this.worker!.postMessage(testMessage);
            } catch (error) {
                clearTimeout(timeoutId);
                this.pendingMessages.delete(testMessage.id);
                reject(error);
            }
        });
    }

    /**
     * Detect browser capabilities
     */
    private detectCapabilities(): WorkerCapabilities {
        const webWorkerSupported = typeof Worker !== 'undefined';
        const offscreenCanvasSupported = typeof OffscreenCanvas !== 'undefined';

        // Test transferable objects support
        let transferableObjectsSupported = false;
        try {
            const testBuffer = new ArrayBuffer(1);
            const testMessage = { test: true };
            // This will throw if transferable objects aren't supported
            transferableObjectsSupported = true; // Assume supported if no error creating ArrayBuffer
        } catch {
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
    public getCapabilities(): WorkerCapabilities {
        return { ...this.capabilities };
    }

    /**
     * Process a single brush stroke stamp
     */
    public async processStroke(
        maskData: Uint8Array,
        imageWidth: number,
        imageHeight: number,
        centerX: number,
        centerY: number,
        brushSize: number,
        mode: 'paint' | 'erase'
    ): Promise<ProcessStrokeResult> {
        await this.initialize();

        if (this.worker && this.capabilities.webWorkerSupported) {
            try {
                return await this.processStrokeWorker(maskData, imageWidth, imageHeight, centerX, centerY, brushSize, mode);
            } catch (error) {
                console.warn('Worker stroke processing failed, falling back to main thread:', error);
                return this.processStrokeMainThread(maskData, imageWidth, imageHeight, centerX, centerY, brushSize, mode);
            }
        } else {
            return this.processStrokeMainThread(maskData, imageWidth, imageHeight, centerX, centerY, brushSize, mode);
        }
    }

    /**
     * Apply a complete stroke path
     */
    public async applyStrokePath(
        maskData: Uint8Array,
        imageWidth: number,
        imageHeight: number,
        path: Array<{ x: number; y: number }>,
        brushSize: number,
        mode: 'paint' | 'erase',
        spacing: number = 0.35
    ): Promise<ProcessStrokeResult> {
        await this.initialize();

        if (this.worker && this.capabilities.webWorkerSupported) {
            try {
                return await this.applyStrokePathWorker(maskData, imageWidth, imageHeight, path, brushSize, mode, spacing);
            } catch (error) {
                console.warn('Worker stroke path processing failed, falling back to main thread:', error);
                return this.applyStrokePathMainThread(maskData, imageWidth, imageHeight, path, brushSize, mode, spacing);
            }
        } else {
            return this.applyStrokePathMainThread(maskData, imageWidth, imageHeight, path, brushSize, mode, spacing);
        }
    }

    /**
     * Create a checkpoint from mask data
     */
    public async createCheckpoint(
        maskData: Uint8Array,
        imageWidth: number,
        imageHeight: number,
        tileSize: number,
        strokeIndex: number
    ): Promise<CreateCheckpointResult> {
        await this.initialize();

        if (this.worker && this.capabilities.webWorkerSupported) {
            try {
                return await this.createCheckpointWorker(maskData, imageWidth, imageHeight, tileSize, strokeIndex);
            } catch (error) {
                console.warn('Worker checkpoint creation failed, falling back to main thread:', error);
                return this.createCheckpointMainThread(maskData, imageWidth, imageHeight, tileSize, strokeIndex);
            }
        } else {
            return this.createCheckpointMainThread(maskData, imageWidth, imageHeight, tileSize, strokeIndex);
        }
    }

    /**
     * Export mask data
     */
    public async exportMask(
        maskData: Uint8Array,
        imageWidth: number,
        imageHeight: number
    ): Promise<ExportMaskResult> {
        await this.initialize();

        if (this.worker && this.capabilities.webWorkerSupported) {
            try {
                return await this.exportMaskWorker(maskData, imageWidth, imageHeight);
            } catch (error) {
                console.warn('Worker mask export failed, falling back to main thread:', error);
                return this.exportMaskMainThread(maskData, imageWidth, imageHeight);
            }
        } else {
            return this.exportMaskMainThread(maskData, imageWidth, imageHeight);
        }
    }

    /**
     * Validate and fix mask binary invariant
     */
    public async validateMask(maskData: Uint8Array): Promise<ValidateMaskResult> {
        await this.initialize();

        if (this.worker && this.capabilities.webWorkerSupported) {
            try {
                return await this.validateMaskWorker(maskData);
            } catch (error) {
                console.warn('Worker mask validation failed, falling back to main thread:', error);
                return this.validateMaskMainThread(maskData);
            }
        } else {
            return this.validateMaskMainThread(maskData);
        }
    }

    /**
     * Worker-based stroke processing
     */
    private async processStrokeWorker(
        maskData: Uint8Array,
        imageWidth: number,
        imageHeight: number,
        centerX: number,
        centerY: number,
        brushSize: number,
        mode: 'paint' | 'erase'
    ): Promise<ProcessStrokeResult> {
        const message: WorkerMessage = {
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
    private async applyStrokePathWorker(
        maskData: Uint8Array,
        imageWidth: number,
        imageHeight: number,
        path: Array<{ x: number; y: number }>,
        brushSize: number,
        mode: 'paint' | 'erase',
        spacing: number
    ): Promise<ProcessStrokeResult> {
        const message: WorkerMessage = {
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
    private async createCheckpointWorker(
        maskData: Uint8Array,
        imageWidth: number,
        imageHeight: number,
        tileSize: number,
        strokeIndex: number
    ): Promise<CreateCheckpointResult> {
        const message: WorkerMessage = {
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
    private async exportMaskWorker(
        maskData: Uint8Array,
        imageWidth: number,
        imageHeight: number
    ): Promise<ExportMaskResult> {
        const message: WorkerMessage = {
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
    private async validateMaskWorker(maskData: Uint8Array): Promise<ValidateMaskResult> {
        const message: WorkerMessage = {
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
    private processStrokeMainThread(
        maskData: Uint8Array,
        imageWidth: number,
        imageHeight: number,
        centerX: number,
        centerY: number,
        brushSize: number,
        mode: 'paint' | 'erase'
    ): ProcessStrokeResult {
        const hasChanges = this.fallbackBrushEngine.applyStamp(
            maskData,
            imageWidth,
            imageHeight,
            centerX,
            centerY,
            brushSize,
            mode
        );

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
    private applyStrokePathMainThread(
        maskData: Uint8Array,
        imageWidth: number,
        imageHeight: number,
        path: Array<{ x: number; y: number }>,
        brushSize: number,
        mode: 'paint' | 'erase',
        spacing: number
    ): ProcessStrokeResult {
        const hasChanges = this.fallbackBrushEngine.applyStrokePath(
            maskData,
            imageWidth,
            imageHeight,
            path,
            brushSize,
            mode
        );

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
    private createCheckpointMainThread(
        maskData: Uint8Array,
        imageWidth: number,
        imageHeight: number,
        tileSize: number,
        strokeIndex: number
    ): CreateCheckpointResult {
        // Simple tile extraction implementation
        const tiles: Array<{ x: number; y: number; data: Uint8Array }> = [];
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
    private exportMaskMainThread(
        maskData: Uint8Array,
        imageWidth: number,
        imageHeight: number
    ): ExportMaskResult {
        return {
            maskData: new Uint8Array(maskData), // Return copy
            imageWidth,
            imageHeight
        };
    }

    /**
     * Main thread fallback for mask validation
     */
    private validateMaskMainThread(maskData: Uint8Array): ValidateMaskResult {
        const isValid = BrushEngine.validateBinaryMask(maskData);

        if (!isValid) {
            BrushEngine.enforceBinaryMask(maskData);
        }

        return { isValid, maskData };
    }

    /**
     * Send a message to the worker and wait for response
     */
    private async sendWorkerMessage(message: WorkerMessage, transferables?: Transferable[]): Promise<WorkerResponse> {
        if (!this.worker) {
            throw new Error('Worker not available');
        }

        return new Promise((resolve, reject) => {
            this.pendingMessages.set(message.id, { resolve, reject });

            try {
                if (transferables && this.capabilities.transferableObjectsSupported) {
                    this.worker!.postMessage(message, transferables);
                } else {
                    this.worker!.postMessage(message);
                }
            } catch (error) {
                this.pendingMessages.delete(message.id);
                reject(error);
            }
        });
    }

    /**
     * Handle worker response messages
     */
    private handleWorkerMessage(response: WorkerResponse): void {
        const pending = this.pendingMessages.get(response.id);
        if (!pending) {
            console.warn('Received response for unknown message ID:', response.id);
            return;
        }

        this.pendingMessages.delete(response.id);

        if (response.type === 'ERROR') {
            pending.reject(new Error(response.error || 'Unknown worker error'));
        } else {
            pending.resolve(response);
        }
    }

    /**
     * Generate a unique message ID
     */
    private generateMessageId(): string {
        return `msg_${++this.messageIdCounter}_${Date.now()}`;
    }

    /**
     * Check if worker is available and ready
     */
    public isWorkerAvailable(): boolean {
        return this.worker !== null && this.capabilities.webWorkerSupported;
    }

    /**
     * Cleanup resources
     */
    public cleanup(): void {
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
    public getPerformanceStats(): {
        workerAvailable: boolean;
        capabilities: WorkerCapabilities;
        pendingMessages: number;
        isInitialized: boolean;
    } {
        return {
            workerAvailable: this.isWorkerAvailable(),
            capabilities: this.getCapabilities(),
            pendingMessages: this.pendingMessages.size,
            isInitialized: this.isInitialized
        };
    }
}