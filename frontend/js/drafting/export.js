/**
 * Export Module - Handles DOCX, PDF, Markdown, Print, Copy actions
 */
export const Export = {
    async downloadDocx(docId) {
        return this._download(`/api/v1/drafting/export/${docId}/docx`, `${docId}.docx`);
    },

    async downloadPdf(docId) {
        return this._download(`/api/v1/drafting/export/${docId}/pdf`, `${docId}.pdf`);
    },

    async downloadMarkdown(docId) {
        return this._download(`/api/v1/drafting/export/${docId}/markdown`, `${docId}.md`);
    },

    copyText(content) {
        if (!content) return;
        navigator.clipboard.writeText(content).then(() => {
            alert('Draft content copied to clipboard!');
        }).catch(err => {
            console.error('Clipboard copy failed:', err);
        });
    },

    printDraft() {
        window.print();
    },

    async _download(url, filename) {
        try {
            const token = localStorage.getItem('access_token');
            const resp = await fetch(url, {
                headers: token ? { 'Authorization': `Bearer ${token}` } : {}
            });
            if (!resp.ok) throw new Error(`Download failed with status ${resp.status}`);
            const blob = await resp.blob();
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(a.href);
        } catch (e) {
            alert('Export failed: ' + e.message);
        }
    }
};
