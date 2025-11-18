/**
 * Utility functions for consistent DOM manipulation across the application.
 */
/**
 * Get element by ID with type checking.
 * @param elementId - Element ID
 * @param expectedType - Optional type constructor
 * @returns Element or null
 */
export function getElementByIdSafe(elementId, expectedType) {
    const element = document.getElementById(elementId);
    if (!element) {
        console.warn(`Element with ID '${elementId}' not found`);
        return null;
    }
    if (expectedType && !(element instanceof expectedType)) {
        console.warn(`Element '${elementId}' is not of expected type ${expectedType.name}`);
        return null;
    }
    return element;
}
