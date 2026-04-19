import { ref, nextTick, watch } from 'vue';
import Split from 'split.js';

export function usePreview(i18n) {
    const { t } = i18n;

    const previewMode = ref('bilingual');
    const syncScrollEnabled = ref(localStorage.getItem('ui_sync_scroll_enabled') === 'true');
    const previewTask = ref(null);
    const isOpen = ref(false);

    // Split.js refs
    const splitInstance = ref(null);
    const previewOffcanvasComponent = ref(null);

    const destroySplit = () => {
        if (splitInstance.value) {
            try {
                splitInstance.value.destroy();
            } catch (e) {
                console.error('Error destroying split:', e);
            }
            splitInstance.value = null;
        }
    };

    const initSplit = () => {
        destroySplit();

        if (previewMode.value !== 'bilingual') {
            return;
        }

        const el1 = document.getElementById('originalPreviewContainer');
        const el2 = document.getElementById('translatedPreviewContainer');

        if (!el1 || !el2) {
            console.warn('Split elements not found');
            return;
        }

        const isMobile = window.innerWidth < 992;

        splitInstance.value = Split(['#originalPreviewContainer', '#translatedPreviewContainer'], {
            sizes: [50, 50],
            minSize: 100,
            gutterSize: 10,
            direction: isMobile ? 'vertical' : 'horizontal',
            cursor: isMobile ? 'row-resize' : 'col-resize'
        });

        setupSyncScroll();
    };

    const setupSyncScroll = () => {
        let isScrolling = false;

        const onScroll = (src, tgt) => {
            if (!syncScrollEnabled.value || isScrolling) return;
            if (!src || !tgt) return;

            const srcScrollHeight = src.scrollHeight - src.clientHeight;
            if (srcScrollHeight <= 0) return;

            const pct = src.scrollTop / srcScrollHeight;
            const tgtScrollHeight = tgt.scrollHeight - tgt.clientHeight;
            if (tgtScrollHeight > 0) {
                tgt.scrollTop = pct * tgtScrollHeight;
            }
            isScrolling = true;
            requestAnimationFrame(() => isScrolling = false);
        };

        const originalPane = document.querySelector('#originalPreviewContainer .preview-pane');
        const translatedFrame = document.querySelector('#translatedPreviewContainer iframe');

        if (originalPane) {
            originalPane.onscroll = () => {
                if (translatedFrame && translatedFrame.contentWindow && translatedFrame.contentWindow.document.documentElement) {
                    onScroll(originalPane, translatedFrame.contentWindow.document.documentElement);
                }
            };
        }

        if (translatedFrame) {
            translatedFrame.onload = () => {
                const win = translatedFrame.contentWindow;
                if (win && win.document && win.document.documentElement) {
                    win.onscroll = () => onScroll(win.document.documentElement, originalPane);
                }
            };
        }
    };

    const openPreview = (task) => {
        previewTask.value = task;
        isOpen.value = true;
        // Content loading and split init handled by PreviewOffcanvas.vue watch
    };

    const loadPreviewContent = (task) => {
        const originalPane = document.querySelector('#originalPreviewContainer .preview-pane');
        const translatedFrame = document.querySelector('#translatedPreviewContainer iframe');

        if (!originalPane || !translatedFrame) return;

        // Load Original Content
        originalPane.innerHTML = '';
        if (task.file) {
            const ext = task.file.name.split('.').pop().toLowerCase();
            if (['txt', 'md', 'json', 'html', 'js', 'py', 'css', 'java', 'c', 'cpp'].includes(ext) || task.file.type.startsWith('text/')) {
                task.file.text().then(txt => {
                    originalPane.innerHTML = `<pre style="margin:0;padding:1rem;white-space:pre;">${escapeHtml(txt)}</pre>`;
                });
            } else if (['pdf'].includes(ext) || task.file.type === 'application/pdf') {
                const iframe = document.createElement('iframe');
                iframe.src = URL.createObjectURL(task.file);
                iframe.style.cssText = 'width:100%;height:100%;border:none;';
                originalPane.appendChild(iframe);
            } else {
                originalPane.innerHTML = `<p class="p-3 text-gray-500">${t('preview_cantPreviewType') || '无法预览此文件类型'} (${ext})</p>`;
            }
        } else {
            originalPane.innerHTML = `<p class="p-3 text-gray-500">${t('preview_noOriginalCache') || '无原始文件缓存'}</p>`;
        }

        // Load Translated Content
        translatedFrame.src = 'about:blank';
        if (task.downloads && task.downloads.html) {
            fetch(task.downloads.html)
                .then(r => r.text())
                .then(h => {
                    translatedFrame.srcdoc = h;
                })
                .catch(e => console.error('Failed to load translated content:', e));
        }
    };

    const escapeHtml = (text) => {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    };

    const closePreview = () => {
        destroySplit();
        isOpen.value = false;
        previewTask.value = null;
    };

    const setPreviewMode = (m) => {
        previewMode.value = m;
        nextTick(() => {
            setTimeout(() => initSplit(), 100);
        });
    };

    const toggleSyncScroll = () => {
        syncScrollEnabled.value = !syncScrollEnabled.value;
        localStorage.setItem('ui_sync_scroll_enabled', String(syncScrollEnabled.value));
    };

    const printPdf = (url) => {
        const msg = t('pdf_preparing') || "正在准备打印，请稍候...";

        const toastContainer = document.createElement('div');
        toastContainer.className = 'fixed top-4 left-1/2 transform -translate-x-1/2 z-[1090]';
        toastContainer.innerHTML = `
            <div class="bg-primary text-white px-4 py-3 rounded shadow-lg flex items-center gap-2">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z" />
                </svg>
                <span>${msg}</span>
            </div>
        `;
        document.body.appendChild(toastContainer);
        setTimeout(() => toastContainer.remove(), 3000);

        const pf = document.getElementById('printFrame');
        if (!pf) return;
        fetch(url).then(r => r.text()).then(h => {
            pf.srcdoc = h;
            pf.onload = () => {
                setTimeout(() => {
                    pf.contentWindow.focus();
                    pf.contentWindow.print();
                }, 500);
            };
        });
    };

    return {
        previewMode,
        syncScrollEnabled,
        previewTask,
        isOpen,
        splitInstance,
        previewOffcanvasComponent,
        initSplit,
        openPreview,
        closePreview,
        setPreviewMode,
        toggleSyncScroll,
        printPdf
    };
}
