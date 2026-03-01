from typing import TypeAlias, Literal, Any

from docutranslate.agents.provider import ProviderType

ModeType: TypeAlias = Literal["ollama", "bigmodel", "aliyuncs", "volces", "google", "siliconflow", "default"]
ThinkingField: TypeAlias = str
EnableValueType: TypeAlias = str | dict[str, Any] | bool
DisableValueType: TypeAlias = str | dict[str, Any] | bool
ThinkingConfig: TypeAlias = tuple[ThinkingField, EnableValueType, DisableValueType]

thinking_mode: dict[ProviderType, ThinkingConfig] = {
    "minimax": ("reasoning_effort", "medium", "none"),
    "ollama": ("reasoning_effort", "medium", "none"),
    "bigmodel": ("thinking", {"type": "enabled"}, {"type": "disabled"}),
    "aliyuncs": (
        "enable_thinking", True, False,
    ),
    "volces": (
        "thinking",
        {"type": "enabled"},
        {"type": "disabled"},
    ),
    "google": ("reasoning_effort", "medium", "none"),
    "siliconflow": ("enable_thinking", True, False),
    "default": ("reasoning_effort", "medium", "minimal"),
}


def get_thinking_mode_by_model_id(model_id: str) -> ThinkingConfig:
    model_id = model_id.strip().lower()
    if "glm" in model_id:
        return thinking_mode["bigmodel"]
    elif "qwen" in model_id:
        return thinking_mode["aliyuncs"]
    elif "seed" in model_id:
        return thinking_mode["volces"]
    elif "gemini" in model_id:
        return thinking_mode["google"]
    return thinking_mode["default"]


def get_thinking_mode(provider: ProviderType, model_id: str) -> ThinkingConfig:
    provider = provider
    if provider == "bigmodel":
        return thinking_mode["bigmodel"]
    elif provider == "aliyuncs":
        return thinking_mode["aliyuncs"]
    elif provider == "volces":
        return thinking_mode["volces"]
    elif provider == "google":
        return thinking_mode["google"]
    elif provider == "siliconflow":
        return thinking_mode["siliconflow"]
    elif provider == "ollama":
        return thinking_mode["ollama"]
    return get_thinking_mode_by_model_id(model_id)
