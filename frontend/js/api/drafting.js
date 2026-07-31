const draftingAPI = {
    getTypes() { return api.get('/drafting/types'); },
    getTemplate(type) { return api.get(`/drafting/templates/${type}`); },
    generate(type, details) { return api.post('/drafting/generate', { draft_type: type, details }); },
    listDocuments() { return api.get('/drafting/documents'); },
    getDocument(id) { return api.get(`/drafting/documents/${id}`); },
    deleteDocument(id) { return api.del(`/drafting/documents/${id}`); },
};

window.draftingAPI = draftingAPI;
