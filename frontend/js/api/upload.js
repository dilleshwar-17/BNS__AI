const uploadAPI = {
    async upload(file, onProgress) {
        return new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();
            const formData = new FormData();
            formData.append('file', file);

            const token = api.getToken();
            if (token) xhr.setRequestHeader && xhr.setRequestHeader('Authorization', `Bearer ${token}`);

            xhr.upload.addEventListener('progress', (e) => {
                if (e.lengthComputable && onProgress) {
                    onProgress(Math.round((e.loaded / e.total) * 100));
                }
            });

            xhr.addEventListener('load', () => {
                if (xhr.status >= 200 && xhr.status < 300) {
                    resolve(JSON.parse(xhr.responseText));
                } else {
                    try { reject(JSON.parse(xhr.responseText)); }
                    catch { reject({ detail: 'Upload failed' }); }
                }
            });

            xhr.addEventListener('error', () => reject({ detail: 'Upload failed' }));
            xhr.addEventListener('abort', () => reject({ detail: 'Upload cancelled' }));

            xhr.open('POST', api.baseUrl + '/upload/');
            xhr.setRequestHeader('Authorization', `Bearer ${token}`);
            xhr.send(formData);
        });
    },
};

window.uploadAPI = uploadAPI;
