
/**
 * Coordinate mapping accuracy tests for CanvasManager
 * Generated from Python test cases
 */

import { CanvasManager } from '../src/canvas-manager.js';

describe('CanvasManager Coordinate Mapping', () => {

    test('Square image in square container', async () => {
        // Create mock canvases
        const imageCanvas = document.createElement('canvas');
        const overlayCanvas = document.createElement('canvas');
        const maskAlphaCanvas = new OffscreenCanvas(1, 1);
        
        // Create container element
        const container = document.createElement('div');
        container.style.width = '600px';
        container.style.height = '600px';
        container.appendChild(imageCanvas);
        document.body.appendChild(container);
        
        const manager = new CanvasManager(imageCanvas, overlayCanvas, maskAlphaCanvas);
        
        // Mock image loading
        const mockImage = new Image();
        mockImage.width = 512;
        mockImage.height = 512;
        mockImage.naturalWidth = 512;
        mockImage.naturalHeight = 512;
        
        // Test coordinate transformations

        const result_44_44 = manager.screenToImage(44, 44);
        expect(result_44_44).toEqual({
            x: 0,
            y: 0
        });
        
        // Test round-trip accuracy
        const backToScreen = manager.imageToScreen(0, 0);
        expect(Math.abs(backToScreen.x - 44)).toBeLessThanOrEqual(1);
        expect(Math.abs(backToScreen.y - 44)).toBeLessThanOrEqual(1);

        const result_556_556 = manager.screenToImage(556, 556);
        expect(result_556_556).toEqual({
            x: 511,
            y: 511
        });
        
        // Test round-trip accuracy
        const backToScreen = manager.imageToScreen(511, 511);
        expect(Math.abs(backToScreen.x - 556)).toBeLessThanOrEqual(1);
        expect(Math.abs(backToScreen.y - 556)).toBeLessThanOrEqual(1);

        const result_300_300 = manager.screenToImage(300, 300);
        expect(result_300_300).toEqual({
            x: 256,
            y: 256
        });
        
        // Test round-trip accuracy
        const backToScreen = manager.imageToScreen(256, 256);
        expect(Math.abs(backToScreen.x - 300)).toBeLessThanOrEqual(1);
        expect(Math.abs(backToScreen.y - 300)).toBeLessThanOrEqual(1);

        
        // Cleanup
        document.body.removeChild(container);
    });

    test('Wide image in square container (letterboxed top/bottom)', async () => {
        // Create mock canvases
        const imageCanvas = document.createElement('canvas');
        const overlayCanvas = document.createElement('canvas');
        const maskAlphaCanvas = new OffscreenCanvas(1, 1);
        
        // Create container element
        const container = document.createElement('div');
        container.style.width = '600px';
        container.style.height = '600px';
        container.appendChild(imageCanvas);
        document.body.appendChild(container);
        
        const manager = new CanvasManager(imageCanvas, overlayCanvas, maskAlphaCanvas);
        
        // Mock image loading
        const mockImage = new Image();
        mockImage.width = 1024;
        mockImage.height = 512;
        mockImage.naturalWidth = 1024;
        mockImage.naturalHeight = 512;
        
        // Test coordinate transformations

        const result_44_156 = manager.screenToImage(44, 156);
        expect(result_44_156).toEqual({
            x: 0,
            y: 0
        });
        
        // Test round-trip accuracy
        const backToScreen = manager.imageToScreen(0, 0);
        expect(Math.abs(backToScreen.x - 44)).toBeLessThanOrEqual(1);
        expect(Math.abs(backToScreen.y - 156)).toBeLessThanOrEqual(1);

        const result_556_444 = manager.screenToImage(556, 444);
        expect(result_556_444).toEqual({
            x: 1023,
            y: 511
        });
        
        // Test round-trip accuracy
        const backToScreen = manager.imageToScreen(1023, 511);
        expect(Math.abs(backToScreen.x - 556)).toBeLessThanOrEqual(1);
        expect(Math.abs(backToScreen.y - 444)).toBeLessThanOrEqual(1);

        const result_300_300 = manager.screenToImage(300, 300);
        expect(result_300_300).toEqual({
            x: 512,
            y: 256
        });
        
        // Test round-trip accuracy
        const backToScreen = manager.imageToScreen(512, 256);
        expect(Math.abs(backToScreen.x - 300)).toBeLessThanOrEqual(1);
        expect(Math.abs(backToScreen.y - 300)).toBeLessThanOrEqual(1);

        
        // Cleanup
        document.body.removeChild(container);
    });

    test('Tall image in square container (letterboxed left/right)', async () => {
        // Create mock canvases
        const imageCanvas = document.createElement('canvas');
        const overlayCanvas = document.createElement('canvas');
        const maskAlphaCanvas = new OffscreenCanvas(1, 1);
        
        // Create container element
        const container = document.createElement('div');
        container.style.width = '600px';
        container.style.height = '600px';
        container.appendChild(imageCanvas);
        document.body.appendChild(container);
        
        const manager = new CanvasManager(imageCanvas, overlayCanvas, maskAlphaCanvas);
        
        // Mock image loading
        const mockImage = new Image();
        mockImage.width = 512;
        mockImage.height = 1024;
        mockImage.naturalWidth = 512;
        mockImage.naturalHeight = 1024;
        
        // Test coordinate transformations

        const result_156_44 = manager.screenToImage(156, 44);
        expect(result_156_44).toEqual({
            x: 0,
            y: 0
        });
        
        // Test round-trip accuracy
        const backToScreen = manager.imageToScreen(0, 0);
        expect(Math.abs(backToScreen.x - 156)).toBeLessThanOrEqual(1);
        expect(Math.abs(backToScreen.y - 44)).toBeLessThanOrEqual(1);

        const result_444_556 = manager.screenToImage(444, 556);
        expect(result_444_556).toEqual({
            x: 511,
            y: 1023
        });
        
        // Test round-trip accuracy
        const backToScreen = manager.imageToScreen(511, 1023);
        expect(Math.abs(backToScreen.x - 444)).toBeLessThanOrEqual(1);
        expect(Math.abs(backToScreen.y - 556)).toBeLessThanOrEqual(1);

        const result_300_300 = manager.screenToImage(300, 300);
        expect(result_300_300).toEqual({
            x: 256,
            y: 512
        });
        
        // Test round-trip accuracy
        const backToScreen = manager.imageToScreen(256, 512);
        expect(Math.abs(backToScreen.x - 300)).toBeLessThanOrEqual(1);
        expect(Math.abs(backToScreen.y - 300)).toBeLessThanOrEqual(1);

        
        // Cleanup
        document.body.removeChild(container);
    });

});
