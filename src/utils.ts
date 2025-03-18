export function unescapeHTML(escapedHTML: string): string {
    return escapedHTML.replace(/&lt;/g, "&lt").replace(/&gt;/g, "&gt").replace(/&amp;/g, "&");
}
