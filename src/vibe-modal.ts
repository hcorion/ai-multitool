/**
 * Vibe Selection Modal Component
 * 
 * This module implements the frontend vibe selection modal for NovelAI vibe encoding.
 * Users can browse vibe collections, adjust encoding and reference strengths, and
 * select vibes for image generation.
 */

import { getElementByIdSafe } from './dom_utils.js';

// Interfaces for vibe data structures
interface VibeCollection {
    guid: string;
    name: string;
    model: string;
    created_at: number;
    preview_image: string;
}

interface VibeCollectionDetails {
    guid: string;
    name: string;
    model: string;
    created_at: number;
    encoding_strengths: number[];
    previews: Record<string, string>;
}

interface SelectedVibe {
    guid: string;
    name: string;
    encoding_strength: number;
    reference_strength: number;
    model: string;
}

interface VibeGenerationParams {
    reference_image_multiple: string[];
    reference_strength_multiple: number[];
}

/**
 * Vibe Selection Modal Class
 * 
 * Manages the vibe selection modal UI, including loading collections,
 * handling user interactions, and validating selections.
 */
export class VibeSelectionModal {
    private modal: HTMLElement | null = null;
    private collections: VibeCollection[] = [];
    private selectedVibes: SelectedVibe[] = [];
    private currentModel: string = '';
    private onVibeSelectedCallback: ((vibes: SelectedVibe[]) => void) | null = null;
    
    // Validation constants
    private static readonly VALID_ENCODING_STRENGTHS = [1.0, 0.85, 0.7, 0.5, 0.35];
    private static readonly VALID_REFERENCE_STRENGTHS = [1.0, 0.85, 0.7, 0.5, 0.35];
    private static readonly MIN_VIBES = 1;
    private static readonly MAX_VIBES = 4;
    
    constructor() {
        this.createModalHTML();
        this.attachEventListeners();
    }
    
    /**
     * Create the modal HTML structure and inject it into the DOM
     */
    private createModalHTML(): void {
        const modalHTML = `
            <div id="vibe-selection-modal" class="modal" style="display: none;">
                <div class="modal-content vibe-modal-content">
                    <div class="modal-header">
                        <h2>Select Vibes</h2>
                        <span class="close" id="vibe-modal-close">&times;</span>
                    </div>
                    <div class="modal-body">
                        <div class="vibe-selection-info">
                            <p>Select up to 4 vibes to influence your image generation. Adjust encoding and reference strengths to control the effect.</p>
                            <div class="selected-vibes-count">
                                Selected: <span id="selected-vibes-count">0</span> / 4
                            </div>
                        </div>
                        
                        <div class="vibe-collections-grid" id="vibe-collections-grid">
                            <!-- Vibe collections will be loaded here -->
                        </div>
                        
                        <div class="vibe-selection-controls" id="vibe-selection-controls" style="display: none;">
                            <div class="vibe-preview-section">
                                <h3>Preview</h3>
                                <img id="vibe-preview-image" class="vibe-preview-image" alt="Vibe preview">
                            </div>
                            
                            <div class="vibe-strength-controls">
                                <div class="strength-control">
                                    <label for="encoding-strength-slider">Encoding Strength:</label>
                                    <div class="discrete-slider">
                                        <input type="range" id="encoding-strength-slider" min="0" max="4" step="1" value="0">
                                        <div class="slider-labels">
                                            <span>1.0</span>
                                            <span>0.85</span>
                                            <span>0.7</span>
                                            <span>0.5</span>
                                            <span>0.35</span>
                                        </div>
                                    </div>
                                    <span id="encoding-strength-value">1.0</span>
                                </div>
                                
                                <div class="strength-control">
                                    <label for="reference-strength-slider">Reference Strength:</label>
                                    <input type="range" id="reference-strength-slider" min="0" max="1" step="0.01" value="1.0">
                                    <span id="reference-strength-value">1.0</span>
                                </div>
                            </div>
                            
                            <div class="vibe-validation-messages" id="vibe-validation-messages">
                                <!-- Validation messages will appear here -->
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button id="vibe-modal-cancel" class="btn btn-secondary">Cancel</button>
                        <button id="vibe-modal-confirm" class="btn btn-primary" disabled>Add Selected Vibes</button>
                    </div>
                </div>
            </div>
        `;
        
        // Inject modal HTML into the document body
        document.body.insertAdjacentHTML('beforeend', modalHTML);
        this.modal = document.getElementById('vibe-selection-modal');
    }
    
