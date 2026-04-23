<template>
    <div>
        <!-- Preview Offcanvas -->
        <div class="offcanvas-overlay" v-if="isOpen" @click="isOpen = false"></div>
        <div class="offcanvas-panel" :class="{ 'offcanvas-open': isOpen }">
            <!-- Header -->
            <div class="offcanvas-header">
                <h5 class="offcanvas-title">
                    {{ previewMode === 'bilingual' ? t('preview_bilingual') : t('preview_translatedOnly') }}
                </h5>
                <div class="btn-group me-auto ms-4">
                    <button type="button" class="btn btn-sm" :class="previewMode === 'bilingual' ? 'btn-primary' : 'btn-outline-primary'"
                            @click="setPreviewMode('bilingual')">{{ t('previewBilingualBtn') }}</button>
                    <button type="button" class="btn btn-sm" :class="previewMode === 'translatedOnly' ? 'btn-primary' : 'btn-outline-primary'"
                            @click="setPreviewMode('translatedOnly')">{{ t('previewTranslatedOnlyBtn') }}</button>
                </div>
                <button type="button" class="btn btn-sm btn-outline-secondary ms-2"
                        :class="{ 'active bg-primary text-white border-primary': syncScrollEnabled }"
                        @click.stop="toggleSyncScroll"
                        :title="t('syncScrollTooltip')">
                    <Heroicon :name="syncScrollEnabled ? 'LinkIcon' : 'LinkSlashIcon'" class="w-4 h-4" />
                </button>

                <!-- Download Dropdown -->
                <div class="btn-group ms-2" v-if="previewTask && previewTask.downloads">
                    <button type="button" class="btn btn-sm btn-outline-primary dropdown-toggle" @click="showDownloadMenu = !showDownloadMenu">
                        <Heroicon name="ArrowDownTrayIcon" class="w-4 h-4 me-1" />
                        <span>{{ t('taskCardDownloadBtn') }}</span>
                    </button>
                    <ul class="dropdown-menu dropdown-menu-end" :class="{ 'show': showDownloadMenu }" v-if="showDownloadMenu">
                        <li v-for="(link, key) in previewTask.downloads" :key="key">
                            <a class="dropdown-item" :href="link" @click="showDownloadMenu = false">
                                <Heroicon :name="getDownloadIcon(key).name" class="w-4 h-4 me-2" />
                                {{ key === 'markdown_zip' ? t('downloadMdZip') : (key === 'markdown' ? t('downloadMdEmbedded') : key.toUpperCase()) }}
                            </a>
                        </li>
                        <li v-if="previewTask.downloads.html">
                            <a class="dropdown-item" href="#" @click.prevent="handlePrintPdf(previewTask.downloads.html)">
                                <Heroicon name="DocumentTextIcon" class="w-4 h-4 me-2" />
                                PDF
                            </a>
                        </li>
                    </ul>
                </div>

                <button type="button" class="btn-close ms-2" @click="isOpen = false"></button>
            </div>

            <!-- Body -->
            <div class="offcanvas-body">
                <div class="preview-split-container flex-grow-1" ref="splitContainer">
                    <div id="originalPreviewContainer" class="preview-pane-wrapper" v-show="previewMode === 'bilingual'">
                        <h6 class="preview-label">{{ t('previewOriginal') }}</h6>
                        <div class="preview-pane" ref="originalPane"></div>
                    </div>
                    <div id="translatedPreviewContainer" class="preview-pane-wrapper">
                        <h6 class="preview-label">{{ t('previewTranslated') }}</h6>
                        <div class="preview-pane">
                            <iframe ref="translatedFrame" src="about:blank"></iframe>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script setup>
import { ref, inject, watch, nextTick, onMounted, onUnmounted } from 'vue';
import { getDownloadIcon } from '../../utils/helpers';
import Heroicon from '../ui/Heroicon.vue';

const props = defineProps({
    t: Function,
});

// Inject from parent
const previewMode = inject('previewMode');
const syncScrollEnabled = inject('syncScrollEnabled');
const previewTask = inject('previewTask');
const isOpen = inject('previewIsOpen');
const setPreviewMode = inject('setPreviewMode');
const toggleSyncScroll = inject('toggleSyncScroll');
const printPdf = inject('printPdf');
const initSplit = inject('initSplit');

