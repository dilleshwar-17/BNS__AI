const chatBubble = {
    render(role, content) {
        return `
            <div class="message ${role}">
                <div class="message-content">${markdown.render(content)}</div>
            </div>
        `;
    },
};

window.chatBubble = chatBubble;
