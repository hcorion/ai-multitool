/**
 * Unified error handling for the AI Multitool frontend.
 *
 * This module provides standardized error handling utilities for consistent
 * error handling across all frontend operations.
 *
 * Note: DOM/UI helpers are included here for convenience but could be split
 * into a separate module for better separation of concerns.
 */
/**
 * Type guard to check if value is an ErrorResponse
 */
export function isErrorResponse(value) {
    return (typeof value === 'object' &&
        value !== null &&
        'success' in value &&
        value.success === false &&
        'error_type' in value &&
        typeof value.error_type === 'string' &&
        'error_message' in value &&
        typeof value.error_message === 'string' &&
        'timestamp' in value &&
        typeof value.timestamp === 'number');
}
/**
 * Extract error message from various error formats
 */
export function extractErrorMessage(error) {
    // Handle ErrorResponse format
    if (isErrorResponse(error)) {
        return error.error_message;
    }
    // Handle objects with error properties
    if (error && typeof error === 'object') {
        if ('error_message' in error && typeof error.error_message === 'string') {
            return error.error_message;
        }
        if ('error' in error) {
            const err = error.error;
            return typeof err === 'string' ? err : JSON.stringify(err);
        }
        if ('message' in error && typeof error.message === 'string') {
            return error.message;
        }
    }
    // Handle string errors
    if (typeof error === 'string') {
        return error;
    }
    // Fallback
    return 'An unknown error occurred';
}
/**
 * Extract error type from error object
 */
export function extractErrorType(error) {
    if (isErrorResponse(error)) {
        return error.error_type;
    }
    if (error && typeof error === 'object') {
        if ('error_type' in error && typeof error.error_type === 'string') {
            return error.error_type;
        }
        if ('name' in error && typeof error.name === 'string') {
            return error.name;
        }
    }
    return 'Error';
}
/**
 * Check if an error is retryable (transient failure)
 *
 * Note: The TypeError + message.includes('fetch') heuristic is browser-dependent
 * and may not work in all environments (e.g., Node.js, older browsers).
 */
export function isRetryableError(error) {
    // Network errors are retryable (browser-specific heuristic)
    if (error instanceof TypeError && error.message.includes('fetch')) {
        return true;
    }
    // Check error type from backend
    if (error && typeof error === 'object') {
        const errorType = ('error_type' in error && typeof error.error_type === 'string' ? error.error_type : '') ||
            ('type' in error && typeof error.type === 'string' ? error.type : '');
        // Retryable error types
        const retryableTypes = [
            'RateLimitError',
            'TimeoutError',
            'NetworkError',
            'ServiceUnavailable',
            'InternalServerError'
        ];
        if (retryableTypes.some(type => errorType.includes(type))) {
            return true;
        }
        // Check HTTP status codes
        if ('status' in error) {
            const status = typeof error.status === 'number'
                ? error.status
                : parseInt(String(error.status), 10);
            // 429 (rate limit), 500-599 (server errors) are retryable
            if (!isNaN(status)) {
                return status === 429 || (status >= 500 && status < 600);
            }
        }
    }
    return false;
}
/**
 * Escape HTML to prevent XSS attacks
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
// Track active timeout for error display
let errorDisplayTimeout = null;
/**
 * Clear error display
 */
export function clearError(targetElement) {
    // Clear any active timeout
    if (errorDisplayTimeout !== null) {
        clearTimeout(errorDisplayTimeout);
        errorDisplayTimeout = null;
    }
    targetElement.innerHTML = '';
    targetElement.style.display = 'none';
}
/**
 * Execute an async operation with retry logic
 *
 * @param operation - The async operation to execute
 * @param options - Retry configuration
 * @returns Promise resolving to the operation result
 *
 * Note: maxRetries represents the number of retries AFTER the initial attempt.
 * Total attempts = maxRetries + 1 (e.g., maxRetries=3 means 4 total attempts)
 */
