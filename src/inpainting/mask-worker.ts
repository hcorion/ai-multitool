/**
 * MaskWorker - WebWorker for heavy mask processing operations
 * Handles stroke processing, checkpoint creation, and mask operations off the main thread
 */

// Worker message types
export interface WorkerMessage {
    id: string;
    type: 'PROCESS_STROKE' | 'CREATE_CHECKPOINT' | 'EXPORT_MASK' | 'APPLY_STROKE_PATH' | 'VALIDATE_MASK';
    data: any;
}

export interface WorkerResponse {
    id: string;
    type: 'STROKE_PROCESSED' | 'CHECKPOINT_CREATED' | 'MASK_EXPORTED' | 'STROKE_PATH_APPLIED' | 'MASK_VALIDATED' | 'ERROR';
    data?: any;
    error?: string;
    dirtyRect?: { x: number; y: number; width: number; height: number };
}

// Stroke processing data structures
interface StrokeProcessData {
    maskData: Uint8Array;
    imageWidth: number;
    imageHeight: number;
    centerX: number;
    centerY: number;
    brushSize: number;
    mode: 'paint' | 'erase';
}

interface StrokePathData {
    maskData: Uint8Array;
    imageWidth: number;
    imageHeight: number;
    path: Array<{ x: number; y: number }>;
    brushSize: number;
    mode: 'paint' | 'erase';
    spacing: number;
}

interface CheckpointData {
    maskData: Uint8Array;
    imageWidth: number;
    imageHeight: number;
    tileSize: number;
    strokeIndex: number;
}

interface ExportMaskData {
    maskData: Uint8Array;
    imageWidth: number;
    imageHeight: number;
}

// Worker-side brush engine implementation
class WorkerBrushEngine {
    /**
     * Apply a circular stamp to mask data at the specified position
     */
    public static applyStamp(
        maskData: Uint8Array,
        imageWidth: number,
        imageHeight: number,
        centerX: number,
        centerY: number,
        brushSize: number,
        mode: 'paint' | 'erase'
    ): { hasChanges: boolean; dirtyRect: { x: number; y: number; width: number; height: number } } {
        // Ensure integer positioning for crisp edges
        const cx = Math.round(centerX);
        const cy = Math.round(centerY);
        const radius = Math.floor(brushSize / 2);
        
        // Binary value based on mode
        const stampValue = mode === 'paint' ? 255 : 0;
        
        let hasChanges = false;
        let minX = cx, minY = cy, maxX = cx, maxY = cy;
        
        // Apply circular stamp using integer arithmetic for crisp edges
        for (let y = cy - radius; y <= cy + radius; y++) {
            for (let x = cx - radius; x <= cx + radius; x++) {
                // Check bounds
                if (x < 0 || x >= imageWidth || y < 0 || y >= imageHeight) {
                    continue;
                }
                
                // Check if point is within circle using integer distance
                const dx = x - cx;
                const dy = y - cy;
                const distanceSquared = dx * dx + dy * dy;
                const radiusSquared = radius * radius;
                
                if (distanceSquared <= radiusSquared) {
                    const index = y * imageWidth + x;
                    
                    // Only update if value is different (binary enforcement)
                    if (maskData[index] !== stampValue) {
                        maskData[index] = stampValue;
                        hasChanges = true;
                        
                        // Track dirty bounds
                        minX = Math.min(minX, x);
                        minY = Math.min(minY, y);
                        maxX = Math.max(maxX, x);
                        maxY = Math.max(maxY, y);
                    }
                }
            }
        }
        
        const dirtyRect = hasChanges ? {
            x: Math.max(0, minX),
            y: Math.max(0, minY),
            width: Math.min(imageWidth - Math.max(0, minX), maxX - Math.max(0, minX) + 1),
            height: Math.min(imageHeight - Math.max(0, minY), maxY - Math.max(0, minY) + 1)
        } : { x: 0, y: 0, width: 0, height: 0 };
        
        return { hasChanges, dirtyRect };
    }

    /**
     * Calculate stamp positions between two points with proper spacing
     */
    public static calculateStampPositions(
        start: { x: number; y: number },
        end: { x: number; y: number },
        brushSize: number,
        spacing: number
    ): { x: number; y: number }[] {
        const stamps: { x: number; y: number }[] = [];
        
        // Calculate distance between points
        const dx = end.x - start.x;
        const dy = end.y - start.y;
        const distance = Math.sqrt(dx * dx + dy * dy);
        
        // Calculate spacing distance (0.35 × brush diameter)
        const spacingDistance = brushSize * spacing;
        
        // If distance is less than spacing, no new stamps needed
        if (distance < spacingDistance) {
            return stamps;
        }
        
        // Calculate number of stamps needed
        const numStamps = Math.floor(distance / spacingDistance);
        
        // Calculate step increments
        const stepX = dx / distance * spacingDistance;
        const stepY = dy / distance * spacingDistance;
        
        // Generate stamp positions
        for (let i = 1; i <= numStamps; i++) {
            const stampX = Math.round(start.x + stepX * i);
            const stampY = Math.round(start.y + stepY * i);
            stamps.push({ x: stampX, y: stampY });
        }
        
        return stamps;
    }

