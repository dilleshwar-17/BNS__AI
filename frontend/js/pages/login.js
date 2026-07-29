const loginPage = {
    render() {
        return `
            <div class="auth-page">
                <div class="auth-card">
                    <h2>Welcome Back</h2>
                    <div class="error-message" id="login-error"></div>
                    <form id="login-form" onsubmit="loginPage.handleSubmit(event)">
                        <div class="form-group">
                            <label>Username</label>
                            <input type="text" id="login-username" required placeholder="Enter your username">
                        </div>
                        <div class="form-group">
                            <label>Password</label>
                            <input type="password" id="login-password" required placeholder="Enter your password">
                        </div>
                        <div class="form-group">
                            <button type="submit" class="btn btn-primary">Login</button>
                        </div>
                    </form>
                    <div class="form-footer">Don't have an account? <a href="#/register">Register</a></div>
                </div>
            </div>
        `;
    },
    async handleSubmit(e) {
        e.preventDefault();
        try {
            await authAPI.login(
                document.getElementById('login-username').value,
                document.getElementById('login-password').value
            );
            app.currentUser = await authAPI.me();
            app.updateUI();
            router.navigate('/chat');
        } catch (err) {
            const el = document.getElementById('login-error');
            if (el) { el.textContent = err.detail || err.message; el.style.display = 'block'; }
        }
    },
};
