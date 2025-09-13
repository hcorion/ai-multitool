import("./chat.js").then((chat) => {
    const urlParams = new URLSearchParams(window.location.search);

    const conversationId = urlParams.get('id')
    if (conversationId) {
        // @ts-ignore
        chat.onConversationSelected(conversationId)
            .then((chatData: any) => {
                chat.refreshChatMessages(chatData.messages);
            })
            .catch((error) => {
                console.error('Failed to load conversation:', error);
            });
    }
});