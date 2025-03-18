export function unescapeHTML(escapedHTML) {
    return escapedHTML.replace(/&lt;/g, "&lt").replace(/&gt;/g, "&gt").replace(/&amp;/g, "&");
}
