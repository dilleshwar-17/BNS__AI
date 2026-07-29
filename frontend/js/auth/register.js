const registerPage = {
    render() {
        return `
            <div class="auth-page">
                <div class="auth-card">
                    <h2>Create Account</h2>
                    <div class="error-message" id="register-error"></div>
                    <form id="register-form" onsubmit="registerPage.handleSubmit(event)">
                        <div class="form-group">
                            <label>Email</label>
                            <input type="email" id="reg-email" required placeholder="Enter your email">
                        </div>
                        <div class="form-group">
                            <label>Username</label>
                            <input type="text" id="reg-username" required placeholder="Choose a username">
                        </div>
                        <div class="form-group">
                            <label>Password</label>
                            <input type="password" id="reg-password" required placeholder="Create a password" minlength="6">
                        </div>
                        <div class="form-group">
                            <button type="submit" class="btn btn-primary">Register</button>
                        </div>
                    </form>
                    <div class="form-footer">Already have an account? <a href="#/login">Login</a></div>
                </div>
            </div>
        `;
    },
    async handleSubmit(e) {
        e.preventDefault();
        try {
            await authAPI.register(
                document.getElementById('reg-email').value,
                document.getElementById('reg-username').value,
                document.getElementById('reg-password').value
            );
            await authAPI.login(
                document.getElementById('reg-username').value,
                document.getElementById('reg-password').value
            );
            router.navigate('/chat');
        } catch (err) {
            const el = document.getElementById('register-error');
            if (el) { el.textContent = err.detail || err.message; el.style.display = 'block'; }
        }
    },
};
