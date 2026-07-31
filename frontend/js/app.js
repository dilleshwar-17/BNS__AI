window.app = {

    async autoLogin() {
        const token = localStorage.getItem('access_token');
        if (token && !window.jwt.isExpired(token)) {
            api.setToken(token);
            const rt = localStorage.getItem('refresh_token');
            if (rt) api.setRefreshToken(rt);
            try { return await window.authAPI.me(); } catch {}
        }
        const guestId = 'guest_' + Date.now();
        try {
            await api.post('/auth/register', { email: guestId + '@local.dev', username: guestId, password: 'GuestPass1' });
        } catch (e) {}
        try {
            const data = await api.post('/auth/login', { username: guestId, password: 'GuestPass1' });
            api.setToken(data.access_token);
            api.setRefreshToken(data.refresh_token);
        } catch (e) {
            try {
                const data = await api.post('/auth/login', { username: 'guest', password: 'GuestPass1' });
                api.setToken(data.access_token);
                api.setRefreshToken(data.refresh_token);
            } catch (e) {}
        }
    },

    async init() {
        this.setupRoutes();
        router.start();
        this.autoLogin().catch(() => {});
    },

    setupRoutes() {
        router.add('/', () => this.renderHome());
        router.add('/chat', () => this.renderChat());
        router.add('/drafting', () => this.renderDrafting());
        router.add('/dashboard', () => this.renderDashboard());
        router.add('/history', () => this.renderHistory());
        router.add('/profile', () => this.renderProfile());
        router.add('/settings', () => this.renderSettings());
        router.add('/login', () => this.renderLogin());
        router.add('/register', () => this.renderRegister());
        router.add('/admin/knowledge', () => this.renderAdminKnowledge());
        router.add('*', () => this.renderNotFound());
    },

    toggleTheme() {
        const html = document.documentElement;
        const current = html.getAttribute('data-theme');
        const theme = current === 'dark' ? 'light' : 'dark';
        html.setAttribute('data-theme', theme);
        const btn = document.querySelector('#theme-toggle');
        if (btn) btn.textContent = theme === 'dark' ? '🌙' : '☀️';
        localStorage.setItem('theme', theme);
    },

    updateUI() {
        const isAdmin = this.currentUser && (this.currentUser.role === 'admin' || this.currentUser.is_superuser);
        const adminLink = document.getElementById('admin-nav-link');
        if (adminLink) {
            adminLink.style.display = isAdmin ? 'inline-block' : 'none';
        }
        const userArea = document.getElementById('user-area');
        const loginBtn = document.getElementById('login-btn');
        const registerBtn = document.getElementById('register-btn');
        const userName = document.getElementById('user-name');
        if (this.currentUser) {
            if (userArea) userArea.style.display = 'flex';
            if (loginBtn) loginBtn.style.display = 'none';
            if (registerBtn) registerBtn.style.display = 'none';
            if (userName) userName.textContent = this.currentUser.username || this.currentUser.email || 'User';
        } else {
            if (userArea) userArea.style.display = 'none';
            if (loginBtn) loginBtn.style.display = 'inline-block';
            if (registerBtn) registerBtn.style.display = 'inline-block';
        }
    },

    loadTheme() {
        const saved = localStorage.getItem('theme');
        const theme = saved === 'light' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', theme);
        const btn = document.querySelector('#theme-toggle');
        if (btn) btn.textContent = theme === 'dark' ? '🌙' : '☀️';
    },

    showLoading(show) {
        const ls = document.getElementById('loading-screen');
        if (ls) ls.style.display = show ? 'flex' : 'none';
    },

    renderPage(html) {
        const main = document.getElementById('main-content');
        if (main) {
            main.innerHTML = `<div class="page">${html}</div>`;
        }
    },

    renderHome() {
        this.renderPage(window.landingPage.render());
    },

    submitHeroQuery() {
        const input = document.getElementById('heroQuery');
        if (input && input.value.trim()) {
            router.navigate('/chat');
        }
    },

    renderChat() {
        this.renderPage(`
            <div class="chat-layout">
                <div class="chat-sidebar">
                    <div class="chat-sidebar-header">
                        <h3>Chat History</h3>
                        <button class="btn btn-primary btn-sm btn-block" onclick="app.newChat()">+ New Chat</button>
                    </div>
                    <div class="chat-list" id="chat-list"></div>
                </div>
                <div class="chat-main">
                    <div class="chat-header">
                        <h2 id="chat-header-title">BNS AI Chat</h2>
                        <div style="display:flex;gap:8px;align-items:center;">
                            <select class="chat-mode-select" id="chat-mode">
                                <option value="legal_guidance">Legal Guidance</option>
                                <option value="legal_drafting">Legal Drafting</option>
                                <option value="section_lookup">Section Lookup</option>
                                <option value="legal_procedure">Legal Procedure</option>
                                <option value="rights_advisory">Rights Advisory</option>
                                <option value="case_law">Case Law</option>
                                <option value="comparison">Comparison</option>
                                <option value="deep_research">Deep Research</option>
                            </select>
                            <select class="chat-mode-select" id="chat-draft-select" style="display:none;">
                                <option value="">Select Draft...</option>
                            </select>
                        </div>
                    </div>
                    <div class="chat-messages" id="chat-messages">
                        ${chat.renderGreeting()}
                    </div>
                    <div class="chat-input-area">
                        <textarea id="chat-input" placeholder="Type your legal question here..." rows="1" onkeydown="if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();chat.sendCurrentMessage();}"></textarea>
                        <button class="btn btn-primary" onclick="chat.sendCurrentMessage()">Send</button>
                    </div>
                </div>
            </div>
        `);
        this.initChat();
    },

    async initChat() {
        await chat.loadChats();
        chat.renderSidebar();
        const pendingChatId = localStorage.getItem('pendingChatId');
        localStorage.removeItem('pendingChatId');
        if (pendingChatId && chat.chats.some(c => c.id === pendingChatId)) {
            await chat.openChat(pendingChatId);
        } else if (chat.chats.length > 0) {
            await chat.openChat(chat.chats[0].id);
        }
        await chat.initDraftSelector();
        const modeSelect = document.getElementById('chat-mode');
        if (modeSelect) {
            modeSelect.addEventListener('change', () => chat.toggleDraftSelector());
        }
    },

    async newChat() {
        const c = await chat.createChat();
        chat.currentChatId = c.id;
        chat.renderSidebar();
        const msgs = await chat.getMessages(c.id);
        chat.renderMessages(msgs);
        const header = document.getElementById('chat-header-title');
        if (header) header.textContent = c.title;
    },

    renderDrafting() {
        this.renderPage(`
            <div class="drafting-page">
                <div class="drafting-layout">
                    <div class="drafting-main">
                        <div class="section-header reveal" style="text-align:left;max-width:none;margin:0 0 28px;">
                            <h2>Legal Drafting</h2>
                            <p class="subtitle">Generate professional Indian legal documents step-by-step</p>
                        </div>
                        <div class="draft-grid" id="draft-grid"></div>
                        <div class="draft-wizard" id="draft-wizard" style="display:none"></div>
                        <div class="draft-preview" id="draft-preview">
                            <h3 id="draft-title"></h3>
                            <pre id="draft-content"></pre>
                            <div class="draft-actions" id="draft-actions"></div>
                        </div>
                    </div>
                    <div class="drafting-sidebar" id="draft-recent">
                        <h3>Recent Drafts</h3>
                        <div class="draft-recent-list" id="draftRecentList">
                            <p class="text-muted">No drafts yet. Generate one above.</p>
                        </div>
                    </div>
                </div>
            </div>
        `);
        this.initDrafting();
    },

    async initDrafting() {
        await drafting.initPage();
        const pendingDraftId = localStorage.getItem('pendingDraftId');
        localStorage.removeItem('pendingDraftId');
        if (pendingDraftId && drafting.openDraft) {
            drafting.openDraft(pendingDraftId);
        }
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.key === 'Enter') {
                const preview = document.getElementById('draft-preview');
                if (preview && preview.classList.contains('visible')) {
                    e.preventDefault();
                    drafting.saveCurrentDraft();
                }
            }
        });
    },

    renderDashboard() {
        this.renderPage(`
            <div class="dashboard-page">
                <div class="section-header reveal" style="text-align:left;max-width:none;margin:0 0 28px;">
                    <h2>Dashboard</h2>
                    <p class="subtitle">A snapshot of your legal activity</p>
                </div>
                <div id="dashboard-content">
                    <div class="loading-screen">
                        <div class="loader"></div>
                        <p>Loading dashboard...</p>
                    </div>
                </div>
            </div>
        `);
        dashboard.render();
    },

    renderHistory() {
        this.renderPage(window.historyPage.render());
        window.historyPage.load();
    },

    renderProfile() {
        this.renderPage(window.profilePage.render());
        window.profilePage.load();
    },

    renderSettings() {
        this.renderPage(window.settingsPage.render());
    },

    renderLogin() {
        this.renderPage(window.loginPage.render());
    },

    renderRegister() {
        this.renderPage(window.registerPage.render());
    },

    renderNotFound() {
        this.renderPage(window.notFoundPage.render());
    },

    renderAdminKnowledge() {
        this.renderPage(`
            <div class="page">
                <div class="loading-screen">
                    <div class="loader"></div>
                    <p>Loading knowledge manager...</p>
                </div>
            </div>
        `);
        adminKnowledge.render();
    }
};
