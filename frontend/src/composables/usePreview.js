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
        // 优先使用预览 iframe（如果已有内容且已渲染）
        // 否则使用独立的打印 iframe（视觉隐藏但保持可见，以便 mermaid 渲染）
        const translatedFrame = document.querySelector('#translatedPreviewContainer iframe');
        let printFrame = document.getElementById('printFrame');

        // 检查预览 iframe 是否已有渲染好的内容
        const hasRenderedContent = (frame) => {
            try {
                const doc = frame.contentDocument || frame.contentWindow.document;
                if (!doc || !doc.body) return false;
                // 检查是否有 mermaid 图表且已渲染（svg 元素存在）
                const mermaidDivs = doc.querySelectorAll('.mermaid');
                if (mermaidDivs.length > 0) {
                    // 有 mermaid，检查是否已渲染
                    return doc.querySelectorAll('svg').length > 0;
                }
                return doc.body.innerHTML.trim().length > 0;
            } catch (e) {
                return false;
            }
        };

        // 打印指定 iframe
        const doPrint = (frame) => {
            frame.contentWindow.focus();
            frame.contentWindow.print();
        };

        // 如果预览 iframe 有渲染好的内容，直接使用
        if (translatedFrame && hasRenderedContent(translatedFrame)) {
            doPrint(translatedFrame);
            return;
        }

        // 否则使用独立的打印 iframe
        if (!printFrame) {
            printFrame = document.createElement('iframe');
            printFrame.id = 'printFrame';
            // 使用 position 移出视口，而不是 display: none
            // 这样 iframe 仍然"可见"，mermaid 可以正常渲染
            printFrame.style.cssText = 'position: fixed; left: -9999px; top: 0; width: 100%; height: 100%;';
            document.body.appendChild(printFrame);
        }

        // 加载内容到打印 iframe
        fetch(url).then(r => r.text()).then(h => {
            printFrame.srcdoc = h;
            printFrame.onload = () => {
                // 等待 mermaid 渲染完成
                setTimeout(() => {
                    doPrint(printFrame);
                }, 1000);
            };
        }).catch(e => {
            console.error('Failed to load content for printing:', e);
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
