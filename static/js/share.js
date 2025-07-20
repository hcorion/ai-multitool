"use strict";
import("./chat.js").then((chat) => {
    const urlParams = new URLSearchParams(window.location.search);
    const conversationId = urlParams.get('id');
    if (conversationId) {
        // @ts-ignore
        chat.onConversationSelected(conversationId, (chatData) => {
            chat.refreshChatMessages(chatData.messages);
        });
    }
});
