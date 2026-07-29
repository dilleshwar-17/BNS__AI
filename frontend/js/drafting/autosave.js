/**
 * Autosave Module - Handles debounced auto-saving to backend with localStorage fallback
 */
export const AutoSave = {
    timer: null,
    debounceMs: 1000,
    storageKey: 'bnsai_draft_autosave',

    save(sessionId, draftType, stepIndex, formData, apiCallback) {
        if (this.timer) clearTimeout(this.timer);

        // Store immediately in Local Storage as fallback
        this.saveLocal(sessionId, draftType, stepIndex, formData);
        this.showStatus('Saving progress...');

        this.timer = setTimeout(async () => {
            try {
                if (navigator.onLine && apiCallback) {
                    await apiCallback(sessionId, draftType, stepIndex, formData);
                    this.showStatus('✓ Draft Saved');
                } else {
                    this.showStatus('Saved offline');
                }
            } catch (err) {
                console.warn('Autosave backend call failed:', err);
                this.showStatus('Saved offline');
            }
        }, this.debounceMs);
    },

    saveLocal(sessionId, draftType, stepIndex, formData) {
        try {
            const data = {
                sessionId,
                draftType,
                stepIndex,
                formData,
                savedAt: new Date().toISOString()
            };
            localStorage.setItem(`${this.storageKey}_${sessionId || draftType}`, JSON.stringify(data));
        } catch (e) {
            console.error('LocalStorage write failed:', e);
        }
    },

    loadLocal(key) {
        try {
            const raw = localStorage.getItem(`${this.storageKey}_${key}`);
            return raw ? JSON.parse(raw) : null;
        } catch {
            return null;
        }
    },

    showStatus(msg) {
        const statusEl = document.getElementById('autosave-indicator');
        if (statusEl) {
            statusEl.textContent = msg;
            statusEl.classList.add('fade-in');
        }
    }
};
