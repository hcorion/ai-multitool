// TypeScript interfaces and types for agent preset management

export interface AgentPreset {
    id: string;
    name: string;
    instructions: string;
    model: 'gpt-5.1' | 'gpt-5' | 'gpt-5-mini' | 'gpt-5-pro';
    default_reasoning_level: 'high' | 'medium' | 'low' | 'none';
    created_at: number;
    updated_at: number;
}

export interface ChatState {
    activeAgentPreset: AgentPreset | null;
    messageReasoningLevel: 'high' | 'medium' | 'low' | 'none' | null;
}

export interface AgentPresetFormData {
    name: string;
    instructions: string;
    model: 'gpt-5.1' | 'gpt-5' | 'gpt-5-mini' | 'gpt-5-pro';
    default_reasoning_level: 'high' | 'medium' | 'low' | 'none';
}

export interface AgentPresetAPIResponse {
    success?: boolean;
    preset?: AgentPreset;
    presets?: AgentPreset[];
    error?: string;
    message?: string;
}

// Global chat state
export let chatState: ChatState = {
    activeAgentPreset: null,
    messageReasoningLevel: null
};

// Local storage keys
const STORAGE_KEYS = {
    ACTIVE_PRESET_ID: 'ai_multitool_active_preset_id',
    PRESET_PREFERENCES: 'ai_multitool_preset_preferences'
} as const;

/**
 * Check if user is logged in by looking for user info in the page
 */
function isUserLoggedIn(): boolean {
    // Check if there's a user info element indicating login status
    const userInfo = document.querySelector('.user-info');
    return userInfo !== null;
}

/**
 * Test connectivity to the agent presets endpoint
 */
export async function testAgentPresetEndpoint(): Promise<{ available: boolean; error?: string }> {
    try {
        console.log('Testing agent preset endpoint connectivity...');
        
        const response = await fetch('/agents', {
            method: 'GET',
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
        });
        
        console.log('Endpoint test response:', response.status, response.statusText);
        
        if (response.ok) {
            return { available: true };
        } else {
            return { 
                available: false, 
                error: `HTTP ${response.status}: ${response.statusText}` 
            };
        }
    } catch (error) {
        console.error('Endpoint test failed:', error);
        return { 
            available: false, 
            error: error instanceof Error ? error.message : 'Unknown error' 
        };
    }
}

/**
 * Load agent presets from the server
 */
export async function loadAgentPresets(): Promise<AgentPreset[]> {
    try {
        console.log('Loading agent presets from /agents endpoint...');
        
        // Check if user is logged in first
        if (!isUserLoggedIn()) {
            console.log('User not logged in, skipping agent preset loading');
            return [];
        }
        
        const response = await fetch('/agents', {
            method: 'GET',
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
        });

        console.log('Agent presets response status:', response.status, response.statusText);

        if (!response.ok) {
            let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
            
            // Try to get more detailed error information
            try {
                const errorText = await response.text();
                console.log('Error response body:', errorText);
                
                // Try to parse as JSON for structured error
                try {
                    const errorData = JSON.parse(errorText);
                    if (errorData.error || errorData.message) {
                        errorMessage = errorData.error || errorData.message;
                    }
                } catch (parseError) {
                    // If not JSON, include the raw text
                    if (errorText && errorText.length < 200) {
                        errorMessage += ` - ${errorText}`;
                    }
                }
            } catch (textError) {
                console.warn('Could not read error response body:', textError);
            }
            
            throw new Error(`Failed to load presets: ${errorMessage}`);
        }

        const data: AgentPresetAPIResponse = await response.json();
        console.log('Agent presets response data:', data);
        
        // Handle different response formats
        if (data.hasOwnProperty('success') && !data.success) {
            const errorMessage = data.error || data.message || 'Unknown server error';
            throw new Error(`Server returned error: ${errorMessage}`);
        }
        
        // Handle direct presets array response (current backend format)
        if (data.hasOwnProperty('presets')) {
            const presets = data.presets || [];
            console.log(`Successfully loaded ${presets.length} agent presets`);
            return presets;
        }
        
        // Handle error responses
        if (data.hasOwnProperty('error')) {
            const errorMessage = data.error || 'Unknown server error';
            throw new Error(`Server returned error: ${errorMessage}`);
        }
        
        // If we get here, the response format is unexpected
        console.warn('Unexpected response format:', data);
        throw new Error('Unexpected response format from server');
        
    } catch (error) {
        // Enhanced error logging with more context
        if (error instanceof TypeError && error.message.includes('fetch')) {
            console.error('Network error loading agent presets - server may be down or unreachable:', error);
            throw new Error('Network error: Unable to connect to server. Please check your connection and try again.');
        } else if (error instanceof Error) {
            console.error('Error loading agent presets:', {
                message: error.message,
                name: error.name,
                stack: error.stack
            });
            throw error;
        } else {
            console.error('Unknown error loading agent presets:', error);
            throw new Error('Unknown error occurred while loading agent presets');
        }
    }
}

