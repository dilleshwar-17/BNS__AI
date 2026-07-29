const sidebar = {
    render(items, onItemClick) {
        return items.map(item => `
            <div class="sidebar-item" data-id="${item.id}">
                <div class="sidebar-item-title">${item.title}</div>
                <div class="sidebar-item-meta">${item.mode || ''}</div>
            </div>
        `).join('');
    },
};
