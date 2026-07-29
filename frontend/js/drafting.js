const drafting = {
    templates: [],
    templateCache: {},
    questionnaireCache: {},
    currentType: null,
    currentGroupIndex: 0,
    formData: {},
    documents: [],
    currentDocId: null,
    autoSaveTimer: null,

    async loadTemplates() {
        try {
            const data = await api.get('/drafting/types');
            this.templates = data.templates || [];
            return this.templates;
        } catch { return []; }
    },

    async loadDocuments() {
        try {
            const data = await api.get('/drafting/documents?page_size=50');
            this.documents = data || [];
            return this.documents;
        } catch { return []; }
    },

    async generateDraft(draftType, details = {}) {
        api._clearCache();
        return api.post('/drafting/generate', { draft_type: draftType, details });
    },

    async getTemplate(draftType) {
        if (this.templateCache[draftType]) return this.templateCache[draftType];
        const data = await api.get(`/drafting/templates/${draftType}`);
        this.templateCache[draftType] = data;
        return data;
    },

    async getQuestionnaire(draftType) {
        if (this.questionnaireCache[draftType]) return this.questionnaireCache[draftType];
        const data = await api.get(`/drafting/questionnaire/${draftType}`);
        this.questionnaireCache[draftType] = data;
        return data;
    },

    async validateGroup(draftType, groupId, details) {
        try {
            return await api.post(`/drafting/questionnaire/${draftType}/validate`, {
                draft_type: draftType, group_id: groupId, details: details
            });
        } catch { return { valid: false, errors: [] }; }
    },

    async suggestField(draftType, fieldId, context) {
        try {
            const res = await api.post(`/drafting/questionnaire/${draftType}/suggest`, {
                draft_type: draftType, field_id: fieldId, context: context
            });
            return res.suggestion || '';
        } catch { return ''; }
    },

    async downloadDocx(docId) {
        try {
            const token = localStorage.getItem('access_token');
            const resp = await fetch(`/api/v1/drafting/export/${docId}/docx`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (!resp.ok) throw new Error('Download failed');
            const blob = await resp.blob();
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = 'document.docx';
            a.click();
            URL.revokeObjectURL(a.href);
        } catch (e) {
            this.showToast('Download failed: ' + e.message);
        }
    },

    async downloadPdf(docId) {
        try {
            const token = localStorage.getItem('access_token');
            const resp = await fetch(`/api/v1/drafting/export/${docId}/pdf`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (!resp.ok) throw new Error('Download failed');
            const blob = await resp.blob();
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = 'document.pdf';
            a.click();
            URL.revokeObjectURL(a.href);
        } catch (e) {
            this.showToast('Download failed: ' + e.message);
        }
    },

    async downloadMarkdown(docId) {
        try {
            const token = localStorage.getItem('access_token');
            const resp = await fetch(`/api/v1/drafting/export/${docId}/markdown`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (!resp.ok) throw new Error('Download failed');
            const blob = await resp.blob();
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = 'document.md';
            a.click();
            URL.revokeObjectURL(a.href);
        } catch (e) {
            this.showToast('Download failed: ' + e.message);
        }
    },

    async initPage() {
        await this.loadTemplates();
        await this.loadDocuments();
        this.renderDashboard();
        this.renderRecentDrafts();
    },

    renderDashboard() {
        const grid = document.getElementById('draft-grid');
        if (!grid) return;
        if (this.templates.length === 0) {
            grid.innerHTML = '<div class="loading-screen"><div class="loader"></div><p>Loading templates...</p></div>';
            return;
        }

        const categories = {};
        this.templates.forEach(t => {
            const cat = t.category || 'general';
            if (!categories[cat]) categories[cat] = [];
            categories[cat].push(t);
        });

        let html = '';
        for (const [cat, items] of Object.entries(categories)) {
            html += `<h3 class="draft-category-title">${cat.charAt(0).toUpperCase() + cat.slice(1)}</h3>`;
            html += '<div class="draft-grid-inner">';
            items.forEach(t => {
                const icon = this.getIcon(t.id);
                html += `
                    <div class="draft-card" onclick="drafting.startWizard('${t.id}')">
                        <div class="draft-card-icon">${icon}</div>
                        <h3>${t.title}</h3>
                        <p>${t.description || ''}</p>
                        ${t.estimated_time ? `<span class="draft-time">${t.estimated_time}</span>` : ''}
                    </div>
                `;
            });
            html += '</div>';
        }
        grid.innerHTML = html;
    },

    getIcon(type) {
        const icons = {
            fir: '\u{1F4DC}', legal_notice: '\u{1F4EC}', bail_application: '\u{1F6E1}',
            affidavit: '\u{1F4C3}', consumer_complaint: '\u{1F6E0}',
            agreement: '\u{1F4CB}', civil_plaint: '\u{2696}',
            divorce_petition: '\u{1F48D}', will: '\u{1F4BC}',
            anticipatory_bail: '\u{1F6E1}', undertaking: '\u{1F4B0}'
        };
        return icons[type] || '\u{1F4C4}';
    },

    renderRecentDrafts() {
        const list = document.getElementById('draftRecentList');
        if (!list) return;
        if (this.documents.length === 0) {
            list.innerHTML = '<p class="text-muted">No drafts yet. Generate one above.</p>';
            return;
        }
        list.innerHTML = this.documents.slice(0, 5).map(d => `
            <div class="draft-recent-item" onclick="drafting.openDraft('${d.id}')">
                <span>${d.title}</span>
                <span class="draft-recent-date">${new Date(d.created_at).toLocaleDateString()}</span>
            </div>
        `).join('');
    },

    startWizard(type) {
        const grid = document.getElementById('draft-grid');
        const wizard = document.getElementById('draft-wizard');
        const preview = document.getElementById('draft-preview');
        if (grid) grid.style.display = 'none';
        if (preview) preview.classList.remove('visible');
        if (wizard) {
            wizard.style.display = 'block';
            wizard.scrollIntoView({ behavior: 'smooth' });
        }
        this.currentType = type;
        this.currentGroupIndex = 0;
        this.formData = {};
        this.currentDocId = null;
        this.loadWizard(type);
        this.startAutoSave();
    },

    backToDashboard() {
        const grid = document.getElementById('draft-grid');
        const wizard = document.getElementById('draft-wizard');
        if (grid) grid.style.display = '';
        if (wizard) wizard.style.display = 'none';
        this.currentType = null;
        this.stopAutoSave();
    },

    async loadWizard(type) {
        try {
            const q = await this.getQuestionnaire(type);
            this.renderWizard(q);
        } catch (e) {
            this.showToast('Failed to load questionnaire');
            this.backToDashboard();
        }
    },

    renderWizard(q) {
        const wizard = document.getElementById('draft-wizard');
        if (!wizard) return;

        const groups = q.groups || [];
        const totalGroups = groups.length;
        const current = this.currentGroupIndex;
        const group = groups[current];
        if (!group && totalGroups > 0) {
            this.currentGroupIndex = 0;
            return this.renderWizard(q);
        }

        const progressPct = totalGroups > 0 ? ((current + 1) / totalGroups) * 100 : 0;

        wizard.innerHTML = `
            <div class="wizard-header">
                <button class="btn btn-ghost btn-sm" onclick="drafting.backToDashboard()">&larr; Back to Templates</button>
                <h2>${q.title}</h2>
                <p class="wizard-desc">${q.description || ''}</p>
            </div>
            <div class="wizard-progress">
                <div class="wizard-progress-bar">
                    <div class="wizard-progress-fill" style="width:${progressPct}%"></div>
                </div>
                <div class="wizard-progress-steps">
                    ${groups.map((g, i) => `
                        <div class="wizard-step ${i < current ? 'completed' : i === current ? 'active' : ''}">
                            <div class="wizard-step-num">${i < current ? '\u2713' : i + 1}</div>
                            <span>${g.title}</span>
                        </div>
                    `).join('')}
                </div>
            </div>
            <div class="wizard-group">
                <div class="wizard-group-header">
                    <h3>${group.title}</h3>
                    <p>${group.description || ''}</p>
                </div>
                <div class="wizard-fields" id="wizardFields">
                    ${group.fields ? group.fields.map(f => this.renderField(f)).join('') : ''}
                </div>
                <div class="wizard-errors" id="wizardErrors"></div>
                <div class="wizard-nav">
                    ${current > 0 ? `<button class="btn btn-outline" onclick="drafting.prevGroup()">&larr; Previous</button>` : '<div></div>'}
                    ${current < totalGroups - 1
                        ? `<button class="btn btn-primary" onclick="drafting.nextGroup()">Next Step &rarr;</button>`
                        : `<button class="btn btn-primary btn-lg" onclick="drafting.reviewAndGenerate()" id="generateBtn">Review & Generate Document</button>`
                    }
                </div>
            </div>
        `;
        this.restoreFieldValues();
        this.bindConditionals();
    },

    renderField(f) {
        const val = this.formData[f.id] || '';
        const required = f.required ? ' <span class="field-required">*</span>' : '';
        const type = f.type;
        const placeholder = f.placeholder || '';
        const id = `field_${f.id}`;

        let inputHtml = '';
        switch (type) {
            case 'textarea':
                inputHtml = `<textarea id="${id}" class="wizard-input wizard-textarea" placeholder="${placeholder}" oninput="drafting.onFieldChange('${f.id}', this.value)">${val}</textarea>`;
                break;
            case 'date':
                inputHtml = `<input type="date" id="${id}" class="wizard-input" value="${val}" onchange="drafting.onFieldChange('${f.id}', this.value)">`;
                break;
            case 'select':
                const opts = (f.options || []).map(o =>
                    `<option value="${o.value}" ${val === o.value ? 'selected' : ''}>${o.label}</option>`
                ).join('');
                inputHtml = `<select id="${id}" class="wizard-input wizard-select" onchange="drafting.onFieldChange('${f.id}', this.value);drafting.onConditionalChange()"><option value="">Select...</option>${opts}</select>`;
                break;
            case 'boolean':
                const checked = val === true || val === 'true' ? 'checked' : '';
                inputHtml = `<label class="wizard-checkbox"><input type="checkbox" id="${id}" ${checked} onchange="drafting.onFieldChange('${f.id}', this.checked);drafting.onConditionalChange()"> <span>Yes</span></label>`;
                break;
            case 'number':
                inputHtml = `<input type="number" id="${id}" class="wizard-input" placeholder="${placeholder}" value="${val}" oninput="drafting.onFieldChange('${f.id}', this.value)">`;
                break;
            case 'phone':
                inputHtml = `<input type="tel" id="${id}" class="wizard-input" placeholder="${placeholder}" value="${val}" oninput="drafting.onFieldChange('${f.id}', this.value)">`;
                break;
            case 'email':
                inputHtml = `<input type="email" id="${id}" class="wizard-input" placeholder="${placeholder}" value="${val}" oninput="drafting.onFieldChange('${f.id}', this.value)">`;
                break;
            default:
                inputHtml = `<input type="text" id="${id}" class="wizard-input" placeholder="${placeholder}" value="${val}" oninput="drafting.onFieldChange('${f.id}', this.value)">`;
        }

        const condClass = f.conditional ? ' wizard-field-conditional' : '';
        return `
            <div class="wizard-field${condClass}" id="fieldGroup_${f.id}" ${f.conditional ? `style="display:${this.evaluateCondition(f) ? 'block' : 'none'}"` : ''}>
                <label class="wizard-label" for="${id}">${f.label}${required}</label>
                ${inputHtml}
                <div class="wizard-field-actions">
                    <button class="btn btn-ghost btn-xs wizard-suggest-btn" onclick="drafting.getSuggestion('${f.id}')" title="AI Suggest" type="button">AI Suggest</button>
                    <span class="wizard-field-error" id="fieldError_${f.id}"></span>
                </div>
            </div>
        `;
    },

    evaluateCondition(f) {
        if (!f.conditional) return true;
        const parts = f.conditional.split('_');
        if (parts.length >= 2) {
            const prefix = parts[0];
            if (prefix === 'type') {
                const fieldKey = 'agreement_type';
                const expectedVal = parts.slice(1).join('_');
                return this.formData[fieldKey] === expectedVal;
            }
        }
        const fieldKey = f.conditional;
        const val = this.formData[fieldKey];
        return val === true || val === 'true';
    },

    bindConditionals() {
    },

    onConditionalChange() {
        const q = this.questionnaireCache[this.currentType];
        if (!q || !q.groups) return;
        const group = q.groups[this.currentGroupIndex];
        if (!group || !group.fields) return;
        group.fields.forEach(f => {
            if (f.conditional) {
                const el = document.getElementById(`fieldGroup_${f.id}`);
                if (el) {
                    el.style.display = this.evaluateCondition(f) ? 'block' : 'none';
                }
            }
        });
    },

    onFieldChange(fieldId, value) {
        this.formData[fieldId] = value;
        const errEl = document.getElementById(`fieldError_${fieldId}`);
        if (errEl) errEl.textContent = '';
    },

    restoreFieldValues() {
        Object.keys(this.formData).forEach(fid => {
            const el = document.getElementById(`field_${fid}`);
            if (el) {
                if (el.type === 'checkbox') el.checked = this.formData[fid] === true || this.formData[fid] === 'true';
                else el.value = this.formData[fid] || '';
            }
        });
    },

    async getSuggestion(fieldId) {
        const q = this.questionnaireCache[this.currentType];
        if (!q) return;
        const btn = document.querySelector(`#fieldGroup_${fieldId} .wizard-suggest-btn`);
        if (btn) { btn.textContent = '...'; btn.disabled = true; }
        const suggestion = await this.suggestField(this.currentType, fieldId, this.formData);
        if (suggestion) {
            this.formData[fieldId] = suggestion;
            const el = document.getElementById(`field_${fieldId}`);
            if (el) { el.value = suggestion; }
        }
        if (btn) { btn.textContent = 'AI Suggest'; btn.disabled = false; }
    },

    async nextGroup() {
        const q = this.questionnaireCache[this.currentType];
        if (!q) return;
        const group = q.groups[this.currentGroupIndex];
        if (!group) return;

        const errorsEl = document.getElementById('wizardErrors');
        errorsEl.innerHTML = '';

        const result = await this.validateGroup(this.currentType, group.id, this.formData);
        if (result && result.errors && result.errors.length > 0) {
            result.errors.forEach(e => {
                const errEl = document.getElementById(`fieldError_${e.field}`);
                if (errEl) errEl.textContent = e.message;
            });
            errorsEl.innerHTML = '<div class="wizard-error-banner">Please fix the highlighted fields before continuing.</div>';
            errorsEl.scrollIntoView({ behavior: 'smooth' });
            return;
        }
        this.currentGroupIndex++;
        this.renderWizard(q);
    },

    prevGroup() {
        if (this.currentGroupIndex > 0) {
            this.currentGroupIndex--;
            const q = this.questionnaireCache[this.currentType];
            if (q) this.renderWizard(q);
        }
    },

    async reviewAndGenerate() {
        const q = this.questionnaireCache[this.currentType];
        if (!q) return;

        const btn = document.getElementById('generateBtn');
        if (btn) { btn.textContent = 'Generating...'; btn.disabled = true; }

        const loadingHtml = `
            <div class="wizard-group">
                <div class="wizard-loading">
                    <div class="loader"></div>
                    <h3>Generating Your ${q.title}</h3>
                    <div class="wizard-progress-steps-vertical">
                        <div class="wizard-step active" id="genStep1"><span>Retrieving legal provisions...</span></div>
                        <div class="wizard-step" id="genStep2"><span>Building prompt...</span></div>
                        <div class="wizard-step" id="genStep3"><span>Generating draft with AI...</span></div>
                        <div class="wizard-step" id="genStep4"><span>Validating and formatting...</span></div>
                    </div>
                </div>
            </div>
        `;
        const wizard = document.getElementById('draft-wizard');
        if (wizard) wizard.innerHTML = loadingHtml;

        setTimeout(() => {
            document.getElementById('genStep1')?.classList.add('active');
        }, 300);
        setTimeout(() => {
            document.getElementById('genStep1')?.classList.add('completed');
            document.getElementById('genStep2')?.classList.add('active');
        }, 800);
        setTimeout(() => {
            document.getElementById('genStep2')?.classList.add('completed');
            document.getElementById('genStep3')?.classList.add('active');
        }, 1500);

        try {
            const result = await this.generateDraft(this.currentType, this.formData);
            if (result && result.content) {
                this.currentDocId = result.id;
                this.showDraftPreview(q.title, result.content, result.id);
            } else {
                const tpl = await this.getTemplate(this.currentType);
                const tplContent = tpl && tpl.template ? tpl.template.template : '';
                this.showDraftPreview(q.title, tplContent, null);
            }
            this.stopAutoSave();
        } catch (e) {
            this.showToast('Generation failed: ' + (e.detail || e.message));
            const tpl = await this.getTemplate(this.currentType);
            const tplContent = tpl && tpl.template ? tpl.template.template : '';
            this.showDraftPreview(q.title, tplContent, null);
            this.stopAutoSave();
        } finally {
            if (btn) { btn.textContent = 'Review & Generate Document'; btn.disabled = false; }
        }
    },

    showDraftPreview(title, content, docId) {
        const preview = document.getElementById('draft-preview');
        const titleEl = document.getElementById('draft-title');
        const contentEl = document.getElementById('draft-content');
        const actionsEl = document.getElementById('draft-actions');
        if (!preview || !contentEl) return;

        titleEl.textContent = title;
        contentEl.textContent = content;
        preview.dataset.draftContent = content;
        preview.dataset.draftTitle = title;
        preview.classList.add('visible');
        preview.scrollIntoView({ behavior: 'smooth' });

        if (actionsEl) {
            let btns = `
                <button class="btn btn-primary btn-sm" onclick="drafting.saveCurrentDraft()">Save</button>
                <button class="btn btn-outline btn-sm" onclick="drafting.copyContent()">Copy</button>
                <button class="btn btn-outline btn-sm" onclick="drafting.downloadTxt()">Download TXT</button>
            `;
            if (docId) {
                btns += `
                    <button class="btn btn-outline btn-sm" onclick="drafting.downloadDocx('${docId}')">DOCX</button>
                    <button class="btn btn-outline btn-sm" onclick="drafting.downloadPdf('${docId}')">PDF</button>
                    <button class="btn btn-outline btn-sm" onclick="drafting.downloadMarkdown('${docId}')">MD</button>
                `;
            }
            btns += `<button class="btn btn-ghost btn-sm" onclick="document.getElementById('draft-preview').classList.remove('visible')">Close</button>`;
            actionsEl.innerHTML = btns;
        }

        this.loadDocuments();
        this.renderRecentDrafts();
    },

    async saveCurrentDraft() {
        const preview = document.getElementById('draft-preview');
        const content = preview.dataset.draftContent;
        const title = preview.dataset.draftTitle;
        const draftType = this.currentType || 'fir';
        if (!content) return;
        try {
            await api.post('/drafting/save', { draft_type: draftType, title: title, content: content });
            this.showToast('Draft saved successfully!');
            await this.loadDocuments();
            this.renderRecentDrafts();
        } catch (err) {
            this.showToast('Error saving: ' + (err.detail || err.message));
        }
    },

    copyContent() {
        const content = document.getElementById('draft-content');
        if (!content) return;
        navigator.clipboard.writeText(content.textContent).then(() => {
            this.showToast('Copied to clipboard!');
        });
    },

    downloadTxt() {
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

    async openDraft(docId) {
        try {
            const doc = await api.get(`/drafting/documents/${docId}`);
            if (doc) {
                this.currentType = doc.doc_type;
                this.showDraftPreview(doc.title, doc.content, doc.id);
            }
        } catch (e) {
            this.showToast('Failed to load draft');
        }
    },

    startAutoSave() {
        this.stopAutoSave();
        this.autoSaveTimer = setInterval(() => {
            if (this.currentType && Object.keys(this.formData).length > 0) {
                localStorage.setItem(`draft_auto_${this.currentType}`, JSON.stringify(this.formData));
            }
        }, 5000);
    },

    stopAutoSave() {
        if (this.autoSaveTimer) {
            clearInterval(this.autoSaveTimer);
            this.autoSaveTimer = null;
        }
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

window.drafting = drafting;
