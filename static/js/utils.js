export function unescapeHTML(escapedHTML) {
    console.log(escapedHTML);
    return escapedHTML.replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&amp;/g, "&");
}
