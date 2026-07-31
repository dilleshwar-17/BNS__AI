const landingPage = {
    render() {
        return `
<section class="hero">
    <div class="hero-tag"><span>⚖️</span> India's AI Legal Assistant</div>
    <h1>BNS AI: Your <span>Legal Intelligence</span> for Indian Law</h1>
    <p class="subtitle">Criminal law queries, BNS section lookups, and AI-powered legal drafting — all in one platform. Free, private, and secure.</p>
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
        <span>⚡ Answers in Seconds</span>
    </div>
</section>

<div class="partner-section reveal">
    <p>Trusted by</p>
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

<div class="section section-dark">
    <div class="section-header reveal">
        <h2>Comprehensive Legal Intelligence Platform</h2>
        <p>Every tool you need to understand, research, and act on Indian criminal law — powered by AI, designed for clarity.</p>
    </div>
    <div class="features-grid">
        <div class="feature-card reveal">
            <div class="feature-icon"><svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="1.5"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg></div>
            <h3>Statute Coverage</h3>
            <p>Complete coverage of the Bharatiya Nyaya Sanhita.</p>
        </div>
        <div class="feature-card reveal">
            <div class="feature-icon"><svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="1.5"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg></div>
            <h3>AI Document Drafting</h3>
            <p>Generate professional legal documents — FIRs, bail applications, legal notices, affidavits, consumer complaints, agreements, and wills — through an intelligent step-by-step questionnaire.</p>
        </div>
        <div class="feature-card reveal">
            <div class="feature-icon"><svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="1.5"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg></div>
            <h3>Instant Section Lookup</h3>
            <p>Query any BNS, BNSS, or BSA section by number. Receive the full text, punishment, procedure, and illustrative examples in seconds.</p>
        </div>
        <div class="feature-card reveal">
            <div class="feature-icon"><svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="1.5"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg></div>
            <h3>Procedural Law Guidance</h3>
            <p>Step-by-step explanations of criminal procedure — from FIR registration and bail applications to trial process and appeals — and many more.</p>
        </div>

    </div>
</div>

<div class="section">
    <div class="section-header reveal">
        <h2>How BNS AI Works</h2>
        <p>A streamlined pipeline from question to actionable legal intelligence.</p>
    </div>
    <div class="steps-grid">
        <div class="step reveal-left">
            <div class="step-num">01</div>
            <div class="step-content">
                <h3>Submit Your Query</h3>
                <p>Pose your legal question in natural language — English or Hindi. BNS AI validates the query against its scope of Indian criminal law before processing.</p>
            </div>
        </div>
        <div class="step-connector"></div>
        <div class="step reveal">
            <div class="step-num">02</div>
            <div class="step-content">
                <h3>Intelligence Processing</h3>
                <p>Your query is classified by intent, enriched with context from the knowledge base and retrieved legal provisions, then processed through the AI engine.</p>
            </div>
        </div>
        <div class="step-connector"></div>
        <div class="step reveal-right">
            <div class="step-num">03</div>
            <div class="step-content">
                <h3>Structured Response</h3>
                <p>You receive a formatted answer citing specific statutory sections, punishments, procedural steps, and relevant legal principles — with a qualified disclaimer.</p>
            </div>
        </div>
    </div>
</div>

<div class="section">
    <div class="section-header reveal">
        <h2>Frequently Asked Questions</h2>
        <p>Got questions about BNS AI? We've got answers.</p>
    </div>
    <div class="faq-list">
        <div class="faq-item reveal">
            <button class="faq-question" onclick="this.parentElement.classList.toggle('active')">
                <span>Is BNS AI free?</span>
                <span class="faq-icon">+</span>
            </button>
            <div class="faq-answer">Yes, BNS AI is completely free to use. You can ask legal questions, draft documents, and look up sections without any charges or registration required.</div>
        </div>
        <div class="faq-item reveal">
            <button class="faq-question" onclick="this.parentElement.classList.toggle('active')">
                <span>Is this legal advice?</span>
                <span class="faq-icon">+</span>
            </button>
            <div class="faq-answer">BNS AI is an AI-powered legal information tool, not a law firm. It provides educational information and should not replace professional legal advice. Always consult a qualified advocate for specific legal matters.</div>
        </div>
        <div class="faq-item reveal">
            <button class="faq-question" onclick="this.parentElement.classList.toggle('active')">
                <span>What areas of law does it cover?</span>
                <span class="faq-icon">+</span>
            </button>
            <div class="faq-answer">BNS AI covers BNS (Bharatiya Nyaya Sanhita), BNSS (Bharatiya Nagarik Suraksha Sanhita), BSA (Bharatiya Sakshya Adhiniyam), Constitution, IPC, CrPC, CPC, family law, property law, consumer law, labour law, and more.</div>
        </div>
        <div class="faq-item reveal">
            <button class="faq-question" onclick="this.parentElement.classList.toggle('active')">
                <span>What documents can I draft?</span>
                <span class="faq-icon">+</span>
            </button>
            <div class="faq-answer">You can draft FIRs, legal notices, bail applications, affidavits, consumer complaints, agreements, civil plaints, divorce petitions, wills, and more professional legal documents.</div>
        </div>
    </div>
</div>

<div class="cta-section reveal">
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
            <p>India's AI legal platform for criminal law research, document drafting, and section lookup. Accessible, private, and always free.</p>
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
        `;
    },
};

window.landingPage = landingPage;
