const landingPage = {
    render() {
        return `
            <div class="hero">
                <h1>BNS AI</h1>
                <p>Your intelligent offline-first legal assistant for Indian law.</p>
                <div class="hero-buttons">
                    <a href="#/chat" class="btn btn-primary">Start Chatting</a>
                    <a href="#/drafting" class="btn btn-outline">Draft Documents</a>
                </div>
            </div>
            <div class="features">
                <div class="feature-card"><div class="feature-icon">⚖️</div><h3>Legal Guidance</h3><p>Expert guidance on Indian laws.</p></div>
                <div class="feature-card"><div class="feature-icon">📝</div><h3>Draft Documents</h3><p>Generate legal documents instantly.</p></div>
                <div class="feature-card"><div class="feature-icon">📚</div><h3>Offline First</h3><p>Built-in knowledge base works offline.</p></div>
                <div class="feature-card"><div class="feature-icon">🔒</div><h3>Secure & Private</h3><p>JWT auth, encrypted data.</p></div>
                <div class="feature-card"><div class="feature-icon">🔍</div><h3>Section Lookup</h3><p>Quick legal section references.</p></div>
                <div class="feature-card"><div class="feature-icon">🌐</div><h3>AI Powered</h3><p>Ollama, Gemini, offline KB.</p></div>
            </div>
        `;
    },
};
