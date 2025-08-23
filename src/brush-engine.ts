/**
 * BrushEngine - Handles brush stamping with binary mask enforcement
 * Implements hard-edge circular stamps with proper spacing and binary values
 */

export interface BrushStroke {
    points: Array<{ x: number; y: number }>;
    brushSize: number;
    mode: 'paint' | 'erase';
    timestamp: number;
}

export interface BrushSettings {
    size: number;
    mode: 'paint' | 'erase';
    spacing: number; // As a fraction of brush diameter (default 0.35)
}

export class BrushEngine {
    private settings: BrushSettings;
    private lastStampPosition: { x: number; y: number } | null = null;
    private currentStroke: BrushStroke | null = null;

    constructor(initialSettings: Partial<BrushSettings> = {}) {
        this.settings = {
            size: 20,
            mode: 'paint',
            spacing: 0.35,
            ...initialSettings
        };
    }

    /**
     * Start a new brush stroke
     */
    public startStroke(x: number, y: number): BrushStroke {
        this.currentStroke = {
            points: [{ x, y }],
            brushSize: this.settings.size,
            mode: this.settings.mode,
            timestamp: Date.now()
        };
        
        this.lastStampPosition = { x, y };
        return this.currentStroke;
    }

    /**
     * Continue the current stroke with a new point
     */
    public continueStroke(x: number, y: number): { x: number; y: number }[] {
        if (!this.currentStroke) {
            throw new Error('No active stroke. Call startStroke first.');
        }

        this.currentStroke.points.push({ x, y });

        // Calculate stamps needed between last position and current position
        const stamps = this.calculateStampPositions(
            this.lastStampPosition!,
            { x, y },
            this.settings.size,
            this.settings.spacing
        );

        // Update last stamp position to the last calculated stamp
        if (stamps.length > 0) {
            this.lastStampPosition = stamps[stamps.length - 1];
        }

        return stamps;
    }

    /**
     * End the current stroke
     */
    public endStroke(): BrushStroke | null {
        const stroke = this.currentStroke;
        this.currentStroke = null;
        this.lastStampPosition = null;
        return stroke;
    }

    /**
     * Calculate stamp positions between two points with proper spacing
     */
    private calculateStampPositions(
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
     * Apply a circular stamp to mask data at the specified position
     */
    public applyStamp(
        maskData: Uint8Array,
        imageWidth: number,
        imageHeight: number,
        centerX: number,
        centerY: number,
        brushSize: number,
        mode: 'paint' | 'erase'
    ): boolean {
        // Ensure integer positioning for crisp edges
        const cx = Math.round(centerX);
        const cy = Math.round(centerY);
        const radius = Math.floor(brushSize / 2);
        
        // Binary value based on mode
        const stampValue = mode === 'paint' ? 255 : 0;
        
        let hasChanges = false;
        
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
                    }
                }
            }
        }
        
        return hasChanges;
    }

    /**
     * Apply multiple stamps from a stroke path
     */
    public applyStrokePath(
        maskData: Uint8Array,
        imageWidth: number,
        imageHeight: number,
        path: { x: number; y: number }[],
        brushSize: number,
        mode: 'paint' | 'erase'
    ): boolean {
        let hasChanges = false;
        
        if (path.length === 0) return false;
        
        // Apply initial stamp
        if (this.applyStamp(maskData, imageWidth, imageHeight, path[0].x, path[0].y, brushSize, mode)) {
            hasChanges = true;
        }
        
        // Apply stamps along the path with proper spacing
        let lastStampPos = path[0];
        
        for (let i = 1; i < path.length; i++) {
            const currentPos = path[i];
            
            // Calculate intermediate stamps
            const stamps = this.calculateStampPositions(
                lastStampPos,
                currentPos,
                brushSize,
                this.settings.spacing
            );
            
            // Apply each stamp
            for (const stampPos of stamps) {
                if (this.applyStamp(maskData, imageWidth, imageHeight, stampPos.x, stampPos.y, brushSize, mode)) {
                    hasChanges = true;
                }
                lastStampPos = stampPos;
            }
        }
        
        return hasChanges;
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

    /**
     * Create a preview of the brush stamp for cursor display
     */
    public createBrushPreview(size: number): HTMLCanvasElement {
        const canvas = document.createElement('canvas');
        const radius = Math.floor(size / 2);
        const diameter = radius * 2 + 1;
        
        canvas.width = diameter;
        canvas.height = diameter;
        
        const ctx = canvas.getContext('2d');
        if (!ctx) {
            throw new Error('Failed to get canvas context for brush preview');
        }
        
        // Clear canvas
        ctx.clearRect(0, 0, diameter, diameter);
        
        // Draw circle outline
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.8)';
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.arc(radius, radius, radius - 0.5, 0, Math.PI * 2);
        ctx.stroke();
        
        // Draw inner circle for better visibility
        ctx.strokeStyle = 'rgba(0, 0, 0, 0.5)';
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.arc(radius, radius, radius - 1.5, 0, Math.PI * 2);
        ctx.stroke();
        
        return canvas;
    }

    /**
     * Update brush settings
     */
    public updateSettings(newSettings: Partial<BrushSettings>): void {
        this.settings = { ...this.settings, ...newSettings };
    }

    /**
     * Get current brush settings
     */
    public getSettings(): BrushSettings {
        return { ...this.settings };
    }

    /**
     * Get the current active stroke
     */
    public getCurrentStroke(): BrushStroke | null {
        return this.currentStroke;
    }

    /**
     * Calculate the bounding box affected by a brush stroke
     */
    public static calculateStrokeBounds(
        stroke: BrushStroke,
        imageWidth: number,
        imageHeight: number
    ): { x: number; y: number; width: number; height: number } | null {
        if (stroke.points.length === 0) return null;
        
        const radius = Math.floor(stroke.brushSize / 2);
        
        let minX = imageWidth;
        let minY = imageHeight;
        let maxX = -1;
        let maxY = -1;
        
        // Find bounds of all points plus brush radius
        for (const point of stroke.points) {
            minX = Math.min(minX, point.x - radius);
            minY = Math.min(minY, point.y - radius);
            maxX = Math.max(maxX, point.x + radius);
            maxY = Math.max(maxY, point.y + radius);
        }
        
        // Clamp to image bounds
        minX = Math.max(0, minX);
        minY = Math.max(0, minY);
        maxX = Math.min(imageWidth - 1, maxX);
        maxY = Math.min(imageHeight - 1, maxY);
        
        if (minX > maxX || minY > maxY) return null;
        
        return {
            x: minX,
            y: minY,
            width: maxX - minX + 1,
            height: maxY - minY + 1
        };
    }
}