/**
 * InpaintingMaskCanvas - A sophisticated 2D painting interface for creating binary masks
 * for image inpainting operations with full-screen popup overlay.
 */

import { CanvasManager, CanvasState } from './canvas-manager.js';

interface InpaintingMaskCanvasConfig {
    imageUrl: string;
    containerElement: HTMLElement;
    onMaskComplete: (maskDataUrl: string) => void;
    onCancel: () => void;
}

export class InpaintingMaskCanvas {
    private config: InpaintingMaskCanvasConfig;
    private popupElement: HTMLElement | null = null;
    private imageCanvas: HTMLCanvasElement | null = null;
    private overlayCanvas: HTMLCanvasElement | null = null;
    private maskAlphaCanvas: OffscreenCanvas | HTMLCanvasElement | null = null;
    private canvasManager: CanvasManager | null = null;
    private isVisible: boolean = false;

    constructor(config: InpaintingMaskCanvasConfig) {
        this.config = config;
    }

    public async show(): Promise<void> {
        if (this.isVisible) return;
        
        this.createPopupStructure();
        this.setupCanvases();
        this.attachEventListeners();
        this.isVisible = true;
        
        // Load the image using CanvasManager
        try {
            await this.loadImage(this.config.imageUrl);
        } catch (error) {
            console.error('Failed to load image:', error);
            this.showError(`Failed to load image: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
    }

    public hide(): void {
        if (!this.isVisible) return;
        
        this.cleanup();
        this.isVisible = false;
    }

    public exportMask(): string {
        if (!this.canvasManager) {
            throw new Error('Canvas not initialized');
        }
        
        const state = this.canvasManager.getState();
        if (!state) {
            throw new Error('No image loaded');
        }
        
        // Create a temporary canvas for export
        const exportCanvas = document.createElement('canvas');
        exportCanvas.width = state.imageWidth;
        exportCanvas.height = state.imageHeight;
        const ctx = exportCanvas.getContext('2d');
        
        if (!ctx) {
            throw new Error('Failed to get export canvas context');
        }
        
        // Get mask image data from canvas manager
        const imageData = this.canvasManager.exportMaskImageData();
        if (!imageData) {
            throw new Error('Failed to export mask image data');
        }
        
        ctx.putImageData(imageData, 0, 0);
        return exportCanvas.toDataURL('image/png');
    }

    private createPopupStructure(): void {
        // Create the main popup overlay
        this.popupElement = document.createElement('div');
        this.popupElement.className = 'inpainting-mask-popup';
        
        // Create the popup content container
        const contentContainer = document.createElement('div');
        contentContainer.className = 'inpainting-mask-content';
        
        // Create the toolbar
        const toolbar = document.createElement('div');
        toolbar.className = 'inpainting-mask-toolbar';
        
        // Add toolbar buttons
        const paintButton = document.createElement('button');
        paintButton.className = 'toolbar-btn paint-btn active';
        paintButton.innerHTML = '🖌️ Paint';
        paintButton.title = 'Paint mask areas';
        
        const eraseButton = document.createElement('button');
        eraseButton.className = 'toolbar-btn erase-btn';
        eraseButton.innerHTML = '🧽 Erase';
        eraseButton.title = 'Erase mask areas';
        
        const brushSizeContainer = document.createElement('div');
        brushSizeContainer.className = 'brush-size-container';
        
        const brushSizeLabel = document.createElement('label');
        brushSizeLabel.textContent = 'Size:';
        
        const brushSizeSlider = document.createElement('input');
        brushSizeSlider.type = 'range';
        brushSizeSlider.min = '1';
        brushSizeSlider.max = '200';
        brushSizeSlider.value = '20';
        brushSizeSlider.className = 'brush-size-slider';
        
        const brushSizeValue = document.createElement('span');
        brushSizeValue.className = 'brush-size-value';
        brushSizeValue.textContent = '20px';
        
        brushSizeContainer.appendChild(brushSizeLabel);
        brushSizeContainer.appendChild(brushSizeSlider);
        brushSizeContainer.appendChild(brushSizeValue);
        
        const undoButton = document.createElement('button');
        undoButton.className = 'toolbar-btn undo-btn';
        undoButton.innerHTML = '↶ Undo';
        undoButton.title = 'Undo last stroke';
        
        const redoButton = document.createElement('button');
        redoButton.className = 'toolbar-btn redo-btn';
        redoButton.innerHTML = '↷ Redo';
        redoButton.title = 'Redo last undone stroke';
        
        const completeButton = document.createElement('button');
        completeButton.className = 'toolbar-btn complete-btn';
        completeButton.innerHTML = '✓ Complete';
        completeButton.title = 'Complete mask and proceed';
        
        const cancelButton = document.createElement('button');
        cancelButton.className = 'toolbar-btn cancel-btn';
        cancelButton.innerHTML = '✕ Cancel';
        cancelButton.title = 'Cancel mask editing';
        
        // Add all buttons to toolbar
        toolbar.appendChild(paintButton);
        toolbar.appendChild(eraseButton);
        toolbar.appendChild(brushSizeContainer);
        toolbar.appendChild(undoButton);
        toolbar.appendChild(redoButton);
        toolbar.appendChild(completeButton);
        toolbar.appendChild(cancelButton);
        
        // Create the canvas container
        const canvasContainer = document.createElement('div');
        canvasContainer.className = 'inpainting-mask-canvas-container';
        
        // Create the three canvases
        this.imageCanvas = document.createElement('canvas');
        this.imageCanvas.className = 'inpainting-canvas image-canvas';
        
        this.overlayCanvas = document.createElement('canvas');
        this.overlayCanvas.className = 'inpainting-canvas overlay-canvas';
        
        // Create OffscreenCanvas for mask alpha (fallback to regular canvas if not supported)
        try {
            this.maskAlphaCanvas = new OffscreenCanvas(1, 1);
        } catch (e) {
            // Fallback for browsers that don't support OffscreenCanvas
            const fallbackCanvas = document.createElement('canvas');
            fallbackCanvas.style.display = 'none';
            this.maskAlphaCanvas = fallbackCanvas as any;
        }
        
        canvasContainer.appendChild(this.imageCanvas);
        canvasContainer.appendChild(this.overlayCanvas);
        
        // Assemble the popup structure
        contentContainer.appendChild(toolbar);
        contentContainer.appendChild(canvasContainer);
        this.popupElement.appendChild(contentContainer);
        
        // Add to container
        this.config.containerElement.appendChild(this.popupElement);
    }

    private setupCanvases(): void {
        if (!this.imageCanvas || !this.overlayCanvas || !this.maskAlphaCanvas) {
            throw new Error('Canvases not created');
        }
        
        // Create canvas manager
        this.canvasManager = new CanvasManager(
            this.imageCanvas,
            this.overlayCanvas,
            this.maskAlphaCanvas
        );
        
        // Set up resize handler
        window.addEventListener('resize', this.handleResize.bind(this));
    }

    private attachEventListeners(): void {
        if (!this.popupElement) return;
        
        // Toolbar event listeners
        const paintBtn = this.popupElement.querySelector('.paint-btn') as HTMLButtonElement;
        const eraseBtn = this.popupElement.querySelector('.erase-btn') as HTMLButtonElement;
        const brushSizeSlider = this.popupElement.querySelector('.brush-size-slider') as HTMLInputElement;
        const brushSizeValue = this.popupElement.querySelector('.brush-size-value') as HTMLSpanElement;
        const undoBtn = this.popupElement.querySelector('.undo-btn') as HTMLButtonElement;
        const redoBtn = this.popupElement.querySelector('.redo-btn') as HTMLButtonElement;
        const completeBtn = this.popupElement.querySelector('.complete-btn') as HTMLButtonElement;
        const cancelBtn = this.popupElement.querySelector('.cancel-btn') as HTMLButtonElement;
        
        // Tool selection
        paintBtn?.addEventListener('click', () => this.setTool('paint'));
        eraseBtn?.addEventListener('click', () => this.setTool('erase'));
        
        // Brush size control
        brushSizeSlider?.addEventListener('input', (e) => {
            const size = (e.target as HTMLInputElement).value;
            brushSizeValue.textContent = `${size}px`;
            this.setBrushSize(parseInt(size));
        });
        
        // History controls
        undoBtn?.addEventListener('click', () => this.undo());
        redoBtn?.addEventListener('click', () => this.redo());
        
        // Action buttons
        completeBtn?.addEventListener('click', () => this.completeMask());
        cancelBtn?.addEventListener('click', () => this.cancelMask());
        
        // Prevent page scroll when popup is open
        document.body.style.overflow = 'hidden';
        
        // Close on escape key
        document.addEventListener('keydown', this.handleKeyDown.bind(this));
    }

    private async loadImage(imageUrl: string): Promise<void> {
        if (!this.canvasManager) {
            throw new Error('Canvas manager not initialized');
        }
        
        try {
            await this.canvasManager.loadImage(imageUrl);
            this.hideError();
        } catch (error) {
            throw error;
        }
    }

    private setTool(tool: 'paint' | 'erase'): void {
        if (!this.popupElement) return;
        
        const paintBtn = this.popupElement.querySelector('.paint-btn');
        const eraseBtn = this.popupElement.querySelector('.erase-btn');
        
        paintBtn?.classList.toggle('active', tool === 'paint');
        eraseBtn?.classList.toggle('active', tool === 'erase');
        
        // Update brush engine mode
        if (this.canvasManager) {
            this.canvasManager.getBrushEngine().updateSettings({ mode: tool });
        }
    }

    private setBrushSize(size: number): void {
        if (this.canvasManager) {
            this.canvasManager.getBrushEngine().updateSettings({ size });
        }
    }

    private undo(): void {
        // Undo logic will be implemented in later tasks
        console.log('Undo requested');
    }

    private redo(): void {
        // Redo logic will be implemented in later tasks
        console.log('Redo requested');
    }

    private completeMask(): void {
        try {
            const maskDataUrl = this.exportMask();
            this.config.onMaskComplete(maskDataUrl);
            this.hide();
        } catch (error) {
            console.error('Failed to complete mask:', error);
        }
    }

    private cancelMask(): void {
        this.config.onCancel();
        this.hide();
    }

    private handleKeyDown(event: KeyboardEvent): void {
        if (!this.isVisible) return;
        
        switch (event.key) {
            case 'Escape':
                this.cancelMask();
                break;
            case 'z':
                if (event.ctrlKey || event.metaKey) {
                    if (event.shiftKey) {
                        this.redo();
                    } else {
                        this.undo();
                    }
                    event.preventDefault();
                }
                break;
        }
    }

    private handleResize(): void {
        if (this.canvasManager) {
            this.canvasManager.handleResize();
        }
    }

    private showError(message: string): void {
        if (!this.popupElement) return;
        
        const canvasContainer = this.popupElement.querySelector('.inpainting-mask-canvas-container');
        if (!canvasContainer) return;
        
        // Create or update error message
        let errorElement = canvasContainer.querySelector('.error-message') as HTMLElement;
        if (!errorElement) {
            errorElement = document.createElement('div');
            errorElement.className = 'error-message';
            errorElement.style.cssText = `
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                background-color: #ff4444;
                color: white;
                padding: 20px;
                border-radius: 8px;
                text-align: center;
                max-width: 400px;
                z-index: 10;
            `;
            canvasContainer.appendChild(errorElement);
        }
        
        errorElement.innerHTML = `
            <div style="font-size: 18px; margin-bottom: 10px;">⚠️ Error</div>
            <div>${message}</div>
            <button onclick="this.parentElement.remove()" style="
                margin-top: 15px;
                padding: 8px 16px;
                background-color: rgba(255,255,255,0.2);
                border: 1px solid rgba(255,255,255,0.3);
                color: white;
                border-radius: 4px;
                cursor: pointer;
            ">Dismiss</button>
        `;
    }

    private hideError(): void {
        if (!this.popupElement) return;
        
        const errorElement = this.popupElement.querySelector('.error-message');
        if (errorElement) {
            errorElement.remove();
        }
    }

    private cleanup(): void {
        // Remove resize handler
        window.removeEventListener('resize', this.handleResize.bind(this));
        
        if (this.popupElement) {
            this.popupElement.remove();
            this.popupElement = null;
        }
        
        // Restore page scroll
        document.body.style.overflow = '';
        
        // Remove event listeners
        document.removeEventListener('keydown', this.handleKeyDown.bind(this));
        
        // Cleanup canvas manager
        if (this.canvasManager) {
            this.canvasManager.cleanup();
            this.canvasManager = null;
        }
        
        // Reset references
        this.imageCanvas = null;
        this.overlayCanvas = null;
        this.maskAlphaCanvas = null;
    }
}