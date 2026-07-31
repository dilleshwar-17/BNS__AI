const searchBox = {
    render(placeholder = 'Search...') {
        return `<div class="search-box"><input type="text" placeholder="${placeholder}" class="search-input" /></div>`;
    },
};

window.searchBox = searchBox;
