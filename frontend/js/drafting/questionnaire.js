const draftingQuestionnaire = {
    render(type) {
        const fields = this.getFields(type);
        return fields.map(f => `
            <div class="form-group">
                <label>${f.label}</label>
                <input type="text" class="draft-field" data-field="${f.key}" placeholder="${f.placeholder || ''}">
            </div>
        `).join('');
    },
    getFields(type) {
        const fields = {
            fir: [{ key: 'complainant_name', label: 'Complainant Name' }, { key: 'incident_date', label: 'Date of Incident' }, { key: 'incident_place', label: 'Place of Incident' }, { key: 'description', label: 'Description' }],
            legal_notice: [{ key: 'sender_name', label: 'Sender Name' }, { key: 'recipient_name', label: 'Recipient Name' }, { key: 'subject', label: 'Subject' }],
        };
        return fields[type] || [];
    },
    getValues() {
        const inputs = document.querySelectorAll('.draft-field');
        const values = {};
        inputs.forEach(i => { values[i.dataset.field] = i.value; });
        return values;
    },
};