// Local state
const splitContainer = ref(null);
const originalPane = ref(null);
const translatedFrame = ref(null);
const showDownloadMenu = ref(false);

const loadContent = (task) => {
    if (!originalPane.value || !translatedFrame.value) return;

    // Load Original
    originalPane.value.innerHTML = '';
    if (task.file) {
        const ext = task.file.name.split('.').pop().toLowerCase();
        if (['txt', 'md', 'json', 'html', 'js', 'py', 'css', 'java', 'c', 'cpp'].includes(ext) || task.file.type.startsWith('text/')) {
            task.file.text().then(txt => {
                const pre = document.createElement('pre');
                pre.style.cssText = 'margin:0;padding:1rem;white-space:pre;';
                pre.textContent = txt;
                originalPane.value.appendChild(pre);
            });
        } else if (['pdf'].includes(ext) || task.file.type === 'application/pdf') {
            const iframe = document.createElement('iframe');
            iframe.src = URL.createObjectURL(task.file);
            iframe.style.cssText = 'width:100%;height:100%;border:none;';
            originalPane.value.appendChild(iframe);
        } else {
            originalPane.value.innerHTML = `<p class="p-3 text-muted">${props.t('preview_cantPreviewType') || '无法预览此文件类型'} (${ext})</p>`;
        }
    } else {
        originalPane.value.innerHTML = `<p class="p-3 text-muted">${props.t('preview_noOriginalCache') || '无原始文件缓存'}</p>`;
    }

    // Load Translated
    translatedFrame.value.src = 'about:blank';
    if (task.downloads && task.downloads.html) {
        fetch(task.downloads.html)
            .then(r => r.text())
            .then(h => {
                translatedFrame.value.srcdoc = h;
            });
    }
};

const handlePrintPdf = (url) => {
    showDownloadMenu.value = false;
    printPdf(url);
};

// Watch for open
watch(isOpen, (open) => {
    if (open && previewTask.value) {
        nextTick(() => {
            setTimeout(() => {
                loadContent(previewTask.value);
                initSplit();
            }, 300);
        });
    }
});

// Close dropdown when clicking outside
watch(showDownloadMenu, (val) => {
    if (val) {
        setTimeout(() => {
            document.addEventListener('click', function closeMenu() {
                showDownloadMenu.value = false;
                document.removeEventListener('click', closeMenu);
            });
        }, 0);
    }
});

// Handle window resize
const handleResize = () => {
    if (isOpen.value) {
        initSplit();
    }
};

onMounted(() => {
    window.addEventListener('resize', handleResize);
});

onUnmounted(() => {
    window.removeEventListener('resize', handleResize);
});
</script>

<style scoped>
.offcanvas-overlay {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.5);
    z-index: 1040;
}

.offcanvas-panel {
    position: fixed;
    top: 0;
    right: 0;
    width: 95vw;
    max-width: 1600px;
    height: 100vh;
    background: var(--bs-body-bg);
    box-shadow: -0.25rem 0 0.5rem rgba(0, 0, 0, 0.15);
    z-index: 1045;
    display: flex;
    flex-direction: column;
    transform: translateX(100%);
    transition: transform 0.3s ease;
}

.offcanvas-panel.offcanvas-open {
    transform: translateX(0);
}

.offcanvas-header {
    display: flex;
    align-items: center;
    padding: 1rem;
    border-bottom: 1px solid var(--bs-border-color);
    flex-shrink: 0;
    position: relative;
    z-index: 10;
}

.offcanvas-title {
    font-size: 1.25rem;
    font-weight: 500;
    margin: 0;
}

.offcanvas-body {
    display: flex;
    flex-direction: column;
    padding: 0.5rem;
    flex: 1;
    min-height: 0;
}

.preview-split-container {
    display: flex;
    flex-direction: column;
    height: 90%;
    flex: 1;
}

@media (min-width: 992px) {
    .preview-split-container {
        flex-direction: row;
    }
}

.preview-pane-wrapper {
    display: flex;
    flex-direction: column;
    overflow: hidden;
    width: 100%;
    height: 100%;
}

@media (min-width: 992px) {
    .preview-pane-wrapper {
        width: 50%;
    }
}

.preview-label {
    text-align: center;
    color: #6c757d;
    font-size: 0.875rem;
    font-weight: 500;
    margin: 0;
    padding: 0.5rem;
    flex-shrink: 0;
}

