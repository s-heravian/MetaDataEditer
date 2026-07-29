const API_BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' 
    ? 'http://localhost:8000' 
    : `http://${window.location.hostname}:8000`;
let currentFilename = null;

const dropZone = document.getElementById('upload-section');
const fileInput = document.getElementById('file-input');
const loader = document.getElementById('loader');
const resultSection = document.getElementById('result-section');
const tableBody = document.querySelector('#metadata-table tbody');
const searchInput = document.getElementById('search-input');
const cleanupBtn = document.getElementById('cleanup-btn');
const downloadBtn = document.getElementById('download-btn');

// --- Drag & Drop logic ---
dropZone.addEventListener('click', () => fileInput.click());

['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
    dropZone.addEventListener(eventName, preventDefaults, false);
});

function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
}

['dragenter', 'dragover'].forEach(eventName => {
    dropZone.addEventListener(eventName, () => dropZone.classList.add('dragover'), false);
});

['dragleave', 'drop'].forEach(eventName => {
    dropZone.addEventListener(eventName, () => dropZone.classList.remove('dragover'), false);
});

dropZone.addEventListener('drop', (e) => {
    const dt = e.dataTransfer;
    const files = dt.files;
    if (files.length) handleFile(files[0]);
});

fileInput.addEventListener('change', function() {
    if (this.files.length) handleFile(this.files[0]);
});

// --- Upload and Process ---
async function handleFile(file) {
    // UI updates
    dropZone.classList.add('hidden');
    resultSection.classList.add('hidden');
    loader.classList.remove('hidden');

    try {
        // 1. Upload File
        const formData = new FormData();
        formData.append('file', file);

        const uploadRes = await fetch(`${API_BASE}/upload`, {
            method: 'POST',
            body: formData
        });

        if (!uploadRes.ok) throw new Error('خطا در آپلود فایل');
        
        const uploadData = await uploadRes.json();
        currentFilename = uploadData.saved_path;

        // 2. Get Metadata
        const metaRes = await fetch(`${API_BASE}/metadata/${currentFilename}`);
        if (!metaRes.ok) throw new Error('خطا در استخراج متادیتا');

        const metadata = await metaRes.json();
        
        // 3. Render Data
        renderTable(metadata);

        // Hide loader, show results
        loader.classList.add('hidden');
        resultSection.classList.remove('hidden');

    } catch (error) {
        alert(error.message);
        loader.classList.add('hidden');
        dropZone.classList.remove('hidden');
    }
}

// --- Render and Search ---
let allMetadataRows = [];

function renderTable(data) {
    tableBody.innerHTML = '';
    allMetadataRows = [];
    
    // Sort keys alphabetically for better reading
    const keys = Object.keys(data).sort();

    keys.forEach(key => {
        // Skip some internal exiftool keys if desired, e.g. SourceFile
        if (key === 'SourceFile' || key === 'ExifToolVersion') return;

        const row = document.createElement('tr');
        
        const keyCell = document.createElement('td');
        keyCell.textContent = key;
        
        const valCell = document.createElement('td');
        let val = data[key];
        if (typeof val === 'object') val = JSON.stringify(val);
        valCell.textContent = val;

        row.appendChild(keyCell);
        row.appendChild(valCell);
        
        tableBody.appendChild(row);
        
        allMetadataRows.push({
            element: row,
            text: `${key} ${val}`.toLowerCase()
        });
    });
}

searchInput.addEventListener('input', (e) => {
    const term = e.target.value.toLowerCase();
    allMetadataRows.forEach(item => {
        if (item.text.includes(term)) {
            item.element.style.display = '';
        } else {
            item.element.style.display = 'none';
        }
    });
});

// --- Download Logic ---
downloadBtn.addEventListener('click', async () => {
    if (!currentFilename) return;
    
    // Add simple loading state
    const originalText = downloadBtn.innerHTML;
    downloadBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> در حال پردازش...';
    downloadBtn.disabled = true;

    try {
        const targetCountry = document.getElementById('target-country').value;
        const processUrl = `${API_BASE}/process/${currentFilename}?target_country=${targetCountry}`;
        
        const response = await fetch(processUrl);
        if (!response.ok) {
            throw new Error('خطا در پردازش و دانلود فایل');
        }
        
        // Get the blob from the response
        const blob = await response.blob();
        
        // Try to get filename from content-disposition header if available, otherwise use default
        let filename = `processed_${currentFilename}`;
        const disposition = response.headers.get('content-disposition');
        if (disposition && disposition.indexOf('filename=') !== -1) {
            const matches = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/.exec(disposition);
            if (matches != null && matches[1]) {
                filename = matches[1].replace(/['"]/g, '');
            }
        }
        
        // Create a temporary link to trigger download
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = filename;
        
        document.body.appendChild(a);
        a.click();
        
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
        alert('فایل پردازش شد و در حال دانلود است. تمام متادیتاهای غیرضروری حذف شده و در صورت لزوم موقعیت ایران به آلمان تغییر یافته است.');
    } catch (error) {
        alert(error.message);
    } finally {
        downloadBtn.innerHTML = originalText;
        downloadBtn.disabled = false;
    }
});

// --- Cleanup Logic ---
cleanupBtn.addEventListener('click', async () => {
    if (!currentFilename) return;

    try {
        const res = await fetch(`${API_BASE}/cleanup/${currentFilename}`, {
            method: 'DELETE'
        });

        if (!res.ok) throw new Error('حذف فایل با مشکل مواجه شد');

        alert('فایل با موفقیت از سرور حذف شد و پایان کار.');
        
        // Reset UI
        currentFilename = null;
        resultSection.classList.add('hidden');
        dropZone.classList.remove('hidden');
        fileInput.value = ''; // clear input

    } catch (error) {
        alert(error.message);
    }
});

// Prompt cleanup before unloading if file is still there
window.addEventListener('beforeunload', (e) => {
    if (currentFilename) {
        // Use keepalive fetch to try sending cleanup in background
        fetch(`${API_BASE}/cleanup/${currentFilename}`, {
            method: 'DELETE',
            keepalive: true
        }).catch(err => console.log('Cleanup error on unload', err));
    }
});
