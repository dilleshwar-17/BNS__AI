class HashRouter {
    constructor() {
        this.routes = {};
        window.addEventListener('hashchange', () => this.handleRoute());
    }

    add(pattern, handler) {
        this.routes[pattern] = handler;
    }

    navigate(path) {
        window.location.hash = path;
    }

    getCurrentPath() {
        return window.location.hash.slice(1) || '/';
    }

    handleRoute() {
        const path = this.getCurrentPath();
        const handler = this.routes[path] || this.routes['*'];
        if (handler) handler(path);
    }

    start() {
        this.handleRoute();
    }
}

window.router = new HashRouter();
