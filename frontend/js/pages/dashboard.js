window.dashboard = {
    async render() {
        const container = document.getElementById('dashboard-content');
        if (!container) return;

        let chats = [], documents = [], user = null;
        try {
            user = await auth.getMe();
            chats = await chat.loadChats();
            documents = await drafting.getDocuments();

            container.innerHTML = `
                <div class="dashboard-grid">
                    <div class="stat-card reveal">
                        <div class="stat-icon">💬</div>
                        <div class="stat-number">${chats.length}</div>
                        <div class="stat-label">Total Chats</div>
                    </div>
                    <div class="stat-card reveal">
                        <div class="stat-icon">📄</div>
                        <div class="stat-number">${documents.length}</div>
                        <div class="stat-label">Documents</div>
                    </div>
                    <div class="stat-card reveal">
                        <div class="stat-icon">👤</div>
                        <div class="stat-number" style="font-size:20px;">${chat.escapeHtml(user.username || user.email || 'User')}</div>
                        <div class="stat-label">Account</div>
                    </div>
                </div>

                <div class="dashboard-section reveal">
                    <h3>Recent Chats</h3>
                    <div class="dashboard-list">
                        ${chats.length === 0 ? `
                            <div class="chat-empty" style="min-height:160px;">
                                <div class="empty-icon">💬</div>
                                <p>No chats yet</p>
                                <a href="#/chat" class="btn btn-outline btn-sm">Start a Conversation</a>
                            </div>
                        ` : chats.slice(0, 5).map(c => `
                            <div class="dashboard-list-item">
                                <div>
                                    <div class="item-title">${chat.escapeHtml(c.title)}</div>
                                    <div class="item-meta">${chat.escapeHtml(c.mode || '')} · ${new Date(c.updated_at).toLocaleDateString()}</div>
                                </div>
                                <button class="btn btn-outline btn-sm" onclick="historyPage.openChat('${c.id}')">Open</button>
                            </div>
                        `).join('')}
                    </div>
                </div>

                <div class="dashboard-section reveal" style="margin-top:24px;">
                    <h3>Recent Documents</h3>
                    <div class="dashboard-list">
                        ${documents.length === 0 ? `
                            <div class="chat-empty" style="min-height:160px;">
                                <div class="empty-icon">📄</div>
                                <p>No documents yet</p>
                                <a href="#/drafting" class="btn btn-outline btn-sm">Draft a Document</a>
                            </div>
                        ` : documents.slice(0, 5).map(d => `
                            <div class="dashboard-list-item">
                                <div>
                                    <div class="item-title">${chat.escapeHtml(d.title)}</div>
                                    <div class="item-meta">${chat.escapeHtml(d.doc_type || '')} · ${new Date(d.created_at).toLocaleDateString()}</div>
                                </div>
                                <button class="btn btn-outline btn-sm" onclick="historyPage.openDocument('${d.id}')">Open</button>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        } catch (err) {
            container.innerHTML = `
                <div class="chat-empty" style="min-height:240px;">
                    <div class="empty-icon">⚠️</div>
                    <p>Error loading dashboard.</p>
                    <p style="font-size:13px;">${chat.escapeHtml(err.message || 'Please try again.')}</p>
                    <a href="#/chat" class="btn btn-outline btn-sm">Go to Chat</a>
                </div>
            `;
        }
    }
};
