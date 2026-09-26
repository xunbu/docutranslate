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


def _get_env_optional_float(key: str) -> Optional[float]:
    val = os.environ.get(key)
    if val:
        try:
            return float(val)
        except ValueError:
            pass
    return None


def _get_env_optional_str(key: str) -> Optional[str]:
    val = os.environ.get(key)
    return val if val else None


def _is_env_set(key: str) -> bool:
    """检查环境变量是否被实际设置（非空）"""
    val = os.environ.get(key)
    return val is not None and val != ""


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
# LLM 默认使用 DeepSeek Harness 风格的流式空闲超时：只要服务端持续
# 发送数据/心跳，就不施加总墙钟上限。
LLM_STREAMING = _get_env_bool("DOCUTRANSLATE_LLM_STREAMING", True)
STREAM_IDLE_TIMEOUT = _get_env_float("DOCUTRANSLATE_STREAM_IDLE_TIMEOUT", 300.0)
# 非流式硬超时为可选覆盖；未设置时继续沿用 DOCUTRANSLATE_TIMEOUT。
NON_STREAM_TIMEOUT = _get_env_optional_float("DOCUTRANSLATE_NON_STREAM_TIMEOUT")
TIMEOUT = _get_env_int("DOCUTRANSLATE_TIMEOUT", 1200)
CONNECT_TIMEOUT = _get_env_float("DOCUTRANSLATE_CONNECT_TIMEOUT", 5.0)
# 未单独配置时沿用总超时，保持旧版 DOCUTRANSLATE_TIMEOUT 的行为兼容。
READ_TIMEOUT = _get_env_float("DOCUTRANSLATE_READ_TIMEOUT", float(TIMEOUT))
WRITE_TIMEOUT = _get_env_float("DOCUTRANSLATE_WRITE_TIMEOUT", 300.0)
POOL_TIMEOUT = _get_env_float("DOCUTRANSLATE_POOL_TIMEOUT", 10.0)
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

# 环境变量是否被实际设置的标记（用于强制覆盖逻辑）
ENV_SET = {
    "mineru_deploy_api_key": _is_env_set("DOCUTRANSLATE_MINERU_DEPLOY_API_KEY"),
    "api_key": _is_env_set("DOCUTRANSLATE_API_KEY"),
    "base_url": _is_env_set("DOCUTRANSLATE_BASE_URL"),
    "model_id": _is_env_set("DOCUTRANSLATE_MODEL_ID"),
    "to_lang": _is_env_set("DOCUTRANSLATE_TO_LANG"),
    "provider": _is_env_set("DOCUTRANSLATE_PROVIDER"),
    "thinking": _is_env_set("DOCUTRANSLATE_THINKING"),
    "chunk_size": _is_env_set("DOCUTRANSLATE_CHUNK_SIZE"),
    "concurrent": _is_env_set("DOCUTRANSLATE_CONCURRENT"),
    "temperature": _is_env_set("DOCUTRANSLATE_TEMPERATURE"),
    "top_p": _is_env_set("DOCUTRANSLATE_TOP_P"),
    "timeout": _is_env_set("DOCUTRANSLATE_TIMEOUT"),
    "connect_timeout": _is_env_set("DOCUTRANSLATE_CONNECT_TIMEOUT"),
    "read_timeout": _is_env_set("DOCUTRANSLATE_READ_TIMEOUT"),
    "write_timeout": _is_env_set("DOCUTRANSLATE_WRITE_TIMEOUT"),
    "pool_timeout": _is_env_set("DOCUTRANSLATE_POOL_TIMEOUT"),
    "retry": _is_env_set("DOCUTRANSLATE_RETRY"),
    "system_proxy_enable": _is_env_set("DOCUTRANSLATE_SYSTEM_PROXY_ENABLE"),
    "custom_prompt": _is_env_set("DOCUTRANSLATE_CUSTOM_PROMPT"),
    "force_json": _is_env_set("DOCUTRANSLATE_FORCE_JSON"),
    "rpm": _is_env_set("DOCUTRANSLATE_RPM"),
    "tpm": _is_env_set("DOCUTRANSLATE_TPM"),
    "extra_body": _is_env_set("DOCUTRANSLATE_EXTRA_BODY"),
}

# ============================================================
# 环境变量默认值模式（仅影响 Web 前端）
# ============================================================
WEB_SKIP_VALIDATION = _get_env_bool("DOCUTRANSLATE_WEB_SKIP_VALIDATION", False)
# 是否强制使用已设置的环境变量值（翻译参数及本地 MinerU 服务密钥）
# 设为 true 时，无论前端是否传参，都强制使用 .env 中的值
# 设为 false 时，仅当前端传参为空时才使用 .env 中的值
ENV_FORCE_OVERRIDE = _get_env_bool("DOCUTRANSLATE_ENV_FORCE_OVERRIDE", False)