export async function withRetry(operation, options = {}) {
    const { maxRetries = 3, initialDelay = 1000, backoffMultiplier = 2, maxDelay = 10000, isRetryable = isRetryableError } = options;
    let lastError;
    let delay = initialDelay;
    // Total attempts = maxRetries + 1 (initial attempt + retries)
    for (let attempt = 0; attempt <= maxRetries; attempt++) {
        try {
            return await operation();
        }
        catch (error) {
            lastError = error;
            // Don't retry if this is the last attempt or error is not retryable
            if (attempt === maxRetries || !isRetryable(error)) {
                throw error;
            }
            // Log retry attempt
            console.warn(`Operation failed (attempt ${attempt + 1}/${maxRetries + 1}), retrying in ${delay}ms...`, error);
            // Wait before retrying
            await new Promise(resolve => setTimeout(resolve, delay));
            // Increase delay for next attempt (exponential backoff)
            delay = Math.min(delay * backoffMultiplier, maxDelay);
        }
    }
    throw lastError;
}
/**
 * Handle API response and extract error if present
 *
 * Note: This function assumes all API endpoints return JSON.
 * For non-JSON responses, use fetch directly or extend this function.
 */
export async function handleApiResponse(response) {
    if (!response.ok) {
        let errorData;
        try {
            errorData = await response.json();
        }
        catch {
            // If JSON parsing fails, create a generic error
            errorData = {
                error_type: 'HTTPError',
                error_message: `HTTP ${response.status}: ${response.statusText}`,
                status: response.status,
                success: false,
                timestamp: Date.now()
            };
        }
        // Add status code to error data if it's an object
        if (errorData && typeof errorData === 'object') {
            errorData.status = response.status;
        }
        throw errorData;
    }
    return await response.json();
}
/**
 * Wrapper for fetch with error handling and retry logic
 */
export async function fetchWithErrorHandling(url, options = {}, retryOptions = {}) {
    return withRetry(async () => {
        const response = await fetch(url, options);
        return handleApiResponse(response);
    }, retryOptions);
}
// Track active timeout for notification
let notificationTimeout = null;
/**
 * Show a user-friendly error notification
 */
export function showErrorNotification(message, duration = 5000) {
    // Clear any existing timeout
    if (notificationTimeout !== null) {
        clearTimeout(notificationTimeout);
        notificationTimeout = null;
    }
    // Create notification element if it doesn't exist
    let notification = document.getElementById('error-notification');
    if (!notification) {
        notification = document.createElement('div');
        notification.id = 'error-notification';
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background-color: #f44336;
            color: white;
            padding: 16px;
            border-radius: 4px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.2);
            z-index: 10000;
            max-width: 400px;
            display: none;
        `;
        document.body.appendChild(notification);
    }
    notification.textContent = message;
    notification.style.display = 'block';
    // Auto-hide after duration
    if (duration > 0) {
        notificationTimeout = window.setTimeout(() => {
            notification.style.display = 'none';
            notificationTimeout = null;
        }, duration);
    }
}
/**
 * Parse jQuery XHR error into standard format
 *
 * Note: This is jQuery-specific and could be moved to a separate legacy module.
 * It reuses the extraction logic via isErrorResponse type guard.
 */
export function parseJQueryError(xhr) {
    let errorMessage = 'An error occurred';
    let errorType = 'Error';
    let errorDetails = {};
    // Try to parse JSON response
    if (xhr.responseJSON) {
        const json = xhr.responseJSON;
        if (isErrorResponse(json)) {
            return json;
        }
        // Fallback to manual extraction
        if (json && typeof json === 'object') {
            if ('error_message' in json && typeof json.error_message === 'string') {
                errorMessage = json.error_message;
            }
            else if ('error' in json && typeof json.error === 'string') {
                errorMessage = json.error;
            }
            if ('error_type' in json && typeof json.error_type === 'string') {
                errorType = json.error_type;
            }
            if ('error_details' in json && typeof json.error_details === 'object') {
                errorDetails = json.error_details;
            }
        }
    }
    else if (xhr.responseText) {
        try {
            const errorData = JSON.parse(xhr.responseText);
            if (isErrorResponse(errorData)) {
                return errorData;
            }
            // Fallback extraction
            errorMessage = extractErrorMessage(errorData);
            errorType = extractErrorType(errorData);
        }
        catch {
            errorMessage = xhr.responseText || `HTTP ${xhr.status}: ${xhr.statusText}`;
        }
    }
    else {
        errorMessage = `HTTP ${xhr.status}: ${xhr.statusText}`;
    }
    return {
        success: false,
        error_type: errorType,
        error_message: errorMessage,
        timestamp: Date.now(),
        error_details: errorDetails
    };
}
