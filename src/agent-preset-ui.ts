// Agent preset UI management functions

import * as agentPresets from './agent-presets.js';
import { AgentPreset, AgentPresetFormData } from './agent-presets.js';

let allAgentPresets: AgentPreset[] = [];
let isModalOpen = false;
let currentEditingPreset: AgentPreset | null = null;

/**
 * Initialize agent preset UI components
 */
export async function initializeAgentPresetUI(): Promise<void> {
    try {
        console.log('Initializing agent preset UI...');
        
        // Log environment info for debugging
        console.log('Current URL:', window.location.href);
        console.log('User logged in:', document.querySelector('.user-info') !== null);
        
        // Set up event listeners first (they don't depend on server data)
        setupEventListeners();
        
        // Set up tab visibility handling
        setupTabVisibilityHandling();
        
        // Try to load presets from server
        try {
            await refreshAgentPresets();
            console.log('Agent presets loaded successfully');
        } catch (presetError) {
            console.warn('Failed to load agent presets, continuing with empty list:', presetError);
            // Initialize with empty presets list so UI still works
            allAgentPresets = [];
            renderAgentPresetSelector();
            
            // Show a user-friendly message only if user is logged in
            if (document.querySelector('.user-info')) {
                showAgentPresetWarning('Unable to load agent presets. You can still use the default assistant.');
            } else {
                console.log('User not logged in, skipping preset warning');
            }
        }
        
        // Try to load active preset from storage (this should work even if server fails)
        try {
            await agentPresets.loadActivePresetFromStorage();
        } catch (storageError) {
            console.warn('Failed to load active preset from storage:', storageError);
            // Continue without saved preset
        }
        
        // Initialize UI components (these should always work)
        renderAgentPresetSelector();
        renderReasoningLevelSelector();
        updateReasoningLevelIndicator();
        
        console.log('Agent preset UI initialization completed');
        
    } catch (error) {
        console.error('Critical error initializing agent preset UI:', error);
        
        // Even if everything fails, try to set up basic UI
        try {
            allAgentPresets = [];
            setupEventListeners();
            renderAgentPresetSelector();
            renderReasoningLevelSelector();
            showAgentPresetError('Agent preset system unavailable. Using default assistant only.');
        } catch (fallbackError) {
            console.error('Failed to initialize fallback UI:', fallbackError);
        }
    }
}

/**
 * Set up event listeners for agent preset UI
 */
