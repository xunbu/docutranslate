from typing import TypeAlias, Literal, Any

from docutranslate.agents.provider import ProviderType

ModeType: TypeAlias = Literal["ollama", "bigmodel", "aliyun", "volces", "google", "siliconflow", "default"]
ThinkingField: TypeAlias = str
EnableValueType: TypeAlias = str | dict[str,Any] | bool
DisableValueType: TypeAlias =  str | dict[str,Any] | bool
ThinkingConfig: TypeAlias= tuple[ThinkingField, EnableValueType, DisableValueType]

thinking_mode: dict[ProviderType,ThinkingConfig] = {
    "ollama": ("reasoning_effort", "medium", "none"),
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
    "default": ("reasoning_effort", "medium", "minimal"),
}


def get_thinking_mode_by_model_id(model_id: str) -> ThinkingConfig :
    model_id = model_id.strip().lower()
    if "glm-4.5" in model_id:
        return thinking_mode["bigmodel"]
    elif "qwen3" in model_id:
        return thinking_mode["aliyun"]
    elif "seed-1-6" in model_id:
        return thinking_mode["volces"]
    elif "gemini" in model_id:
        return thinking_mode["google"]
    return thinking_mode["default"]


def get_thinking_mode(provider: ProviderType, model_id: str) -> ThinkingConfig :
    provider = provider
    if provider == "bigmodel":
        return thinking_mode["bigmodel"]
    elif provider == "aliyun":
        return thinking_mode["aliyun"]
    elif provider == "volces":
        return thinking_mode["volces"]
    elif provider == "google":
        return thinking_mode["google"]
    elif provider == "siliconflow":
        return thinking_mode["siliconflow"]
    elif provider == "ollama":
        return thinking_mode["ollama"]
    return get_thinking_mode_by_model_id(model_id)