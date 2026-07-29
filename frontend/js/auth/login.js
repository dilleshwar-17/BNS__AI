window.auth = {
    async register(email, username, password) {
        return api.post('/auth/register', { email, username, password });
    },

    async login(username, password) {
        const data = await api.post('/auth/login', { username, password });
        api.setToken(data.access_token);
        localStorage.setItem('refresh_token', data.refresh_token);
        return data;
    },

    async refresh() {
        const rt = localStorage.getItem('refresh_token');
        if (!rt) throw new Error('No refresh token');
        const data = await api.post('/auth/refresh', { refresh_token: rt });
        api.setToken(data.access_token);
        localStorage.setItem('refresh_token', data.refresh_token);
        return data;
    },

    async getMe() {
        return api.get('/users/me');
    },

    logout() {
        api.setToken(null);
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('user');
    },

    isLoggedIn() {
        return !!api.token;
    },

    async ensureAuth() {
        if (this.isLoggedIn()) {
            try {
                return await this.getMe();
            } catch {
                this.logout();
            }
        }
        return null;
    },
};