function setupEventListeners(): void {
    // Agent preset selector
    const presetSelector = document.getElementById('agent-preset-selector');
    if (presetSelector) {
        presetSelector.addEventListener('change', handlePresetSelection);
    }
    
    // Reasoning level selector
    const reasoningSelector = document.getElementById('reasoning-level-selector');
    if (reasoningSelector) {
        reasoningSelector.addEventListener('change', handleReasoningLevelSelection);
    }
    
    // Clear reasoning override button
    const clearOverrideButton = document.getElementById('clear-reasoning-override');
    if (clearOverrideButton) {
        clearOverrideButton.addEventListener('click', clearReasoningOverride);
    }
    
    // Listen for reasoning indicator updates
    document.addEventListener('updateReasoningIndicator', updateReasoningLevelIndicator);
    
    // Manage presets button
    const manageButton = document.getElementById('manage-presets-btn');
    if (manageButton) {
        manageButton.addEventListener('click', openPresetManagementModal);
    }
    
    // Create new preset button (in management modal)
    const createNewButton = document.getElementById('create-new-preset-btn');
    if (createNewButton) {
        createNewButton.addEventListener('click', () => openAgentPresetModal());
    }
    
    // Management modal close button
    const managementCloseButton = document.getElementById('preset-management-modal-close');
    if (managementCloseButton) {
        managementCloseButton.addEventListener('click', closePresetManagementModal);
    }
    
    // Toggle preset controls button
    const toggleButton = document.getElementById('toggle-preset-controls');
    if (toggleButton) {
        toggleButton.addEventListener('click', togglePresetControls);
    }
    
    // Make header clickable to toggle
    const presetHeader = document.getElementById('preset-header');
    if (presetHeader) {
        presetHeader.addEventListener('click', (e) => {
            // Don't toggle if clicking on buttons
            if (!(e.target as HTMLElement).closest('button')) {
                togglePresetControls();
            }
        });
    }
    
    // Modal event listeners
    const modal = document.getElementById('agent-preset-modal');
    const closeButton = document.getElementById('preset-modal-close');
    const cancelButton = document.getElementById('preset-modal-cancel');
    const saveButton = document.getElementById('preset-modal-save');
    const deleteButton = document.getElementById('preset-modal-delete');
    
    if (closeButton) {
        closeButton.addEventListener('click', closeAgentPresetModal);
    }
    
    if (cancelButton) {
        cancelButton.addEventListener('click', closeAgentPresetModal);
    }
    
    if (saveButton) {
        saveButton.addEventListener('click', handlePresetSave);
    }
    
    if (deleteButton) {
        deleteButton.addEventListener('click', handlePresetDelete);
    }
    
    // Modal backdrop click for form modal
    if (modal) {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                closeAgentPresetModal();
            }
        });
    }
    
    // Modal backdrop click for management modal
    const managementModal = document.getElementById('agent-preset-management-modal');
    if (managementModal) {
        managementModal.addEventListener('click', (e) => {
            if (e.target === managementModal) {
                closePresetManagementModal();
            }
        });
    }
    
    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            if (isModalOpen) {
                closeAgentPresetModal();
            } else if (managementModal && managementModal.style.display === 'block') {
                closePresetManagementModal();
            }
        }
    });
    
    // Form validation
    const form = document.getElementById('agent-preset-form');
    if (form) {
        form.addEventListener('input', validateFormRealTime);
    }
}

/**
 * Refresh agent presets from server
 */
async function refreshAgentPresets(): Promise<void> {
    try {
        console.log('Refreshing agent presets from server...');
        allAgentPresets = await agentPresets.loadAgentPresets();
        renderAgentPresetSelector();
        console.log('Agent presets refreshed successfully');
    } catch (error) {
        console.error('Failed to refresh agent presets:', error);
        
        // Provide more context about the error
        if (error instanceof Error) {
            if (error.message.includes('401') || error.message.includes('Unauthorized')) {
                throw new Error('Authentication required. Please refresh the page and log in again.');
            } else if (error.message.includes('403') || error.message.includes('Forbidden')) {
                throw new Error('Access denied. You may not have permission to access agent presets.');
            } else if (error.message.includes('404') || error.message.includes('Not Found')) {
                throw new Error('Agent presets feature not available on this server.');
            } else if (error.message.includes('500') || error.message.includes('Internal Server Error')) {
                throw new Error('Server error. Please try again later or contact support.');
            } else if (error.message.includes('Network error')) {
                throw new Error('Network connection problem. Please check your internet connection.');
            }
        }
        
        throw error;
    }
}

/**
 * Render the agent preset selector dropdown
 */
function renderAgentPresetSelector(): void {
    const selector = document.getElementById('agent-preset-selector') as HTMLSelectElement;
    if (!selector) return;
    
    // Clear existing options
    selector.innerHTML = '';
    
    // Add default option
    const defaultOption = document.createElement('option');
    defaultOption.value = '';
    defaultOption.textContent = 'Default Assistant';
    selector.appendChild(defaultOption);
    
    // Add preset options (filter out the default preset since we already added it manually)
    allAgentPresets
        .filter(preset => preset.id !== 'default')
        .forEach(preset => {
            const option = document.createElement('option');
            option.value = preset.id;
            option.textContent = preset.name;
            selector.appendChild(option);
        });
    
    // Set current selection
    if (agentPresets.chatState.activeAgentPreset) {
        selector.value = agentPresets.chatState.activeAgentPreset.id;
    }
}

/**
 * Render the reasoning level selector
 */
