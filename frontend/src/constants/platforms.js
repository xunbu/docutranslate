// AI Platform configurations
export const KNOWN_PLATFORMS = [
    {val: "custom", label: "platformCustom", provider: "default"},
    {val: "https://api.302.ai/v1", label: "302.AI", provider: ""},
    {val: "https://api.minimaxi.com/v1", label: "MiniMax", provider: "minimax"},
    {val: "https://api.openai.com/v1", label: "OpenAI", provider: "default"},
    {
        val: "https://generativelanguage.googleapis.com/v1beta/openai/",
        label: "Gemini",
        provider: "google"
    },
    {val: "https://api.deepseek.com/v1", label: "DeepSeek", provider: ""},
    {
        val: "https://dashscope.aliyuncs.com/compatible-mode/v1",
        label: "阿里云百炼(DashScope)",
        provider: "aliyuncs"
    },
    {
        val: "https://ark.cn-beijing.volces.com/api/v3",
        label: "火山引擎(volces)",
        provider: "volces"
    },
    {val: "https://api.siliconflow.cn/v1", label: "硅基流动(siliconflow CN)", provider: "siliconflow"},
    {val: "https://open.bigmodel.cn/api/paas/v4", label: "智谱AI(bigmodel CN)", provider: "bigmodel"},
    {val: "https://www.dmxapi.cn/v1", label: "DMXAPI_CN", provider: ""},
    {val: "https://www.dmxapi.com/v1", label: "DMXAPI_GLOBAL", provider: ""},
    {val: "https://ai.juguang.chat/v1", label: "聚光AI(juguang CN)", provider: ""},
    {val: "https://openrouter.ai/api/v1", label: "OpenRouter", provider: ""},
    {val: "http://127.0.0.1:1234/v1", label: "LM Studio", provider: ""},
    {val: "http://127.0.0.1:11434/v1", label: "Ollama", provider: "ollama"}
];

export const PROVIDERS = ['default', 'google', 'minimax', 'ollama', 'aliyuncs', 'volces', 'siliconflow', 'bigmodel'];

export const API_HREF_MAP = {
    "https://api.302.ai/v1": ["https://dash.302.ai/settings", ""],
    "https://api.minimaxi.com/v1": ["https://platform.minimaxi.com/user-center/basic-information/interface-key", ""],
    "https://api.openai.com/v1": ["https://platform.openai.com/api-keys", ""],
    "https://generativelanguage.googleapis.com/v1beta/openai/": ["https://aistudio.google.com/app/apikey", ""],
    "https://api.deepseek.com/v1": ["https://platform.deepseek.com/api_keys", ""],
    "https://dashscope.aliyuncs.com/compatible-mode/v1": ["https://dashscope.console.aliyun.com/apiKey", ""],
    "https://ark.cn-beijing.volces.com/api/v3": ["https://console.volcengine.com/ark/region:ark+cn-beijing/apiKey", ""],
    "https://api.siliconflow.cn/v1": ["https://cloud.siliconflow.cn/account/ak", ""],
    "https://open.bigmodel.cn/api/paas/v4": ["https://bigmodel.cn/usercenter/apikeys", ""],
    "https://www.dmxapi.cn/v1": ["https://www.dmxapi.cn/settings", ""],
    "https://www.dmxapi.com/v1": ["https://www.dmxapi.com/settings", ""],
    "https://ai.juguang.chat/v1": ["https://ai.juguang.chat/", ""],
    "https://openrouter.ai/api/v1": ["https://openrouter.ai/settings/keys", ""]
};
