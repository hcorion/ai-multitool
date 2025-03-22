import * as utils from "./utils.js";

export type ChatMessage = {
    role: string;
    text: string;
};
export type MessageHistory = {
    type: string;
    text: string;
    delta: string;
    snapshot: string;
    threadId: string;
    status: string;
    messages: ChatMessage[];
};

export function onConversationSelected(conversationId: string, successCallback: (chatData: MessageHistory) => void): void {
    console.log(`conversation: ${conversationId}`);
    $.ajax({
        type: "GET",
        url: "/chat?thread_id=" + encodeURIComponent(conversationId),
        contentType: "application/json",
        scriptCharset: "utf-8",
        success: (response: string) => {
            let chatData: MessageHistory = JSON.parse(response);
            successCallback(chatData);
        },
        error: (error) => {
            throw new Error(`Error: ${error}`);
        },
    });
}


showdown.extension("highlight", function () {
    return [
        {
            type: "output",
            filter: function (text, converter, options) {
                var left = "<pre><code\\b[^>]*>",
                    right = "</code></pre>",
                    flags = "g";
                var replacement = function (_wholeMatch: string, match: string, left: string, right: string) {
                    var lang = (left.match(/class=\"([^ \"]+)/) || [])[1];
                    if (lang) {
                        left = left.slice(0, 18) + "hljs " + left.slice(18);
                        if (hljs.getLanguage(lang)) {
                            return left + hljs.highlight(lang, utils.unescapeHTML(match)).value + right;
                        } else {
                            return left + hljs.highlightAuto(utils.unescapeHTML(match)).value + right;
                        }
                    } else {
                        left = left.slice(0, 10) + ' class="hljs" ' + left.slice(10);
                        return left + hljs.highlightAuto(utils.unescapeHTML(match)).value + right;
                    }
                };
                return showdown.helper.replaceRecursiveRegExp(text, replacement, left, right, flags);
            },
        },
    ];
});

export function refreshChatMessages(messages: ChatMessage[]): void {
    const chatHistory = document.getElementById("chat-history") as HTMLDivElement;
    chatHistory.innerHTML = "";
    // Display AI response in chat history
    messages.forEach((message) => {
        var converter = new showdown.Converter({
            strikethrough: true,
            smoothLivePreview: true,
            tasklists: true,
            tables: true,
            extensions: ["highlight"],
        }),
            text = message.text,
            html = converter.makeHtml(text);
        chatHistory.innerHTML += `<div class="ai-message">${utils.unescapeHTML(html)}</div>`;
    });
    chatHistory.scrollTop = chatHistory.scrollHeight; // Scroll to bottom
}
