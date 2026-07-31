const profilePage = {
    render() {
        return `
            <div class="dashboard-page">
                <div class="section-header reveal" style="text-align:left;max-width:none;margin:0 0 28px;">
                    <h2>Profile</h2>
                    <p class="subtitle">Your account details</p>
                </div>
                <div class="profile-card reveal" id="profile-card" style="max-width:520px;">
                    <div class="loading-screen" style="min-height:180px;">
                        <div class="loader"></div>
                        <p>Loading profile...</p>
                    </div>
                </div>
            </div>
        `;
    },

    async load() {
        const card = document.getElementById('profile-card');
        if (!card) return;
        try {
            const user = await authAPI.me();
            const name = user.username || user.email || 'User';
            const initials = name.split(/[\s@]/).filter(Boolean).slice(0, 2)
                .map(p => p[0].toUpperCase()).join('') || 'U';
            const joined = user.created_at ? new Date(user.created_at).toLocaleDateString() : 'Unknown';
            const role = user.is_superuser ? 'Admin'
                : (user.role && user.role !== 'user' ? user.role : 'Standard User');

            card.innerHTML = `
                <div class="profile-header" style="display:flex;align-items:center;gap:18px;margin-bottom:24px;">
                    <div class="profile-avatar" style="width:64px;height:64px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:24px;font-weight:700;color:#fff;background:linear-gradient(135deg,var(--jade),var(--gold));">${initials}</div>
                    <div>
                        <h3 style="margin:0;font-size:20px;">${this.escapeHtml(name)}</h3>
                        <span class="badge" style="margin-top:6px;">${role}</span>
                    </div>
                </div>
                <div class="dashboard-list">
                    <div class="dashboard-list-item">
                        <div><div class="item-title">Username</div><div class="item-meta">${this.escapeHtml(user.username || '—')}</div></div>
                    </div>
                    <div class="dashboard-list-item">
                        <div><div class="item-title">Email</div><div class="item-meta">${this.escapeHtml(user.email || '—')}</div></div>
                    </div>
                    <div class="dashboard-list-item">
                        <div><div class="item-title">Member Since</div><div class="item-meta">${joined}</div></div>
                    </div>
                    <div class="dashboard-list-item">
                        <div><div class="item-title">Role</div><div class="item-meta">${role}</div></div>
                    </div>
                </div>
                <div style="display:flex;gap:10px;margin-top:24px;">
                    <a href="#/settings" class="btn btn-outline btn-sm">Settings</a>
                    <button class="btn btn-outline btn-sm" onclick="logout.execute()">Logout</button>
                </div>
            `;
        } catch (err) {
            card.innerHTML = `
                <div class="chat-empty" style="min-height:200px;">
                    <div class="empty-icon">🔒</div>
                    <p>Could not load your profile.</p>
                    <p style="font-size:13px;">${this.escapeHtml(err.detail || err.message)}</p>
                    <a href="#/login" class="btn btn-outline btn-sm">Sign In</a>
                </div>
            `;
        }
    },

    escapeHtml(text) {
        const d = document.createElement('div');
        d.textContent = text == null ? '' : String(text);
        return d.innerHTML;
    },
};

window.profilePage = profilePage;
