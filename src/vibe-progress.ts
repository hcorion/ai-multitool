/**
 * Vibe Progress Modal Component
 * 
 * This module implements the progress modal for vibe encoding operations.
 * It displays real-time progress updates during encoding (5 steps) and 
 * preview generation (25 steps) phases, with live preview thumbnails.
 */

// Progress update interface matching the backend SSE format
interface ProgressUpdate {
    phase: 'encoding' | 'preview' | 'complete' | 'unknown';
    step: number;
    total: number;
    message: string;
    preview_url?: string;
    complete?: boolean;
    error?: string;
}

/**
 * Vibe Progress Modal Class
 * 
 * Manages the progress modal UI for vibe encoding operations,
 * including SSE connection for real-time updates and preview thumbnails.
 */
export class VibeProgressModal {
    private modal: HTMLElement | null = null;
    private eventSource: EventSource | null = null;
    private onCompleteCallback: (() => void) | null = null;
    private onErrorCallback: ((error: string) => void) | null = null;
    
    constructor() {
        this.createModalHTML();
        this.attachEventListeners();
    }
    
    /**
     * Create the modal HTML structure and inject it into the DOM
     */
    private createModalHTML(): void {
        const modalHTML = `
            <div id="vibe-progress-modal" class="modal" style="display: none;">
                <div class="modal-content vibe-progress-modal-content">
                    <div class="modal-header">
                        <h2>Creating Vibe Collection</h2>
                    </div>
                    <div class="modal-body">
                        <div class="vibe-progress-info">
                            <p id="vibe-progress-message">Initializing...</p>
                        </div>
                        
                        <div class="vibe-progress-bar-container">
                            <div class="vibe-progress-bar" id="vibe-progress-bar">
                                <div class="vibe-progress-fill" id="vibe-progress-fill" style="width: 0%"></div>
                            </div>
                            <div class="vibe-progress-text">
                                <span id="vibe-progress-step">0</span> / <span id="vibe-progress-total">30</span>
                            </div>
                        </div>
                        
                        <div class="vibe-progress-phases">
                            <div class="vibe-phase" id="vibe-phase-encoding">
                                <span class="phase-icon">⏳</span>
                                <span class="phase-label">Encoding (5 steps)</span>
                            </div>
                            <div class="vibe-phase" id="vibe-phase-preview">
                                <span class="phase-icon">⏳</span>
                                <span class="phase-label">Preview Generation (25 steps)</span>
                            </div>
                        </div>
                        
                        <div class="vibe-preview-thumbnails" id="vibe-preview-thumbnails">
                            <!-- Live preview thumbnails will appear here -->
                        </div>
                        
                        <div class="vibe-progress-error" id="vibe-progress-error" style="display: none;">
                            <span class="error-icon">⚠️</span>
                            <span class="error-message" id="vibe-error-message"></span>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button id="vibe-progress-close" class="btn btn-secondary" style="display: none;">Close</button>
                    </div>
                </div>
            </div>
        `;
        
        // Inject modal HTML into the document body
        document.body.insertAdjacentHTML('beforeend', modalHTML);
        this.modal = document.getElementById('vibe-progress-modal');
    }
    
    /**
     * Attach event listeners to modal elements
     */
    private attachEventListeners(): void {
        const closeBtn = document.getElementById('vibe-progress-close');
        closeBtn?.addEventListener('click', () => this.hide());
    }
    
    /**
     * Show the progress modal and start listening for SSE updates
     */
    public show(progressUrl: string, onComplete?: () => void, onError?: (error: string) => void): void {
        if (!this.modal) return;
        
        this.onCompleteCallback = onComplete || null;
        this.onErrorCallback = onError || null;
        
        // Reset UI state
        this.resetUI();
        
        // Show modal
        this.modal.style.display = 'block';
        
        // Start SSE connection
        this.startEventSource(progressUrl);
    }
    
    /**
     * Hide the progress modal and close SSE connection
     */
    public hide(): void {
        if (!this.modal) return;
        
        this.modal.style.display = 'none';
        this.closeEventSource();
    }
    
    /**
     * Reset the UI to initial state
     */
    private resetUI(): void {
        // Reset progress bar
        const progressFill = document.getElementById('vibe-progress-fill');
        const progressStep = document.getElementById('vibe-progress-step');
        const progressMessage = document.getElementById('vibe-progress-message');
        const closeBtn = document.getElementById('vibe-progress-close');
        const errorDiv = document.getElementById('vibe-progress-error');
        const thumbnailsDiv = document.getElementById('vibe-preview-thumbnails');
        
        if (progressFill) progressFill.style.width = '0%';
        if (progressStep) progressStep.textContent = '0';
        if (progressMessage) progressMessage.textContent = 'Initializing...';
        if (closeBtn) closeBtn.style.display = 'none';
        if (errorDiv) errorDiv.style.display = 'none';
        if (thumbnailsDiv) thumbnailsDiv.innerHTML = '';
        
        // Reset phase indicators
        this.updatePhaseIndicator('encoding', 'pending');
        this.updatePhaseIndicator('preview', 'pending');
    }
    