    /**
     * Attach event listeners to modal elements
     */
    private attachEventListeners(): void {
        if (!this.modal) return;
        
        // Close modal events
        const closeBtn = document.getElementById('vibe-modal-close');
        const cancelBtn = document.getElementById('vibe-modal-cancel');
        
        closeBtn?.addEventListener('click', () => this.hide());
        cancelBtn?.addEventListener('click', () => this.hide());
        
        // Click outside modal to close
        this.modal.addEventListener('click', (e) => {
            if (e.target === this.modal) {
                this.hide();
            }
        });
        
        // Escape key to close
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.modal?.style.display === 'block') {
                this.hide();
            }
        });
        
        // Confirm selection
        const confirmBtn = document.getElementById('vibe-modal-confirm');
        confirmBtn?.addEventListener('click', () => this.confirmSelection());
        
        // Strength sliders
        const encodingSlider = document.getElementById('encoding-strength-slider') as HTMLInputElement;
        const referenceSlider = document.getElementById('reference-strength-slider') as HTMLInputElement;
        
        encodingSlider?.addEventListener('input', () => this.updateEncodingStrength());
        referenceSlider?.addEventListener('input', () => this.updateReferenceStrength());
    }
    
    /**
     * Show the vibe selection modal
     */
    public show(currentModel: string, onVibeSelected: (vibes: SelectedVibe[]) => void): void {
        if (!this.modal) return;
        
        this.currentModel = currentModel;
        this.onVibeSelectedCallback = onVibeSelected;
        this.selectedVibes = [];
        
        this.modal.style.display = 'block';
        this.loadCollections();
        this.updateSelectedVibesCount();
        this.hideSelectionControls();
    }
    
    /**
     * Hide the vibe selection modal
     */
    public hide(): void {
        if (!this.modal) return;
        
        this.modal.style.display = 'none';
        this.selectedVibes = [];
        this.hideSelectionControls();
    }
    
    /**
     * Load vibe collections from the API
     */
    private async loadCollections(): Promise<void> {
        try {
            const response = await fetch('/vibes');
            
            if (!response.ok) {
                throw new Error(`Failed to load vibes: ${response.statusText}`);
            }
            
            const data = await response.json();
            this.collections = data.collections || [];
            this.renderCollections();
            
        } catch (error) {
            console.error('Error loading vibe collections:', error);
            this.showError('Failed to load vibe collections. Please try again.');
        }
    }
    
    /**
     * Render the vibe collections grid
     */
    private renderCollections(): void {
        const grid = document.getElementById('vibe-collections-grid');
        if (!grid) return;
        
        if (this.collections.length === 0) {
            grid.innerHTML = '<div class="no-vibes-message">No vibe collections found. Create some vibes first!</div>';
            return;
        }
        
        grid.innerHTML = '';
        
        this.collections.forEach(collection => {
            const collectionElement = this.createCollectionElement(collection);
            grid.appendChild(collectionElement);
        });
    }
    
    /**
     * Create a DOM element for a vibe collection
     */
    private createCollectionElement(collection: VibeCollection): HTMLElement {
        const element = document.createElement('div');
        element.className = 'vibe-collection-item';
        element.dataset.guid = collection.guid;
        
        const isCompatible = this.validateModelCompatibility(collection.model, this.currentModel);
        const compatibilityClass = isCompatible ? 'compatible' : 'incompatible';
        const compatibilityIcon = isCompatible ? '✓' : '⚠️';
        
        element.innerHTML = `
            <div class="vibe-collection-preview">
                <img src="${collection.preview_image}" alt="${collection.name}" class="vibe-thumbnail">
                <div class="vibe-collection-overlay ${compatibilityClass}">
                    <span class="compatibility-icon">${compatibilityIcon}</span>
                </div>
            </div>
            <div class="vibe-collection-info">
                <h4 class="vibe-collection-name">${this.escapeHtml(collection.name)}</h4>
                <p class="vibe-collection-model">Model: ${collection.model}</p>
                <p class="vibe-collection-date">${this.formatDate(collection.created_at)}</p>
                ${!isCompatible ? '<p class="compatibility-warning">⚠️ Model incompatible</p>' : ''}
            </div>
        `;
        
        // Add click handler
        element.addEventListener('click', () => this.selectCollection(collection));
        
        return element;
    }
    
    /**
     * Handle collection selection
     */
    private async selectCollection(collection: VibeCollection): Promise<void> {
        // Check if already selected
        const existingIndex = this.selectedVibes.findIndex(v => v.guid === collection.guid);
        if (existingIndex !== -1) {
            // Remove from selection
            this.selectedVibes.splice(existingIndex, 1);
            this.updateSelectedVibesCount();
            this.hideSelectionControls();
            this.updateCollectionSelection();
            return;
        }
        
        // Check vibe count constraint
        if (!this.validateVibeCount([...this.selectedVibes, {} as SelectedVibe])) {
            this.showValidationMessage('Maximum 4 vibes allowed', 'error');
            return;
        }
        
        // Check model compatibility
        if (!this.validateModelCompatibility(collection.model, this.currentModel)) {
            this.showValidationMessage('This vibe is incompatible with the current model', 'warning');
            // Still allow selection but show warning
        }
        
        try {
            // Load collection details to get available encoding strengths
            const details = await this.loadCollectionDetails(collection.guid);
            
            // Add to selection with default values
            const selectedVibe: SelectedVibe = {
                guid: collection.guid,
                name: collection.name,
                encoding_strength: 1.0, // Default to highest strength
                reference_strength: 1.0, // Default to highest strength
                model: collection.model
            };
            
            this.selectedVibes.push(selectedVibe);
            this.updateSelectedVibesCount();
            this.showSelectionControls(selectedVibe, details);
            this.updateCollectionSelection();
            
        } catch (error) {
            console.error('Error loading collection details:', error);
            this.showError('Failed to load vibe details. Please try again.');
        }
    }
    
    /**
     * Load detailed information for a vibe collection
     */
    private async loadCollectionDetails(guid: string): Promise<VibeCollectionDetails> {
        const response = await fetch(`/vibes/${guid}`);
        
        if (!response.ok) {
            throw new Error(`Failed to load vibe details: ${response.statusText}`);
        }
        
        return await response.json();
    }
    
    /**
     * Show the vibe selection controls for the currently selected vibe
     */
    private showSelectionControls(selectedVibe: SelectedVibe, details: VibeCollectionDetails): void {
        const controls = document.getElementById('vibe-selection-controls');
        if (!controls) return;
        
        controls.style.display = 'block';
        
        // Update preview image
        this.updatePreviewImage(selectedVibe, details);
        
        // Set slider values
        const encodingSlider = document.getElementById('encoding-strength-slider') as HTMLInputElement;
        const referenceSlider = document.getElementById('reference-strength-slider') as HTMLInputElement;
        
        if (encodingSlider) {
            const encodingIndex = VibeSelectionModal.VALID_ENCODING_STRENGTHS.indexOf(selectedVibe.encoding_strength);
            encodingSlider.value = encodingIndex.toString();
        }
        
        if (referenceSlider) {
            referenceSlider.value = selectedVibe.reference_strength.toString();
        }
        
        this.updateStrengthDisplays();
    }
    
    /**
     * Hide the vibe selection controls
     */
    private hideSelectionControls(): void {
        const controls = document.getElementById('vibe-selection-controls');
        if (controls) {
            controls.style.display = 'none';
        }
        this.clearValidationMessages();
    }
    
    /**
     * Update the preview image based on current strength settings
     */
    private updatePreviewImage(selectedVibe: SelectedVibe, details: VibeCollectionDetails): void {
        const previewImg = document.getElementById('vibe-preview-image') as HTMLImageElement;
        if (!previewImg) return;
        
        // Find closest reference strength for preview
        const closestRefStrength = this.findClosestReferenceStrength(selectedVibe.reference_strength);
        const previewKey = `enc${selectedVibe.encoding_strength}_ref${closestRefStrength}`;
        
        const previewPath = details.previews[previewKey];
        if (previewPath) {
            previewImg.src = previewPath;
        } else {
            // Fallback to first available preview
            const firstPreview = Object.values(details.previews)[0];
            if (firstPreview) {
                previewImg.src = firstPreview;
            }
        }
    }
    
    /**
     * Handle encoding strength slider change
     */
    private updateEncodingStrength(): void {
        const slider = document.getElementById('encoding-strength-slider') as HTMLInputElement;
        if (!slider || this.selectedVibes.length === 0) return;
        
        const strengthIndex = parseInt(slider.value);
        const newStrength = VibeSelectionModal.VALID_ENCODING_STRENGTHS[strengthIndex];
        
        // Update the last selected vibe
        const lastVibe = this.selectedVibes[this.selectedVibes.length - 1];
        lastVibe.encoding_strength = newStrength;
        
        this.updateStrengthDisplays();
        this.validateCurrentSelection();
        
        // Update preview if we have collection details
        // Note: In a full implementation, we'd cache the details
        this.loadCollectionDetails(lastVibe.guid).then(details => {
            this.updatePreviewImage(lastVibe, details);
        }).catch(console.error);
    }
    
    /**
     * Handle reference strength slider change
     */
    private updateReferenceStrength(): void {
        const slider = document.getElementById('reference-strength-slider') as HTMLInputElement;
        if (!slider || this.selectedVibes.length === 0) return;
        
        const newStrength = parseFloat(slider.value);
        
        // Update the last selected vibe
        const lastVibe = this.selectedVibes[this.selectedVibes.length - 1];
        lastVibe.reference_strength = newStrength;
        
        this.updateStrengthDisplays();
        this.validateCurrentSelection();
        
        // Update preview if we have collection details
        this.loadCollectionDetails(lastVibe.guid).then(details => {
            this.updatePreviewImage(lastVibe, details);
        }).catch(console.error);
    }
    
    /**
     * Update the strength display values
     */
    private updateStrengthDisplays(): void {
        const encodingValue = document.getElementById('encoding-strength-value');
        const referenceValue = document.getElementById('reference-strength-value');
        const encodingSlider = document.getElementById('encoding-strength-slider') as HTMLInputElement;
        const referenceSlider = document.getElementById('reference-strength-slider') as HTMLInputElement;
        
        if (encodingValue && encodingSlider) {
            const strengthIndex = parseInt(encodingSlider.value);
            const strength = VibeSelectionModal.VALID_ENCODING_STRENGTHS[strengthIndex];
            encodingValue.textContent = strength.toString();
        }
        
        if (referenceValue && referenceSlider) {
            const strength = parseFloat(referenceSlider.value);
            referenceValue.textContent = strength.toFixed(2);
        }
    }
    
    /**
     * Update the selected vibes count display
     */
    private updateSelectedVibesCount(): void {
        const countElement = document.getElementById('selected-vibes-count');
        if (countElement) {
            countElement.textContent = this.selectedVibes.length.toString();
        }
        
        // Update confirm button state
        const confirmBtn = document.getElementById('vibe-modal-confirm') as HTMLButtonElement;
        if (confirmBtn) {
            confirmBtn.disabled = this.selectedVibes.length === 0;
        }
    }
    
    /**
     * Update visual selection state of collection items
     */
    private updateCollectionSelection(): void {
        const items = document.querySelectorAll('.vibe-collection-item');
        items.forEach(item => {
            const guid = item.getAttribute('data-guid');
            const isSelected = this.selectedVibes.some(v => v.guid === guid);
            item.classList.toggle('selected', isSelected);
        });
    }
    
    /**
     * Validate current selection and show appropriate messages
     */
    private validateCurrentSelection(): void {
        this.clearValidationMessages();
        
        // Validate vibe count
        if (!this.validateVibeCount(this.selectedVibes)) {
            if (this.selectedVibes.length === 0) {
                this.showValidationMessage('Select at least 1 vibe', 'info');
            } else {
                this.showValidationMessage('Maximum 4 vibes allowed', 'error');
            }
            return;
        }
        
        // Validate each vibe
        for (const vibe of this.selectedVibes) {
            if (!this.validateEncodingStrength(vibe.encoding_strength)) {
                this.showValidationMessage(`Invalid encoding strength: ${vibe.encoding_strength}`, 'error');
                return;
            }
            
            if (!this.validateReferenceStrengthRange(vibe.reference_strength)) {
                this.showValidationMessage(`Reference strength must be between 0.0 and 1.0`, 'error');
                return;
            }
            
            if (!this.validateModelCompatibility(vibe.model, this.currentModel)) {
                this.showValidationMessage(`Vibe "${vibe.name}" is incompatible with current model`, 'warning');
            }
        }
        
        if (this.selectedVibes.length > 0) {
            this.showValidationMessage('Selection is valid', 'success');
        }
    }
    
    /**
     * Confirm the current selection and close modal
     */
    private confirmSelection(): void {
        if (this.selectedVibes.length === 0) {
            this.showValidationMessage('Please select at least one vibe', 'error');
            return;
        }
        
        // Final validation
        if (!this.validateVibeCount(this.selectedVibes)) {
            this.showValidationMessage('Invalid vibe count', 'error');
            return;
        }
        
        // Call the callback with selected vibes
        if (this.onVibeSelectedCallback) {
            this.onVibeSelectedCallback([...this.selectedVibes]);
        }
        
        this.hide();
    }
    
    /**
     * Show validation message
     */
    private showValidationMessage(message: string, type: 'info' | 'warning' | 'error' | 'success'): void {
        const container = document.getElementById('vibe-validation-messages');
        if (!container) return;
        
        const messageElement = document.createElement('div');
        messageElement.className = `validation-message validation-${type}`;
        messageElement.textContent = message;
        
        container.appendChild(messageElement);
    }
    
    /**
     * Clear all validation messages
     */
    private clearValidationMessages(): void {
        const container = document.getElementById('vibe-validation-messages');
        if (container) {
            container.innerHTML = '';
        }
    }
    
    /**
     * Show error message
     */
    private showError(message: string): void {
        this.showValidationMessage(message, 'error');
    }
    
    // Validation methods (implementing the business logic from property tests)
    
    /**
     * Validate vibe count constraint (1-4 vibes)
     */
    private validateVibeCount(vibes: SelectedVibe[]): boolean {
        return vibes.length >= VibeSelectionModal.MIN_VIBES && vibes.length <= VibeSelectionModal.MAX_VIBES;
    }
    
    /**
     * Validate encoding strength is one of the allowed values
     */
    private validateEncodingStrength(encodingStrength: number): boolean {
        return VibeSelectionModal.VALID_ENCODING_STRENGTHS.includes(encodingStrength);
    }
    
    /**
     * Validate reference strength is in range [0.0, 1.0]
     */
    private validateReferenceStrengthRange(referenceStrength: number): boolean {
        return referenceStrength >= 0.0 && referenceStrength <= 1.0;
    }
    
    /**
     * Validate model compatibility
     */
    private validateModelCompatibility(vibeModel: string, currentModel: string): boolean {
        return vibeModel === currentModel;
    }
    
    /**
     * Find closest reference strength for preview display
     */
    private findClosestReferenceStrength(targetStrength: number): number {
        if (targetStrength < 0.0 || targetStrength > 1.0) {
            throw new Error('Target strength must be in range [0.0, 1.0]');
        }
        
        return VibeSelectionModal.VALID_REFERENCE_STRENGTHS.reduce((closest, current) => {
            return Math.abs(current - targetStrength) < Math.abs(closest - targetStrength) ? current : closest;
        });
    }
    
    // Utility methods
    
    /**
     * Escape HTML to prevent XSS
     */
    private escapeHtml(text: string): string {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    /**
     * Format Unix timestamp to readable date
     */
    private formatDate(timestamp: number): string {
        return new Date(timestamp * 1000).toLocaleDateString();
    }
    
    /**
     * Get selected vibes formatted for generation API
     */
    public getVibesForGeneration(): VibeGenerationParams {
        // This would need to fetch the actual encoded data for each vibe
        // For now, return the structure that would be used
        return {
            reference_image_multiple: [], // Would be populated with base64 encoded data
            reference_strength_multiple: this.selectedVibes.map(v => v.reference_strength)
        };
    }
}

// Export singleton instance
export const vibeSelectionModal = new VibeSelectionModal();