function renderReasoningLevelSelector(): void {
    const selector = document.getElementById('reasoning-level-selector') as HTMLSelectElement;
    if (!selector) return;
    
    // Clear existing options
    selector.innerHTML = '';
    
    // Add default option (use preset default)
    const defaultOption = document.createElement('option');
    defaultOption.value = '';
    defaultOption.textContent = 'Use Preset Default';
    selector.appendChild(defaultOption);
    
    // Add reasoning level options
    const levels = [
        { value: 'high', label: 'High (Detailed Analysis)' },
        { value: 'medium', label: 'Medium (Balanced)' },
        { value: 'low', label: 'Low (Quick Response)' },
        { value: 'none', label: 'None (Quickest Response)' }
    ];
    
    levels.forEach(level => {
        const option = document.createElement('option');
        option.value = level.value;
        option.textContent = level.label;
        selector.appendChild(option);
    });
    
    // Set current selection
    selector.value = agentPresets.chatState.messageReasoningLevel || '';
}

/**
 * Handle agent preset selection
 */
async function handlePresetSelection(event: Event): Promise<void> {
    const selector = event.target as HTMLSelectElement;
    const presetId = selector.value;
    
    try {
        if (presetId) {
            const preset = allAgentPresets.find(p => p.id === presetId);
            if (preset) {
                agentPresets.setActiveAgentPreset(preset);
            } else {
                throw new Error('Selected preset not found');
            }
        } else {
            agentPresets.setActiveAgentPreset(null);
        }
    } catch (error) {
        console.error('Error selecting preset:', error);
        agentPresets.handleAgentPresetError(error as Error, 'select');
        
        // Reset selector to previous value
        if (agentPresets.chatState.activeAgentPreset) {
            selector.value = agentPresets.chatState.activeAgentPreset.id;
        } else {
            selector.value = '';
        }
    }
}

/**
 * Handle reasoning level selection
 */
function handleReasoningLevelSelection(event: Event): void {
    const selector = event.target as HTMLSelectElement;
    const level = selector.value as 'high' | 'medium' | 'low' | 'none' | '';
    
    try {
        agentPresets.setMessageReasoningLevel(level || null);
        updateReasoningLevelIndicator();
    } catch (error) {
        handleReasoningLevelError(error as Error, 'set');
        
        // Reset selector to previous valid state
        if (agentPresets.chatState.messageReasoningLevel) {
            selector.value = agentPresets.chatState.messageReasoningLevel;
        } else {
            selector.value = '';
        }
    }
}

/**
 * Clear reasoning level override
 */
function clearReasoningOverride(): void {
    try {
        agentPresets.setMessageReasoningLevel(null);
        
        // Update the selector
        const reasoningSelector = document.getElementById('reasoning-level-selector') as HTMLSelectElement;
        if (reasoningSelector) {
            reasoningSelector.value = '';
        }
        
        updateReasoningLevelIndicator();
    } catch (error) {
        handleReasoningLevelError(error as Error, 'clear');
    }
}

/**
 * Update the reasoning level indicator in the input area
 */
function updateReasoningLevelIndicator(): void {
    try {
        const indicator = document.getElementById('reasoning-level-indicator');
        const displayElement = document.getElementById('reasoning-override-display');
        
        if (!indicator || !displayElement) return;
        
        const isOverride = agentPresets.chatState.messageReasoningLevel !== null;
        
        if (isOverride) {
            const level = agentPresets.chatState.messageReasoningLevel!;
            const displayText = formatReasoningLevelForIndicator(level);
            displayElement.textContent = displayText;
            indicator.style.display = 'block';
        } else {
            indicator.style.display = 'none';
        }
    } catch (error) {
        handleReasoningLevelError(error as Error, 'display');
    }
}

/**
 * Format reasoning level for the input area indicator
 */
