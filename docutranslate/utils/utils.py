# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
from urllib.request import getproxies


def get_httpx_proxies():
    https_proxy = getproxies().get("https")
    http_proxy = getproxies().get("http")
    proxies = {}
    if https_proxy:
        proxies["https://"] = https_proxy
    if http_proxy:
        proxies["http://"] = http_proxy
    return proxies

if __name__ == '__main__':
    print(get_httpx_proxies())