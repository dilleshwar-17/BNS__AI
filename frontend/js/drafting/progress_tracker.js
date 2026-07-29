/**
 * Progress Tracker Module - Live SSE / WebSockets generation status progression
 */
export const ProgressTracker = {
    render() {
        return `
            <div class="generation-progress-card">
                <div class="progress-header">
                    <div class="loader-spinner"></div>
                    <h3>Generating Your Legal Document...</h3>
                </div>
                <div class="progress-bar-outer">
                    <div class="progress-bar-inner" id="generation-progress-bar" style="width: 10%"></div>
                </div>
                <div class="progress-steps" id="generation-steps-list">
                    <div class="prog-step step-done">✓ Validating Information</div>
                    <div class="prog-step step-active" id="step-retrieving">⏳ Retrieving Legal Provisions & BNS Sections</div>
                    <div class="prog-step step-pending" id="step-context">○ Building AI Context</div>
                    <div class="prog-step step-pending" id="step-generating">○ Generating Draft</div>
                    <div class="prog-step step-pending" id="step-validating">○ Verifying Legal Accuracy</div>
                </div>
                <p class="progress-status-msg" id="progress-status-msg">Communicating with AI backend service...</p>
            </div>
        `;
    },

    update(status, message, percent) {
        const bar = document.getElementById('generation-progress-bar');
        const msg = document.getElementById('progress-status-msg');
        if (bar) bar.style.width = `${percent}%`;
        if (msg) msg.textContent = message;

        const map = {
            'validating': 'step-done',
            'retrieving': 'step-retrieving',
            'building_prompt': 'step-context',
            'generating': 'step-generating',
            'validating_output': 'step-validating'
        };

        if (map[status]) {
            const el = document.getElementById(map[status]);
            if (el) {
                el.className = 'prog-step step-active';
                el.textContent = `⏳ ${message}`;
            }
        }
    }
};