.preview-pane {
    flex-grow: 1;
    border: 1px solid var(--bs-border-color);
    border-radius: 0.25rem;
    overflow: auto;
    position: relative;
    background: var(--bs-body-bg);
}

.preview-pane iframe {
    width: 100%;
    height: 100%;
    border: none;
    display: block;
}

#translatedPreviewContainer .preview-pane {
    overflow: hidden;
}

/* Button styles */
.btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 0.375rem 0.75rem;
    font-size: 0.875rem;
    font-weight: 500;
    line-height: 1.5;
    border-radius: 0.25rem;
    border: 1px solid transparent;
    cursor: pointer;
    transition: all 0.15s ease;
}

.btn-sm {
    padding: 0.25rem 0.5rem;
    font-size: 0.75rem;
}

.btn-primary {
    background: var(--bs-primary);
    border-color: var(--bs-primary);
    color: white;
}

.btn-outline-primary {
    background: transparent;
    border-color: var(--bs-primary);
    color: var(--bs-primary);
}

.btn-outline-primary:hover {
    background: var(--bs-primary);
    color: white;
}

.btn-outline-secondary {
    background: transparent;
    border-color: #6c757d;
    color: #6c757d;
}

.btn-outline-secondary:hover {
    background: #6c757d;
    color: white;
}

.btn-group {
    display: inline-flex;
}

.btn-group .btn {
    border-radius: 0;
}

.btn-group .btn:first-child {
    border-radius: 0.25rem 0 0 0.25rem;
}

.btn-group .btn:last-child {
    border-radius: 0 0.25rem 0.25rem 0;
}

.btn-close {
    width: 1.5rem;
    height: 1.5rem;
    background: transparent url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16' fill='%23000'%3e%3cpath d='M.293.293a1 1 0 011.414 0L8 6.586 14.293.293a1 1 0 111.414 1.414L9.414 8l6.293 6.293a1 1 0 01-1.414 1.414L8 9.414l-6.293 6.293a1 1 0 01-1.414-1.414L6.586 8 .293 1.707a1 1 0 010-1.414z'/%3e%3c/svg%3e") center/1em auto no-repeat;
    border: 0;
    border-radius: 0.25rem;
    opacity: 0.5;
    cursor: pointer;
}

.btn-close:hover {
    opacity: 1;
}

/* Dropdown */
.dropdown-menu {
    position: absolute;
    top: 100%;
    right: 0;
    z-index: 1000;
    display: none;
    min-width: 10rem;
    padding: 0.5rem 0;
    margin: 0.125rem 0 0;
    font-size: 0.875rem;
    color: #212529;
    background-color: #fff;
    border: 1px solid var(--bs-border-color);
    border-radius: 0.25rem;
    box-shadow: 0 0.5rem 1rem rgba(0, 0, 0, 0.15);
}

.dropdown-menu.show {
    display: block;
}

.dropdown-item {
    display: flex;
    align-items: center;
    width: 100%;
    padding: 0.5rem 1rem;
    clear: both;
    font-weight: 400;
    color: #212529;
    text-align: inherit;
    text-decoration: none;
    white-space: nowrap;
    background-color: transparent;
    border: 0;
    cursor: pointer;
}

.dropdown-item:hover {
    background-color: #f8f9fa;
    color: #16181b;
}

/* Dark mode */
[data-theme="dark"] .offcanvas-panel {
    background: #1f2937;
}

[data-theme="dark"] .preview-label {
    color: #9ca3af;
}

[data-theme="dark"] .btn-close {
    filter: invert(1) grayscale(100%) brightness(200%);
}

[data-theme="dark"] .dropdown-menu {
    background-color: #374151;
    color: #f3f4f6;
    border-color: #4b5563;
}

[data-theme="dark"] .dropdown-item {
    color: #f3f4f6;
}

[data-theme="dark"] .dropdown-item:hover {
    background-color: #4b5563;
    color: #fff;
}

[data-theme="dark"] .btn-outline-secondary {
    border-color: #9ca3af;
    color: #9ca3af;
}

[data-theme="dark"] .btn-outline-secondary:hover {
    background: #9ca3af;
    color: #1f2937;
}

.text-muted {
    color: #6c757d !important;
}

[data-theme="dark"] .text-muted {
    color: #9ca3af !important;
}

.p-3 {
    padding: 1rem;
}
</style>