function formatReasoningLevelForIndicator(level: string): string {
    switch (level) {
        case 'high':
            return '🧠High';
        case 'medium':
            return '⚡Medium';
        case 'low':
            return '💨Low';
        case 'none':
            return '✖️None';
        default:
            return level;
    }
}

/**
 * Handle reasoning level operation failures with retry logic
 */
export function handleReasoningLevelError(error: Error, operation: string, retryCount: number = 0): void {
    console.error(`Reasoning level ${operation} error (attempt ${retryCount + 1}):`, error);
    
    const maxRetries = 2;
    
    if (retryCount < maxRetries) {
        // Retry after a short delay
        setTimeout(() => {
            try {
                switch (operation) {
                    case 'set':
                        // Retry setting the reasoning level
                        const currentLevel = agentPresets.chatState.messageReasoningLevel;
                        agentPresets.setMessageReasoningLevel(currentLevel);
                        updateReasoningLevelIndicator();
                        break;
                    case 'clear':
                        // Retry clearing the reasoning level
                        clearReasoningOverride();
                        break;
                    case 'display':
                        // Retry updating the display
                        updateReasoningLevelIndicator();
                        break;
                }
            } catch (retryError) {
                handleReasoningLevelError(retryError as Error, operation, retryCount + 1);
            }
        }, 1000 * (retryCount + 1)); // Exponential backoff
    } else {
        // Max retries reached, show user-friendly error
        let message = `Failed to ${operation} reasoning level`;
        
        if (error.message.includes('Network')) {
            message = 'Network error - reasoning level changes may not be saved';
        } else if (error.message.includes('validation')) {
            message = 'Invalid reasoning level - using default instead';
        }
        
        showReasoningLevelError(message);
        
        // Fallback to safe state
        try {
            agentPresets.setMessageReasoningLevel(null);
            updateReasoningLevelIndicator();
        } catch (fallbackError) {
            console.error('Failed to reset to safe state:', fallbackError);
        }
    }
}

/**
 * Show reasoning level error message to user
 */
function showReasoningLevelError(message: string): void {
    console.error('Reasoning level error:', message);
    
    // Try to use existing error display mechanism
    const errorContainer = document.getElementById('agent-preset-error');
    if (errorContainer) {
        errorContainer.textContent = message;
        errorContainer.style.display = 'block';
        
        // Auto-hide after 5 seconds
        setTimeout(() => {
            errorContainer.style.display = 'none';
        }, 5000);
    } else {
        // Fallback to console warning if no error container
        console.warn('No error container found, reasoning level error:', message);
    }
}

/**
 * Open the agent preset management modal
 */
function openAgentPresetModal(preset?: AgentPreset): void {
    const modal = document.getElementById('agent-preset-modal');
    if (!modal) return;
    
    isModalOpen = true;
    currentEditingPreset = preset || null;
    
    // Set modal title and button text
    const title = document.getElementById('preset-modal-title');
    const saveButton = document.getElementById('preset-modal-save') as HTMLButtonElement;
    const deleteButton = document.getElementById('preset-modal-delete') as HTMLButtonElement;
    
    if (title) {
        title.textContent = preset ? 'Edit Agent Preset' : 'Create New Agent Preset';
    }
    
    if (saveButton) {
        saveButton.textContent = preset ? 'Update Preset' : 'Create Preset';
    }
    
    if (deleteButton) {
        deleteButton.style.display = preset ? 'inline-block' : 'none';
    }
    
    // Populate form
    populatePresetForm(preset);
    
    // Clear any previous errors
    clearFormErrors();
    
    // Show modal
    modal.style.display = 'block';
    
    // Focus on name field
    const nameField = document.getElementById('preset-name') as HTMLInputElement;
    if (nameField) {
        nameField.focus();
    }
}

/**
 * Close the agent preset management modal
 */
function closeAgentPresetModal(): void {
    const modal = document.getElementById('agent-preset-modal');
    if (!modal) return;
    
    isModalOpen = false;
    currentEditingPreset = null;
    
    modal.style.display = 'none';
    clearFormErrors();
}

