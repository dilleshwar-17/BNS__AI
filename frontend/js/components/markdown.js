const markdown = {
    render(text) {
        if (!text) return '';
        let html = this.escapeHtml(text);
        html = html.replace(/### (.+)/g, '<h3>$1</h3>');
        html = html.replace(/## (.+)/g, '<h2>$1</h2>');
        html = html.replace(/# (.+)/g, '<h1>$1</h1>');
        html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
        html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');
        html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
        html = html.replace(/^- (.+)/gm, '<li>$1</li>');
        html = html.replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>');
        html = html.replace(/\n\n/g, '</p><p>');
        html = '<p>' + html + '</p>';
        html = html.replace(/<p><\/p>/g, '');
        return html;
    },
    escapeHtml(text) {
        const d = document.createElement('div');
        d.textContent = text;
        return d.innerHTML;
    },
};
