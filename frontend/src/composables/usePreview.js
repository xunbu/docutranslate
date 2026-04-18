import { ref, nextTick, watch } from 'vue';

export function usePreview(i18n) {
    const { t } = i18n;

    const previewMode = ref('bilingual');
    const syncScrollEnabled = ref(localStorage.getItem('ui_sync_scroll_enabled') === 'true');
    const previewTask = ref(null);
    const isOpen = ref(false);

    // Split.js refs
    const splitInstance = ref(null);
    const splitContainer = ref(null);
    const originalPane = ref(null);
    const translatedFrame = ref(null);
    const previewOffcanvasComponent = ref(null);

    // Watch for offcanvas open to get refs
    watch(isOpen, (open) => {
        if (open) {
            nextTick(() => {
                // Give time for the component to render
                setTimeout(() => {
                    if (previewOffcanvasComponent.value) {
                        splitContainer.value = previewOffcanvasComponent.value.splitContainer;
                        originalPane.value = previewOffcanvasComponent.value.originalPane;
                        translatedFrame.value = previewOffcanvasComponent.value.translatedFrame;
                    }
                }, 100);
            });
        }
    });

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
                if (el1 && el2 && window.Split) {
                    splitInstance.value = window.Split(['#originalPreviewContainer', '#translatedPreviewContainer'], {
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
        isOpen.value = true;

        // Get refs from component after it renders
        nextTick(() => {
            setTimeout(() => {
                if (previewOffcanvasComponent.value) {
                    splitContainer.value = previewOffcanvasComponent.value.splitContainer;
                    originalPane.value = previewOffcanvasComponent.value.originalPane;
                    translatedFrame.value = previewOffcanvasComponent.value.translatedFrame;
                }

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
                        if (originalPane.value) originalPane.value.innerHTML = `<p class="p-3 text-gray-500">${t('preview_cantPreviewType') || '无法预览此文件类型'} (${ext})</p>`;
                    }
                } else {
                    if (originalPane.value) originalPane.value.innerHTML = `<p class="p-3 text-gray-500">${t('preview_noOriginalCache') || '无原始文件缓存'}</p>`;
                }

                // Load Translated Content
                if (translatedFrame.value) translatedFrame.value.src = 'about:blank';
                if (task.downloads && task.downloads.html) {
                    fetch(task.downloads.html).then(r => r.text()).then(h => {
                        if (translatedFrame.value) translatedFrame.value.srcdoc = h;
                    });
                }

                // Re-init Split.js and Sync Scroll listeners
                initSplit();
            }, 150);
        });
    };

    const closePreview = () => {
        isOpen.value = false;
        previewTask.value = null;
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

        // Create toast notification
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
        setTimeout(() => {
            toastContainer.remove();
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
        isOpen,
        splitInstance,
        splitContainer,
        originalPane,
        translatedFrame,
        previewOffcanvasComponent,
        initSplit,
        setupSyncScroll,
        openPreview,
        closePreview,
        setPreviewMode,
        toggleSyncScroll,
        printPdf
    };
}
