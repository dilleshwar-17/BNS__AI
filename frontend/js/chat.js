const chat = {
    currentChatId: null,
    chats: [],

    loadChats() {
        return api.get('/chat/').then(data => {
            this.chats = data;
            return this.chats;
        }).catch(() => []);
    },

    createChat(title = 'New Chat', mode = 'legal_guidance') {
        return api.post('/chat/', { title, mode }).then(c => {
            this.chats.unshift(c);
            return c;
        });
    },

    getMessages(chatId) {
        return api.get(`/chat/${chatId}`);
    },

    sendMessage(chatId, message, mode = 'legal_guidance') {
        return api.post(`/chat/${chatId}`, { message, mode });
    },

    deleteChat(chatId) {
        return api.del(`/chat/${chatId}`).then(() => {
            this.chats = this.chats.filter(c => c.id !== chatId);
            api._clearCache();
        });
    },

    renderSidebar() {
        const list = document.getElementById('chat-list');
        if (!list) return;
        list.innerHTML = this.chats.map(c => `
            <div class="chat-item ${c.id === this.currentChatId ? 'active' : ''}" data-chat-id="${c.id}">
                <div class="chat-item-title">${this.escapeHtml(c.title)}</div>
                <div class="chat-item-meta">${c.mode} · ${new Date(c.updated_at).toLocaleDateString()}</div>
            </div>
        `).join('');
        list.querySelectorAll('.chat-item').forEach(el => {
            el.addEventListener('click', () => this.openChat(el.dataset.chatId));
        });
    },

    escapeHtml(text) {
        const d = document.createElement('div');
        d.textContent = text;
        return d.innerHTML;
    },

    renderMessages(messages) {
        const container = document.getElementById('chat-messages');
        if (!container) return;
        if (!messages || messages.length === 0) {
            container.innerHTML = `
                <div class="chat-empty">
                    <div class="empty-icon">⚖️</div>
                    <p>Start a conversation with BNS AI</p>
                    <p style="font-size:13px;">Ask about Indian law, legal procedures, or draft documents</p>
                </div>
            `;
            return;
        }
        container.innerHTML = messages.map(m => `
            <div class="message ${m.role}">
                <div class="message-content">${this.renderMarkdown(m.content)}</div>
                <div class="message-actions">
                    <button onclick="chat.copyMessage(this)">Copy</button>
                    <span style="font-size:11px;color:var(--text-secondary);margin-left:auto;">${new Date(m.created_at).toLocaleTimeString()}</span>
                </div>
            </div>
        `).join('');
        container.scrollTop = container.scrollHeight;
    },

    renderMarkdown(text) {
        if (!text) return '';
        let html = this.escapeHtml(text);
        html = html.replace(/### (.+)/g, '<h3>$1</h3>');
        html = html.replace(/## (.+)/g, '<h2>$1</h2>');
        html = html.replace(/# (.+)/g, '<h1>$1</h1>');
        html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
        html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');
        html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
        html = html.replace(/^- (.+)/gm, '<li>$1</li>');
        html = html.replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>');
        html = html.replace(/\n\n/g, '</p><p>');
        html = '<p>' + html + '</p>';
        html = html.replace(/<p><\/p>/g, '');
        return html;
    },

    copyMessage(btn) {
        const content = btn.closest('.message').querySelector('.message-content');
        navigator.clipboard.writeText(content.textContent).then(() => {
            btn.textContent = 'Copied!';
            setTimeout(() => { btn.textContent = 'Copy'; }, 2000);
        });
    },

    _debounce(fn, ms) {
        let timer;
        return function(...args) {
            clearTimeout(timer);
            timer = setTimeout(() => fn.apply(this, args), ms);
        };
    },

    async openChat(chatId) {
        const prevChat = this.currentChatId;
        this.currentChatId = chatId;

        const container = document.getElementById('chat-messages');
        if (container) container.innerHTML = '<div class="loading">Loading messages...</div>';

        const msgs = await this.getMessages(chatId);
        this.renderSidebar();
        this.renderMessages(msgs);
        const header = document.getElementById('chat-header-title');
        const chat = this.chats.find(c => c.id === chatId);
        if (header && chat) header.textContent = chat.title;
    },

    async sendCurrentMessage() {
        const input = document.getElementById('chat-input');
        const modeSelect = document.getElementById('chat-mode');
        if (!input || !input.value.trim()) return;
        if (!this.currentChatId) {
            await this.createChat(input.value.slice(0, 50));
            this.currentChatId = this.chats[0]?.id;
        }
        const message = input.value;
        const mode = modeSelect ? modeSelect.value : 'legal_guidance';
        input.value = '';

        const container = document.getElementById('chat-messages');
        const userDiv = document.createElement('div');
        userDiv.className = 'message user';
        userDiv.innerHTML = `<div class="message-content"><p>${this.escapeHtml(message)}</p></div>`;
        container.appendChild(userDiv);
        container.scrollTop = container.scrollHeight;

        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'message assistant';
        loadingDiv.innerHTML = `<div class="message-content"><p><em>Thinking...</em></p></div>`;
        container.appendChild(loadingDiv);
        container.scrollTop = container.scrollHeight;

        try {
            const msg = await this.sendMessage(this.currentChatId, message, mode);
            loadingDiv.outerHTML = `
                <div class="message assistant">
                    <div class="message-content">${this.renderMarkdown(msg.content)}</div>
                    <div class="message-actions">
                        <button onclick="chat.copyMessage(this)">Copy</button>
                    </div>
                </div>
            `;
            container.scrollTop = container.scrollHeight;
            api._clearCache();
            await this.loadChats();
            this.renderSidebar();
        } catch (err) {
            loadingDiv.innerHTML = `<div class="message-content"><p style="color:#ff6b6b;">Error: ${this.escapeHtml(err.detail || err.message)}</p></div>`;
        }
    },

    async initDraftSelector() {
        const select = document.getElementById('chat-draft-select');
        if (!select) return;
        try {
            const data = await api.get('/drafting/types');
            const labels = { fir: 'FIR', legal_notice: 'Legal Notice', bail_application: 'Bail Application', affidavit: 'Affidavit', consumer_complaint: 'Consumer Complaint', agreement: 'Agreement', civil_plaint: 'Civil Plaint', divorce_petition: 'Divorce Petition', will: 'Will' };
            select.innerHTML = '<option value="">Select Draft...</option>' +
                data.draft_types.map(t => `<option value="${t}">${labels[t] || t}</option>`).join('');
            select.addEventListener('change', () => {
                const val = select.value;
                if (val) router.navigate('/drafting');
            });
        } catch {}
    },

    toggleDraftSelector() {
        const mode = document.getElementById('chat-mode');
        const draft = document.getElementById('chat-draft-select');
        if (!mode || !draft) return;
        draft.style.display = mode.value === 'legal_drafting' ? 'inline-block' : 'none';
    }
};
