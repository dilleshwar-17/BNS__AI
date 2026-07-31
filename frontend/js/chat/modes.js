const chatModes = {
    list: [
        { value: 'legal_guidance', label: 'Legal Guidance' },
        { value: 'legal_drafting', label: 'Legal Drafting' },
        { value: 'section_lookup', label: 'Section Lookup' },
        { value: 'legal_procedure', label: 'Legal Procedure' },
        { value: 'rights_advisory', label: 'Rights Advisory' },
        { value: 'case_law', label: 'Case Law' },
        { value: 'comparison', label: 'Comparison' },
        { value: 'deep_research', label: 'Deep Research' },
    ],
    render(selected = 'legal_guidance') {
        return this.list.map(m => `<option value="${m.value}" ${m.value === selected ? 'selected' : ''}>${m.label}</option>`).join('');
    },
};

window.chatModes = chatModes;
