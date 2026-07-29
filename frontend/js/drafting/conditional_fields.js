/**
 * Conditional Fields Module - Evaluates template rules to show/hide dynamic fields
 */
export const ConditionalFields = {
    evaluate(fieldDef, currentValues) {
        if (!fieldDef.conditional || !fieldDef.conditional.depends_on) {
            return true;
        }

        const dependsOn = fieldDef.conditional.depends_on;
        const expectedValue = fieldDef.conditional.value;
        const op = fieldDef.conditional.operator || 'eq';
        const actualValue = currentValues[dependsOn];

        if (actualValue === undefined || actualValue === null) {
            return false;
        }

        switch (op) {
            case 'eq':
                if (typeof expectedValue === 'boolean') {
                    return String(actualValue) === String(expectedValue) || (actualValue === 'yes' && expectedValue === true);
                }
                return String(actualValue).toLowerCase() === String(expectedValue).toLowerCase();
            case 'neq':
                return String(actualValue).toLowerCase() !== String(expectedValue).toLowerCase();
            case 'in':
                return Array.isArray(expectedValue) && expectedValue.includes(actualValue);
            case 'truthy':
                return Boolean(actualValue) && actualValue !== 'no' && actualValue !== 'false';
            default:
                return true;
        }
    },

    updateVisibility(container, currentValues, fields) {
        if (!container) return;
        fields.forEach(field => {
            const fieldEl = container.querySelector(`[data-field-wrapper="${field.id}"]`);
            if (fieldEl) {
                const visible = this.evaluate(field, currentValues);
                fieldEl.style.display = visible ? 'block' : 'none';
                const inputs = fieldEl.querySelectorAll('input, select, textarea');
                inputs.forEach(i => {
                    if (!visible) {
                        i.setAttribute('disabled', 'true');
                    } else {
                        i.removeAttribute('disabled');
                    }
                });
            }
        });
    }
};
