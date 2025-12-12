/**
 * Vibe Panel Component
 * 
 * This module implements the vibe panel for the NovelAI generation form.
 * It displays selected vibes with thumbnails, strength controls, and remove buttons.
 * It also handles the "Add Vibe" button and integrates with the vibe selection modal.
 */

import { vibeSelectionModal } from './vibe-modal.js';
import { getElementByIdSafe } from './dom_utils.js';

// Interfaces for vibe data structures
interface SelectedVibe {
    guid: string;
    name: string;
    encoding_strength: number;
    reference_strength: number;
    model: string;
    preview_paths?: Record<string, string>; // Preview image paths keyed by 'enc{X}_ref{Y}'
}

interface VibeGenerationParams {
    reference_image_multiple: string[];
    reference_strength_multiple: number[];
}

/**
 * Vibe Panel Class
 * 
 * Manages the vibe panel in the NovelAI generation form, including
 * displaying selected vibes, handling strength adjustments, and
 * preparing vibe parameters for image generation.
 */
export class VibePanel {
    private vibes: SelectedVibe[] = [];
    private panelElement: HTMLElement | null = null;
    private addVibeButton: HTMLElement | null = null;
    private readonly maxVibes: number = 4;
    
    // Valid strength values for validation
    private static readonly VALID_ENCODING_STRENGTHS = [1.0, 0.85, 0.7, 0.5, 0.35];
    
    constructor() {
        this.createPanelHTML();
        this.attachEventListeners();
    }
    
    /**
     * Create the vibe panel HTML and inject it into the NovelAI form
     */
    private createPanelHTML(): void {
        // Find the NovelAI form section to insert the vibe panel
        const novelaiForm = document.querySelector('#prompt-form');
        if (!novelaiForm) {
            console.error('NovelAI form not found');
            return;
        }
        
        // Create the "Add Vibe" button HTML
        const addVibeButtonHTML = `
            <div class="vibe-add-section novelai" style="display: none;">
                <button type="button" id="add-vibe-btn" class="vibe-add-button">
                    🎨 Add Vibe
                </button>
                <span class="vibe-help-text">Add visual style references to influence generation</span>
            </div>
        `;
        
        // Create the vibe panel HTML
        const vibePanelHTML = `
            <div id="vibe-panel" class="vibe-panel novelai" style="display: none;">
                <div class="vibe-panel-header">
                    <h3>Selected Vibes</h3>
                    <span class="vibe-count">0 / 4</span>
                </div>
                <div id="vibe-list" class="vibe-list">
                    <!-- Selected vibes will be displayed here -->
                </div>
            </div>
        `;
        
        // Find the submit button to insert the vibe panel before it
        const submitButton = novelaiForm.querySelector('#generate-submit-btn');
        if (submitButton) {
            // Insert the add vibe button before the submit button
            submitButton.insertAdjacentHTML('beforebegin', addVibeButtonHTML);
            // Insert the vibe panel before the submit button
            submitButton.insertAdjacentHTML('beforebegin', vibePanelHTML);
        }
        
        // Get references to the created elements
        this.addVibeButton = document.getElementById('add-vibe-btn');
        this.panelElement = document.getElementById('vibe-panel');
    }
    
    /**
     * Attach event listeners to vibe panel elements
     */
    private attachEventListeners(): void {
        // Add Vibe button click handler
        this.addVibeButton?.addEventListener('click', () => this.showVibeSelectionModal());
        
        // Listen for form submission to include vibe parameters
        const form = document.getElementById('prompt-form');
        form?.addEventListener('submit', (e) => this.onFormSubmit(e));
    }
    
    /**
     * Show the vibe selection modal
     */
    private showVibeSelectionModal(): void {
        // Get current model for compatibility checking
        const currentModel = this.getCurrentModel();
        
        // Show the vibe selection modal
        vibeSelectionModal.show(currentModel, (selectedVibes: SelectedVibe[]) => {
            this.addVibes(selectedVibes);
        });
    }
    
