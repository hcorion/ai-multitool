export function unescapeHTML(escapedHTML: string): string {
    return escapedHTML.replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&amp;/g, "&");
}
