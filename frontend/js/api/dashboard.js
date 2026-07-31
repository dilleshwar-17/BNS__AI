const dashboardAPI = {
    getStats() { return api.get('/dashboard/'); },
};

window.dashboardAPI = dashboardAPI;
