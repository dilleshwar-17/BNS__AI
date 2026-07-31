window.api = {
    baseUrl: '/api/v1',
    token: null,
    refreshToken: null,
    cache: new Map(),
    cacheTTL: 60000,

    _cacheKey(url, body) {
        return url + (body ? JSON.stringify(body) : '');
    },

    _getCached(key) {
        const entry = this.cache.get(key);
        if (entry && Date.now() - entry.ts < this.cacheTTL) {
            return entry.data;
        }
        this.cache.delete(key);
        return null;
    },

    _setCached(key, data) {
        if (this.cache.size > 50) {
            const oldest = this.cache.keys().next().value;
            this.cache.delete(oldest);
        }
        this.cache.set(key, { data, ts: Date.now() });
    },

    _clearCache() {
        this.cache.clear();
    },

    getToken() {
        return this.token || localStorage.getItem('access_token');
    },

    getRefreshToken() {
        return this.refreshToken || localStorage.getItem('refresh_token');
    },

    setToken(token) {
        this.token = token;
        if (token) localStorage.setItem('access_token', token);
        else localStorage.removeItem('access_token');
    },

    setRefreshToken(token) {
        this.refreshToken = token;
        if (token) localStorage.setItem('refresh_token', token);
        else localStorage.removeItem('refresh_token');
    },

    _timeoutFor(method, url) {
        if (method === 'POST') {
            if (url === '/chat' || url.startsWith('/chat/') || url === '/drafting/generate' || url.startsWith('/drafting/generate')) {
                return 120000;
            }
        }
        return 60000;
    },

    async _fetchWithTimeout(url, options, timeout = 60000) {
        const controller = new AbortController();
        const id = setTimeout(() => controller.abort(), timeout);
        options.signal = controller.signal;
        try {
            const resp = await fetch(url, options);
            return resp;
        } finally {
            clearTimeout(id);
        }
    },

    async request(method, url, body) {
        const cacheKey = this._cacheKey(url, body);
        if (method === 'GET') {
            const cached = this._getCached(cacheKey);
            if (cached) return cached;
        }

        const headers = { 'Content-Type': 'application/json' };
        const token = this.getToken();
        if (token) headers['Authorization'] = `Bearer ${token}`;

        try {
            const resp = await this._fetchWithTimeout(this.baseUrl + url, {
                method,
                headers,
                body: body ? JSON.stringify(body) : undefined,
            }, this._timeoutFor(method, url));
            if (resp.status === 401) {
                const refreshed = await this._tryRefresh();
                if (refreshed) {
                    headers['Authorization'] = `Bearer ${this.getToken()}`;
                    const retryResp = await this._fetchWithTimeout(this.baseUrl + url, {
                        method, headers,
                        body: body ? JSON.stringify(body) : undefined,
                    }, this._timeoutFor(method, url));
                    if (!retryResp.ok) throw await retryResp.json();
                    const data = await retryResp.json();
                    if (method === 'GET') this._setCached(cacheKey, data);
                    return data;
                }
                throw { detail: 'Session expired. Please login again.' };
            }
            if (!resp.ok) throw await resp.json();
            if (resp.status === 204) return null;
            const data = await resp.json();
            if (method === 'GET') this._setCached(cacheKey, data);
            return data;
        } catch (err) {
            if (err.detail) throw err;
            throw { detail: err.message || 'Network error. Check your connection.' };
        }
    },

    async _tryRefresh() {
        const refresh = this.getRefreshToken();
        if (!refresh) return false;
        try {
            const resp = await this._fetchWithTimeout(this.baseUrl + '/auth/refresh', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ refresh_token: refresh }),
            });
            if (!resp.ok) return false;
            const data = await resp.json();
            this.setToken(data.access_token);
            this.setRefreshToken(data.refresh_token);
            return true;
        } catch { return false; }
    },

    get(url) { return this.request('GET', url); },
    post(url, body) { return this.request('POST', url, body); },
    del(url) { return this.request('DELETE', url); },
};
