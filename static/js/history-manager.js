/**
 * HistoryManager - Manages stroke-based undo/redo functionality for the inpainting mask canvas
 * Implements deterministic replay with checkpoint system for memory efficiency
 */
export class HistoryManager {
    strokes = [];
    checkpoints = [];
    currentIndex = -1; // Index of the last applied stroke (-1 means no strokes)
    maxMemoryMB = 250; // Default memory limit
    nextStrokeId = 1;
    nextCheckpointId = 1;
    imageWidth = 0;
    imageHeight = 0;
    tileSize = 256; // 256x256 tiles
    strokesSinceLastCheckpoint = 0;
    checkpointInterval = 20; // Create checkpoint every 20 strokes
    workerManager = null;
    constructor(maxMemoryMB = 250, workerManager) {
        this.maxMemoryMB = maxMemoryMB;
        this.workerManager = workerManager || null;
    }
    /**
     * Add a new stroke to the history
     * Clears redo history when new strokes are added
     */
    addStroke(stroke, maskData) {
        // Create stroke command with unique ID
        const strokeCommand = {
            ...stroke,
            id: `stroke_${this.nextStrokeId++}`
        };
        // Clear any strokes after current index (redo history)
        if (this.currentIndex < this.strokes.length - 1) {
            this.strokes = this.strokes.slice(0, this.currentIndex + 1);
            // Also remove checkpoints that are no longer valid
            this.cleanupInvalidCheckpoints();
            this.strokesSinceLastCheckpoint = 0; // Reset counter after clearing redo
        }
        // Add the new stroke
        this.strokes.push(strokeCommand);
        this.currentIndex = this.strokes.length - 1;
        this.strokesSinceLastCheckpoint++;
        // Create periodic checkpoint if needed and mask data is available
        if (maskData && this.shouldCreatePeriodicCheckpoint()) {
            this.createTileBasedCheckpoint(maskData);
            this.strokesSinceLastCheckpoint = 0;
        }
        // Check memory usage and cleanup if needed
        this.manageMemory();
        return strokeCommand;
    }
    /**
     * Undo the last stroke
     * Returns the stroke that was undone, or null if nothing to undo
     */
    undo() {
        if (!this.canUndo()) {
            return null;
        }
        const undoneStroke = this.strokes[this.currentIndex];
        this.currentIndex--;
        return undoneStroke;
    }
    /**
     * Redo the next stroke
     * Returns the stroke that was redone, or null if nothing to redo
     */
    redo() {
        if (!this.canRedo()) {
            return null;
        }
        this.currentIndex++;
        const redoneStroke = this.strokes[this.currentIndex];
        return redoneStroke;
    }
    /**
     * Check if undo is possible
     */
    canUndo() {
        return this.currentIndex >= 0;
    }
    /**
     * Check if redo is possible
     */
    canRedo() {
        return this.currentIndex < this.strokes.length - 1;
    }
    /**
     * Get current history state
     */
    getState() {
        return {
            canUndo: this.canUndo(),
            canRedo: this.canRedo(),
            strokeCount: this.strokes.length,
            currentIndex: this.currentIndex
        };
    }
    /**
     * Get all strokes up to the current index (for replay)
     */
    getCurrentStrokes() {
        return this.strokes.slice(0, this.currentIndex + 1);
    }
    /**
     * Get all strokes (including undone ones)
     */
    getAllStrokes() {
        return [...this.strokes];
    }
    /**
     * Set image dimensions for tile-based checkpoints
     */
    setImageDimensions(width, height) {
        this.imageWidth = width;
        this.imageHeight = height;
    }
    /**
     * Set the WorkerManager for async operations
     */
    setWorkerManager(workerManager) {
        this.workerManager = workerManager;
    }
    /**
     * Create a checkpoint of the current mask state (legacy method for compatibility)
     */
    createCheckpoint(maskData) {
        // For backward compatibility, if image dimensions are not set, create a full checkpoint
        if (this.imageWidth === 0 || this.imageHeight === 0) {
            return this.createFullCheckpoint(maskData);
        }
        return this.createTileBasedCheckpoint(maskData);
    }
    /**
     * Create a tile-based checkpoint of the current mask state
     */
    createTileBasedCheckpoint(maskData) {
        if (this.imageWidth === 0 || this.imageHeight === 0) {
            throw new Error('Image dimensions must be set before creating tile-based checkpoints');
        }
        const tiles = this.extractTiles(maskData);
        const checkpoint = {
            tiles,
            timestamp: Date.now(),
            strokeIndex: this.currentIndex,
            id: `checkpoint_${this.nextCheckpointId++}`,
            imageWidth: this.imageWidth,
            imageHeight: this.imageHeight,
            tileSize: this.tileSize
        };
        this.checkpoints.push(checkpoint);
        // Keep checkpoints sorted by stroke index
        this.checkpoints.sort((a, b) => a.strokeIndex - b.strokeIndex);
        // Manage memory after adding checkpoint
        this.manageMemory();
        return checkpoint;
    }
    /**
     * Create a tile-based checkpoint using WebWorker (with fallback)
     */
    async createTileBasedCheckpointAsync(maskData) {
        if (this.imageWidth === 0 || this.imageHeight === 0) {
            throw new Error('Image dimensions must be set before creating tile-based checkpoints');
        }
        if (this.workerManager) {
            try {
                const result = await this.workerManager.createCheckpoint(maskData, this.imageWidth, this.imageHeight, this.tileSize, this.currentIndex);
                const checkpoint = {
                    tiles: result.tiles,
                    timestamp: result.timestamp,
                    strokeIndex: result.strokeIndex,
                    id: `checkpoint_${this.nextCheckpointId++}`,
                    imageWidth: result.imageWidth,
                    imageHeight: result.imageHeight,
                    tileSize: result.tileSize
                };
                this.checkpoints.push(checkpoint);
                // Keep checkpoints sorted by stroke index
                this.checkpoints.sort((a, b) => a.strokeIndex - b.strokeIndex);
                // Manage memory after adding checkpoint
                this.manageMemory();
                return checkpoint;
            }
            catch (error) {
                console.warn('Async checkpoint creation failed, falling back to sync:', error);
                return this.createTileBasedCheckpoint(maskData);
            }
        }
        else {
            return this.createTileBasedCheckpoint(maskData);
        }
    }
    /**
     * Create a full checkpoint (stores complete mask data)
     */
    createFullCheckpoint(maskData) {
        const checkpoint = {
            maskData: new Uint8Array(maskData), // Create a copy
            timestamp: Date.now(),
            strokeIndex: this.currentIndex,
            id: `checkpoint_${this.nextCheckpointId++}`,
            imageWidth: this.imageWidth,
            imageHeight: this.imageHeight,
            tileSize: this.tileSize
        };
        this.checkpoints.push(checkpoint);
        // Keep checkpoints sorted by stroke index
        this.checkpoints.sort((a, b) => a.strokeIndex - b.strokeIndex);
        // Manage memory after adding checkpoint
        this.manageMemory();
        return checkpoint;
    }
    /**
     * Get the most recent checkpoint at or before the given stroke index
     */
    getNearestCheckpoint(strokeIndex) {
        let nearestCheckpoint = null;
        for (const checkpoint of this.checkpoints) {
            if (checkpoint.strokeIndex <= strokeIndex) {
                if (!nearestCheckpoint || checkpoint.strokeIndex > nearestCheckpoint.strokeIndex) {
                    nearestCheckpoint = checkpoint;
                }
            }
        }
        return nearestCheckpoint;
    }
    /**
     * Get strokes that need to be replayed from a checkpoint to reach the target index
     */
    getStrokesFromCheckpoint(checkpoint, targetIndex) {
        const startIndex = checkpoint.strokeIndex + 1;
        const endIndex = Math.min(targetIndex + 1, this.strokes.length);
        if (startIndex >= endIndex) {
            return [];
        }
        return this.strokes.slice(startIndex, endIndex);
    }
    /**
     * Clear all history
     */
    clear() {
        this.strokes = [];
        this.checkpoints = [];
        this.currentIndex = -1;
        this.nextStrokeId = 1;
        this.nextCheckpointId = 1;
        this.strokesSinceLastCheckpoint = 0;
    }
    /**
     * Get memory usage estimate in MB
     */
    getMemoryUsageMB() {
        let totalBytes = 0;
        // Calculate stroke memory usage
        for (const stroke of this.strokes) {
            // Estimate: each point is ~16 bytes (x, y as numbers), plus metadata
            totalBytes += stroke.points.length * 16 + 64; // 64 bytes for metadata
        }
        // Calculate checkpoint memory usage
        for (const checkpoint of this.checkpoints) {
            if (checkpoint.maskData) {
                // Full checkpoint
                totalBytes += checkpoint.maskData.length + 64; // 64 bytes for metadata
            }
            else if (checkpoint.tiles) {
                // Tile-based checkpoint
                let tileBytes = 0;
                for (const tile of checkpoint.tiles) {
                    tileBytes += tile.data.length + 16; // 16 bytes for tile metadata (x, y)
                }
                totalBytes += tileBytes + 64; // 64 bytes for checkpoint metadata
            }
        }
        return totalBytes / (1024 * 1024);
    }
    /**
     * Manage memory usage by removing old checkpoints and coalescing strokes if needed
     */
    manageMemory() {
        const currentUsage = this.getMemoryUsageMB();
        if (currentUsage <= this.maxMemoryMB) {
            return;
        }
        // First, try removing old checkpoints (keep at least one)
        while (this.checkpoints.length > 1 && this.getMemoryUsageMB() > this.maxMemoryMB) {
            // Remove the oldest checkpoint
            this.checkpoints.shift();
        }
        // If still over limit, remove old strokes (but keep recent ones for undo/redo)
        const minStrokesToKeep = 50; // Keep at least 50 strokes for undo/redo
        while (this.strokes.length > minStrokesToKeep && this.getMemoryUsageMB() > this.maxMemoryMB) {
            // Remove the oldest stroke
            this.strokes.shift();
            this.currentIndex--;
            // Update checkpoint stroke indices
            for (const checkpoint of this.checkpoints) {
                checkpoint.strokeIndex--;
            }
            // Remove checkpoints that are no longer valid
            this.checkpoints = this.checkpoints.filter(cp => cp.strokeIndex >= -1);
        }
        // Ensure currentIndex is still valid
        this.currentIndex = Math.max(-1, Math.min(this.currentIndex, this.strokes.length - 1));
    }
    /**
     * Remove checkpoints that reference strokes that no longer exist
     */
    cleanupInvalidCheckpoints() {
        const maxValidStrokeIndex = this.strokes.length - 1;
        this.checkpoints = this.checkpoints.filter(cp => cp.strokeIndex <= maxValidStrokeIndex);
    }
    /**
     * Set the maximum memory limit
     */
    setMaxMemoryMB(maxMemoryMB) {
        this.maxMemoryMB = Math.max(50, maxMemoryMB); // Minimum 50MB
        this.manageMemory();
    }
    /**
     * Get the maximum memory limit
     */
    getMaxMemoryMB() {
        return this.maxMemoryMB;
    }
    /**
     * Extract tiles from mask data for efficient storage
     */
    extractTiles(maskData) {
        const tiles = [];
        const tilesX = Math.ceil(this.imageWidth / this.tileSize);
        const tilesY = Math.ceil(this.imageHeight / this.tileSize);
        for (let tileY = 0; tileY < tilesY; tileY++) {
            for (let tileX = 0; tileX < tilesX; tileX++) {
                const tileData = this.extractTile(maskData, tileX, tileY);
                // Only store non-empty tiles (optimization)
                if (this.isTileNonEmpty(tileData)) {
                    tiles.push({
                        x: tileX,
                        y: tileY,
                        data: tileData
                    });
                }
            }
        }
        return tiles;
    }
    /**
     * Extract a single tile from mask data
     */
    extractTile(maskData, tileX, tileY) {
        const startX = tileX * this.tileSize;
        const startY = tileY * this.tileSize;
        const endX = Math.min(startX + this.tileSize, this.imageWidth);
        const endY = Math.min(startY + this.tileSize, this.imageHeight);
        const tileWidth = endX - startX;
        const tileHeight = endY - startY;
        const tileData = new Uint8Array(tileWidth * tileHeight);
        for (let y = 0; y < tileHeight; y++) {
            for (let x = 0; x < tileWidth; x++) {
                const sourceIndex = (startY + y) * this.imageWidth + (startX + x);
                const tileIndex = y * tileWidth + x;
                tileData[tileIndex] = maskData[sourceIndex];
            }
        }
        return tileData;
    }
    /**
     * Check if a tile contains non-zero data
     */
    isTileNonEmpty(tileData) {
        for (let i = 0; i < tileData.length; i++) {
            if (tileData[i] !== 0) {
                return true;
            }
        }
        return false;
    }
    /**
     * Reconstruct full mask data from checkpoint tiles
     */
    reconstructMaskFromCheckpoint(checkpoint) {
        if (checkpoint.maskData) {
            // Legacy checkpoint with full mask data
            return new Uint8Array(checkpoint.maskData);
        }
        if (!checkpoint.tiles) {
            throw new Error('Checkpoint has no mask data or tiles');
        }
        // Reconstruct from tiles
        const maskData = new Uint8Array(checkpoint.imageWidth * checkpoint.imageHeight);
        maskData.fill(0); // Initialize with zeros
        for (const tile of checkpoint.tiles) {
            this.applyTileToMask(maskData, tile, checkpoint.imageWidth, checkpoint.tileSize);
        }
        return maskData;
    }
    /**
     * Apply a tile to the mask data
     */
    applyTileToMask(maskData, tile, imageWidth, tileSize) {
        const startX = tile.x * tileSize;
        const startY = tile.y * tileSize;
        const endX = Math.min(startX + tileSize, imageWidth);
        const endY = Math.min(startY + tileSize, this.imageHeight);
        const tileWidth = endX - startX;
        const tileHeight = endY - startY;
        for (let y = 0; y < tileHeight; y++) {
            for (let x = 0; x < tileWidth; x++) {
                const maskIndex = (startY + y) * imageWidth + (startX + x);
                const tileIndex = y * tileWidth + x;
                if (tileIndex < tile.data.length) {
                    maskData[maskIndex] = tile.data[tileIndex];
                }
            }
        }
    }
    /**
     * Check if a periodic checkpoint should be created
     */
    shouldCreatePeriodicCheckpoint() {
        return this.strokesSinceLastCheckpoint >= this.checkpointInterval;
    }
    /**
     * Set the checkpoint interval (number of strokes between automatic checkpoints)
     */
    setCheckpointInterval(interval) {
        this.checkpointInterval = Math.max(1, interval);
    }
    /**
     * Get the current checkpoint interval
     */
    getCheckpointInterval() {
        return this.checkpointInterval;
    }
    /**
     * Get the number of strokes since the last checkpoint
     */
    getStrokesSinceLastCheckpoint() {
        return this.strokesSinceLastCheckpoint;
    }
    /**
     * Replay strokes from a checkpoint to recreate mask state deterministically
     */
    replayFromCheckpoint(checkpoint, targetStrokeIndex, replayCallback) {
        // Start with the checkpoint mask data
        const maskData = this.reconstructMaskFromCheckpoint(checkpoint);
        // Get strokes to replay
        const strokesToReplay = this.getStrokesFromCheckpoint(checkpoint, targetStrokeIndex);
        // Replay each stroke
        for (const stroke of strokesToReplay) {
            replayCallback(stroke);
        }
        return maskData;
    }
    /**
     * Export history state for debugging
     */
    exportDebugInfo() {
        return {
            strokeCount: this.strokes.length,
            checkpointCount: this.checkpoints.length,
            currentIndex: this.currentIndex,
            memoryUsageMB: this.getMemoryUsageMB(),
            maxMemoryMB: this.maxMemoryMB,
            imageWidth: this.imageWidth,
            imageHeight: this.imageHeight,
            tileSize: this.tileSize,
            checkpointInterval: this.checkpointInterval,
            strokesSinceLastCheckpoint: this.strokesSinceLastCheckpoint,
            state: this.getState(),
            strokes: this.strokes.map(s => ({
                id: s.id,
                mode: s.mode,
                brushSize: s.brushSize,
                pointCount: s.points.length,
                timestamp: s.timestamp
            })),
            checkpoints: this.checkpoints.map(cp => ({
                id: cp.id,
                strokeIndex: cp.strokeIndex,
                timestamp: cp.timestamp,
                imageWidth: cp.imageWidth,
                imageHeight: cp.imageHeight,
                tileSize: cp.tileSize,
                maskDataSize: cp.maskData?.length || 0,
                tileCount: cp.tiles?.length || 0
            }))
        };
    }
    /**
     * Validate the integrity of the history state
     */
    validateIntegrity() {
        const errors = [];
        // Check current index bounds
        if (this.currentIndex < -1 || this.currentIndex >= this.strokes.length) {
            errors.push(`Invalid currentIndex: ${this.currentIndex}, stroke count: ${this.strokes.length}`);
        }
        // Check stroke IDs are unique
        const strokeIds = new Set();
        for (const stroke of this.strokes) {
            if (strokeIds.has(stroke.id)) {
                errors.push(`Duplicate stroke ID: ${stroke.id}`);
            }
            strokeIds.add(stroke.id);
        }
        // Check checkpoint IDs are unique
        const checkpointIds = new Set();
        for (const checkpoint of this.checkpoints) {
            if (checkpointIds.has(checkpoint.id)) {
                errors.push(`Duplicate checkpoint ID: ${checkpoint.id}`);
            }
            checkpointIds.add(checkpoint.id);
        }
        // Check checkpoint stroke indices are valid
        for (const checkpoint of this.checkpoints) {
            if (checkpoint.strokeIndex < -1 || checkpoint.strokeIndex >= this.strokes.length) {
                errors.push(`Invalid checkpoint stroke index: ${checkpoint.strokeIndex} for checkpoint ${checkpoint.id}`);
            }
        }
        // Check checkpoints are sorted by stroke index
        for (let i = 1; i < this.checkpoints.length; i++) {
            if (this.checkpoints[i].strokeIndex < this.checkpoints[i - 1].strokeIndex) {
                errors.push(`Checkpoints not sorted by stroke index at position ${i}`);
                break;
            }
        }
        return {
            isValid: errors.length === 0,
            errors
        };
    }
}
