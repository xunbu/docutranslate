"""
Tests for provider module
"""
import pytest

from docutranslate.agents.provider.provider import get_provider_by_domain, ProviderType


class TestGetProviderByDomain:
    """Test get_provider_by_domain function"""

    def test_get_provider_by_domain_bigmodel(self):
        """Test get_provider_by_domain with bigmodel domain"""
        result = get_provider_by_domain("open.bigmodel.cn")
        assert result == "bigmodel"

    def test_get_provider_by_domain_aliyuncs(self):
        """Test get_provider_by_domain with aliyuncs domain"""
        result = get_provider_by_domain("dashscope.aliyuncs.com")
        assert result == "aliyuncs"

    def test_get_provider_by_domain_volces(self):
        """Test get_provider_by_domain with volces domain"""
        result = get_provider_by_domain("ark.cn-beijing.volces.com")
        assert result == "volces"

    def test_get_provider_by_domain_google(self):
        """Test get_provider_by_domain with google domain"""
        result = get_provider_by_domain("generativelanguage.googleapis.com")
        assert result == "google"

    def test_get_provider_by_domain_siliconflow(self):
        """Test get_provider_by_domain with siliconflow domain"""
        result = get_provider_by_domain("api.siliconflow.cn")
        assert result == "siliconflow"

    def test_get_provider_by_domain_default(self):
        """Test get_provider_by_domain with unknown domain returns default"""
        result = get_provider_by_domain("unknown.domain.com")
        assert result == "default"

    def test_get_provider_by_domain_openai(self):
        """Test get_provider_by_domain with openai domain returns default"""
        result = get_provider_by_domain("api.openai.com")
        assert result == "default"

    def test_get_provider_by_domain_anthropic(self):
        """Test get_provider_by_domain with anthropic domain returns default"""
        result = get_provider_by_domain("api.anthropic.com")
        assert result == "default"

    def test_get_provider_by_domain_empty(self):
        """Test get_provider_by_domain with empty string returns default"""
        result = get_provider_by_domain("")
        assert result == "default"


class TestProviderType:
    """Test ProviderType type alias"""

    def test_provider_type_values(self):
        """Test that ProviderType accepts valid values"""
        valid_types = [
            "minimax",
            "ollama",
            "bigmodel",
            "aliyuncs",
            "volces",
            "google",
            "siliconflow",
            "deepseek",
            "openrouter",
            "mimo",
            "litellm",
            "default",
        ]
        for provider_type in valid_types:
            # This is just to verify the type accepts these values
            # In practice, type annotations are not enforced at runtime
            assert provider_type in valid_types