/**
 * Populate the preset form with data
 */
function populatePresetForm(preset?: AgentPreset): void {
    const nameField = document.getElementById('preset-name') as HTMLInputElement;
    const instructionsField = document.getElementById('preset-instructions') as HTMLTextAreaElement;
    const modelField = document.getElementById('preset-model') as HTMLSelectElement;
    const reasoningField = document.getElementById('preset-reasoning-level') as HTMLSelectElement;
    
    if (preset) {
        if (nameField) nameField.value = preset.name;
        if (instructionsField) instructionsField.value = preset.instructions;
        if (modelField) modelField.value = preset.model;
        if (reasoningField) reasoningField.value = preset.default_reasoning_level;
    } else {
        if (nameField) nameField.value = '';
        if (instructionsField) instructionsField.value = '';
        if (modelField) modelField.value = 'gpt-5.1';
        if (reasoningField) reasoningField.value = 'medium';
    }
}

/**
 * Handle preset save (create or update)
 */
async function handlePresetSave(): Promise<void> {
    try {
        const formData = getFormData();
        const errors = agentPresets.validateAgentPresetForm(formData);
        
        if (errors.length > 0) {
            displayFormErrors(errors);
            return;
        }
        
        // Disable save button during operation
        const saveButton = document.getElementById('preset-modal-save') as HTMLButtonElement;
        if (saveButton) {
            saveButton.disabled = true;
            saveButton.textContent = 'Saving...';
        }
        
        let savedPreset: AgentPreset;
        
        if (currentEditingPreset) {
            // Update existing preset
            savedPreset = await agentPresets.updateAgentPreset(currentEditingPreset.id, formData);
        } else {
            // Create new preset
            savedPreset = await agentPresets.createAgentPreset(formData);
        }
        
        // Refresh presets list
        await refreshAgentPresets();
        
        // If this was the active preset, update it
        if (agentPresets.chatState.activeAgentPreset?.id === savedPreset.id) {
            agentPresets.setActiveAgentPreset(savedPreset);
        }
        
        // Close modal
        closeAgentPresetModal();
        
        // Refresh management modal if it's open
        const managementModal = document.getElementById('agent-preset-management-modal');
        if (managementModal && managementModal.style.display === 'block') {
            renderPresetList();
        }
        
        // Show success message
        showSuccessMessage(currentEditingPreset ? 'Preset updated successfully' : 'Preset created successfully');
        
    } catch (error) {
        console.error('Error saving preset:', error);
        agentPresets.handleAgentPresetError(error as Error, currentEditingPreset ? 'update' : 'create');
    } finally {
        // Re-enable save button
        const saveButton = document.getElementById('preset-modal-save') as HTMLButtonElement;
        if (saveButton) {
            saveButton.disabled = false;
            saveButton.textContent = currentEditingPreset ? 'Update Preset' : 'Create Preset';
        }
    }
}

/**
 * Handle preset deletion with confirmation
 */
async function handlePresetDelete(): Promise<void> {
    if (!currentEditingPreset) return;
    
    const presetName = currentEditingPreset.name;
    const confirmed = confirm(`Are you sure you want to delete the preset "${presetName}"? This action cannot be undone.`);
    
    if (!confirmed) return;
    
    try {
        // Disable delete button during operation
        const deleteButton = document.getElementById('preset-modal-delete') as HTMLButtonElement;
        if (deleteButton) {
            deleteButton.disabled = true;
            deleteButton.textContent = 'Deleting...';
        }
        
        await agentPresets.deleteAgentPreset(currentEditingPreset.id);
        
        // If this was the active preset, clear it
        if (agentPresets.chatState.activeAgentPreset?.id === currentEditingPreset.id) {
            agentPresets.setActiveAgentPreset(null);
        }
        
        // Refresh presets list
        await refreshAgentPresets();
        
        // Close modal
        closeAgentPresetModal();
        
        // Show success message
        showSuccessMessage('Preset deleted successfully');
        
    } catch (error) {
        console.error('Error deleting preset:', error);
        agentPresets.handleAgentPresetError(error as Error, 'delete');
    } finally {
        // Re-enable delete button
        const deleteButton = document.getElementById('preset-modal-delete') as HTMLButtonElement;
        if (deleteButton) {
            deleteButton.disabled = false;
            deleteButton.textContent = 'Delete Preset';
        }
    }
}

