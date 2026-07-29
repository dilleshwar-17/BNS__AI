const navbar = {
    render() {
        return `
            <nav id="navbar">
                <div class="nav-brand" onclick="router.navigate('/')">
                    <span class="nav-logo">⚖️</span>
                    <span class="nav-title">BNS AI</span>
                </div>
                <div class="nav-links" id="nav-links">
                    <a href="#/chat" class="nav-link">Chat</a>
                    <a href="#/drafting" class="nav-link">Drafting</a>
                    <a href="#/admin/knowledge" class="nav-link" id="admin-nav-link" style="display:none">Knowledge</a>
                </div>
                <div class="nav-actions">
                    <button class="icon-btn" id="theme-toggle" onclick="app.toggleTheme()">🌙</button>
                    <a href="#/login" class="btn btn-outline btn-sm" id="login-btn">Login</a>
                    <a href="#/register" class="btn btn-primary btn-sm" id="register-btn">Register</a>
                    <div id="user-area" style="display:none;align-items:center;gap:12px;">
                        <span class="user-badge" id="user-name">User</span>
                        <button class="btn btn-outline btn-sm" onclick="logout.execute()">Logout</button>
                    </div>
                </div>
            </nav>
        `;
    },
};
