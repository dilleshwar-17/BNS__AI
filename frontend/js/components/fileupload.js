const fileUpload = {
    render() {
        return `
            <div class="file-upload-area">
                <input type="file" id="file-input" accept=".pdf,.docx,.txt" />
                <button class="btn btn-primary btn-sm" onclick="fileUpload.upload()">Upload</button>
            </div>
        `;
    },
    async upload() {
        const input = document.getElementById('file-input');
        if (!input || !input.files.length) return;
        toast.show('Upload functionality coming soon');
    },
};

window.fileUpload = fileUpload;
