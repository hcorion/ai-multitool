/**
 * Type declarations for UMD global libraries
 * These libraries are loaded via script tags in the HTML and are available globally
 */

/**
 * Showdown - Markdown to HTML converter
 */
declare const showdown: {
    Converter: new (options?: ShowdownOptions) => ShowdownConverter;
    extension: (name: string, extension: () => ShowdownExtension[]) => void;
    helper: {
        replaceRecursiveRegExp: (
            text: string,
            replacement: (wholeMatch: string, match: string, left: string, right: string) => string,
            left: string,
            right: string,
            flags: string
        ) => string;
    };
};

interface ShowdownOptions {
    strikethrough?: boolean;
    smoothLivePreview?: boolean;
    tasklists?: boolean;
    tables?: boolean;
    extensions?: string[];
}

interface ShowdownConverter {
    makeHtml: (text: string) => string;
}

interface ShowdownExtension {
    type: string;
    filter: (text: string, converter: any, options: any) => string;
}

/**
 * Highlight.js - Syntax highlighting library
 */
declare const hljs: {
    highlight: (language: string, code: string) => HighlightResult;
    highlightAuto: (code: string) => HighlightResult;
    getLanguage: (language: string) => any;
};

interface HighlightResult {
    value: string;
    language?: string;
    relevance?: number;
}