/**
 * Create a new agent preset
 */
export async function createAgentPreset(formData: AgentPresetFormData): Promise<AgentPreset> {
    try {
        const response = await fetch('/agents', {
            method: 'POST',
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });

        if (!response.ok) {
            throw new Error(`Failed to create preset: ${response.status} ${response.statusText}`);
        }

        const data: AgentPresetAPIResponse = await response.json();
        
        if (!data.success) {
            throw new Error(data.error || 'Failed to create preset');
        }

        if (!data.preset) {
            throw new Error('No preset data returned');
        }

        return data.preset;
    } catch (error) {
        console.error('Error creating agent preset:', error);
        throw error;
    }
}

/**
 * Update an existing agent preset
 */
export async function updateAgentPreset(presetId: string, formData: AgentPresetFormData): Promise<AgentPreset> {
    try {
        const response = await fetch(`/agents/${presetId}`, {
            method: 'PUT',
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });

        if (!response.ok) {
            throw new Error(`Failed to update preset: ${response.status} ${response.statusText}`);
        }

        const data: AgentPresetAPIResponse = await response.json();
        
        if (!data.success) {
            throw new Error(data.error || 'Failed to update preset');
        }

        if (!data.preset) {
            throw new Error('No preset data returned');
        }

        return data.preset;
    } catch (error) {
        console.error('Error updating agent preset:', error);
        throw error;
    }
}

/**
 * Delete an agent preset
 */
