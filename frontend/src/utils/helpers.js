// Helper utilities
export function emptyToNull(val) {
    return (!val && val !== 0 && val !== false) ? null : val;
}

export function capitalize(s) {
    return s.charAt(0).toUpperCase() + s.slice(1);
}

// Returns heroicon component name and props for file types
export function getFileIcon(filename) {
    const ext = typeof filename === 'string' ? filename.split('.').pop().toLowerCase() : filename;
    const iconMap = {
        'pdf': { name: 'DocumentTextIcon', solid: false },
        'doc': { name: 'DocumentTextIcon', solid: false },
        'docx': { name: 'DocumentTextIcon', solid: false },
        'ppt': { name: 'DocumentTextIcon', solid: false },
        'pptx': { name: 'DocumentTextIcon', solid: false },
        'xls': { name: 'TableCellsIcon', solid: false },
        'xlsx': { name: 'TableCellsIcon', solid: false },
        'md': { name: 'DocumentTextIcon', solid: false },
        'markdown': { name: 'DocumentTextIcon', solid: false },
        'markdown_zip': { name: 'ArchiveBoxArrowDownIcon', solid: false },
        'txt': { name: 'DocumentTextIcon', solid: false },
        'html': { name: 'CodeBracketIcon', solid: false },
        'htm': { name: 'CodeBracketIcon', solid: false },
        'epub': { name: 'BookOpenIcon', solid: false },
        'mobi': { name: 'BookOpenIcon', solid: false },
        'zip': { name: 'ArchiveBoxArrowDownIcon', solid: false },
        'rar': { name: 'ArchiveBoxArrowDownIcon', solid: false },
        'json': { name: 'CodeBracketIcon', solid: false },
        'csv': { name: 'TableCellsIcon', solid: false },
        'srt': { name: 'DocumentTextIcon', solid: false },
        'ass': { name: 'DocumentTextIcon', solid: false }
    };
    return iconMap[ext] || { name: 'DocumentIcon', solid: false };
}

// Download icon mapping for download dropdown
export function getDownloadIcon(key) {
    const iconMap = {
        'markdown': { name: 'DocumentTextIcon', solid: false },
        'markdown_zip': { name: 'ArchiveBoxArrowDownIcon', solid: false },
        'docx': { name: 'DocumentTextIcon', solid: false },
        'json': { name: 'CodeBracketIcon', solid: false },
        'txt': { name: 'DocumentTextIcon', solid: false },
        'xlsx': { name: 'TableCellsIcon', solid: false },
        'csv': { name: 'TableCellsIcon', solid: false },
        'srt': { name: 'DocumentTextIcon', solid: false },
        'epub': { name: 'BookOpenIcon', solid: false },
        'ass': { name: 'DocumentTextIcon', solid: false },
        'html': { name: 'CodeBracketIcon', solid: false },
        'pptx': { name: 'DocumentTextIcon', solid: false },
        'pdf': { name: 'DocumentTextIcon', solid: false }
    };
    return iconMap[key] || { name: 'DocumentIcon', solid: false };
}