/**
 * Get form data from the modal
 */
function getFormData(): AgentPresetFormData {
    const nameField = document.getElementById('preset-name') as HTMLInputElement;
    const instructionsField = document.getElementById('preset-instructions') as HTMLTextAreaElement;
    const modelField = document.getElementById('preset-model') as HTMLSelectElement;
    const reasoningField = document.getElementById('preset-reasoning-level') as HTMLSelectElement;
    
    return {
        name: nameField?.value?.trim() || '',
        instructions: instructionsField?.value?.trim() || '',
        model: (modelField?.value as 'gpt-5.1' | 'gpt-5' | 'gpt-5-mini' | 'gpt-5-pro') || 'gpt-5.1',
        default_reasoning_level: (reasoningField?.value as 'high' | 'medium' | 'low' | 'none') || 'medium'
    };
}

/**
 * Validate form in real-time
 */
function validateFormRealTime(): void {
    const formData = getFormData();
    const errors = agentPresets.validateAgentPresetForm(formData);
    
    // Update field-specific validation
    updateFieldValidation('preset-name', formData.name.length === 0 ? ['Name is required'] : []);
    updateFieldValidation('preset-instructions', formData.instructions.length === 0 ? ['Instructions are required'] : []);
    
    // Update save button state
    const saveButton = document.getElementById('preset-modal-save') as HTMLButtonElement;
    if (saveButton) {
        saveButton.disabled = errors.length > 0;
    }
}

/**
 * Update validation state for a specific field
 */
function updateFieldValidation(fieldId: string, errors: string[]): void {
    const field = document.getElementById(fieldId);
    if (!field) return;
    
    if (errors.length > 0) {
        field.classList.add('error');
    } else {
        field.classList.remove('error');
    }
}

/**
 * Display form validation errors
 */
function displayFormErrors(errors: string[]): void {
    const errorContainer = document.getElementById('preset-form-errors');
    if (!errorContainer) return;
    
    errorContainer.innerHTML = '';
    
    if (errors.length > 0) {
        const errorList = document.createElement('ul');
        errors.forEach(error => {
            const errorItem = document.createElement('li');
            errorItem.textContent = error;
            errorList.appendChild(errorItem);
        });
        
        errorContainer.appendChild(errorList);
        errorContainer.style.display = 'block';
    } else {
        errorContainer.style.display = 'none';
    }
}

/**
 * Clear form validation errors
 */
function clearFormErrors(): void {
    const errorContainer = document.getElementById('preset-form-errors');
    if (errorContainer) {
        errorContainer.innerHTML = '';
        errorContainer.style.display = 'none';
    }
    
    // Clear field-level errors
    const fields = ['preset-name', 'preset-instructions'];
    fields.forEach(fieldId => {
        const field = document.getElementById(fieldId);
        if (field) {
            field.classList.remove('error');
        }
    });
}

/**
 * Show success message
 */
function showSuccessMessage(message: string): void {
    const successContainer = document.getElementById('agent-preset-success');
    if (successContainer) {
        successContainer.textContent = message;
        successContainer.style.display = 'block';
        
        // Auto-hide after 3 seconds
        setTimeout(() => {
            successContainer.style.display = 'none';
        }, 3000);
    }
}

/**
 * Show warning message to user
 */
function showAgentPresetWarning(message: string): void {
    console.warn('Agent preset warning:', message);
    agentPresets.showWarningMessage(message);
}

/**
 * Show error message to user
 */
function showAgentPresetError(message: string): void {
    console.error('Agent preset error:', message);
    agentPresets.handleAgentPresetError(new Error(message), 'load');
}

