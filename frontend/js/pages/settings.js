const settingsPage = {
    render() {
        const theme = (document.documentElement.getAttribute('data-theme') || 'dark') === 'dark' ? 'dark' : 'light';
        const user = window.app && app.currentUser;
        return `
            <div class="dashboard-page">
                <div class="section-header reveal" style="text-align:left;max-width:none;margin:0 0 28px;">
                    <h2>Settings</h2>
                    <p class="subtitle">Customize your BNS AI experience</p>
                </div>
                <div class="history-grid" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:24px;">

                    <div class="dashboard-section reveal">
                        <h3>🎨 Appearance</h3>
                        <p class="item-meta" style="margin-top:4px;">Choose how BNS AI looks for you.</p>
                        <div class="setting-group" style="display:flex;gap:10px;margin-top:16px;">
                            <button class="btn ${theme === 'dark' ? 'btn-primary' : 'btn-outline'}" onclick="app.toggleTheme();settingsPage.refresh()">🌙 Dark</button>
                            <button class="btn ${theme === 'light' ? 'btn-primary' : 'btn-outline'}" onclick="app.toggleTheme();settingsPage.refresh()">☀️ Light</button>
                        </div>
                    </div>

                    <div class="dashboard-section reveal">
                        <h3>👤 Account</h3>
                        ${user ? `
                            <div class="dashboard-list" style="margin-top:16px;">
                                <div class="dashboard-list-item">
                                    <div><div class="item-title">Username</div><div class="item-meta">${this.escapeHtml(user.username || '—')}</div></div>
                                </div>
                                <div class="dashboard-list-item">
                                    <div><div class="item-title">Email</div><div class="item-meta">${this.escapeHtml(user.email || '—')}</div></div>
                                </div>
                            </div>
                            <div style="display:flex;gap:10px;margin-top:16px;">
                                <a href="#/profile" class="btn btn-outline btn-sm">View Profile</a>
                                <button class="btn btn-outline btn-sm" onclick="logout.execute()">Logout</button>
                            </div>
                        ` : `
                            <div class="chat-empty" style="min-height:160px;align-items:flex-start;">
                                <div class="empty-icon">🔒</div>
                                <p>Sign in to manage your account.</p>
                                <a href="#/login" class="btn btn-outline btn-sm">Sign In</a>
                            </div>
                        `}
                    </div>

                    <div class="dashboard-section reveal">
                        <h3>⚖️ About</h3>
                        <p class="item-meta" style="margin-top:4px;line-height:1.6;">BNS AI is an AI-powered legal information tool for Indian criminal law research, document drafting, and section lookup. It is free, private, and secure.</p>
                        <p class="item-meta" style="margin-top:12px;line-height:1.6;">© ${new Date().getFullYear()} BNS AI. Made with ❤️ in India.</p>
                    </div>

                </div>
            </div>
        `;
    },

    refresh() {
        const main = document.getElementById('main-content');
        if (!main) return;
        app.renderSettings();
        const btn = document.querySelector('#theme-toggle');
        if (btn) {
            const theme = document.documentElement.getAttribute('data-theme');
            btn.textContent = theme === 'dark' ? '🌙' : '☀️';
        }
    },

    escapeHtml(text) {
        const d = document.createElement('div');
        d.textContent = text == null ? '' : String(text);
        return d.innerHTML;
    },
};

window.settingsPage = settingsPage;
