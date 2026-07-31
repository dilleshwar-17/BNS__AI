window.themeManager = {
    load() {
        const saved = localStorage.getItem('theme');
        const theme = saved === 'light' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', theme);
        const btn = document.querySelector('#theme-toggle');
        if (btn) btn.textContent = theme === 'dark' ? '🌙' : '☀️';
    },
    toggle() {
        const html = document.documentElement;
        const current = html.getAttribute('data-theme');
        const next = current === 'dark' ? 'light' : 'dark';
        html.setAttribute('data-theme', next);
        const btn = document.querySelector('#theme-toggle');
        if (btn) btn.textContent = next === 'dark' ? '🌙' : '☀️';
        localStorage.setItem('theme', next);
    },
};
