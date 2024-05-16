export function unescapeHTML(escapedHTML: string): string {
    console.log(escapedHTML);
    return escapedHTML.replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&amp;/g, "&");
}
