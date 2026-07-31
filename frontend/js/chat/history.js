const chatHistory = {
    async load() {
        return chatAPI.list();
    },
    render(chats, currentId) {
        return chats.map(c => `
            <div class="chat-item ${c.id === currentId ? 'active' : ''}" data-chat-id="${c.id}">
                <div class="chat-item-title">${c.title}</div>
                <div class="chat-item-meta">${c.mode} · ${new Date(c.updated_at).toLocaleDateString()}</div>
            </div>
        `).join('');
    },
};

window.chatHistory = chatHistory;