    /**
     * Get the current NovelAI model for compatibility checking
     */
    private getCurrentModel(): string {
        // For NovelAI, we'll use a default model name
        // In a full implementation, this would check the actual model selection
        return 'nai-diffusion-4-5-full';
    }
    
    /**
     * Add vibes to the panel
     */
    public addVibes(newVibes: SelectedVibe[]): void {
        // Add new vibes, respecting the maximum limit
        for (const vibe of newVibes) {
            if (this.vibes.length >= this.maxVibes) {
                console.warn('Maximum vibe limit reached');
                break;
            }
            
            // Check if vibe is already added
            if (!this.vibes.some(v => v.guid === vibe.guid)) {
                this.vibes.push(vibe);
            }
        }
        
        this.render();
    }
    
    /**
     * Add a single vibe to the panel
     */
    public addVibe(vibe: SelectedVibe): boolean {
        // Check vibe count constraint
        if (this.vibes.length >= this.maxVibes) {
            console.warn('Maximum 4 vibes allowed');
            return false;
        }
        
        // Check if vibe is already added
        if (this.vibes.some(v => v.guid === vibe.guid)) {
            console.warn('Vibe already added');
            return false;
        }
        
        this.vibes.push(vibe);
        this.render();
        return true;
    }
    
    /**
     * Remove a vibe from the panel
     */
    public removeVibe(guid: string): void {
        const index = this.vibes.findIndex(v => v.guid === guid);
        if (index !== -1) {
            this.vibes.splice(index, 1);
            this.render();
        }
    }
    
    /**
     * Update vibe strength settings
     */
    public updateVibe(guid: string, encodingStrength: number, referenceStrength: number): void {
        const vibe = this.vibes.find(v => v.guid === guid);
        if (vibe) {
            vibe.encoding_strength = encodingStrength;
            vibe.reference_strength = referenceStrength;
            this.render();
        }
    }
    
    /**
     * Render the vibe panel
     */
    public render(): void {
        if (!this.panelElement) return;
        
        const vibeList = this.panelElement.querySelector('#vibe-list');
        const vibeCount = this.panelElement.querySelector('.vibe-count');
        
        if (!vibeList) return;
        
        // Update vibe count
        if (vibeCount) {
            vibeCount.textContent = `${this.vibes.length} / ${this.maxVibes}`;
        }
        
        // Show/hide panel based on whether there are vibes
        if (this.vibes.length === 0) {
            this.panelElement.style.display = 'none';
            vibeList.innerHTML = '';
            return;
        }
        
        this.panelElement.style.display = 'block';
        
        // Render each vibe
        vibeList.innerHTML = '';
        this.vibes.forEach((vibe, index) => {
            const vibeElement = this.createVibeElement(vibe, index);
            vibeList.appendChild(vibeElement);
        });
    }
    
    /**
     * Create a DOM element for a selected vibe
     */
    private createVibeElement(vibe: SelectedVibe, index: number): HTMLElement {
        const element = document.createElement('div');
        element.className = 'vibe-item';
        element.dataset.guid = vibe.guid;
        
        element.innerHTML = `
            <div class="vibe-item-content">
                <div class="vibe-thumbnail-container">
                    <img class="vibe-thumbnail" src="${this.getPreviewImagePath(vibe)}" alt="${this.escapeHtml(vibe.name)}">
                </div>
                <div class="vibe-info">
                    <h4 class="vibe-name">${this.escapeHtml(vibe.name)}</h4>
                    <div class="vibe-controls">
                        <div class="vibe-strength-control">
                            <label>Encoding:</label>
                            <select class="encoding-strength-select" data-guid="${vibe.guid}">
                                ${VibePanel.VALID_ENCODING_STRENGTHS.map(strength => 
                                    `<option value="${strength}" ${strength === vibe.encoding_strength ? 'selected' : ''}>${strength}</option>`
                                ).join('')}
                            </select>
                        </div>
                        <div class="vibe-strength-control">
                            <label>Reference:</label>
                            <input type="range" class="reference-strength-slider" 
                                   data-guid="${vibe.guid}"
                                   min="0" max="1" step="0.01" 
                                   value="${vibe.reference_strength}">
                            <span class="reference-strength-value">${vibe.reference_strength.toFixed(2)}</span>
                        </div>
                    </div>
                </div>
                <div class="vibe-actions">
                    <button type="button" class="vibe-remove-btn" data-guid="${vibe.guid}" title="Remove vibe">
                        ×
                    </button>
                </div>
            </div>
        `;
        
        // Attach event listeners to the controls
        this.attachVibeElementListeners(element);
        
        return element;
    }
    