/**
 * Open the preset management modal
 */
function openPresetManagementModal(): void {
    const modal = document.getElementById('agent-preset-management-modal');
    if (!modal) return;
    
    modal.style.display = 'block';
    renderPresetList();
}

/**
 * Close the preset management modal
 */
function closePresetManagementModal(): void {
    const modal = document.getElementById('agent-preset-management-modal');
    if (!modal) return;
    
    modal.style.display = 'none';
}

/**
 * Render the list of presets in the management modal
 */
function renderPresetList(): void {
    const listContainer = document.getElementById('preset-list');
    const loadingElement = document.getElementById('preset-list-loading');
    const noPresetsElement = document.getElementById('no-presets-message');
    
    if (!listContainer || !loadingElement || !noPresetsElement) return;
    
    // Show loading state
    loadingElement.style.display = 'block';
    listContainer.innerHTML = '';
    noPresetsElement.style.display = 'none';
    
    // Filter out the default preset for the management interface
    const customPresets = allAgentPresets.filter(preset => preset.id !== 'default');
    
    // Hide loading state
    loadingElement.style.display = 'none';
    
    if (customPresets.length === 0) {
        noPresetsElement.style.display = 'block';
        return;
    }
    
    // Render each preset
    customPresets.forEach(preset => {
        const presetElement = createPresetListItem(preset);
        listContainer.appendChild(presetElement);
    });
}

/**
 * Create a preset list item element
 */
function createPresetListItem(preset: AgentPreset): HTMLElement {
    const isActive = agentPresets.chatState.activeAgentPreset?.id === preset.id;
    
    const presetItem = document.createElement('div');
    presetItem.className = `preset-item ${isActive ? 'active-preset' : ''}`;
    
    presetItem.innerHTML = `
        <div class="preset-info">
            <div class="preset-name">${escapeHtml(preset.name)}</div>
            <div class="preset-details">
                <span class="preset-model">${preset.model}</span>
                <span class="preset-reasoning">Reasoning: ${preset.default_reasoning_level}</span>
                ${isActive ? '<span class="preset-status active">Active</span>' : ''}
            </div>
            <div class="preset-instructions" title="${escapeHtml(preset.instructions)}">
                ${escapeHtml(preset.instructions)}
            </div>
        </div>
        <div class="preset-actions">
            ${!isActive ? `<button class="preset-action-btn select-btn" data-preset-id="${preset.id}">Select</button>` : ''}
            <button class="preset-action-btn edit-btn" data-preset-id="${preset.id}">Edit</button>
            <button class="preset-action-btn delete-btn" data-preset-id="${preset.id}">Delete</button>
        </div>
    `;
    
    // Add event listeners for action buttons
    const selectBtn = presetItem.querySelector('.select-btn');
    const editBtn = presetItem.querySelector('.edit-btn');
    const deleteBtn = presetItem.querySelector('.delete-btn');
    
    if (selectBtn) {
        selectBtn.addEventListener('click', () => selectPreset(preset.id));
    }
    
    if (editBtn) {
        editBtn.addEventListener('click', () => editPreset(preset.id));
    }
    
    if (deleteBtn) {
        deleteBtn.addEventListener('click', () => deletePreset(preset.id));
    }
    
    return presetItem;
}

/**
 * Select a preset as active
 */
async function selectPreset(presetId: string): Promise<void> {
    try {
        const preset = allAgentPresets.find(p => p.id === presetId);
        if (preset) {
            agentPresets.setActiveAgentPreset(preset);
            renderPresetList(); // Refresh the list to show new active state
            showSuccessMessage(`Activated preset: ${preset.name}`);
        }
    } catch (error) {
        console.error('Error selecting preset:', error);
        agentPresets.handleAgentPresetError(error as Error, 'select');
    }
}

/**
 * Edit a preset
 */
function editPreset(presetId: string): void {
    const preset = allAgentPresets.find(p => p.id === presetId);
    if (preset) {
        closePresetManagementModal();
        openAgentPresetModal(preset);
    }
}