# ============================================================
# MarkdownWorkflowParams 默认值
# ============================================================
CONVERT_ENGINE = _get_env_str("DOCUTRANSLATE_CONVERT_ENGINE", "identity")
MD2DOCX_ENGINE = _get_env_str("DOCUTRANSLATE_MD2DOCX_ENGINE", "auto")
MINERU_TOKEN = _get_env_str("DOCUTRANSLATE_MINERU_TOKEN", "")
MODEL_VERSION = _get_env_str("DOCUTRANSLATE_MODEL_VERSION", "vlm")
FORMULA_OCR = _get_env_bool("DOCUTRANSLATE_FORMULA_OCR", True)
MINERU_LANGUAGE = _get_env_str("DOCUTRANSLATE_MINERU_LANGUAGE", "ch")
MINERU_CONNECT_TIMEOUT = _get_env_float("DOCUTRANSLATE_MINERU_CONNECT_TIMEOUT", 5.0)
MINERU_READ_TIMEOUT = _get_env_float("DOCUTRANSLATE_MINERU_READ_TIMEOUT", 600.0)
MINERU_WRITE_TIMEOUT = _get_env_float("DOCUTRANSLATE_MINERU_WRITE_TIMEOUT", 600.0)
MINERU_TASK_TIMEOUT = _get_env_float("DOCUTRANSLATE_MINERU_TASK_TIMEOUT", 3600.0)
MINERU_POOL_TIMEOUT = _get_env_float("DOCUTRANSLATE_MINERU_POOL_TIMEOUT", 1.0)
MINERU_DEPLOY_BASE_URL = _get_env_str("DOCUTRANSLATE_MINERU_DEPLOY_BASE_URL", "http://127.0.0.1:8000")
MINERU_DEPLOY_API_KEY = _get_env_str("DOCUTRANSLATE_MINERU_DEPLOY_API_KEY", "")
MINERU_DEPLOY_BACKEND = _get_env_str("DOCUTRANSLATE_MINERU_DEPLOY_BACKEND", "hybrid-engine")
MINERU_DEPLOY_EFFORT = _get_env_str("DOCUTRANSLATE_MINERU_DEPLOY_EFFORT", "medium")
MINERU_DEPLOY_PARSE_METHOD = _get_env_str("DOCUTRANSLATE_MINERU_DEPLOY_PARSE_METHOD", "auto")
MINERU_DEPLOY_TABLE_ENABLE = _get_env_bool("DOCUTRANSLATE_MINERU_DEPLOY_TABLE_ENABLE", True)
MINERU_DEPLOY_FORMULA_ENABLE = _get_env_bool("DOCUTRANSLATE_MINERU_DEPLOY_FORMULA_ENABLE", True)
MINERU_DEPLOY_IMAGE_ANALYSIS = _get_env_bool("DOCUTRANSLATE_MINERU_DEPLOY_IMAGE_ANALYSIS", True)
MINERU_DEPLOY_START_PAGE_ID = _get_env_int("DOCUTRANSLATE_MINERU_DEPLOY_START_PAGE_ID", 0)
MINERU_DEPLOY_END_PAGE_ID = _get_env_int("DOCUTRANSLATE_MINERU_DEPLOY_END_PAGE_ID", 99999)
MINERU_DEPLOY_SERVER_URL = _get_env_str("DOCUTRANSLATE_MINERU_DEPLOY_SERVER_URL", "")
MINERU_DEPLOY_CONNECT_TIMEOUT = _get_env_float("DOCUTRANSLATE_MINERU_DEPLOY_CONNECT_TIMEOUT", 5.0)
MINERU_DEPLOY_READ_TIMEOUT = _get_env_float("DOCUTRANSLATE_MINERU_DEPLOY_READ_TIMEOUT", 1800.0)
MINERU_DEPLOY_WRITE_TIMEOUT = _get_env_float("DOCUTRANSLATE_MINERU_DEPLOY_WRITE_TIMEOUT", 300.0)
MINERU_DEPLOY_POOL_TIMEOUT = _get_env_float("DOCUTRANSLATE_MINERU_DEPLOY_POOL_TIMEOUT", 1.0)
MINERU_DEPLOY_UPLOAD_CONNECT_TIMEOUT = _get_env_float(
    "DOCUTRANSLATE_MINERU_DEPLOY_UPLOAD_CONNECT_TIMEOUT", 2000.0
)
MINERU_DEPLOY_UPLOAD_READ_TIMEOUT = _get_env_float(
    "DOCUTRANSLATE_MINERU_DEPLOY_UPLOAD_READ_TIMEOUT", 2000.0
)
MINERU_DEPLOY_UPLOAD_WRITE_TIMEOUT = _get_env_float(
    "DOCUTRANSLATE_MINERU_DEPLOY_UPLOAD_WRITE_TIMEOUT", 2000.0
)
MINERU_DEPLOY_UPLOAD_POOL_TIMEOUT = _get_env_float(
    "DOCUTRANSLATE_MINERU_DEPLOY_UPLOAD_POOL_TIMEOUT", 2000.0
)
MINERU_DEPLOY_TASK_TIMEOUT = _get_env_float("DOCUTRANSLATE_MINERU_DEPLOY_TASK_TIMEOUT", 3600.0)
MINERU_DEPLOY_POLL_INTERVAL = _get_env_float("DOCUTRANSLATE_MINERU_DEPLOY_POLL_INTERVAL", 1.0)

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
    "connect_timeout": CONNECT_TIMEOUT,
    "read_timeout": READ_TIMEOUT,
    "write_timeout": WRITE_TIMEOUT,
    "pool_timeout": POOL_TIMEOUT,
    "retry": RETRY,
    "system_proxy_enable": SYSTEM_PROXY_ENABLE,
    "extra_body": EXTRA_BODY,
    "web_skip_validation": WEB_SKIP_VALIDATION,
    "env_force_override": ENV_FORCE_OVERRIDE,
}