    /**
     * Attach event listeners to a vibe element's controls
     */
    private attachVibeElementListeners(element: HTMLElement): void {
        const guid = element.dataset.guid;
        if (!guid) return;
        
        // Remove button
        const removeBtn = element.querySelector('.vibe-remove-btn') as HTMLButtonElement;
        removeBtn?.addEventListener('click', () => this.removeVibe(guid));
        
        // Encoding strength select
        const encodingSelect = element.querySelector('.encoding-strength-select') as HTMLSelectElement;
        encodingSelect?.addEventListener('change', () => {
            const newStrength = parseFloat(encodingSelect.value);
            const vibe = this.vibes.find(v => v.guid === guid);
            if (vibe) {
                vibe.encoding_strength = newStrength;
                this.updateVibeThumbnail(element, vibe);
            }
        });
        
        // Reference strength slider
        const referenceSlider = element.querySelector('.reference-strength-slider') as HTMLInputElement;
        const referenceValue = element.querySelector('.reference-strength-value') as HTMLSpanElement;
        
        referenceSlider?.addEventListener('input', () => {
            const newStrength = parseFloat(referenceSlider.value);
            const vibe = this.vibes.find(v => v.guid === guid);
            if (vibe) {
                vibe.reference_strength = newStrength;
                if (referenceValue) {
                    referenceValue.textContent = newStrength.toFixed(2);
                }
                this.updateVibeThumbnail(element, vibe);
            }
        });
    }
    
    /**
     * Update the thumbnail image for a vibe based on current strength settings
     */
    private updateVibeThumbnail(element: HTMLElement, vibe: SelectedVibe): void {
        const thumbnail = element.querySelector('.vibe-thumbnail') as HTMLImageElement;
        if (thumbnail) {
            thumbnail.src = this.getPreviewImagePath(vibe);
        }
    }
    
    /**
     * Format a strength value to match the JSON key format (minimal decimal places)
     * Examples: 1.0 -> "1.0", 0.85 -> "0.85", 0.5 -> "0.5", 0.7 -> "0.7"
     */
    private formatStrengthForKey(value: number): string {
        const str = value.toString();
        // If it's a whole number, add .0
        if (!str.includes('.')) {
            return str + '.0';
        }
        return str;
    }
    
    /**
     * Convert a full resolution PNG path to a thumbnail JPG path
     */
    private toThumbnailPath(pngPath: string): string {
        // Convert /path/to/preview.png to /path/to/preview.thumb.jpg
        return pngPath.replace(/\.png$/, '.thumb.jpg');
    }
    
    /**
     * Get the preview image path for a vibe based on its current strength settings
     * Returns the thumbnail JPG for smaller display in the vibe list
     */
    private getPreviewImagePath(vibe: SelectedVibe): string {
        if (!vibe.preview_paths) {
            return '';
        }
        
        const closestRefStrength = this.findClosestReferenceStrength(vibe.reference_strength);
        // Format numbers to match JSON key format (minimal decimal places)
        const encStrengthStr = this.formatStrengthForKey(vibe.encoding_strength);
        const refStrengthStr = this.formatStrengthForKey(closestRefStrength);
        const previewKey = `enc${encStrengthStr}_ref${refStrengthStr}`;
        
        const fullPath = vibe.preview_paths[previewKey] || '';
        // Use thumbnail for the vibe list display
        return fullPath ? this.toThumbnailPath(fullPath) : '';
    }
    
