const notFoundPage = {
    render() {
        return `
            <div class="auth-page">
                <div class="auth-card reveal" style="text-align:center;padding:56px 40px;">
                    <div class="auth-icon">🔍</div>
                    <h2>404</h2>
                    <p class="auth-subtitle">Page not found — the page you're looking for doesn't exist.</p>
                    <div style="display:flex;gap:10px;justify-content:center;">
                        <a href="#/" class="btn btn-primary">Go Home</a>
                        <a href="#/chat" class="btn btn-outline">Ask a Legal Question</a>
                    </div>
                </div>
            </div>
        `;
    },
};

window.notFoundPage = notFoundPage;
