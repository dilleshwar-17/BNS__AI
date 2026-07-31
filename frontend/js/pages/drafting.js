window.drafting = {
    draftTypes: [],
    templateCache: {},

    async loadDraftTypes() {
        try {
            const data = await api.get('/drafting/types');
            this.draftTypes = data.draft_types;
            return this.draftTypes;
        } catch { return []; }
    },

    async generateDraft(draftType, details = {}) {
        api._clearCache();
        return api.post('/drafting/generate', { draft_type: draftType, details });
    },

    async getDocuments() {
        return api.get('/drafting/documents');
    },

    async deleteDocument(docId) {
        api._clearCache();
        return api.del(`/drafting/documents/${docId}`);
    },

    async getTemplate(draftType) {
        if (this.templateCache[draftType]) {
            return this.templateCache[draftType];
        }
        const data = await api.get(`/drafting/templates/${draftType}`);
        this.templateCache[draftType] = data;
        return data;
    },

    renderCards() {
        const grid = document.getElementById('draft-grid');
        if (!grid) return;
        const labels = {
            fir: 'FIR', legal_notice: 'Legal Notice', bail_application: 'Bail Application',
            affidavit: 'Affidavit', consumer_complaint: 'Consumer Complaint',
            agreement: 'Agreement', civil_plaint: 'Civil Plaint',
            divorce_petition: 'Divorce Petition', will: 'Will'
        };
        const descriptions = {
            fir: 'File a First Information Report', legal_notice: 'Send a formal legal notice',
            bail_application: 'Apply for regular bail', affidavit: 'Create a sworn affidavit',
            consumer_complaint: 'File a consumer complaint', agreement: 'Draft a contract or agreement',
            civil_plaint: 'File a civil suit plaint', divorce_petition: 'File for divorce',
            will: 'Create a last will and testament'
        };
        const icons = {
            fir: '📄', legal_notice: '📬', bail_application: '🛡️',
            affidavit: '📋', consumer_complaint: '🛠️', agreement: '📑',
            civil_plaint: '⚖️', divorce_petition: '💍', will: '💼'
        };
        grid.innerHTML = this.draftTypes.map(type => `
            <div class="draft-card reveal">
                <div class="draft-card-icon">${icons[type] || '📄'}</div>
                <h3>${labels[type] || type}</h3>
                <p>${descriptions[type] || ''}</p>
                <button class="btn btn-primary btn-sm" onclick="drafting.previewTemplate('${type}')">Generate</button>
            </div>
        `).join('');
    },

    async previewTemplate(draftType) {
        const preview = document.getElementById('draft-preview');
        const content = document.getElementById('draft-content');
        const title = document.getElementById('draft-title');
        if (!preview || !content) return;

        content.textContent = 'Loading...';
        preview.classList.add('visible');

        try {
            const template = await this.getTemplate(draftType);
            title.textContent = template.title;
            content.textContent = template.template;
            preview.dataset.draftType = draftType;
        } catch (err) {
            content.textContent = 'Error loading template: ' + (err.detail || err.message);
        }
    },

    async saveCurrentDraft() {
        const preview = document.getElementById('draft-preview');
        const content = document.getElementById('draft-content');
        const draftType = preview.dataset.draftType;
        if (!draftType || !content) return;
        try {
            await this.generateDraft(draftType, {});
            this.showToast('Draft saved successfully!');
        } catch (err) {
            this.showToast('Error saving draft: ' + (err.detail || err.message));
        }
    },

    copyDraft() {
        const content = document.getElementById('draft-content');
        if (!content) return;
        navigator.clipboard.writeText(content.textContent).then(() => {
            this.showToast('Copied to clipboard!');
        });
    },

    downloadDraft() {
        const content = document.getElementById('draft-content');
        const title = document.getElementById('draft-title');
        if (!content) return;
        const blob = new Blob([content.textContent], { type: 'text/plain' });
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = (title ? title.textContent : 'draft') + '.txt';
        a.click();
        URL.revokeObjectURL(a.href);
    },

    showToast(msg) {
        const existing = document.querySelector('.toast');
        if (existing) existing.remove();
        const t = document.createElement('div');
        t.className = 'toast';
        t.textContent = msg;
        document.body.appendChild(t);
        setTimeout(() => t.remove(), 3000);
    }
};
