const adminKnowledge = {
    currentFile: null,
    pollingTimer: null,

    async render() {
        const main = document.getElementById('main-content');
        if (!main) return;
        main.innerHTML = `
<div class="admin-knowledge-page">
    <h2>Knowledge Base Management</h2>
    <p class="subtitle">Upload legal documents to build the knowledge base. Supported: PDF, DOCX, TXT, images (OCR).</p>

    <div class="admin-section">
        <h3>Upload Document</h3>
        <div class="upload-zone" id="upload-zone">
            <div class="upload-placeholder">
                <div class="upload-icon">📄</div>
                <p>Drag & drop a file here, or click to browse</p>
                <p class="upload-hint">PDF, DOCX, TXT, PNG, JPG, TIFF (max 10MB)</p>
                <input type="file" id="file-input" accept=".pdf,.docx,.doc,.txt,.png,.jpg,.jpeg,.tiff,.tif,.bmp" style="display:none">
            </div>
            <div class="upload-progress" id="upload-progress" style="display:none">
                <div class="progress-bar">
                    <div class="progress-fill" id="progress-fill"></div>
                </div>
                <p id="upload-status-text">Uploading...</p>
            </div>
        </div>
        <div id="upload-result" style="display:none" class="upload-result"></div>
    </div>

    <div class="admin-section">
        <h3>Ingestion Jobs</h3>
        <div id="job-list">
            <div class="loading-spinner"><div class="loader"></div><p>Loading jobs...</p></div>
        </div>
    </div>

    <div class="admin-section">
        <h3>Uploaded Documents</h3>
        <div class="doc-filters">
            <select id="doc-type-filter">
                <option value="">All Types</option>
                <option value="pdf">PDF</option>
                <option value="docx">DOCX</option>
                <option value="txt">TXT</option>
                <option value="image">Image</option>
            </select>
            <select id="doc-status-filter">
                <option value="">All Status</option>
                <option value="uploaded">Uploaded</option>
                <option value="ingested">Ingested</option>
                <option value="failed">Failed</option>
            </select>
            <button class="btn btn-sm btn-outline" onclick="adminKnowledge.loadDocuments()">Refresh</button>
        </div>
        <div id="document-list">
            <div class="loading-spinner"><div class="loader"></div><p>Loading documents...</p></div>
        </div>
    </div>
</div>
        `;
        this.initUploadZone();
        this.loadJobs();
        this.loadDocuments();
    },

    initUploadZone() {
        const zone = document.getElementById('upload-zone');
        const input = document.getElementById('file-input');
        if (!zone || !input) return;

        zone.addEventListener('click', () => input.click());

        zone.addEventListener('dragover', (e) => {
            e.preventDefault();
            zone.classList.add('drag-over');
        });

        zone.addEventListener('dragleave', () => {
            zone.classList.remove('drag-over');
        });

        zone.addEventListener('drop', (e) => {
            e.preventDefault();
            zone.classList.remove('drag-over');
            const files = e.dataTransfer.files;
            if (files.length > 0) this.uploadFile(files[0]);
        });

        input.addEventListener('change', () => {
            if (input.files.length > 0) this.uploadFile(input.files[0]);
        });
    },

    async uploadFile(file) {
        const progressDiv = document.getElementById('upload-progress');
        const resultDiv = document.getElementById('upload-result');
        const fill = document.getElementById('progress-fill');
        const statusText = document.getElementById('upload-status-text');

        if (progressDiv) progressDiv.style.display = 'block';
        if (resultDiv) resultDiv.style.display = 'none';

        try {
            const data = await uploadAPI.upload(file, (pct) => {
                if (fill) fill.style.width = pct + '%';
                if (statusText) statusText.textContent = `Uploading... ${pct}%`;
            });

            if (fill) fill.style.width = '100%';
            if (statusText) statusText.textContent = 'Upload complete! Starting ingestion...';

            if (resultDiv) {
                resultDiv.style.display = 'block';
                resultDiv.innerHTML = `
                    <div class="upload-success">
                        <span>✅ Uploaded: ${data.filename}</span>
                        <button class="btn btn-primary btn-sm" onclick="adminKnowledge.startIngestion('${data.id}')">
                            Ingest Now
                        </button>
                        <button class="btn btn-sm btn-outline" onclick="adminKnowledge.autoIngest('${data.id}')">
                            Auto-Ingest
                        </button>
                    </div>
                `;
            }

            this.loadDocuments();
            this.loadJobs();
        } catch (err) {
            if (progressDiv) progressDiv.style.display = 'none';
            if (resultDiv) {
                resultDiv.style.display = 'block';
                resultDiv.innerHTML = `<div class="upload-error">❌ ${err.detail || 'Upload failed'}</div>`;
            }
        }
    },

    async autoIngest(fileId) {
        this.startIngestion(fileId);
    },

    async startIngestion(fileId, chunkStrategy = 'recursive') {
        try {
            const job = await ingestionAPI.ingest(fileId, { chunk_strategy: chunkStrategy });
            const resultDiv = document.getElementById('upload-result');
            if (resultDiv) {
                resultDiv.innerHTML = `<div class="upload-success">✅ Ingestion started! <a href="#" onclick="adminKnowledge.viewJob('${job.id}');return false;">View job</a></div>`;
            }
            this.loadJobs();
            this.startPolling(job.id);
        } catch (err) {
            const resultDiv = document.getElementById('upload-result');
            if (resultDiv) {
                resultDiv.innerHTML = `<div class="upload-error">❌ Ingestion failed: ${err.detail || 'Unknown error'}</div>`;
            }
        }
    },

    startPolling(jobId) {
        if (this.pollingTimer) clearInterval(this.pollingTimer);
        this.pollingTimer = setInterval(async () => {
            try {
                const job = await ingestionAPI.getJob(jobId);
                this.updateJobRow(job);
                if (job.status === 'completed' || job.status === 'failed') {
                    clearInterval(this.pollingTimer);
                    this.pollingTimer = null;
                    this.loadJobs();
                }
            } catch {
                clearInterval(this.pollingTimer);
                this.pollingTimer = null;
            }
        }, 2000);
    },

    async loadJobs() {
        const container = document.getElementById('job-list');
        if (!container) return;

        try {
            const data = await ingestionAPI.listJobs({ limit: 20 });
            if (data.jobs.length === 0) {
                container.innerHTML = '<p class="text-muted">No ingestion jobs yet. Upload a document above.</p>';
                return;
            }

            container.innerHTML = `
                <table class="admin-table">
                    <thead>
                        <tr>
                            <th>Filename</th>
                            <th>Status</th>
                            <th>Progress</th>
                            <th>Chunks</th>
                            <th>Date</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody id="job-table-body">
                        ${data.jobs.map(j => this.jobRow(j)).join('')}
                    </tbody>
                </table>
            `;
        } catch (err) {
            container.innerHTML = `<p class="error-text">❌ Failed to load jobs: ${err.detail || 'Error'}</p>`;
        }
    },

    jobRow(job) {
        const statusClass = job.status === 'completed' ? 'status-ok' :
            job.status === 'failed' ? 'status-error' :
            job.status === 'processing' ? 'status-progress' : 'status-pending';
        const progressBar = job.status === 'processing' || job.status === 'completed'
            ? `<div class="progress-bar-sm"><div class="progress-fill-sm" style="width:${job.progress}%"></div></div>`
            : '';
        return `
            <tr id="job-row-${job.id}">
                <td title="${job.filename}">${job.filename.length > 30 ? job.filename.substring(0, 27) + '...' : job.filename}</td>
                <td><span class="status-badge ${statusClass}">${job.status}</span></td>
                <td>${progressBar} ${job.progress}%</td>
                <td>${job.chunks_count}</td>
                <td>${new Date(job.created_at).toLocaleDateString()}</td>
                <td>
                    <button class="btn btn-xs btn-outline" onclick="adminKnowledge.viewJob('${job.id}')">View</button>
                </td>
            </tr>
        `;
    },

    updateJobRow(job) {
        const row = document.getElementById(`job-row-${job.id}`);
        if (row) {
            row.outerHTML = this.jobRow(job);
        }
    },

    async viewJob(jobId) {
        try {
            const job = await ingestionAPI.getJob(jobId);
            alert(`Job: ${job.filename}\nStatus: ${job.status}\nProgress: ${job.progress}%\nChunks: ${job.chunks_count}\nError: ${job.error_message || 'None'}\nStats: ${JSON.stringify(job.stats, null, 2)}`);
        } catch (err) {
            alert('Failed to load job details');
        }
    },

    async loadDocuments() {
        const container = document.getElementById('document-list');
        if (!container) return;

        const typeFilter = document.getElementById('doc-type-filter')?.value || '';
        const statusFilter = document.getElementById('doc-status-filter')?.value || '';

        try {
            const params = { limit: 50 };
            if (typeFilter) params.file_type = typeFilter;
            if (statusFilter) params.status = statusFilter;

            const data = await documentsAPI.list(params);
            if (data.documents.length === 0) {
                container.innerHTML = '<p class="text-muted">No documents uploaded yet.</p>';
                return;
            }

            const totalSize = data.documents.reduce((sum, d) => sum + d.file_size, 0);
            container.innerHTML = `
                <p class="doc-count">${data.total} documents (${this.formatSize(totalSize)})</p>
                <table class="admin-table">
                    <thead>
                        <tr>
                            <th>Filename</th>
                            <th>Type</th>
                            <th>Size</th>
                            <th>Status</th>
                            <th>Date</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${data.documents.map(d => `
                            <tr>
                                <td title="${d.filename}">${d.filename.length > 35 ? d.filename.substring(0, 32) + '...' : d.filename}</td>
                                <td>${d.file_type}</td>
                                <td>${this.formatSize(d.file_size)}</td>
                                <td><span class="status-badge ${d.status === 'ingested' ? 'status-ok' : d.status === 'failed' ? 'status-error' : 'status-pending'}">${d.status}</span></td>
                                <td>${new Date(d.created_at).toLocaleDateString()}</td>
                                <td>
                                    <button class="btn btn-xs btn-outline" onclick="adminKnowledge.startIngestion('${d.id}')">Ingest</button>
                                    <button class="btn btn-xs btn-outline" onclick="adminKnowledge.deleteDoc('${d.id}')">Delete</button>
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            `;
        } catch (err) {
            container.innerHTML = `<p class="error-text">❌ Failed to load documents: ${err.detail || 'Error'}</p>`;
        }
    },

    async deleteDoc(docId) {
        if (!confirm('Delete this document and all related ingestion data?')) return;
        try {
            await documentsAPI.del(docId);
            this.loadDocuments();
            this.loadJobs();
        } catch (err) {
            alert(`Delete failed: ${err.detail || 'Error'}`);
        }
    },

    formatSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    },
};
