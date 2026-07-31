const draftValidator = {
    validate(type, values) {
        const required = draftingQuestionnaire.getFields(type).map(f => f.key);
        const missing = required.filter(k => !values[k]);
        return { valid: missing.length === 0, missing };
    },
};

window.draftValidator = draftValidator;
