import { ref, nextTick } from 'vue';

export function usePreview(i18n) {
    const { t } = i18n;

    const previewMode = ref('bilingual');
    const syncScrollEnabled = ref(localStorage.getItem('ui_sync_scroll_enabled') === 'true');
    const previewTask = ref(null);

    // Split.js refs
    const splitInstance = ref(null);
    const splitContainer = ref(null);
    const originalPane = ref(null);
    const translatedFrame = ref(null);
    const previewOffcanvasComponent = ref(null);

    const initSplit = () => {
        if (splitInstance.value) {
            try { splitInstance.value.destroy(); } catch (e) {}
            splitInstance.value = null;
        }
        const isMobile = window.innerWidth < 992;
        if (splitContainer.value) {
            splitContainer.value.style.flexDirection = isMobile ? 'column' : 'row';
        }
        if (previewMode.value === 'bilingual') {
            nextTick(() => {
                const el1 = document.getElementById('originalPreviewContainer');
                const el2 = document.getElementById('translatedPreviewContainer');
                if (el1 && el2) {
                    splitInstance.value = new Split(['#originalPreviewContainer', '#translatedPreviewContainer'], {
                        sizes: [50, 50], minSize: 150, gutterSize: 10,
                        direction: isMobile ? 'vertical' : 'horizontal',
                        cursor: isMobile ? 'row-resize' : 'col-resize'
                    });
                }
            });
        }
        setupSyncScroll();
    };

    const setupSyncScroll = () => {
        let isScrolling = false;
        const onScroll = (src, tgt) => {
            if (!syncScrollEnabled.value || isScrolling) return;
            const pct = src.scrollTop / (src.scrollHeight - src.clientHeight);
            tgt.scrollTop = pct * (tgt.scrollHeight - tgt.clientHeight);
            isScrolling = true;
            requestAnimationFrame(() => isScrolling = false);
        };

        if (originalPane.value) originalPane.value.onscroll = () => {
            if (translatedFrame.value && translatedFrame.value.contentWindow)
                onScroll(originalPane.value, translatedFrame.value.contentWindow.document.documentElement);
        };

        if (translatedFrame.value) translatedFrame.value.onload = () => {
            const win = translatedFrame.value.contentWindow;
            if (win) win.onscroll = () => onScroll(win.document.documentElement, originalPane.value);
        };
    };

    const openPreview = (task) => {
        previewTask.value = task;
        const offcanvasEl = previewOffcanvasComponent.value?.previewOffcanvas;
        if (!offcanvasEl) return;
        const off = new bootstrap.Offcanvas(offcanvasEl);
        off.show();

        // Get refs from component
        splitContainer.value = previewOffcanvasComponent.value?.splitContainer;
        originalPane.value = previewOffcanvasComponent.value?.originalPane;
        translatedFrame.value = previewOffcanvasComponent.value?.translatedFrame;

        // Load Original Content
        if (originalPane.value) originalPane.value.innerHTML = '';
        if (task.file) {
            const ext = task.file.name.split('.').pop().toLowerCase();
            if (['txt', 'md', 'json', 'html', 'js', 'py', 'css', 'java', 'c', 'cpp'].includes(ext) || task.file.type.startsWith('text/')) {
                task.file.text().then(txt => {
                    if (originalPane.value) originalPane.value.innerHTML = `<pre>${txt}</pre>`;
                });
            } else if (['pdf'].includes(ext) || task.file.type === 'application/pdf') {
                const iframe = document.createElement('iframe');
                iframe.src = URL.createObjectURL(task.file);
                iframe.style.width = '100%';
                iframe.style.height = '100%';
                iframe.style.border = 'none';
                if (originalPane.value) originalPane.value.appendChild(iframe);
            } else {
                if (originalPane.value) originalPane.value.innerHTML = `<p class="p-3 text-muted">${t('preview_cantPreviewType') || '无法预览此文件类型'} (${ext})</p>`;
            }
        } else {
            if (originalPane.value) originalPane.value.innerHTML = `<p class="p-3 text-muted">${t('preview_noOriginalCache') || '无原始文件缓存'}</p>`;
        }

        // Load Translated Content
        if (translatedFrame.value) translatedFrame.value.src = 'about:blank';
        if (task.downloads && task.downloads.html) {
            fetch(task.downloads.html).then(r => r.text()).then(h => {
                if (translatedFrame.value) translatedFrame.value.srcdoc = h;
            });
        }

        // Re-init Split.js and Sync Scroll listeners
        setTimeout(initSplit, 300);
    };

    const setPreviewMode = (m) => {
        previewMode.value = m;
        nextTick(() => initSplit());
    };

    const toggleSyncScroll = () => {
        syncScrollEnabled.value = !syncScrollEnabled.value;
        localStorage.setItem('ui_sync_scroll_enabled', String(syncScrollEnabled.value));
    };

    const printPdf = (url) => {
        const msg = t('pdf_preparing') || "正在准备打印，请稍候...";
        const toastContainer = document.createElement('div');
        toastContainer.className = 'toast-container position-fixed top-0 start-50 translate-middle-x p-3';
        toastContainer.style.zIndex = '1090';
        toastContainer.innerHTML = `
        <div class="toast align-items-center text-bg-primary border-0 fade show" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="d-flex">
                <div class="toast-body">
                    <i class="bi bi-printer-fill me-2"></i>${msg}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        </div>
    `;
        document.body.appendChild(toastContainer);
        setTimeout(() => {
            const toast = toastContainer.querySelector('.toast');
            if (toast) {
                toast.classList.remove('show');
                setTimeout(() => {
                    if (toastContainer.parentNode) toastContainer.remove();
                }, 500);
            }
        }, 3000);

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
        splitInstance,
        splitContainer,
        originalPane,
        translatedFrame,
        previewOffcanvasComponent,
        initSplit,
        setupSyncScroll,
        openPreview,
        setPreviewMode,
        toggleSyncScroll,
        printPdf
    };
}
