const authState = {
    user: null,
    isAuthenticated() { return !!this.user; },
    setUser(user) { this.user = user; },
    clear() { this.user = null; },
};
