const documentsAPI = {
    list(params) {
        const q = params ? '?' + new URLSearchParams(params).toString() : '';
        return api.get('/documents/' + q);
    },
    get(id) {
        return api.get(`/documents/${id}`);
    },
    del(id) {
        return api.del(`/documents/${id}`);
    },
    adminList(params) {
        const q = params ? '?' + new URLSearchParams(params).toString() : '';
        return api.get('/documents/admin/all' + q);
    },
};

window.documentsAPI = documentsAPI;
