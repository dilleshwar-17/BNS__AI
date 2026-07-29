/**
 * File Upload Module - Drag and drop file management for document attachments
 */
export const FileUpload = {
    files: [],

    renderUploadZone(fieldId, label = 'Upload Evidence / Document', acceptedTypes = '.pdf,.docx,.jpg,.png') {
        return `
            <div class="file-upload-wrapper" id="upload-wrapper-${fieldId}">
                <label class="form-label">${label}</label>
                <div class="drop-zone" id="drop-zone-${fieldId}"
                     ondragover="event.preventDefault(); this.classList.add('drag-over')"
                     ondragleave="this.classList.remove('drag-over')"
                     ondrop="window.DraftingApp?.handleFileDrop(event, '${fieldId}')">
                    <div class="drop-zone-icon">📁</div>
                    <div class="drop-zone-text">Drag & drop files here, or <span class="browse-link">browse</span></div>
                    <div class="drop-zone-sub">Supported formats: PDF, DOCX, JPG, PNG (Max 10MB)</div>
                    <input type="file" id="file-input-${fieldId}" class="file-input-hidden"
                           accept="${acceptedTypes}" multiple
                           onchange="window.DraftingApp?.handleFileSelect(event, '${fieldId}')" />
                </div>
                <div class="file-list" id="file-list-${fieldId}"></div>
            </div>
        `;
    },

    addFile(fieldId, file) {
        if (file.size > 10 * 1024 * 1024) {
            alert(`File ${file.name} exceeds 10MB limit.`);
            return;
        }
        this.files.push({ fieldId, file });
        this.renderFileList(fieldId);
    },

    removeFile(fieldId, index) {
        this.files = this.files.filter((f, idx) => !(f.fieldId === fieldId && idx === index));
        this.renderFileList(fieldId);
    },

    renderFileList(fieldId) {
        const listEl = document.getElementById(`file-list-${fieldId}`);
        if (!listEl) return;
        const fieldFiles = this.files.filter(f => f.fieldId === fieldId);

        listEl.innerHTML = fieldFiles.map((f, idx) => {
            const icon = f.file.name.endsWith('.pdf') ? '📄' : f.file.name.match(/\.(jpg|png)$/i) ? '🖼️' : '📑';
            const size = (f.file.size / 1024).toFixed(1) + ' KB';
            return `
                <div class="file-item">
                    <span class="file-icon">${icon}</span>
                    <span class="file-name">${f.file.name}</span>
                    <span class="file-size">${size}</span>
                    <button type="button" class="btn-remove-file" onclick="window.DraftingApp?.removeFile('${fieldId}', ${idx})">✕</button>
                </div>
            `;
        }).join('');
    }
};
