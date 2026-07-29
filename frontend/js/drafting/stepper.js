/**
 * Stepper Module - Manages multi-step wizard navigation and step indicators
 */
export const Stepper = {
    render(groups, currentIndex = 0) {
        if (!groups || groups.length === 0) return '';

        const total = groups.length;
        const items = groups.map((g, idx) => {
            const isCompleted = idx < currentIndex;
            const isCurrent = idx === currentIndex;
            const statusClass = isCompleted ? 'completed' : isCurrent ? 'active' : 'pending';
            const icon = isCompleted ? '✓' : idx + 1;

            return `
                <div class="stepper-item ${statusClass}" data-step="${idx}" onclick="window.DraftingApp?.jumpToStep(${idx})">
                    <div class="stepper-node">${icon}</div>
                    <span class="stepper-label">${g.title || `Step ${idx + 1}`}</span>
                </div>
            `;
        });

        return `
            <div class="stepper-container">
                <div class="stepper-bar">
                    ${items.join('<div class="stepper-connector"></div>')}
                </div>
                <div class="stepper-meta">
                    <span>Step ${currentIndex + 1} of ${total}</span>
                    <span>${Math.round(((currentIndex + 1) / total) * 100)}% Completed</span>
                </div>
            </div>
        `;
    }
};
