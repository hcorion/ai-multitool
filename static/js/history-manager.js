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
    constructor(maxMemoryMB = 250) {
        this.maxMemoryMB = maxMemoryMB;
    }
    /**
     * Add a new stroke to the history
     * Clears redo history when new strokes are added
     */
    addStroke(stroke) {
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
        }
        // Add the new stroke
        this.strokes.push(strokeCommand);
        this.currentIndex = this.strokes.length - 1;
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
     * Create a checkpoint of the current mask state
     */
    createCheckpoint(maskData) {
        const checkpoint = {
            maskData: new Uint8Array(maskData), // Create a copy
            timestamp: Date.now(),
            strokeIndex: this.currentIndex,
            id: `checkpoint_${this.nextCheckpointId++}`
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
            totalBytes += checkpoint.maskData.length + 64; // 64 bytes for metadata
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
     * Export history state for debugging
     */
    exportDebugInfo() {
        return {
            strokeCount: this.strokes.length,
            checkpointCount: this.checkpoints.length,
            currentIndex: this.currentIndex,
            memoryUsageMB: this.getMemoryUsageMB(),
            maxMemoryMB: this.maxMemoryMB,
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
                maskDataSize: cp.maskData.length
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
