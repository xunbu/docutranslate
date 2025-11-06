# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
from urllib.request import getproxies
import httpx

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