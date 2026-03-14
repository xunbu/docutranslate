"""
Global pytest fixtures for DocuTranslate tests
"""
import os
import sys
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional

import pytest

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture(scope="session")
def test_data_dir() -> Path:
    """Fixture for test data directory"""
    data_dir = project_root / "tests" / "test_data"
    data_dir.mkdir(exist_ok=True)
    return data_dir


@pytest.fixture
def temp_dir() -> Path:
    """Fixture for temporary directory that gets cleaned up after test"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_env_vars(monkeypatch) -> None:
    """Fixture to set up mock environment variables for testing"""
    monkeypatch.setenv("DOCUTRANSLATE_BASE_URL", "https://api.openai.com/v1")
    monkeypatch.setenv("DOCUTRANSLATE_API_KEY", "test-api-key")
    monkeypatch.setenv("DOCUTRANSLATE_MODEL_ID", "gpt-4o")
    monkeypatch.setenv("DOCUTRANSLATE_TO_LANG", "中文")
    monkeypatch.setenv("DOCUTRANSLATE_CONCURRENT", "10")
    monkeypatch.setenv("DOCUTRANSLATE_MINERU_TOKEN", "test-mineru-token")
    monkeypatch.delenv("DOCUTRANSLATE_PROXY_ENABLED", raising=False)


@pytest.fixture
def mock_llm_response() -> Dict[str, Any]:
    """Fixture for mock LLM API response"""
    return {
        "id": "test-response-id",
        "object": "chat.completion",
        "created": 1234567890,
        "model": "gpt-4o",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "这是翻译后的内容"
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 10,
            "total_tokens": 20
        }
    }


@pytest.fixture
def mock_mineru_response() -> Dict[str, Any]:
    """Fixture for mock MinerU API response"""
    return {
        "code": 200,
        "message": "success",
        "data": {
            "md_content": "# 测试文档\n\n这是测试内容",
            "images": []
        }
    }
