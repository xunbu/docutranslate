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
                mineruDeployApiKeyLabel: "本地服务 API Key（可选）",
                mineruDeployApiKeyPlaceholder: "未启用鉴权时无需填写",
                mineruDeployApiKeyHelp: "填写自建 MinerU 解析服务的访问密钥，非在线 Token 或翻译模型密钥。留空使用服务端环境变量；强制环境变量模式下以服务端配置为准。",
                mineruDeployApiKeyShow: "显示密钥",
                mineruDeployApiKeyHide: "隐藏密钥",
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
