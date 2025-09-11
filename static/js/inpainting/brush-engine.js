/**
 * BrushEngine - Handles brush stamping with binary mask enforcement
 * Implements hard-edge circular stamps with proper spacing and binary values
 */
export class BrushEngine {
    settings;
    lastStampPosition = null;
    currentStroke = null;
    constructor(initialSettings = {}) {
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
    startStroke(x, y) {
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
    continueStroke(x, y) {
        if (!this.currentStroke) {
            throw new Error('No active stroke. Call startStroke first.');
        }
        this.currentStroke.points.push({ x, y });
        // Calculate stamps needed between last position and current position
        const stamps = this.calculateStampPositions(this.lastStampPosition, { x, y }, this.settings.size, this.settings.spacing);
        // Always update last stamp position to the current position to ensure continuity
        this.lastStampPosition = { x, y };
        return stamps;
    }
    /**
     * End the current stroke
     */
    endStroke() {
        const stroke = this.currentStroke;
        this.currentStroke = null;
        this.lastStampPosition = null;
        return stroke;
    }
    /**
     * Calculate stamp positions between two points with proper spacing
     */
    calculateStampPositions(start, end, brushSize, spacing) {
        const stamps = [];
        // Calculate distance between points
        const dx = end.x - start.x;
        const dy = end.y - start.y;
        const distance = Math.sqrt(dx * dx + dy * dy);
        // Calculate spacing distance (reduce spacing for better continuity)
        const spacingDistance = brushSize * Math.min(spacing, 0.25); // Cap at 0.25 for better coverage
        // If distance is very small, no new stamps needed
        if (distance < 1) {
            return stamps;
        }
        // Calculate number of stamps needed to ensure continuous coverage
        const numStamps = Math.max(1, Math.ceil(distance / spacingDistance));
        // Calculate actual step size to ensure we reach the end point
        const stepX = dx / numStamps;
        const stepY = dy / numStamps;
        // Generate stamp positions, ensuring we always reach the end point
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
    applyStamp(maskData, imageWidth, imageHeight, centerX, centerY, brushSize, mode) {
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
    applyStrokePath(maskData, imageWidth, imageHeight, path, brushSize, mode) {
        let hasChanges = false;
        if (path.length === 0)
            return false;
        // Apply initial stamp
        if (this.applyStamp(maskData, imageWidth, imageHeight, path[0].x, path[0].y, brushSize, mode)) {
            hasChanges = true;
        }
        // Apply stamps along the path with proper spacing
        let lastStampPos = path[0];
        for (let i = 1; i < path.length; i++) {
            const currentPos = path[i];
            // Calculate intermediate stamps
            const stamps = this.calculateStampPositions(lastStampPos, currentPos, brushSize, this.settings.spacing);
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
    static validateBinaryMask(maskData) {
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
    static enforceBinaryMask(maskData) {
        for (let i = 0; i < maskData.length; i++) {
            maskData[i] = maskData[i] > 127 ? 255 : 0;
        }
    }
    /**
     * Create a preview of the brush stamp for cursor display
     */
    createBrushPreview(size) {
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
    updateSettings(newSettings) {
        this.settings = { ...this.settings, ...newSettings };
    }
    /**
     * Get current brush settings
     */
    getSettings() {
        return { ...this.settings };
    }
    /**
     * Get the current active stroke
     */
    getCurrentStroke() {
        return this.currentStroke;
    }
    /**
     * Calculate the bounding box affected by a brush stroke
     */
    static calculateStrokeBounds(stroke, imageWidth, imageHeight) {
        if (stroke.points.length === 0)
            return null;
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
        if (minX > maxX || minY > maxY)
            return null;
        return {
            x: minX,
            y: minY,
            width: maxX - minX + 1,
            height: maxY - minY + 1
        };
    }
}
