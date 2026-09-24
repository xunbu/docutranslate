export const PREVIEW_MESSAGE_SOURCE = 'docutranslate-preview';

// The preview runs with an opaque origin. This bridge only exchanges scroll
// positions and print requests; document scripts cannot access the app.
export function withPreviewBridge(html) {
    return `${html}
<script>
(() => {
    const source = '${PREVIEW_MESSAGE_SOURCE}';
    const root = () => document.scrollingElement || document.documentElement;
    let applyingScroll = false;
    window.addEventListener('scroll', () => {
        if (applyingScroll) return;
        const el = root();
        const max = el.scrollHeight - el.clientHeight;
        parent.postMessage({ source, type: 'scroll', progress: max > 0 ? el.scrollTop / max : 0 }, '*');
    }, { passive: true });
    window.addEventListener('message', event => {
        if (event.source !== parent || !event.data || event.data.source !== source) return;
        if (event.data.type === 'scroll') {
            const progress = Number(event.data.progress);
            if (!Number.isFinite(progress)) return;
            applyingScroll = true;
            const el = root();
            el.scrollTop = Math.max(0, Math.min(1, progress)) * (el.scrollHeight - el.clientHeight);
            requestAnimationFrame(() => { applyingScroll = false; });
        } else if (event.data.type === 'print') {
            window.focus();
            window.print();
        }
    });
})();
</script>`;
}
