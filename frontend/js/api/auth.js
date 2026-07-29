window.authAPI = {
    async register(email, username, password) {
        return api.post('/auth/register', { email, username, password });
    },
    async login(username, password) {
        const data = await api.post('/auth/login', { username, password });
        api.setToken(data.access_token);
        api.setRefreshToken(data.refresh_token);
        return data;
    },
    async refresh() {
        const rt = api.getRefreshToken();
        if (!rt) throw new Error('No refresh token');
        const data = await api.post('/auth/refresh', { refresh_token: rt });
        api.setToken(data.access_token);
        api.setRefreshToken(data.refresh_token);
        return data;
    },
    async me() {
        return api.get('/users/me');
    },
    logout() {
        api.setToken(null);
        api.setRefreshToken(null);
        localStorage.removeItem('user');
    },
};
