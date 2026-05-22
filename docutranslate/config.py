# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
"""DocuTranslate 配置模块 - 从环境变量读取默认值"""
import os
from typing import Optional
from pathlib import Path


def _get_exe_dir() -> Path:
    """Get the directory where the executable or script is located"""
    import sys
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后的 exe 目录
        return Path(sys.executable).parent
    else:
        # 普通 Python 脚本
        return Path(__file__).parent.parent


def _load_dotenv():
    """Load .env file"""
    from dotenv import load_dotenv
    env_path = None

    # 优先级顺序：
    # 1. 当前工作目录及其父目录
    # 2. exe/脚本所在目录
    current_dir = Path.cwd()
    exe_dir = _get_exe_dir()

    search_dirs = [current_dir] + list(current_dir.parents) + [exe_dir]

    for dir_path in search_dirs:
        candidate = dir_path / ".env"
        if candidate.exists():
            env_path = candidate
            break

    if env_path:
        load_dotenv(env_path)


# Load .env on module import
_load_dotenv()


def _get_env_str(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


def _get_env_int(key: str, default: int) -> int:
    val = os.environ.get(key)
    if val:
        try:
            return int(val)
        except ValueError:
            pass
    return default


def _get_env_float(key: str, default: float) -> float:
    val = os.environ.get(key)
    if val:
        try:
            return float(val)
        except ValueError:
            pass
    return default


def _get_env_bool(key: str, default: bool) -> bool:
    val = os.environ.get(key)
    if val is not None:
        return val.lower() in ("true", "1", "yes", "on")
    return default


def _get_env_optional_int(key: str) -> Optional[int]:
    val = os.environ.get(key)
    if val:
        try:
            return int(val)
        except ValueError:
            pass
    return None


def _get_env_optional_str(key: str) -> Optional[str]:
    val = os.environ.get(key)
    return val if val else None


# ============================================================
# BaseWorkflowParams 默认值
# ============================================================
API_KEY = _get_env_str("DOCUTRANSLATE_API_KEY", "xx")
BASE_URL = _get_env_str("DOCUTRANSLATE_BASE_URL", "")
MODEL_ID = _get_env_str("DOCUTRANSLATE_MODEL_ID", "")
TO_LANG = _get_env_str("DOCUTRANSLATE_TO_LANG", "中文")
SKIP_TRANSLATE = _get_env_bool("DOCUTRANSLATE_SKIP_TRANSLATE", False)
CHUNK_SIZE = _get_env_int("DOCUTRANSLATE_CHUNK_SIZE", 4000)
CONCURRENT = _get_env_int("DOCUTRANSLATE_CONCURRENT", 30)
TEMPERATURE = _get_env_float("DOCUTRANSLATE_TEMPERATURE", 0.7)
TOP_P = _get_env_float("DOCUTRANSLATE_TOP_P", 0.9)
TIMEOUT = _get_env_int("DOCUTRANSLATE_TIMEOUT", 1200)
THINKING = _get_env_str("DOCUTRANSLATE_THINKING", "disable")
RETRY = _get_env_int("DOCUTRANSLATE_RETRY", 2)
SYSTEM_PROXY_ENABLE = _get_env_bool("DOCUTRANSLATE_SYSTEM_PROXY_ENABLE", False)
CUSTOM_PROMPT = _get_env_str("DOCUTRANSLATE_CUSTOM_PROMPT", "")
FORCE_JSON = _get_env_bool("DOCUTRANSLATE_FORCE_JSON", False)
RPM = _get_env_optional_int("DOCUTRANSLATE_RPM")
TPM = _get_env_optional_int("DOCUTRANSLATE_TPM")
PROVIDER = _get_env_optional_str("DOCUTRANSLATE_PROVIDER")
EXTRA_BODY = _get_env_str("DOCUTRANSLATE_EXTRA_BODY", "")
GLOSSARY_GENERATE_ENABLE = _get_env_bool("DOCUTRANSLATE_GLOSSARY_GENERATE_ENABLE", False)

# ============================================================
# 环境变量默认值模式（仅影响 Web 前端）
# ============================================================
WEB_SKIP_VALIDATION = _get_env_bool("DOCUTRANSLATE_WEB_SKIP_VALIDATION", False)

# ============================================================
# MarkdownWorkflowParams 默认值
# ============================================================
CONVERT_ENGINE = _get_env_str("DOCUTRANSLATE_CONVERT_ENGINE", "identity")
MD2DOCX_ENGINE = _get_env_str("DOCUTRANSLATE_MD2DOCX_ENGINE", "auto")
MINERU_TOKEN = _get_env_str("DOCUTRANSLATE_MINERU_TOKEN", "")
MODEL_VERSION = _get_env_str("DOCUTRANSLATE_MODEL_VERSION", "vlm")
FORMULA_OCR = _get_env_bool("DOCUTRANSLATE_FORMULA_OCR", True)
CODE_OCR = _get_env_bool("DOCUTRANSLATE_CODE_OCR", True)
MINERU_LANGUAGE = _get_env_str("DOCUTRANSLATE_MINERU_LANGUAGE", "ch")
MINERU_DEPLOY_BASE_URL = _get_env_str("DOCUTRANSLATE_MINERU_DEPLOY_BASE_URL", "http://127.0.0.1:8000")
MINERU_DEPLOY_BACKEND = _get_env_str("DOCUTRANSLATE_MINERU_DEPLOY_BACKEND", "hybrid-auto-engine")
MINERU_DEPLOY_PARSE_METHOD = _get_env_str("DOCUTRANSLATE_MINERU_DEPLOY_PARSE_METHOD", "auto")
MINERU_DEPLOY_TABLE_ENABLE = _get_env_bool("DOCUTRANSLATE_MINERU_DEPLOY_TABLE_ENABLE", True)
MINERU_DEPLOY_FORMULA_ENABLE = _get_env_bool("DOCUTRANSLATE_MINERU_DEPLOY_FORMULA_ENABLE", True)
MINERU_DEPLOY_START_PAGE_ID = _get_env_int("DOCUTRANSLATE_MINERU_DEPLOY_START_PAGE_ID", 0)
MINERU_DEPLOY_END_PAGE_ID = _get_env_int("DOCUTRANSLATE_MINERU_DEPLOY_END_PAGE_ID", 99999)
MINERU_DEPLOY_SERVER_URL = _get_env_str("DOCUTRANSLATE_MINERU_DEPLOY_SERVER_URL", "")

# ============================================================
# TextWorkflowParams 默认值
# ============================================================
INSERT_MODE = _get_env_str("DOCUTRANSLATE_INSERT_MODE", "replace")
SEPARATOR = _get_env_str("DOCUTRANSLATE_SEPARATOR", "\n")
SEGMENT_MODE = _get_env_str("DOCUTRANSLATE_SEGMENT_MODE", "line")

# ============================================================
# 系统参数
# ============================================================
PORT = _get_env_int("DOCUTRANSLATE_PORT", 8010)
PROXY_ENABLED = _get_env_bool("DOCUTRANSLATE_PROXY_ENABLED", False)
CACHE_NUM = _get_env_int("DOCUTRANSLATE_CACHE_NUM", 10)

# ============================================================
# 兼容旧版 default_params
# ============================================================
default_params = {
    "thinking": THINKING,
    "chunk_size": CHUNK_SIZE,
    "concurrent": CONCURRENT,
    "temperature": TEMPERATURE,
    "top_p": TOP_P,
    "timeout": TIMEOUT,
    "retry": RETRY,
    "system_proxy_enable": SYSTEM_PROXY_ENABLE,
    "extra_body": EXTRA_BODY,
    "web_skip_validation": WEB_SKIP_VALIDATION,
}
