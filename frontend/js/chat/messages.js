const chatMessages = {
    render(messages) {
        if (!messages || messages.length === 0) {
            return '<div class="chat-empty"><div class="empty-icon">⚖️</div><p>Start a conversation</p></div>';
        }
        return messages.map(m => `
            <div class="message ${m.role}">
                <div class="message-content">${markdown.render(m.content)}</div>
                <div class="message-actions">
                    <button onclick="chat.copyMessage(this)">Copy</button>
                    <span style="font-size:11px;color:var(--text-secondary);margin-left:auto;">${new Date(m.created_at).toLocaleTimeString()}</span>
                </div>
            </div>
        `).join('');
    },
};

window.chatMessages = chatMessages;
