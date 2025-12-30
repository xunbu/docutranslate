from typing import TypeAlias, Literal

ProviderType: TypeAlias = Literal["ollama", "bigmodel", "aliyun", "volces", "google", "siliconflow", "default"]

def get_provider_by_domain(domain:str)->ProviderType:
    if domain == "open.bigmodel.cn":
        return "bigmodel"
    elif domain == "dashscope.aliyuncs.com":
        return "aliyun"
    elif domain == "ark.cn-beijing.volces.com":
        return "volces"
    elif domain == "generativelanguage.googleapis.com":
        return "google"
    elif domain == "api.siliconflow.cn":
        return "siliconflow"
    return "default"