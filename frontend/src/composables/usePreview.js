import { ref, nextTick, onUnmounted } from 'vue';
import Split from 'split.js';
import { PREVIEW_MESSAGE_SOURCE, withPreviewBridge } from '../utils/previewFrame.js';

export function usePreview() {
    const previewMode = ref('bilingual');
    const syncScrollEnabled = ref(localStorage.getItem('ui_sync_scroll_enabled') === 'true');
    const previewTask = ref(null);
    const isOpen = ref(false);
    const splitInstance = ref(null);
    const previewOffcanvasComponent = ref(null);
    let syncingScroll = false;

    const destroySplit = () => {
        if (!splitInstance.value) return;
        try {
            splitInstance.value.destroy();
        } catch (error) {
            console.error('Error destroying preview split:', error);
        }
        splitInstance.value = null;
    };

    const setupSyncScroll = () => {
        const originalPane = document.querySelector('#originalPreviewContainer .preview-pane');
        const translatedFrame = document.querySelector('#translatedPreviewContainer iframe');
        if (!originalPane) return;
        originalPane.onscroll = () => {
            if (!isOpen.value || !syncScrollEnabled.value || syncingScroll || !translatedFrame?.contentWindow) return;
            const max = originalPane.scrollHeight - originalPane.clientHeight;
            translatedFrame.contentWindow.postMessage({
                source: PREVIEW_MESSAGE_SOURCE,
                type: 'scroll',
                progress: max > 0 ? originalPane.scrollTop / max : 0
            }, '*');
            syncingScroll = true;
            requestAnimationFrame(() => { syncingScroll = false; });
        };
    };

    const handlePreviewMessage = (event) => {
        const frame = document.querySelector('#translatedPreviewContainer iframe');
        if (event.source !== frame?.contentWindow || event.data?.source !== PREVIEW_MESSAGE_SOURCE || event.data.type !== 'scroll') return;
        if (!isOpen.value || !syncScrollEnabled.value || previewMode.value !== 'bilingual' || syncingScroll) return;
        const progress = Number(event.data.progress);
        if (!Number.isFinite(progress)) return;
        const originalPane = document.querySelector('#originalPreviewContainer .preview-pane');
        if (!originalPane) return;
        syncingScroll = true;
        originalPane.scrollTop = Math.max(0, Math.min(1, progress)) * (originalPane.scrollHeight - originalPane.clientHeight);
        requestAnimationFrame(() => { syncingScroll = false; });
    };
    window.addEventListener('message', handlePreviewMessage);
    onUnmounted(() => window.removeEventListener('message', handlePreviewMessage));

    const initSplit = () => {
        destroySplit();
        if (!isOpen.value || previewMode.value !== 'bilingual') return;
        if (!document.getElementById('originalPreviewContainer') || !document.getElementById('translatedPreviewContainer')) return;
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

    const openPreview = (task) => {
        previewTask.value = task;
        isOpen.value = true;
    };

    const closePreview = () => {
        isOpen.value = false;
        previewTask.value = null;
        destroySplit();
    };

    const setPreviewMode = (mode) => {
        previewMode.value = mode;
        nextTick(() => setTimeout(initSplit, 100));
    };

    const toggleSyncScroll = () => {
        syncScrollEnabled.value = !syncScrollEnabled.value;
        localStorage.setItem('ui_sync_scroll_enabled', String(syncScrollEnabled.value));
    };

    const printPdf = async (url) => {
        try {
            const response = await fetch(url);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const html = await response.text();
            let printFrame = document.getElementById('printFrame');
            const isNewFrame = !printFrame;
            if (isNewFrame) {
                printFrame = document.createElement('iframe');
                printFrame.id = 'printFrame';
                printFrame.setAttribute('sandbox', 'allow-scripts allow-modals');
                printFrame.style.cssText = 'position: fixed; left: -9999px; top: 0; width: 100%; height: 100%;';
            }
            printFrame.onload = () => {
                printFrame.onload = null;
                setTimeout(() => {
                    printFrame.contentWindow?.postMessage({ source: PREVIEW_MESSAGE_SOURCE, type: 'print' }, '*');
                }, 1000);
            };
            printFrame.srcdoc = withPreviewBridge(html);
            if (isNewFrame) document.body.appendChild(printFrame);
        } catch (error) {
            console.error('Failed to load content for printing:', error);
        }
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
