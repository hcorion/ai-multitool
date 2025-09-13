/**
 * MaskFileManager - Manages temporary mask files and cleanup
 * for the inpainting mask canvas system.
 */
export class MaskFileManager {
    temporaryFiles = new Map();
    cleanupInterval = null;
    maxAge = 5 * 60 * 1000; // 5 minutes default
    maxFiles = 50; // Maximum number of temporary files
    constructor(options) {
        if (options?.maxAge) {
            this.maxAge = options.maxAge;
        }
        if (options?.maxFiles) {
            this.maxFiles = options.maxFiles;
        }
        // Start automatic cleanup if interval is specified
        if (options?.autoCleanupInterval) {
            this.startAutoCleanup(options.autoCleanupInterval);
        }
    }
    /**
     * Store a temporary mask file
     */
    storeMaskFile(dataUrl, metadata) {
        const id = this.generateFileId();
        const maskFile = {
            id,
            dataUrl,
            timestamp: Date.now(),
            metadata
        };
        this.temporaryFiles.set(id, maskFile);
        // Cleanup old files if we exceed the limit
        this.enforceFileLimit();
        return id;
    }
    /**
     * Retrieve a temporary mask file
     */
    getMaskFile(id) {
        const file = this.temporaryFiles.get(id);
        if (!file) {
            return null;
        }
        // Check if file has expired
        if (this.isExpired(file)) {
            this.temporaryFiles.delete(id);
            return null;
        }
        return file;
    }
    /**
     * Remove a specific temporary mask file
     */
    removeMaskFile(id) {
        const removed = this.temporaryFiles.delete(id);
        return removed;
    }
    /**
     * Clean up expired temporary files
     */
    cleanupExpiredFiles() {
        const now = Date.now();
        let cleanedCount = 0;
        for (const [id, file] of this.temporaryFiles.entries()) {
            if (this.isExpired(file, now)) {
                this.temporaryFiles.delete(id);
                cleanedCount++;
            }
        }
        return cleanedCount;
    }
    /**
     * Clean up all temporary files
     */
    cleanupAllFiles() {
        const count = this.temporaryFiles.size;
        this.temporaryFiles.clear();
        return count;
    }
    /**
     * Get statistics about temporary files
     */
    getStatistics() {
        const now = Date.now();
        let expiredCount = 0;
        let totalSizeEstimate = 0;
        let oldestTimestamp = Infinity;
        let newestTimestamp = 0;
        let oldestId = '';
        let newestId = '';
        for (const [id, file] of this.temporaryFiles.entries()) {
            if (this.isExpired(file, now)) {
                expiredCount++;
            }
            // Estimate size based on data URL length (rough approximation)
            totalSizeEstimate += file.dataUrl.length;
            if (file.timestamp < oldestTimestamp) {
                oldestTimestamp = file.timestamp;
                oldestId = id;
            }
            if (file.timestamp > newestTimestamp) {
                newestTimestamp = file.timestamp;
                newestId = id;
            }
        }
        const stats = {
            totalFiles: this.temporaryFiles.size,
            expiredFiles: expiredCount,
            totalSizeEstimate
        };
        if (oldestId) {
            stats.oldestFile = {
                id: oldestId,
                age: now - oldestTimestamp
            };
        }
        if (newestId) {
            stats.newestFile = {
                id: newestId,
                age: now - newestTimestamp
            };
        }
        return stats;
    }
    /**
     * Start automatic cleanup of expired files
     */
    startAutoCleanup(intervalMs = 60000) {
        this.stopAutoCleanup();
        this.cleanupInterval = window.setInterval(() => {
            this.cleanupExpiredFiles();
        }, intervalMs);
    }
    /**
     * Stop automatic cleanup
     */
    stopAutoCleanup() {
        if (this.cleanupInterval !== null) {
            clearInterval(this.cleanupInterval);
            this.cleanupInterval = null;
        }
    }
    /**
     * Cleanup resources
     */
    cleanup() {
        this.stopAutoCleanup();
        this.cleanupAllFiles();
    }
    /**
     * Generate a unique file ID
     */
    generateFileId() {
        const timestamp = Date.now().toString(36);
        const random = Math.random().toString(36).substring(2, 8);
        return `mask_${timestamp}_${random}`;
    }
    /**
     * Check if a file has expired
     */
    isExpired(file, now = Date.now()) {
        return (now - file.timestamp) > this.maxAge;
    }
    /**
     * Enforce the maximum number of files by removing oldest files
     */
    enforceFileLimit() {
        if (this.temporaryFiles.size <= this.maxFiles) {
            return;
        }
        // Sort files by timestamp (oldest first)
        const sortedFiles = Array.from(this.temporaryFiles.entries())
            .sort(([, a], [, b]) => a.timestamp - b.timestamp);
        // Remove oldest files until we're under the limit
        const filesToRemove = this.temporaryFiles.size - this.maxFiles;
        for (let i = 0; i < filesToRemove; i++) {
            const [id] = sortedFiles[i];
            this.temporaryFiles.delete(id);
        }
    }
}
// Global instance for the application
export const maskFileManager = new MaskFileManager({
    maxAge: 5 * 60 * 1000, // 5 minutes
    maxFiles: 50,
    autoCleanupInterval: 60 * 1000 // 1 minute
});