export async function deleteAgentPreset(presetId: string): Promise<void> {
    try {
        const response = await fetch(`/agents/${presetId}`, {
            method: 'DELETE',
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error(`Failed to delete preset: ${response.status} ${response.statusText}`);
        }

        const data: AgentPresetAPIResponse = await response.json();
        
        if (!data.success) {
            throw new Error(data.error || 'Failed to delete preset');
        }
    } catch (error) {
        console.error('Error deleting agent preset:', error);
        throw error;
    }
}

/**
 * Set the active agent preset
 */
export function setActiveAgentPreset(preset: AgentPreset | null): void {
    chatState.activeAgentPreset = preset;
    
    // Save to local storage
    if (preset) {
        localStorage.setItem(STORAGE_KEYS.ACTIVE_PRESET_ID, preset.id);
    } else {
        localStorage.removeItem(STORAGE_KEYS.ACTIVE_PRESET_ID);
    }
    
    // Update UI
    updateAgentPresetDisplay();
    updateReasoningLevelDisplay(); // Update reasoning display to show preset's default level
}

/**
 * Set the message-level reasoning override
 */
export function setMessageReasoningLevel(level: 'high' | 'medium' | 'low' | 'none' | null): void {
    chatState.messageReasoningLevel = level;
    updateReasoningLevelDisplay();
}

/**
 * Get the effective reasoning level (override or preset default)
 */
export function getEffectiveReasoningLevel(): 'high' | 'medium' | 'low' | 'none' {
    if (chatState.messageReasoningLevel) {
        return chatState.messageReasoningLevel;
    }
    
    if (chatState.activeAgentPreset) {
        return chatState.activeAgentPreset.default_reasoning_level;
    }
    
    return 'medium'; // Default fallback
}

/**
 * Load active preset from local storage
 */
export async function loadActivePresetFromStorage(): Promise<void> {
    try {
        const savedPresetId = localStorage.getItem(STORAGE_KEYS.ACTIVE_PRESET_ID);
        if (!savedPresetId) {
            return;
        }

        const presets = await loadAgentPresets();
        const savedPreset = presets.find(p => p.id === savedPresetId);
        
        if (savedPreset) {
            chatState.activeAgentPreset = savedPreset;
            updateAgentPresetDisplay();
            updateReasoningLevelDisplay(); // Update reasoning display to show preset's default level
        } else {
            // Clean up invalid storage
            localStorage.removeItem(STORAGE_KEYS.ACTIVE_PRESET_ID);
        }
    } catch (error) {
        console.warn('Failed to load active preset from storage:', error);
        // Continue without preset - don't block the application
    }
}

/**
 * Update the agent preset display in the UI
 */
function updateAgentPresetDisplay(): void {
    const presetSelector = document.getElementById('agent-preset-selector') as HTMLSelectElement;
    const activePresetDisplay = document.getElementById('active-agent-preset');
    const currentAgentDisplay = document.getElementById('current-agent-display');
    
    const currentPresetName = chatState.activeAgentPreset ? chatState.activeAgentPreset.name : 'Default Assistant';
    
    if (presetSelector) {
        if (chatState.activeAgentPreset) {
            presetSelector.value = chatState.activeAgentPreset.id;
        } else {
            presetSelector.value = '';
        }
    }
    
    if (activePresetDisplay) {
        activePresetDisplay.textContent = currentPresetName;
    }
    
    // Update compact display
    if (currentAgentDisplay) {
        currentAgentDisplay.textContent = currentPresetName;
    }
}

/**
 * Update the reasoning level display in the UI
 */
function updateReasoningLevelDisplay(): void {
    const reasoningSelector = document.getElementById('reasoning-level-selector') as HTMLSelectElement;
    const reasoningDisplay = document.getElementById('current-reasoning-level');
    const currentReasoningDisplay = document.getElementById('current-reasoning-display');
    
    const effectiveLevel = getEffectiveReasoningLevel();
    const isOverride = chatState.messageReasoningLevel !== null;
    
    if (reasoningSelector) {
        reasoningSelector.value = chatState.messageReasoningLevel || '';
    }
    
    if (reasoningDisplay) {
        reasoningDisplay.textContent = effectiveLevel;
        reasoningDisplay.className = isOverride ? 'reasoning-override' : 'reasoning-default';
    }
    
    // Update compact display
    if (currentReasoningDisplay) {
        const displayText = effectiveLevel.charAt(0).toUpperCase() + effectiveLevel.slice(1);
        currentReasoningDisplay.textContent = displayText;
        
        // Preserve base class and add appropriate modifier class
        currentReasoningDisplay.className = 'current-reasoning';
        if (isOverride) {
            currentReasoningDisplay.classList.add('reasoning-override');
        } else {
            currentReasoningDisplay.classList.add('reasoning-default');
        }
    }
    
    // Trigger update of reasoning level indicator in input area
    // Use a small delay to ensure the DOM is ready
    setTimeout(() => {
        const updateIndicatorEvent = new CustomEvent('updateReasoningIndicator');
        document.dispatchEvent(updateIndicatorEvent);
    }, 0);
}

/**
 * Validate agent preset form data
 */
export function validateAgentPresetForm(formData: AgentPresetFormData): string[] {
    const errors: string[] = [];
    
    if (!formData.name || formData.name.trim().length === 0) {
        errors.push('Name is required');
    } else if (formData.name.trim().length > 100) {
        errors.push('Name must be 100 characters or less');
    }
    
    if (!formData.instructions || formData.instructions.trim().length === 0) {
        errors.push('Instructions are required');
    } else if (formData.instructions.trim().length > 5000) {
        errors.push('Instructions must be 5000 characters or less');
    }
    
    if (!['gpt-5.1', 'gpt-5', 'gpt-5-mini', 'gpt-5-pro'].includes(formData.model)) {
        errors.push('Invalid model selection');
    }
    
    if (!['high', 'medium', 'low', 'none'].includes(formData.default_reasoning_level)) {
        errors.push('Invalid reasoning level selection');
    }
    
    return errors;
}

/**
 * Handle errors with user-friendly messages
 */
export function handleAgentPresetError(error: Error, operation: string): void {
    console.error(`Agent preset ${operation} error:`, error);
    
    let message = `Failed to ${operation} agent preset`;
    
    if (error.message.includes('404')) {
        message = 'Agent preset not found';
    } else if (error.message.includes('401')) {
        message = 'Authentication required - please refresh the page';
    } else if (error.message.includes('403')) {
        message = 'Permission denied';
    } else if (error.message.includes('500')) {
        message = 'Server error - please try again later';
    } else if (error.message.includes('Network')) {
        message = 'Network error - please check your connection';
    } else if (error.message) {
        message = error.message;
    }
    
    showErrorMessage(message);
}

/**
 * Show error message to user
 */
function showErrorMessage(message: string): void {
    console.error('Agent preset error:', message);
    
    // Try to use existing error display mechanism
    const errorContainer = document.getElementById('agent-preset-error');
    if (errorContainer) {
        errorContainer.textContent = message;
        errorContainer.style.display = 'block';
        
        // Auto-hide after 8 seconds for errors
        setTimeout(() => {
            errorContainer.style.display = 'none';
        }, 8000);
    } else {
        // Fallback to console warning if no error container
        console.warn('No error container found, error message:', message);
    }
}

/**
 * Show warning message to user
 */
export function showWarningMessage(message: string): void {
    console.warn('Agent preset warning:', message);
    
    // Try to use existing error display mechanism with warning styling
    const errorContainer = document.getElementById('agent-preset-error');
    if (errorContainer) {
        errorContainer.textContent = message;
        errorContainer.style.display = 'block';
        errorContainer.style.backgroundColor = '#fff3cd';
        errorContainer.style.color = '#856404';
        errorContainer.style.borderColor = '#ffeaa7';
        
        // Auto-hide after 6 seconds for warnings
        setTimeout(() => {
            errorContainer.style.display = 'none';
            // Reset to error styling
            errorContainer.style.backgroundColor = '';
            errorContainer.style.color = '';
            errorContainer.style.borderColor = '';
        }, 6000);
    } else {
        console.warn('No error container found, warning message:', message);
    }
}