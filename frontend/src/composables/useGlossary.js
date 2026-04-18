import { ref, computed } from 'vue';

export function useGlossary() {
    const glossaryData = ref({});

    const glossaryCount = computed(() => Object.keys(glossaryData.value).length);

    const handleGlossaryFiles = (e) => {
        const files = e.target.files;
        if (!files.length) return;
        Array.from(files).forEach(f => {
            Papa.parse(f, {
                header: true, skipEmptyLines: true,
                complete: (res) => {
                    if (res.data) res.data.forEach(r => {
                        if (r.src && r.dst) glossaryData.value[r.src.trim()] = r.dst.trim();
                    });
                }
            });
        });
    };

    const clearGlossary = () => {
        glossaryData.value = {};
    };

    const openGlossaryModal = () => {
        new bootstrap.Modal(document.getElementById('glossaryModal')).show();
    };

    const downloadGlossaryTemplate = () => {
        window.open('/service/glossary/template', '_blank');
    };

    return {
        glossaryData,
        glossaryCount,
        handleGlossaryFiles,
        clearGlossary,
        openGlossaryModal,
        downloadGlossaryTemplate
    };
}
