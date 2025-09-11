/**
 * MaskFileManager - Manages temporary mask files and cleanup
 * for the inpainting mask canvas system.
 */

export interface MaskFile {
    id: string;
    dataUrl: string;
    timestamp: number;
    metadata?: {
        width: number;
        height: number;
        totalPixels: number;
        maskedPixels: number;
        maskPercentage: number;
        isBinary: boolean;
    };
}

export class MaskFileManager {
    private temporaryFiles: Map<string, MaskFile> = new Map();
    private cleanupInterval: number | null = null;
    private maxAge: number = 5 * 60 * 1000; // 5 minutes default
    private maxFiles: number = 50; // Maximum number of temporary files

    constructor(options?: {
        maxAge?: number;
        maxFiles?: number;
        autoCleanupInterval?: number;
    }) {
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
    public storeMaskFile(dataUrl: string, metadata?: MaskFile['metadata']): string {
        const id = this.generateFileId();
        const maskFile: MaskFile = {
            id,
            dataUrl,
            timestamp: Date.now(),
            metadata
        };

        this.temporaryFiles.set(id, maskFile);

        // Cleanup old files if we exceed the limit
        this.enforceFileLimit();

        console.log(`Stored temporary mask file: ${id}`);
        return id;
    }

    /**
     * Retrieve a temporary mask file
     */
    public getMaskFile(id: string): MaskFile | null {
        const file = this.temporaryFiles.get(id);
        if (!file) {
            return null;
        }

        // Check if file has expired
        if (this.isExpired(file)) {
            this.temporaryFiles.delete(id);
            console.log(`Removed expired mask file: ${id}`);
            return null;
        }

        return file;
    }

    /**
     * Remove a specific temporary mask file
     */
    public removeMaskFile(id: string): boolean {
        const removed = this.temporaryFiles.delete(id);
        if (removed) {
            console.log(`Removed temporary mask file: ${id}`);
        }
        return removed;
    }

    /**
     * Clean up expired temporary files
     */
    public cleanupExpiredFiles(): number {
        const now = Date.now();
        let cleanedCount = 0;

        for (const [id, file] of this.temporaryFiles.entries()) {
            if (this.isExpired(file, now)) {
                this.temporaryFiles.delete(id);
                cleanedCount++;
            }
        }

        if (cleanedCount > 0) {
            console.log(`Cleaned up ${cleanedCount} expired mask files`);
        }

        return cleanedCount;
    }

    /**
     * Clean up all temporary files
     */
    public cleanupAllFiles(): number {
        const count = this.temporaryFiles.size;
        this.temporaryFiles.clear();
        
        if (count > 0) {
            console.log(`Cleaned up all ${count} temporary mask files`);
        }

        return count;
    }

    /**
     * Get statistics about temporary files
     */
    public getStatistics(): {
        totalFiles: number;
        expiredFiles: number;
        totalSizeEstimate: number;
        oldestFile?: { id: string; age: number };
        newestFile?: { id: string; age: number };
    } {
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

        const stats: any = {
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
    public startAutoCleanup(intervalMs: number = 60000): void {
        this.stopAutoCleanup();
        
        this.cleanupInterval = window.setInterval(() => {
            this.cleanupExpiredFiles();
        }, intervalMs);

        console.log(`Started automatic mask file cleanup (interval: ${intervalMs}ms)`);
    }

    /**
     * Stop automatic cleanup
     */
    public stopAutoCleanup(): void {
        if (this.cleanupInterval !== null) {
            clearInterval(this.cleanupInterval);
            this.cleanupInterval = null;
            console.log('Stopped automatic mask file cleanup');
        }
    }

    /**
     * Cleanup resources
     */
    public cleanup(): void {
        this.stopAutoCleanup();
        this.cleanupAllFiles();
    }

    /**
     * Generate a unique file ID
     */
    private generateFileId(): string {
        const timestamp = Date.now().toString(36);
        const random = Math.random().toString(36).substring(2, 8);
        return `mask_${timestamp}_${random}`;
    }

    /**
     * Check if a file has expired
     */
    private isExpired(file: MaskFile, now: number = Date.now()): boolean {
        return (now - file.timestamp) > this.maxAge;
    }

    /**
     * Enforce the maximum number of files by removing oldest files
     */
    private enforceFileLimit(): void {
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
            console.log(`Removed old mask file due to limit: ${id}`);
        }
    }
}

// Global instance for the application
export const maskFileManager = new MaskFileManager({
    maxAge: 5 * 60 * 1000, // 5 minutes
    maxFiles: 50,
    autoCleanupInterval: 60 * 1000 // 1 minute
});