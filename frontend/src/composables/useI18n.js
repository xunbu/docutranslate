import { ref } from 'vue';

export function useI18n() {
    const currentLang = ref(localStorage.getItem('ui_language') || 'zh');
    const i18nData = ref({});

    const t = (k, params) => {
        let v = i18nData.value[k] || k;
        if (params) {
            for (const [key, val] of Object.entries(params)) {
                v = v.replace(new RegExp(`\\{${key}\\}`, 'g'), String(val));
            }
        }
        return v;
    };

    const setLanguage = async (l) => {
        currentLang.value = l;
        localStorage.setItem('ui_language', l);
        document.documentElement.lang = l === 'zh' ? 'zh-CN' : (l === 'vi' ? 'vi' : 'en');
        // Reload i18n data
        try {
            const res = await fetch(`/static/i18n/${l}.json`);
            i18nData.value = await res.json();
        } catch (e) {
            console.error('Failed to load i18n:', e);
        }
    };

    const loadI18n = async () => {
        try {
            const lang = currentLang.value || 'zh';
            const res = await fetch(`/static/i18n/${lang}.json`);
            i18nData.value = await res.json();
        } catch (e) {
            // Fallback defaults
            i18nData.value = {
                pageTitle: "DocuTranslate",
                tutorialBtn: "教程",
                projectContributeBtn: "项目协作",
                workflowTitle: "选择工作流",
                autoWorkflowLabel: "自动选择工作流",
                workflowOptionPptx: "PPTX 演示文稿",
                pptxSettingsTitleText: "PPTX 设置",
                mineruDeployServerUrlLabel: "Server URL",
                mineruDeployLangListLabel: "语言列表 (Pipeline模式)",
                mineruDeployServerUrlPlaceholder: "http://127.0.0.1:30000",
                mineruDeployParseMethodLabel: "解析方法 (Parse Method)",
                mineruDeployTableEnableLabel: "表格识别 (Table Recognition)"
            };
        }
    };

    return {
        currentLang,
        i18nData,
        t,
        setLanguage,
        loadI18n
    };
}
