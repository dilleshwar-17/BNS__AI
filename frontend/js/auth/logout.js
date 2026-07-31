const logout = {
    execute() {
        authAPI.logout();
        app.currentUser = null;
        app.updateUI();
        router.navigate('/');
    },
};

window.logout = logout;
