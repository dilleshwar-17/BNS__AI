window.themeManager = {
    load() {
        const saved = localStorage.getItem('theme');
        if (saved === 'light') {
            document.documentElement.setAttribute('data-theme', 'light');
            document.querySelector('#theme-toggle').textContent = '☀️';
        }
    },
    toggle() {
        const html = document.documentElement;
        const current = html.getAttribute('data-theme');
        const next = current === 'light' ? 'dark' : 'light';
        html.setAttribute('data-theme', next);
        document.querySelector('#theme-toggle').textContent = next === 'dark' ? '🌙' : '☀️';
        localStorage.setItem('theme', next);
    },
};
