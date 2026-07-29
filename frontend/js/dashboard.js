const dashboard = {
    async render() {
        const container = document.getElementById('dashboard-content');
        if (!container) return;

        let chats = [], documents = [];
        try {
            const user = await auth.getMe();
            chats = await chat.loadChats();
            documents = await drafting.getDocuments();
            container.innerHTML = `
                <div class="dashboard-grid">
                    <div class="stat-card">
                        <div class="stat-number">${chats.length}</div>
                        <div class="stat-label">Total Chats</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">${documents.length}</div>
                        <div class="stat-label">Documents</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">${user.username}</div>
                        <div class="stat-label">Account</div>
                    </div>
                </div>
                <div class="dashboard-section">
                    <h3>Recent Chats</h3>
                    <div class="dashboard-list">
                        ${chats.slice(0, 5).map(c => `
                            <div class="dashboard-list-item">
                                <div>
                                    <div class="item-title">${chat.escapeHtml(c.title)}</div>
                                    <div class="item-meta">${c.mode} · ${new Date(c.updated_at).toLocaleDateString()}</div>
                                </div>
                                <a href="#/chat" class="btn btn-outline btn-sm" onclick="chat.openChat('${c.id}')">Open</a>
                            </div>
                        `).join('') || '<p style="color:var(--text-secondary);">No chats yet.</p>'}
                    </div>
                </div>
                <div class="dashboard-section" style="margin-top:24px;">
                    <h3>Recent Documents</h3>
                    <div class="dashboard-list">
                        ${documents.slice(0, 5).map(d => `
                            <div class="dashboard-list-item">
                                <div>
                                    <div class="item-title">${chat.escapeHtml(d.title)}</div>
                                    <div class="item-meta">${d.doc_type} · ${new Date(d.created_at).toLocaleDateString()}</div>
                                </div>
                            </div>
                        `).join('') || '<p style="color:var(--text-secondary);">No documents yet.</p>'}
                    </div>
                </div>
            `;
        } catch (err) {
            container.innerHTML = `<p>Error loading dashboard. ${err.message}</p>`;
        }
    }
};
