
/**
 * Mask overlay binary invariant tests for CanvasManager
 * Generated from Python test cases
 */

import { CanvasManager } from '../src/canvas-manager.js';

describe('Mask Overlay Binary Invariant', () => {

    test('Single pixel mask', async () => {
        // Create mock canvases
        const imageCanvas = document.createElement('canvas');
        const overlayCanvas = document.createElement('canvas');
        const maskAlphaCanvas = new OffscreenCanvas(1, 1);
        
        // Set up canvas dimensions
        const width = 3;
        const height = 3;
        
        imageCanvas.width = width;
        imageCanvas.height = height;
        overlayCanvas.width = width;
        overlayCanvas.height = height;
        maskAlphaCanvas.width = width;
        maskAlphaCanvas.height = height;
        
        // Create container element
        const container = document.createElement('div');
        container.style.width = '400px';
        container.style.height = '400px';
        container.appendChild(imageCanvas);
        document.body.appendChild(container);
        
        const manager = new CanvasManager(imageCanvas, overlayCanvas, maskAlphaCanvas);
        
        // Mock image loading by directly setting up state
        const mockImage = new Image();
        mockImage.width = width;
        mockImage.height = height;
        mockImage.naturalWidth = width;
        mockImage.naturalHeight = height;
        
        // Simulate image load
        await manager.loadImage('data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==');
        
        // Set up mask data
        const state = manager.getState();
        const maskData = new Uint8Array(width * height);

        maskData[0 * width + 0] = 0;
        maskData[0 * width + 1] = 0;
        maskData[0 * width + 2] = 0;
        maskData[1 * width + 0] = 0;
        maskData[1 * width + 1] = 255;
        maskData[1 * width + 2] = 0;
        maskData[2 * width + 0] = 0;
        maskData[2 * width + 1] = 0;
        maskData[2 * width + 2] = 0;
        
        // Apply mask data directly to state
        state.maskData = maskData;
        
        // Update overlay
        manager.updateMaskOverlay();
        
        // Get overlay canvas context and verify binary values
        const overlayCtx = overlayCanvas.getContext('2d');
        const overlayImageData = overlayCtx.getImageData(0, 0, width, height);
        const overlayData = overlayImageData.data;
        
        // Verify that overlay alpha values are binary (0 or 255)
        for (let i = 0; i < overlayData.length; i += 4) {
            const alpha = overlayData[i + 3];
            expect(alpha === 0 || alpha === 255).toBe(true);
        }
        
        // Verify overlay matches expected pattern

        expect(overlayData[(0 * width + 0) * 4 + 3]).toBe(0);
        expect(overlayData[(0 * width + 1) * 4 + 3]).toBe(0);
        expect(overlayData[(0 * width + 2) * 4 + 3]).toBe(0);
        expect(overlayData[(1 * width + 0) * 4 + 3]).toBe(0);
        expect(overlayData[(1 * width + 1) * 4 + 3]).toBe(255);
        expect(overlayData[(1 * width + 2) * 4 + 3]).toBe(0);
        expect(overlayData[(2 * width + 0) * 4 + 3]).toBe(0);
        expect(overlayData[(2 * width + 1) * 4 + 3]).toBe(0);
        expect(overlayData[(2 * width + 2) * 4 + 3]).toBe(0);
        
        // Cleanup
        document.body.removeChild(container);
    });

    test('Circular brush stamp', async () => {
        // Create mock canvases
        const imageCanvas = document.createElement('canvas');
        const overlayCanvas = document.createElement('canvas');
        const maskAlphaCanvas = new OffscreenCanvas(1, 1);
        
        // Set up canvas dimensions
        const width = 5;
        const height = 5;
        
        imageCanvas.width = width;
        imageCanvas.height = height;
        overlayCanvas.width = width;
        overlayCanvas.height = height;
        maskAlphaCanvas.width = width;
        maskAlphaCanvas.height = height;
        
        // Create container element
        const container = document.createElement('div');
        container.style.width = '400px';
        container.style.height = '400px';
        container.appendChild(imageCanvas);
        document.body.appendChild(container);
        
        const manager = new CanvasManager(imageCanvas, overlayCanvas, maskAlphaCanvas);
        
        // Mock image loading by directly setting up state
        const mockImage = new Image();
        mockImage.width = width;
        mockImage.height = height;
        mockImage.naturalWidth = width;
        mockImage.naturalHeight = height;
        
        // Simulate image load
        await manager.loadImage('data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==');
        
        // Set up mask data
        const state = manager.getState();
        const maskData = new Uint8Array(width * height);

        maskData[0 * width + 0] = 0;
        maskData[0 * width + 1] = 255;
        maskData[0 * width + 2] = 255;
        maskData[0 * width + 3] = 255;
        maskData[0 * width + 4] = 0;
        maskData[1 * width + 0] = 255;
        maskData[1 * width + 1] = 255;
        maskData[1 * width + 2] = 255;
        maskData[1 * width + 3] = 255;
        maskData[1 * width + 4] = 255;
        maskData[2 * width + 0] = 255;
        maskData[2 * width + 1] = 255;
        maskData[2 * width + 2] = 255;
        maskData[2 * width + 3] = 255;
        maskData[2 * width + 4] = 255;
        maskData[3 * width + 0] = 255;
        maskData[3 * width + 1] = 255;
        maskData[3 * width + 2] = 255;
        maskData[3 * width + 3] = 255;
        maskData[3 * width + 4] = 255;
        maskData[4 * width + 0] = 0;
        maskData[4 * width + 1] = 255;
        maskData[4 * width + 2] = 255;
        maskData[4 * width + 3] = 255;
        maskData[4 * width + 4] = 0;
        
        // Apply mask data directly to state
        state.maskData = maskData;
        
        // Update overlay
        manager.updateMaskOverlay();
        
        // Get overlay canvas context and verify binary values
        const overlayCtx = overlayCanvas.getContext('2d');
        const overlayImageData = overlayCtx.getImageData(0, 0, width, height);
        const overlayData = overlayImageData.data;
        
        // Verify that overlay alpha values are binary (0 or 255)
        for (let i = 0; i < overlayData.length; i += 4) {
            const alpha = overlayData[i + 3];
            expect(alpha === 0 || alpha === 255).toBe(true);
        }
        
        // Verify overlay matches expected pattern

        expect(overlayData[(0 * width + 0) * 4 + 3]).toBe(0);
        expect(overlayData[(0 * width + 1) * 4 + 3]).toBe(255);
        expect(overlayData[(0 * width + 2) * 4 + 3]).toBe(255);
        expect(overlayData[(0 * width + 3) * 4 + 3]).toBe(255);
        expect(overlayData[(0 * width + 4) * 4 + 3]).toBe(0);
        expect(overlayData[(1 * width + 0) * 4 + 3]).toBe(255);
        expect(overlayData[(1 * width + 1) * 4 + 3]).toBe(255);
        expect(overlayData[(1 * width + 2) * 4 + 3]).toBe(255);
        expect(overlayData[(1 * width + 3) * 4 + 3]).toBe(255);
        expect(overlayData[(1 * width + 4) * 4 + 3]).toBe(255);
        expect(overlayData[(2 * width + 0) * 4 + 3]).toBe(255);
        expect(overlayData[(2 * width + 1) * 4 + 3]).toBe(255);
        expect(overlayData[(2 * width + 2) * 4 + 3]).toBe(255);
        expect(overlayData[(2 * width + 3) * 4 + 3]).toBe(255);
        expect(overlayData[(2 * width + 4) * 4 + 3]).toBe(255);
        expect(overlayData[(3 * width + 0) * 4 + 3]).toBe(255);
        expect(overlayData[(3 * width + 1) * 4 + 3]).toBe(255);
        expect(overlayData[(3 * width + 2) * 4 + 3]).toBe(255);
        expect(overlayData[(3 * width + 3) * 4 + 3]).toBe(255);
        expect(overlayData[(3 * width + 4) * 4 + 3]).toBe(255);
        expect(overlayData[(4 * width + 0) * 4 + 3]).toBe(0);
        expect(overlayData[(4 * width + 1) * 4 + 3]).toBe(255);
        expect(overlayData[(4 * width + 2) * 4 + 3]).toBe(255);
        expect(overlayData[(4 * width + 3) * 4 + 3]).toBe(255);
        expect(overlayData[(4 * width + 4) * 4 + 3]).toBe(0);
        
        // Cleanup
        document.body.removeChild(container);
    });

    test('Mixed paint and erase', async () => {
        // Create mock canvases
        const imageCanvas = document.createElement('canvas');
        const overlayCanvas = document.createElement('canvas');
        const maskAlphaCanvas = new OffscreenCanvas(1, 1);
        
        // Set up canvas dimensions
        const width = 4;
        const height = 4;
        
        imageCanvas.width = width;
        imageCanvas.height = height;
        overlayCanvas.width = width;
        overlayCanvas.height = height;
        maskAlphaCanvas.width = width;
        maskAlphaCanvas.height = height;
        
        // Create container element
        const container = document.createElement('div');
        container.style.width = '400px';
        container.style.height = '400px';
        container.appendChild(imageCanvas);
        document.body.appendChild(container);
        
        const manager = new CanvasManager(imageCanvas, overlayCanvas, maskAlphaCanvas);
        
        // Mock image loading by directly setting up state
        const mockImage = new Image();
        mockImage.width = width;
        mockImage.height = height;
        mockImage.naturalWidth = width;
        mockImage.naturalHeight = height;
        
        // Simulate image load
        await manager.loadImage('data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==');
        
        // Set up mask data
        const state = manager.getState();
        const maskData = new Uint8Array(width * height);

        maskData[0 * width + 0] = 255;
        maskData[0 * width + 1] = 255;
        maskData[0 * width + 2] = 0;
        maskData[0 * width + 3] = 0;
        maskData[1 * width + 0] = 255;
        maskData[1 * width + 1] = 0;
        maskData[1 * width + 2] = 0;
        maskData[1 * width + 3] = 255;
        maskData[2 * width + 0] = 0;
        maskData[2 * width + 1] = 0;
        maskData[2 * width + 2] = 255;
        maskData[2 * width + 3] = 255;
        maskData[3 * width + 0] = 0;
        maskData[3 * width + 1] = 255;
        maskData[3 * width + 2] = 255;
        maskData[3 * width + 3] = 0;
        
        // Apply mask data directly to state
        state.maskData = maskData;
        
        // Update overlay
        manager.updateMaskOverlay();
        
        // Get overlay canvas context and verify binary values
        const overlayCtx = overlayCanvas.getContext('2d');
        const overlayImageData = overlayCtx.getImageData(0, 0, width, height);
        const overlayData = overlayImageData.data;
        
        // Verify that overlay alpha values are binary (0 or 255)
        for (let i = 0; i < overlayData.length; i += 4) {
            const alpha = overlayData[i + 3];
            expect(alpha === 0 || alpha === 255).toBe(true);
        }
        
        // Verify overlay matches expected pattern

        expect(overlayData[(0 * width + 0) * 4 + 3]).toBe(255);
        expect(overlayData[(0 * width + 1) * 4 + 3]).toBe(255);
        expect(overlayData[(0 * width + 2) * 4 + 3]).toBe(0);
        expect(overlayData[(0 * width + 3) * 4 + 3]).toBe(0);
        expect(overlayData[(1 * width + 0) * 4 + 3]).toBe(255);
        expect(overlayData[(1 * width + 1) * 4 + 3]).toBe(0);
        expect(overlayData[(1 * width + 2) * 4 + 3]).toBe(0);
        expect(overlayData[(1 * width + 3) * 4 + 3]).toBe(255);
        expect(overlayData[(2 * width + 0) * 4 + 3]).toBe(0);
        expect(overlayData[(2 * width + 1) * 4 + 3]).toBe(0);
        expect(overlayData[(2 * width + 2) * 4 + 3]).toBe(255);
        expect(overlayData[(2 * width + 3) * 4 + 3]).toBe(255);
        expect(overlayData[(3 * width + 0) * 4 + 3]).toBe(0);
        expect(overlayData[(3 * width + 1) * 4 + 3]).toBe(255);
        expect(overlayData[(3 * width + 2) * 4 + 3]).toBe(255);
        expect(overlayData[(3 * width + 3) * 4 + 3]).toBe(0);
        
        // Cleanup
        document.body.removeChild(container);
    });

});
