# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
import re
from urllib.request import getproxies
import httpx


def mask_secrets(text: str) -> str:
    """
    隐藏字符串中的敏感信息，包括 api_key、mineru_token 等。
    """
    if not text:
        return text

    # 隐藏 api_key
    text = re.sub(
        r'(["\']?api_key["\']?\s*[:=]\s*["\']?)([a-zA-Z0-9_\-\.]{4,})(["\']?)',
        r'\1[API_KEY_HIDDEN]\3',
        text
    )
    text = re.sub(
        r'(api_key["\']?\s*:\s*["\']?)([a-zA-Z0-9_\-\.]{4,})',
        r'\1[API_KEY_HIDDEN]',
        text
    )

    # 隐藏 mineru_token
    text = re.sub(
        r'(["\']?mineru_token["\']?\s*[:=]\s*["\']?)([a-zA-Z0-9_\-\.]{4,})(["\']?)',
        r'\1[MINERU_TOKEN_HIDDEN]\3',
        text
    )
    text = re.sub(
        r'(mineru_token["\']?\s*:\s*["\']?)([a-zA-Z0-9_\-\.]{4,})',
        r'\1[MINERU_TOKEN_HIDDEN]',
        text
    )

    # 隐藏常见的 token 模式 (40+ 字符的字母数字字符串，可能是 OpenAI key 等)
    text = re.sub(
        r'(sk-[a-zA-Z0-9_\-]{20,})',
        r'[OPENAI_KEY_HIDDEN]',
        text
    )

    # 隐藏以 "token" 结尾或包含 "token" 的长字符串值
    text = re.sub(
        r'([a-zA-Z_]+token[a-zA-Z_]*["\']?\s*[:=]\s*["\']?)([a-zA-Z0-9_\-\.]{10,})',
        r'\1[HIDDEN]',
        text
    )

    return text

def get_httpx_proxies(asyn=True):
    https_proxy = getproxies().get("https")
    http_proxy = getproxies().get("http")
    proxies = {}
    if https_proxy:
        # print(f"检测到系统代理:{https_proxy}")
        if asyn:
            proxies["https://"] = httpx.AsyncHTTPTransport(proxy=https_proxy)
        else:
            proxies["https://"] = httpx.HTTPTransport(proxy=https_proxy)
    if http_proxy:
        # print(f"检测到系统代理:{http_proxy}")
        if asyn:
            proxies["http://"] = httpx.AsyncHTTPTransport(proxy=http_proxy)
        else:
            proxies["https://"] = httpx.HTTPTransport(proxy=https_proxy)
    return proxies

if __name__ == '__main__':
    print(get_httpx_proxies())