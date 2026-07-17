"""Tests for LiteLLM provider integration."""

from docutranslate.agents.provider.provider import get_provider_by_domain, ProviderType
from docutranslate.agents.thinking.thinking_factory import get_thinking_mode, thinking_mode


class TestProviderDetection:

    def test_litellm_in_hostname(self):
        assert get_provider_by_domain("litellm.example.com") == "litellm"

    def test_litellm_subdomain(self):
        assert get_provider_by_domain("my-litellm-proxy.internal") == "litellm"

    def test_localhost_not_matched_as_litellm(self):
        """localhost should NOT be auto-detected as litellm - it could be Ollama or anything."""
        assert get_provider_by_domain("localhost") == "default"

    def test_127_not_matched_as_litellm(self):
        assert get_provider_by_domain("127.0.0.1") == "default"

    def test_existing_providers_unaffected(self):
        assert get_provider_by_domain("open.bigmodel.cn") == "bigmodel"
        assert get_provider_by_domain("dashscope.aliyuncs.com") == "aliyuncs"
        assert get_provider_by_domain("api.deepseek.com") == "deepseek"
        assert get_provider_by_domain("generativelanguage.googleapis.com") == "google"
        assert get_provider_by_domain("api.siliconflow.cn") == "siliconflow"
        assert get_provider_by_domain("ark.cn-beijing.volces.com") == "volces"

    def test_unknown_domain_returns_default(self):
        assert get_provider_by_domain("api.example.com") == "default"
        assert get_provider_by_domain("random.host.io") == "default"


class TestThinkingMode:

    def test_litellm_in_thinking_mode_dict(self):
        assert "litellm" in thinking_mode

    def test_litellm_thinking_delegates_to_model_id(self):
        """LiteLLM proxies multiple providers, so thinking mode should be
        resolved by model name rather than a fixed provider config."""
        result = get_thinking_mode("litellm", "qwen-plus")
        assert result is not None
        assert result == thinking_mode["aliyuncs"]

    def test_litellm_thinking_gemini_model(self):
        result = get_thinking_mode("litellm", "gemini-2.5-flash")
        assert result == thinking_mode["google"]

    def test_litellm_thinking_glm_model(self):
        result = get_thinking_mode("litellm", "glm-4-plus")
        assert result == thinking_mode["bigmodel"]

    def test_litellm_thinking_unknown_model_uses_default(self):
        result = get_thinking_mode("litellm", "some-random-model")
        assert result == thinking_mode["default"]

    def test_litellm_type_in_provider_type(self):
        """Verify 'litellm' is a valid ProviderType literal value."""
        provider: ProviderType = "litellm"
        assert provider == "litellm"