    /**
     * Find the closest valid reference strength for preview display
     */
    private findClosestReferenceStrength(targetStrength: number): number {
        const validStrengths = [1.0, 0.85, 0.7, 0.5, 0.35];
        return validStrengths.reduce((closest, current) => {
            return Math.abs(current - targetStrength) < Math.abs(closest - targetStrength) ? current : closest;
        });
    }
    
    /**
     * Get vibe parameters formatted for image generation
     */
    public getVibesForGeneration(): VibeGenerationParams {
        // In a full implementation, this would fetch the actual encoded data
        // For now, we'll return the structure that would be used
        return {
            reference_image_multiple: this.vibes.map(v => `vibe_${v.guid}_${v.encoding_strength}`), // Placeholder
            reference_strength_multiple: this.vibes.map(v => v.reference_strength)
        };
    }
    
    /**
     * Handle form submission to include vibe parameters
     */
    private onFormSubmit(event: Event): void {
        // Only add vibe parameters if we're using NovelAI and have vibes
        const provider = getElementByIdSafe('provider', HTMLSelectElement);
        if (!provider || provider.value !== 'novelai' || this.vibes.length === 0) {
            return;
        }
        
        // Get the form element
        const form = event.target as HTMLFormElement;
        if (!form) return;
        
        // Remove any existing vibe input fields
        const existingVibeInputs = form.querySelectorAll('input[name^="vibe_"]');
        existingVibeInputs.forEach(input => input.remove());
        
        // Add vibe parameters as hidden form fields
        const vibeParams = this.getVibesForGeneration();
        
        // Add reference strengths
        vibeParams.reference_strength_multiple.forEach((strength, index) => {
            const input = document.createElement('input');
            input.type = 'hidden';
            input.name = `vibe_reference_strength_${index}`;
            input.value = strength.toString();
            form.appendChild(input);
        });
        
        // Add vibe GUIDs and encoding strengths
        this.vibes.forEach((vibe, index) => {
            const guidInput = document.createElement('input');
            guidInput.type = 'hidden';
            guidInput.name = `vibe_guid_${index}`;
            guidInput.value = vibe.guid;
            form.appendChild(guidInput);
            
            const encodingInput = document.createElement('input');
            encodingInput.type = 'hidden';
            encodingInput.name = `vibe_encoding_strength_${index}`;
            encodingInput.value = vibe.encoding_strength.toString();
            form.appendChild(encodingInput);
        });
    }
    
    /**
     * Show the vibe panel (called when NovelAI is selected)
     */
    public show(): void {
        const addVibeSection = document.querySelector('.vibe-add-section');
        if (addVibeSection) {
            (addVibeSection as HTMLElement).style.display = 'block';
        }
        
        // Only show the panel if there are vibes
        if (this.vibes.length > 0 && this.panelElement) {
            this.panelElement.style.display = 'block';
        }
    }
    
    /**
     * Hide the vibe panel (called when other providers are selected)
     */
    public hide(): void {
        const addVibeSection = document.querySelector('.vibe-add-section');
        if (addVibeSection) {
            (addVibeSection as HTMLElement).style.display = 'none';
        }
        
        if (this.panelElement) {
            this.panelElement.style.display = 'none';
        }
    }
    
    /**
     * Clear all vibes from the panel
     */
    public clearVibes(): void {
        this.vibes = [];
        this.render();
    }
    
    /**
     * Get the current vibes
     */
    public getVibes(): SelectedVibe[] {
        return [...this.vibes];
    }
    
    /**
     * Escape HTML to prevent XSS
     */
    private escapeHtml(text: string): string {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Export singleton instance
export const vibePanel = new VibePanel();