    /**
     * Apply multiple stamps from a stroke path
     */
    public static applyStrokePath(
        maskData: Uint8Array,
        imageWidth: number,
        imageHeight: number,
        path: { x: number; y: number }[],
        brushSize: number,
        mode: 'paint' | 'erase',
        spacing: number = 0.35
    ): { hasChanges: boolean; dirtyRect: { x: number; y: number; width: number; height: number } } {
        let hasChanges = false;
        let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
        
        if (path.length === 0) {
            return { hasChanges: false, dirtyRect: { x: 0, y: 0, width: 0, height: 0 } };
        }
        
        // Apply initial stamp
        const initialResult = this.applyStamp(maskData, imageWidth, imageHeight, path[0].x, path[0].y, brushSize, mode);
        if (initialResult.hasChanges) {
            hasChanges = true;
            minX = Math.min(minX, initialResult.dirtyRect.x);
            minY = Math.min(minY, initialResult.dirtyRect.y);
            maxX = Math.max(maxX, initialResult.dirtyRect.x + initialResult.dirtyRect.width - 1);
            maxY = Math.max(maxY, initialResult.dirtyRect.y + initialResult.dirtyRect.height - 1);
        }
        
        // Apply stamps along the path with proper spacing
        let lastStampPos = path[0];
        
        for (let i = 1; i < path.length; i++) {
            const currentPos = path[i];
            
            // Calculate intermediate stamps
            const stamps = this.calculateStampPositions(lastStampPos, currentPos, brushSize, spacing);
            
            // Apply each stamp
            for (const stampPos of stamps) {
                const stampResult = this.applyStamp(maskData, imageWidth, imageHeight, stampPos.x, stampPos.y, brushSize, mode);
                if (stampResult.hasChanges) {
                    hasChanges = true;
                    minX = Math.min(minX, stampResult.dirtyRect.x);
                    minY = Math.min(minY, stampResult.dirtyRect.y);
                    maxX = Math.max(maxX, stampResult.dirtyRect.x + stampResult.dirtyRect.width - 1);
                    maxY = Math.max(maxY, stampResult.dirtyRect.y + stampResult.dirtyRect.height - 1);
                }
                lastStampPos = stampPos;
            }
        }
        
        const dirtyRect = hasChanges ? {
            x: Math.max(0, minX),
            y: Math.max(0, minY),
            width: Math.min(imageWidth - Math.max(0, minX), maxX - Math.max(0, minX) + 1),
            height: Math.min(imageHeight - Math.max(0, minY), maxY - Math.max(0, minY) + 1)
        } : { x: 0, y: 0, width: 0, height: 0 };
        
        return { hasChanges, dirtyRect };
    }

    /**
     * Validate that mask data contains only binary values (0 or 255)
     */
    public static validateBinaryMask(maskData: Uint8Array): boolean {
        for (let i = 0; i < maskData.length; i++) {
            const value = maskData[i];
            if (value !== 0 && value !== 255) {
                return false;
            }
        }
        return true;
    }

    /**
     * Enforce binary values in mask data (convert to 0 or 255)
     */
    public static enforceBinaryMask(maskData: Uint8Array): void {
        for (let i = 0; i < maskData.length; i++) {
            maskData[i] = maskData[i] > 127 ? 255 : 0;
        }
    }
}

