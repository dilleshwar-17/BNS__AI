const chatStream = {
    async connect(chatId, message, mode) {
        try {
            const response = await fetch(`/api/v1/chat/${chatId}/stream`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${api.getToken()}` },
                body: JSON.stringify({ message, mode }),
            });
            return this.readStream(response);
        } catch (err) {
            throw err;
        }
    },
    async readStream(response) {
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let fullContent = '';
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            const text = decoder.decode(value);
            const lines = text.split('\n').filter(l => l.startsWith('data: '));
            for (const line of lines) {
                try {
                    const data = JSON.parse(line.slice(6));
                    if (data.token) fullContent += data.token;
                    if (data.done) return { content: fullContent, messageId: data.message_id };
                } catch {}
            }
        }
        return { content: fullContent, messageId: null };
    },
};
