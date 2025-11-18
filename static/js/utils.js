/**
 * Unescape HTML entities for display.
 * @param escapedHTML - String containing HTML entities
 * @returns Unescaped string
 */
export function unescapeHTML(escapedHTML) {
    return escapedHTML.replace(/&lt;/g, "&lt").replace(/&gt;/g, "&gt").replace(/&amp;/g, "&");
}
/**
 * Copy text to clipboard with fallback for non-secure contexts.
 * @param textToCopy - Text to copy
 */
export async function copyToClipboard(textToCopy) {
    // Navigator clipboard api needs a secure context (https)
    if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(textToCopy);
    }
    else {
        // Use the 'out of viewport hidden text area' trick
        const textArea = document.createElement("textarea");
        textArea.value = textToCopy;
        // Move textarea out of the viewport so it's not visible
        textArea.style.position = "absolute";
        textArea.style.left = "-999999px";
        document.body.prepend(textArea);
        textArea.select();
        try {
            document.execCommand('copy');
        }
        catch (error) {
            console.error(error);
        }
        finally {
            textArea.remove();
        }
    }
}
