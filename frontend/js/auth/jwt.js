window.jwt = {
    decode(token) {
        try {
            const payload = token.split('.')[1];
            return JSON.parse(atob(payload));
        } catch { return null; }
    },
    isExpired(token) {
        const data = this.decode(token);
        if (!data || !data.exp) return true;
        return Date.now() >= data.exp * 1000;
    },
};
