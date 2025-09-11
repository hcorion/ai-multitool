
/**
 * Binary mask enforcement tests for BrushEngine
 * Generated from Python test cases
 */

import { BrushEngine } from '../src/inpainting/brush-engine.js';

describe('BrushEngine Binary Mask Enforcement', () => {

    test('Paint mode produces only 255 values', () => {
        const engine = new BrushEngine({
            size: 20,
            mode: 'paint',
            spacing: 0.35
        });
        
        const imageWidth = 100;
        const imageHeight = 100;
        const maskData = new Uint8Array(imageWidth * imageHeight);
        
        // Pre-fill if specified
        // No pre-fill
        
        // Apply stamps

        engine.applyStamp(maskData, imageWidth, imageHeight, 50, 50, 20, 'paint');

        engine.applyStamp(maskData, imageWidth, imageHeight, 25, 25, 20, 'paint');

        engine.applyStamp(maskData, imageWidth, imageHeight, 75, 75, 20, 'paint');

        
        // Verify binary invariant
        const isValid = BrushEngine.validateBinaryMask(maskData);
        expect(isValid).toBe(true);
        
        // Verify only expected values exist
        const uniqueValues = new Set(maskData);
        const expectedValues = new Set([0, 255]);
        for (const value of uniqueValues) {
            expect(expectedValues.has(value)).toBe(true);
        }
    });

    test('Erase mode produces only 0 values', () => {
        const engine = new BrushEngine({
            size: 15,
            mode: 'erase',
            spacing: 0.35
        });
        
        const imageWidth = 100;
        const imageHeight = 100;
        const maskData = new Uint8Array(imageWidth * imageHeight);
        
        // Pre-fill if specified
        maskData.fill(255);
        
        // Apply stamps

        engine.applyStamp(maskData, imageWidth, imageHeight, 50, 50, 15, 'erase');

        
        // Verify binary invariant
        const isValid = BrushEngine.validateBinaryMask(maskData);
        expect(isValid).toBe(true);
        
        // Verify only expected values exist
        const uniqueValues = new Set(maskData);
        const expectedValues = new Set([0, 255]);
        for (const value of uniqueValues) {
            expect(expectedValues.has(value)).toBe(true);
        }
    });

    test('Mixed paint and erase maintains binary values', () => {
        const engine = new BrushEngine({
            size: 10,
            mode: 'paint',
            spacing: 0.35
        });
        
        const imageWidth = 50;
        const imageHeight = 50;
        const maskData = new Uint8Array(imageWidth * imageHeight);
        
        // Pre-fill if specified
        // No pre-fill
        
        // Apply stamps

        engine.applyStamp(maskData, imageWidth, imageHeight, 25, 25, 10, 'paint');

        engine.applyStamp(maskData, imageWidth, imageHeight, 25, 25, 10, 'erase');

        engine.applyStamp(maskData, imageWidth, imageHeight, 20, 20, 10, 'paint');

        
        // Verify binary invariant
        const isValid = BrushEngine.validateBinaryMask(maskData);
        expect(isValid).toBe(true);
        
        // Verify only expected values exist
        const uniqueValues = new Set(maskData);
        const expectedValues = new Set([0, 255]);
        for (const value of uniqueValues) {
            expect(expectedValues.has(value)).toBe(true);
        }
    });

});
