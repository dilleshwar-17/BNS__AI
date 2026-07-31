const historyPage = {
    modeLabels: {
        legal_guidance: 'Legal Guidance', legal_drafting: 'Legal Drafting',
        section_lookup: 'Section Lookup', legal_procedure: 'Legal Procedure',
        rights_advisory: 'Rights Advisory', case_law: 'Case Law',
        comparison: 'Comparison', deep_research: 'Deep Research',
    },

    render() {
        return `
            <div class="dashboard-page">
                <div class="section-header reveal" style="text-align:left;max-width:none;margin:0 0 28px;">
                    <h2>History</h2>
                    <p class="subtitle">Your past chats and drafted documents</p>
                </div>
                <div class="history-grid" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:24px;">
                    <div class="dashboard-section reveal">
                        <h3>💬 Chat History</h3>
                        <div class="dashboard-list" id="history-chats">
                            <div class="loading-screen" style="min-height:120px;">
                                <div class="loader"></div>
                                <p>Loading chats...</p>
                            </div>
                        </div>
                    </div>
                    <div class="dashboard-section reveal">
                        <h3>📄 Documents</h3>
                        <div class="dashboard-list" id="history-documents">
                            <div class="loading-screen" style="min-height:120px;">
                                <div class="loader"></div>
                                <p>Loading documents...</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    },

    async load() {
        this.renderChats();
        this.renderDocuments();
    },

    async renderChats() {
        const list = document.getElementById('history-chats');
        if (!list) return;
        try {
            const chats = await api.get('/chat/');
            if (!chats || chats.length === 0) {
                list.innerHTML = `
                    <div class="chat-empty" style="min-height:200px;">
                        <div class="empty-icon">💬</div>
                        <p>No chats yet</p>
                        <a href="#/chat" class="btn btn-outline btn-sm">Start a Conversation</a>
                    </div>
                `;
                return;
            }
            list.innerHTML = chats.map(c => `
                <div class="dashboard-list-item">
                    <div>
                        <div class="item-title">${this.escapeHtml(c.title)}</div>
                        <div class="item-meta">${this.modeLabels[c.mode] || c.mode} · ${new Date(c.updated_at).toLocaleDateString()}</div>
                    </div>
                    <button class="btn btn-outline btn-sm" onclick="historyPage.openChat('${c.id}')">Open</button>
                </div>
            `).join('');
        } catch (err) {
            list.innerHTML = `<p class="error-text">Failed to load chats: ${this.escapeHtml(err.detail || err.message)}</p>`;
        }
    },

    async renderDocuments() {
        const list = document.getElementById('history-documents');
        if (!list) return;
        try {
            const docs = await api.get('/drafting/documents');
            if (!docs || docs.length === 0) {
                list.innerHTML = `
                    <div class="chat-empty" style="min-height:200px;">
                        <div class="empty-icon">📄</div>
                        <p>No documents yet</p>
                        <a href="#/drafting" class="btn btn-outline btn-sm">Draft a Document</a>
                    </div>
                `;
                return;
            }
            list.innerHTML = docs.map(d => `
                <div class="dashboard-list-item">
                    <div>
                        <div class="item-title">${this.escapeHtml(d.title)}</div>
                        <div class="item-meta">${this.escapeHtml(d.doc_type || 'Document')} · ${new Date(d.created_at).toLocaleDateString()}</div>
                    </div>
                    <button class="btn btn-outline btn-sm" onclick="historyPage.openDocument('${d.id}')">Open</button>
                </div>
            `).join('');
        } catch (err) {
            list.innerHTML = `<p class="error-text">Failed to load documents: ${this.escapeHtml(err.detail || err.message)}</p>`;
        }
    },

    openChat(chatId) {
        localStorage.setItem('pendingChatId', chatId);
        router.navigate('/chat');
    },

    openDocument(docId) {
        localStorage.setItem('pendingDraftId', docId);
        router.navigate('/drafting');
    },

    escapeHtml(text) {
        const d = document.createElement('div');
        d.textContent = text == null ? '' : String(text);
        return d.innerHTML;
    },
};

window.historyPage = historyPage;
