// Helper utilities
export function emptyToNull(val) {
    return (!val && val !== 0 && val !== false) ? null : val;
}

export function capitalize(s) {
    return s.charAt(0).toUpperCase() + s.slice(1);
}

export function getFileIcon(filename) {
    const ext = filename.split('.').pop().toLowerCase();
    const iconMap = {
        'pdf': 'bi-file-earmark-pdf',
        'doc': 'bi-file-earmark-word',
        'docx': 'bi-file-earmark-word',
        'ppt': 'bi-file-earmark-ppt',
        'pptx': 'bi-file-earmark-ppt',
        'xls': 'bi-file-earmark-excel',
        'xlsx': 'bi-file-earmark-excel',
        'md': 'bi-file-earmark-markdown',
        'txt': 'bi-file-earmark-text',
        'html': 'bi-file-earmark-code',
        'htm': 'bi-file-earmark-code',
        'epub': 'bi-book',
        'mobi': 'bi-book',
        'zip': 'bi-file-earmark-zip',
        'rar': 'bi-file-earmark-zip',
        'json': 'bi-file-earmark-code',
        'csv': 'bi-file-earmark-spreadsheet'
    };
    return iconMap[ext] || 'bi-file-earmark';
}
