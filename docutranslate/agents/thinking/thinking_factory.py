from typing import TypeAlias

mode_type:TypeAlias=str
thinking_field: TypeAlias=str
enable_value: TypeAlias= str | dict
disable_value: TypeAlias= str | dict


thinking_mode:dict[mode_type,tuple[thinking_field, enable_value, disable_value]]={
        "bigmodel": ("thinking", {"type": "enabled"}, {"type": "disabled"}),
        "aliyun": (
            "extra_body",
            {"enable_thinking": True},
            {"enable_thinking": False},
        ),
        "volces": (
            "thinking",
            {"type": "enabled"},
            {"type": "disabled"},
        ),
        "google": (
            "extra_body",
            {
                "google": {
                    "thinking_config": {"thinking_budget": -1, "include_thoughts": True}
                }
            },
            {
                "google": {
                    "thinking_config": {"thinking_budget": 0, "include_thoughts": False}
                }
            },
        ),
        "siliconflow": ("enable_thinking", True, False),
    }


def get_thinking_mode_by_model_id(model_id: str) -> tuple[str, str | dict, str | dict] | None:
    model_id = model_id.strip().lower()
    if "glm-4.5" in model_id:
        return thinking_mode["bigmodel"]
    elif "qwen3" in model_id:
        return thinking_mode["aliyun"]
    elif "seed-1-6" in model_id:
        return thinking_mode["volces"]
    elif "gemini" in model_id:
        return thinking_mode["google"]
    return None


def get_thinking_mode(provider: str, model_id: str) -> tuple[str, str | dict, str | dict] | None:
    provider = provider.strip()
    if provider == "open.bigmodel.cn":
        return thinking_mode["bigmodel"]
    elif provider == "dashscope.aliyuncs.com":
        return thinking_mode["aliyun"]
    elif provider == "ark.cn-beijing.volces.com":
        return thinking_mode["volces"]
    elif provider == "generativelanguage.googleapis.com":
        return thinking_mode["google"]
    elif provider == "api.siliconflow.cn":
        return thinking_mode["siliconflow"]
    elif provider == "api.302.ai":
        return get_thinking_mode_by_model_id(model_id)
    return None


# def add_thinking_mode(data: dict, provider: str, model_id: str, think_enable: bool):
#     pass