/**
 * Delete a preset with confirmation
 */
async function deletePreset(presetId: string): Promise<void> {
    const preset = allAgentPresets.find(p => p.id === presetId);
    if (!preset) return;
    
    const confirmed = confirm(`Are you sure you want to delete the preset "${preset.name}"? This action cannot be undone.`);
    if (!confirmed) return;
    
    try {
        await agentPresets.deleteAgentPreset(presetId);
        
        // If this was the active preset, clear it
        if (agentPresets.chatState.activeAgentPreset?.id === presetId) {
            agentPresets.setActiveAgentPreset(null);
        }
        
        // Refresh presets list
        await refreshAgentPresets();
        renderPresetList();
        
        showSuccessMessage('Preset deleted successfully');
        
    } catch (error) {
        console.error('Error deleting preset:', error);
        agentPresets.handleAgentPresetError(error as Error, 'delete');
    }
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text: string): string {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Open preset management modal for editing a specific preset
 */
export function editAgentPreset(presetId: string): void {
    const preset = allAgentPresets.find(p => p.id === presetId);
    if (preset) {
        openAgentPresetModal(preset);
    }
}

/**
 * Set up tab visibility handling for floating controls
 */
function setupTabVisibilityHandling(): void {
    // Get all tab buttons
    const tabButtons = document.querySelectorAll('.tablinks');
    const floatingControls = document.getElementById('floating-agent-controls');
    
    if (!floatingControls) return;
    
    // Add click listeners to all tab buttons
    tabButtons.forEach(button => {
        button.addEventListener('click', (e) => {
            const target = e.target as HTMLElement;
            const tabName = target.textContent?.trim();
            
            // Show floating controls only on Chat tab
            if (tabName === 'Chat') {
                floatingControls.style.display = 'block';
            } else {
                floatingControls.style.display = 'none';
                // Also collapse if expanded
                const expandedControls = document.getElementById('preset-controls-expanded');
                const toggleButton = document.getElementById('toggle-preset-controls');
                if (expandedControls && toggleButton) {
                    expandedControls.style.display = 'none';
                    toggleButton.textContent = '⮟';
                    toggleButton.classList.remove('expanded');
                    toggleButton.title = 'Expand Agent Controls';
                }
            }
        });
    });
    
    // Initially show only if Chat tab is active
    const chatTab = document.getElementById('chatTab');
    if (chatTab && chatTab.classList.contains('active')) {
        floatingControls.style.display = 'block';
    } else {
        floatingControls.style.display = 'none';
    }
}

/**
 * Toggle the preset controls expanded/collapsed state
 */
function togglePresetControls(): void {
    const expandedControls = document.getElementById('preset-controls-expanded');
    const toggleButton = document.getElementById('toggle-preset-controls');
    
    if (!expandedControls || !toggleButton) return;
    
    const isExpanded = expandedControls.style.display === 'block';
    
    if (isExpanded) {
        // Collapse
        expandedControls.style.display = 'none';
        toggleButton.textContent = '⮟';
        toggleButton.classList.remove('expanded');
        toggleButton.title = 'Expand Agent Controls';
    } else {
        // Expand
        expandedControls.style.display = 'block';
        toggleButton.textContent = '⮝';
        toggleButton.classList.add('expanded');
        toggleButton.title = 'Collapse Agent Controls';
    }
}

/**
 * Get current chat state for use in chat requests
 */
export function getChatRequestData(): { agent_preset_id?: string; reasoning_level?: string } {
    const data: { agent_preset_id?: string; reasoning_level?: string } = {};
    
    if (agentPresets.chatState.activeAgentPreset) {
        data.agent_preset_id = agentPresets.chatState.activeAgentPreset.id;
    }
    
    const effectiveReasoningLevel = agentPresets.getEffectiveReasoningLevel();
    data.reasoning_level = effectiveReasoningLevel;
    
    return data;
}