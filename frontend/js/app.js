window.app = {

    async autoLogin() {
        const token = localStorage.getItem('access_token');
        if (token && !window.jwt.isExpired(token)) {
            api.setToken(token);
            const rt = localStorage.getItem('refresh_token');
            if (rt) api.setRefreshToken(rt);
            try {
                const u = await window.authAPI.me();
                this.currentUser = u;
                this.updateUI();
                return u;
            } catch (err) {
                console.error("Token validation failed, attempting refresh or re-login", err);
            }
        }

        // Try to refresh token
        const rt = localStorage.getItem('refresh_token');
        if (rt) {
            try {
                const data = await window.authAPI.refresh();
                const u = await window.authAPI.me();
                this.currentUser = u;
                this.updateUI();
                return u;
            } catch (err) {
                console.error("Token refresh failed", err);
            }
        }

        // Check if we have persistent guest credentials saved in localStorage
        let guestUsername = localStorage.getItem('guest_username');
        let guestPassword = localStorage.getItem('guest_password');

        if (guestUsername && guestPassword) {
            try {
                const data = await api.post('/auth/login', { username: guestUsername, password: guestPassword });
                api.setToken(data.access_token);
                api.setRefreshToken(data.refresh_token);
                const u = await window.authAPI.me();
                this.currentUser = u;
                this.updateUI();
                return u;
            } catch (err) {
                console.warn("Stored guest credentials failed to log in, creating a new user", err);
                localStorage.removeItem('guest_username');
                localStorage.removeItem('guest_password');
            }
        }

        // Create new guest credentials and persist them
        const guestId = 'guest_' + Math.random().toString(36).substring(2, 11) + '_' + Date.now();
        const pwd = 'GuestPass1_' + Math.random().toString(36).substring(2, 7);

        try {
            await api.post('/auth/register', { email: guestId + '@local.dev', username: guestId, password: pwd });
            localStorage.setItem('guest_username', guestId);
            localStorage.setItem('guest_password', pwd);
        } catch (e) {
            console.error("Guest registration failed", e);
        }

        try {
            const data = await api.post('/auth/login', { username: guestId, password: pwd });
            api.setToken(data.access_token);
            api.setRefreshToken(data.refresh_token);
            const u = await window.authAPI.me();
            this.currentUser = u;
            this.updateUI();
            return u;
        } catch (e) {
            // Last resort hardcoded guest account
            try {
                const data = await api.post('/auth/login', { username: 'guest', password: 'GuestPass1' });
                api.setToken(data.access_token);
                api.setRefreshToken(data.refresh_token);
                const u = await window.authAPI.me();
                this.currentUser = u;
                this.updateUI();
                return u;
            } catch (e) {
                console.error("All fallback auto-logins failed", e);
            }
        }
    },

    async init() {
        this.setupRoutes();
        this.showLoading(true);
        try {
            await this.autoLogin();
        } catch (e) {
            console.error("Auto login failed during initialization", e);
        } finally {
            this.showLoading(false);
            router.start();
        }
    },

    setupRoutes() {
        router.add('/', () => this.renderHome());
        router.add('/chat', () => this.renderChat());
        router.add('/drafting', () => this.renderDrafting());
        router.add('/dashboard', () => this.renderDashboard());
        router.add('/admin/knowledge', () => this.renderAdminKnowledge());
        router.add('*', () => this.renderHome());
    },

    toggleTheme() {
        const html = document.documentElement;
        const current = html.getAttribute('data-theme');
        const theme = current === 'light' ? 'dark' : 'light';
        html.setAttribute('data-theme', theme);
        document.querySelector('#theme-toggle').textContent = theme === 'dark' ? '🌙' : '☀️';
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
        if (saved === 'light') {
            document.documentElement.setAttribute('data-theme', 'light');
            document.querySelector('#theme-toggle').textContent = '☀️';
        }
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
        this.renderPage(`
<section class="hero">
    <div class="hero-tag"><span>⚖️</span> India's Offline-First Legal AI</div>
    <h1>BNS AI: Your <span>Legal Intelligence</span> for Indian Law</h1>
    <p class="subtitle">Criminal law queries, BNS section lookups, and AI-powered legal drafting — all in one platform. Free, private, and works offline.</p>
    <div class="hero-chat" id="heroChat">
        <div class="hero-chat-header">
            <span class="dot"></span>
            <span>BNS AI</span>
        </div>
        <div class="hero-chat-body" id="heroChatBody">
            <div class="hero-chat-bubble bot">Hello, how can I help you today?</div>
            <div class="hero-chat-bubble user" onclick="document.getElementById('heroQuery').value=this.textContent;app.submitHeroQuery()">What is the punishment for theft under BNS?</div>
            <div class="hero-chat-bubble user" onclick="document.getElementById('heroQuery').value=this.textContent;app.submitHeroQuery()">How to file a bail application?</div>
            <div class="hero-chat-bubble user" onclick="document.getElementById('heroQuery').value=this.textContent;app.submitHeroQuery()">Explain Section 302 BNS</div>
        </div>
        <div class="hero-chat-input">
            <input type="text" id="heroQuery" placeholder="Ask a legal question..." onkeydown="if(event.key==='Enter')app.submitHeroQuery()">
            <button onclick="app.submitHeroQuery()">➤</button>
        </div>
    </div>
    <div class="hero-trust">
        <span>🔒 Private & Secure</span>
        <span>📚 Covers BNS, BNSS, Constitution & more</span>
        <span>⚡ Answers in Seconds</span>
    </div>
</section>

<div class="partner-section">
    <p>Trusted by legal professionals across India</p>
    <div class="partner-track" id="partnerTrack">
        <span class="partner-logo">Criminal Law Practitioners</span>
        <span class="partner-logo">High Court Advocates</span>
        <span class="partner-logo">Law Students & Researchers</span>
        <span class="partner-logo">District Court Litigants</span>
        <span class="partner-logo">Legal Aid Clinics</span>
        <span class="partner-logo">Judicial Aspirants</span>
        <span class="partner-logo">Corporate Legal Teams</span>
        <span class="partner-logo">Human Rights Organizations</span>
        <span class="partner-logo">Police & Investigation Units</span>
        <span class="partner-logo">NGO Legal Cells</span>
        <span class="partner-logo">Criminal Law Practitioners</span>
        <span class="partner-logo">High Court Advocates</span>
        <span class="partner-logo">Law Students & Researchers</span>
        <span class="partner-logo">District Court Litigants</span>
        <span class="partner-logo">Legal Aid Clinics</span>
        <span class="partner-logo">Judicial Aspirants</span>
        <span class="partner-logo">Corporate Legal Teams</span>
        <span class="partner-logo">Human Rights Organizations</span>
        <span class="partner-logo">Police & Investigation Units</span>
        <span class="partner-logo">NGO Legal Cells</span>
    </div>
</div>

<section class="section">
    <div class="stats-row">
        <div class="stat-item">
            <div class="stat-number">1<span class="stat-suffix">K+</span></div>
            <div class="stat-label">Users Served</div>
        </div>
        <div class="stat-item">
            <div class="stat-number">10<span class="stat-suffix">K+</span></div>
            <div class="stat-label">Queries Answered</div>
        </div>
        <div class="stat-item">
            <div class="stat-number">10<span class="stat-suffix">+</span></div>
            <div class="stat-label">Document Types</div>
        </div>
        <div class="stat-item">
            <div class="stat-number">4.8<span class="stat-suffix">★</span></div>
            <div class="stat-label">User Rating</div>
        </div>
    </div>
</section>

<div class="section section-dark">
    <div class="section-header">
        <h2>Comprehensive Legal Intelligence Platform</h2>
        <p>Every tool you need to understand, research, and act on Indian criminal law — powered by AI, designed for clarity.</p>
    </div>
    <div class="features-grid">
        <div class="feature-card">
            <div class="feature-icon"><svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="1.5"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg></div>
            <h3>Statute Coverage</h3>
            <p>Complete coverage of the Bharatiya Nyaya Sanhita, Bharatiya Nagarik Suraksha Sanhita, Bharatiya Sakshya Adhiniyam, and the Constitution of India.</p>
        </div>
        <div class="feature-card">
            <div class="feature-icon"><svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="1.5"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg></div>
            <h3>AI Document Drafting</h3>
            <p>Generate professional legal documents — FIRs, bail applications, legal notices, affidavits, consumer complaints, agreements, and wills — through an intelligent step-by-step questionnaire.</p>
        </div>
        <div class="feature-card">
            <div class="feature-icon"><svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="1.5"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg></div>
            <h3>Instant Section Lookup</h3>
            <p>Query any BNS, BNSS, or BSA section by number. Receive the full text, punishment, procedure, and illustrative examples in seconds.</p>
        </div>
        <div class="feature-card">
            <div class="feature-icon"><svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="1.5"><path d="M5 8l6 6 8-8"/><path d="M21 12v5a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2h10"/></svg></div>
            <h3>Bilingual Access</h3>
            <p>Ask legal questions in English or Hindi and receive clear, section-cited responses in your preferred language. Natural language understanding eliminates the need for legal jargon.</p>
        </div>
        <div class="feature-card">
            <div class="feature-icon"><svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="1.5"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg></div>
            <h3>Procedural Law Guidance</h3>
            <p>Step-by-step explanations of criminal procedure — from FIR registration and bail applications to trial process and appeals — grounded in BNSS and CrPC provisions.</p>
        </div>
        <div class="feature-card">
            <div class="feature-icon"><svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="1.5"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg></div>
            <h3>Intelligent Query Processing</h3>
            <p>Query validation ensures only BNS-related questions receive substantive responses. Intent classification routes queries to the appropriate legal workflow automatically.</p>
        </div>
    </div>
</div>

<div class="section">
    <div class="section-header">
        <h2>How BNS AI Works</h2>
        <p>A streamlined pipeline from question to actionable legal intelligence.</p>
    </div>
    <div class="steps-grid">
        <div class="step">
            <div class="step-num">01</div>
            <div class="step-content">
                <h3>Submit Your Query</h3>
                <p>Pose your legal question in natural language — English or Hindi. BNS AI validates the query against its scope of Indian criminal law before processing.</p>
            </div>
        </div>
        <div class="step-connector"></div>
        <div class="step">
            <div class="step-num">02</div>
            <div class="step-content">
                <h3>Intelligence Processing</h3>
                <p>Your query is classified by intent, enriched with context from the offline knowledge base and retrieved legal provisions, then processed through the AI engine.</p>
            </div>
        </div>
        <div class="step-connector"></div>
        <div class="step">
            <div class="step-num">03</div>
            <div class="step-content">
                <h3>Structured Response</h3>
                <p>You receive a formatted answer citing specific statutory sections, punishments, procedural steps, and relevant legal principles — with a qualified disclaimer.</p>
            </div>
        </div>
    </div>
</div>

<div class="section">
    <div class="section-header">
        <h2>Frequently Asked Questions</h2>
        <p>Got questions about BNS AI? We've got answers.</p>
    </div>
    <div class="faq-list">
        <div class="faq-item">
            <button class="faq-question" onclick="this.parentElement.classList.toggle('active')">
                <span>Is BNS AI free?</span>
                <span class="faq-icon">+</span>
            </button>
            <div class="faq-answer">Yes, BNS AI is completely free to use. You can ask legal questions, draft documents, and look up sections without any charges or registration required.</div>
        </div>
        <div class="faq-item">
            <button class="faq-question" onclick="this.parentElement.classList.toggle('active')">
                <span>Is this legal advice?</span>
                <span class="faq-icon">+</span>
            </button>
            <div class="faq-answer">BNS AI is an AI-powered legal information tool, not a law firm. It provides educational information and should not replace professional legal advice. Always consult a qualified advocate for specific legal matters.</div>
        </div>
        <div class="faq-item">
            <button class="faq-question" onclick="this.parentElement.classList.toggle('active')">
                <span>What areas of law does it cover?</span>
                <span class="faq-icon">+</span>
            </button>
            <div class="faq-answer">BNS AI covers BNS (Bharatiya Nyaya Sanhita), BNSS (Bharatiya Nagarik Suraksha Sanhita), BSA (Bharatiya Sakshya Adhiniyam), Constitution, IPC, CrPC, CPC, family law, property law, consumer law, labour law, and more.</div>
        </div>
        <div class="faq-item">
            <button class="faq-question" onclick="this.parentElement.classList.toggle('active')">
                <span>What documents can I draft?</span>
                <span class="faq-icon">+</span>
            </button>
            <div class="faq-answer">You can draft FIRs, legal notices, bail applications, affidavits, consumer complaints, agreements, civil plaints, divorce petitions, wills, and more professional legal documents.</div>
        </div>
        <div class="faq-item">
            <button class="faq-question" onclick="this.parentElement.classList.toggle('active')">
                <span>Does it work offline?</span>
                <span class="faq-icon">+</span>
            </button>
            <div class="faq-answer">Yes, BNS AI is designed with an offline-first approach. It has a built-in knowledge base that works without internet, with graceful fallback from AI models to the local knowledge base.</div>
        </div>
    </div>
</div>

<div class="cta-section">
    <h2>Have a Legal Query? Ask for Free.</h2>
    <p>1,000+ users have already asked. No signup required.</p>
    <a href="#/chat" class="btn btn-lg">Start Asking Questions</a>
</div>

<footer id="footer">
    <div class="footer-grid">
        <div class="footer-brand">
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
                <span style="font-size:22px;">⚖️</span>
                <span style="font-size:17px;font-weight:700;color:#fff;">BNS AI</span>
            </div>
            <p>India's offline-first legal AI platform for criminal law research, document drafting, and section lookup. Accessible, private, and always free.</p>
            <div class="footer-social">
                <a href="#">𝕏</a>
                <a href="#">in</a>
                <a href="#">▶</a>
            </div>
        </div>
        <div class="footer-col">
            <h4>Product</h4>
            <a href="#/chat">AI Chat</a>
            <a href="#/drafting">Draft Documents</a>
            <a href="#/dashboard">Dashboard</a>
        </div>
        <div class="footer-col">
            <h4>Resources</h4>
            <a href="#/chat">Legal Guidance</a>
            <a href="#/drafting">Document Templates</a>
            <a href="#/chat">Section Lookup</a>
        </div>
        <div class="footer-col">
            <h4>Company</h4>
            <a href="#">About</a>
            <a href="#">Contact</a>
            <a href="#">Careers</a>
        </div>
        <div class="footer-col">
            <h4>Legal</h4>
            <a href="#">Privacy Policy</a>
            <a href="#">Terms of Service</a>
            <a href="#">Disclaimer</a>
        </div>
    </div>
    <div class="footer-bottom">
        <span>© ${new Date().getFullYear()} BNS AI. All rights reserved.</span>
        <span>Made with ❤️ in India</span>
    </div>
</footer>
`);
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
                        <div class="chat-empty">
                            <div class="empty-icon">⚖️</div>
                            <p>Start a conversation with BNS AI</p>
                            <p style="font-size:13px;">Ask about Indian law, legal procedures, or draft documents</p>
                        </div>
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
        if (chat.chats.length > 0) {
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
                        <h2>Legal Drafting</h2>
                        <p class="subtitle">Generate professional Indian legal documents step-by-step</p>
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
                <h2>Dashboard</h2>
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