    /**
     * Start the EventSource connection for SSE updates
     */
    private startEventSource(progressUrl: string): void {
        this.closeEventSource();
        
        this.eventSource = new EventSource(progressUrl);
        
        this.eventSource.onmessage = (event) => {
            try {
                const update: ProgressUpdate = JSON.parse(event.data);
                this.updateProgress(update);
            } catch (error) {
                console.error('Error parsing progress update:', error);
            }
        };
        
        this.eventSource.onerror = (error) => {
            console.error('SSE connection error:', error);
            this.closeEventSource();
            this.showError('Connection lost. Please check if the vibe was created.');
        };
    }
    
    /**
     * Close the EventSource connection
     */
    private closeEventSource(): void {
        if (this.eventSource) {
            this.eventSource.close();
            this.eventSource = null;
        }
    }
    
    /**
     * Update the progress display based on SSE update
     */
    private updateProgress(update: ProgressUpdate): void {
        const progressFill = document.getElementById('vibe-progress-fill');
        const progressStep = document.getElementById('vibe-progress-step');
        const progressTotal = document.getElementById('vibe-progress-total');
        const progressMessage = document.getElementById('vibe-progress-message');
        
        // Update progress bar
        if (progressFill && update.total > 0) {
            const percentage = (update.step / update.total) * 100;
            progressFill.style.width = `${percentage}%`;
        }
        
        if (progressStep) progressStep.textContent = update.step.toString();
        if (progressTotal) progressTotal.textContent = update.total.toString();
        if (progressMessage) progressMessage.textContent = update.message;
        
        // Update phase indicators
        if (update.phase === 'encoding') {
            this.updatePhaseIndicator('encoding', 'active');
            this.updatePhaseIndicator('preview', 'pending');
        } else if (update.phase === 'preview') {
            this.updatePhaseIndicator('encoding', 'complete');
            this.updatePhaseIndicator('preview', 'active');
            
            // Add preview thumbnail if available
            if (update.preview_url) {
                this.addPreviewThumbnail(update.preview_url);
            }
        } else if (update.phase === 'complete') {
            this.updatePhaseIndicator('encoding', 'complete');
            this.updatePhaseIndicator('preview', 'complete');
            this.onComplete();
        }
        
        // Handle errors
        if (update.error) {
            this.showError(update.error);
        }
        
        // Handle completion
        if (update.complete && !update.error) {
            this.onComplete();
        }
    }
    
    /**
     * Update a phase indicator's visual state
     */
    private updatePhaseIndicator(phase: 'encoding' | 'preview', state: 'pending' | 'active' | 'complete'): void {
        const phaseElement = document.getElementById(`vibe-phase-${phase}`);
        if (!phaseElement) return;
        
        const iconElement = phaseElement.querySelector('.phase-icon');
        if (!iconElement) return;
        
        // Remove existing state classes
        phaseElement.classList.remove('pending', 'active', 'complete');
        phaseElement.classList.add(state);
        
        // Update icon
        switch (state) {
            case 'pending':
                iconElement.textContent = '⏳';
                break;
            case 'active':
                iconElement.textContent = '🔄';
                break;
            case 'complete':
                iconElement.textContent = '✅';
                break;
        }
    }
    
    /**
     * Add a preview thumbnail to the display
     */
    public addPreviewThumbnail(imageUrl: string): void {
        const thumbnailsDiv = document.getElementById('vibe-preview-thumbnails');
        if (!thumbnailsDiv) return;
        
        const thumbnail = document.createElement('img');
        thumbnail.src = imageUrl;
        thumbnail.className = 'vibe-progress-thumbnail';
        thumbnail.alt = 'Preview';
        
        thumbnailsDiv.appendChild(thumbnail);
        
        // Scroll to show latest thumbnail
        thumbnailsDiv.scrollLeft = thumbnailsDiv.scrollWidth;
    }
    
    /**
     * Show an error message
     */
    private showError(message: string): void {
        const errorDiv = document.getElementById('vibe-progress-error');
        const errorMessage = document.getElementById('vibe-error-message');
        const closeBtn = document.getElementById('vibe-progress-close');
        
        if (errorDiv) errorDiv.style.display = 'flex';
        if (errorMessage) errorMessage.textContent = message;
        if (closeBtn) closeBtn.style.display = 'block';
        
        this.closeEventSource();
        
        if (this.onErrorCallback) {
            this.onErrorCallback(message);
        }
    }
    
    /**
     * Handle completion
     */
    private onComplete(): void {
        const closeBtn = document.getElementById('vibe-progress-close');
        const progressMessage = document.getElementById('vibe-progress-message');
        
        if (closeBtn) closeBtn.style.display = 'block';
        if (progressMessage) progressMessage.textContent = 'Vibe collection created successfully!';
        
        this.closeEventSource();
        
        if (this.onCompleteCallback) {
            this.onCompleteCallback();
        }
    }
}

// Export singleton instance
export const vibeProgressModal = new VibeProgressModal();
