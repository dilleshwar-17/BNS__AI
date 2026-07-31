const spinner = {
    render() {
        return '<div class="loader"></div>';
    },
    show(container) {
        if (container) container.innerHTML = `<div class="loading-screen">${this.render()}<p>Loading...</p></div>`;
    },
};

window.spinner = spinner;