// Worker-side checkpoint system
class WorkerCheckpointSystem {
    /**
     * Extract tiles from mask data for efficient storage
     */
    public static extractTiles(maskData: Uint8Array, imageWidth: number, imageHeight: number, tileSize: number): Array<{ x: number; y: number; data: Uint8Array }> {
        const tiles: Array<{ x: number; y: number; data: Uint8Array }> = [];
        const tilesX = Math.ceil(imageWidth / tileSize);
        const tilesY = Math.ceil(imageHeight / tileSize);

        for (let tileY = 0; tileY < tilesY; tileY++) {
            for (let tileX = 0; tileX < tilesX; tileX++) {
                const tileData = this.extractTile(maskData, imageWidth, imageHeight, tileX, tileY, tileSize);
                
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
    private static extractTile(maskData: Uint8Array, imageWidth: number, imageHeight: number, tileX: number, tileY: number, tileSize: number): Uint8Array {
        const startX = tileX * tileSize;
        const startY = tileY * tileSize;
        const endX = Math.min(startX + tileSize, imageWidth);
        const endY = Math.min(startY + tileSize, imageHeight);
        
        const tileWidth = endX - startX;
        const tileHeight = endY - startY;
        const tileData = new Uint8Array(tileWidth * tileHeight);

        for (let y = 0; y < tileHeight; y++) {
            for (let x = 0; x < tileWidth; x++) {
                const sourceIndex = (startY + y) * imageWidth + (startX + x);
                const tileIndex = y * tileWidth + x;
                tileData[tileIndex] = maskData[sourceIndex];
            }
        }

        return tileData;
    }

    /**
     * Check if a tile contains non-zero data
     */
    private static isTileNonEmpty(tileData: Uint8Array): boolean {
        for (let i = 0; i < tileData.length; i++) {
            if (tileData[i] !== 0) {
                return true;
            }
        }
        return false;
    }
}

// Message handlers
const messageHandlers = {
    PROCESS_STROKE: (data: StrokeProcessData): any => {
        const result = WorkerBrushEngine.applyStamp(
            data.maskData,
            data.imageWidth,
            data.imageHeight,
            data.centerX,
            data.centerY,
            data.brushSize,
            data.mode
        );
        
        return {
            maskData: data.maskData, // Return modified mask data
            hasChanges: result.hasChanges,
            dirtyRect: result.dirtyRect
        };
    },

    APPLY_STROKE_PATH: (data: StrokePathData): any => {
        const result = WorkerBrushEngine.applyStrokePath(
            data.maskData,
            data.imageWidth,
            data.imageHeight,
            data.path,
            data.brushSize,
            data.mode,
            data.spacing
        );
        
        return {
            maskData: data.maskData, // Return modified mask data
            hasChanges: result.hasChanges,
            dirtyRect: result.dirtyRect
        };
    },

    CREATE_CHECKPOINT: (data: CheckpointData): any => {
        const tiles = WorkerCheckpointSystem.extractTiles(
            data.maskData,
            data.imageWidth,
            data.imageHeight,
            data.tileSize
        );
        
        return {
            tiles,
            strokeIndex: data.strokeIndex,
            timestamp: Date.now(),
            imageWidth: data.imageWidth,
            imageHeight: data.imageHeight,
            tileSize: data.tileSize
        };
    },

    EXPORT_MASK: (data: ExportMaskData): any => {
        // Create a grayscale PNG data URL
        // For now, return the raw mask data - the main thread will handle PNG conversion
        return {
            maskData: data.maskData,
            imageWidth: data.imageWidth,
            imageHeight: data.imageHeight
        };
    },

    VALIDATE_MASK: (data: { maskData: Uint8Array }): any => {
        const isValid = WorkerBrushEngine.validateBinaryMask(data.maskData);
        
        if (!isValid) {
            // Enforce binary values
            WorkerBrushEngine.enforceBinaryMask(data.maskData);
        }
        
        return {
            isValid,
            maskData: data.maskData // Return corrected mask data if needed
        };
    }
};

// Worker message handler
self.onmessage = (event: MessageEvent<WorkerMessage>) => {
    const { id, type, data } = event.data;
    
    try {
        const handler = messageHandlers[type];
        if (!handler) {
            throw new Error(`Unknown message type: ${type}`);
        }
        
        const result = handler(data);
        
        const response: WorkerResponse = {
            id,
            type: `${type.replace('_', '_').replace('PROCESS', 'PROCESSED').replace('CREATE', 'CREATED').replace('EXPORT', 'EXPORTED').replace('APPLY', 'APPLIED').replace('VALIDATE', 'VALIDATED')}` as any,
            data: result,
            dirtyRect: result.dirtyRect
        };
        
        // Use transferable objects for large data
        const transferables: Transferable[] = [];
        if (result.maskData && result.maskData instanceof Uint8Array) {
            transferables.push(result.maskData.buffer);
        }
        
        if (transferables.length > 0) {
            self.postMessage(response, { transfer: transferables });
        } else {
            self.postMessage(response);
        }
        
    } catch (error) {
        const errorResponse: WorkerResponse = {
            id,
            type: 'ERROR',
            error: error instanceof Error ? error.message : String(error)
        };
        
        self.postMessage(errorResponse);
    }
};

// Types are already exported at the top of the file