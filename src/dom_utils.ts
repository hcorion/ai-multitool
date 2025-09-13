/**
 * Utility functions for consistent DOM manipulation across the application.
 */

/**
 * Safely get an element by ID with type checking.
 */
export function getElementByIdSafe<T extends HTMLElement>(
    elementId: string,
    expectedType?: new () => T
): T | null {
    const element = document.getElementById(elementId);
    if (!element) {
        console.warn(`Element with ID '${elementId}' not found`);
        return null;
    }
    
    if (expectedType && !(element instanceof expectedType)) {
        console.warn(`Element '${elementId}' is not of expected type ${expectedType.name}`);
        return null;
    }
    
    return element as T;
}