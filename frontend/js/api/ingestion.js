const ingestionAPI = {
    ingest(fileId, params) {
        const q = params ? '?' + new URLSearchParams(params).toString() : '';
        return api.post(`/ingestion/ingest/${fileId}` + q);
    },
    listJobs(params) {
        const q = params ? '?' + new URLSearchParams(params).toString() : '';
        return api.get('/ingestion/jobs' + q);
    },
    getJob(jobId) {
        return api.get(`/ingestion/jobs/${jobId}`);
    },
    adminListJobs(params) {
        const q = params ? '?' + new URLSearchParams(params).toString() : '';
        return api.get('/ingestion/admin/jobs' + q);
    },
};
