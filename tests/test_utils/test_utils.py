"""
Tests for utils.utils module
"""
import os
from unittest.mock import patch, MagicMock

import httpx
import pytest

from docutranslate.utils.utils import get_httpx_proxies


def test_get_httpx_proxies_no_proxy():
    """Test get_httpx_proxies when no system proxy is set"""
    with patch('docutranslate.utils.utils.getproxies', return_value={}):
        proxies = get_httpx_proxies()
        assert proxies == {}


def test_get_httpx_proxies_https_proxy_async():
    """Test get_httpx_proxies with HTTPS proxy for async client"""
    with patch('docutranslate.utils.utils.getproxies', return_value={'https': 'http://proxy:8080'}):
        proxies = get_httpx_proxies(asyn=True)
        assert "https://" in proxies
        assert isinstance(proxies["https://"], httpx.AsyncHTTPTransport)


def test_get_httpx_proxies_https_proxy_sync():
    """Test get_httpx_proxies with HTTPS proxy for sync client"""
    with patch('docutranslate.utils.utils.getproxies', return_value={'https': 'http://proxy:8080'}):
        proxies = get_httpx_proxies(asyn=False)
        assert "https://" in proxies
        assert isinstance(proxies["https://"], httpx.HTTPTransport)


def test_get_httpx_proxies_http_proxy_async():
    """Test get_httpx_proxies with HTTP proxy for async client"""
    with patch('docutranslate.utils.utils.getproxies', return_value={'http': 'http://proxy:8080'}):
        proxies = get_httpx_proxies(asyn=True)
        assert "http://" in proxies
        assert isinstance(proxies["http://"], httpx.AsyncHTTPTransport)


def test_get_httpx_proxies_both_proxies():
    """Test get_httpx_proxies with both HTTP and HTTPS proxies"""
    with patch('docutranslate.utils.utils.getproxies', return_value={
        'http': 'http://http-proxy:8080',
        'https': 'http://https-proxy:8080'
    }):
        proxies = get_httpx_proxies()
        assert "http://" in proxies
        assert "https://" in proxies
        assert isinstance(proxies["http://"], httpx.AsyncHTTPTransport)
        assert isinstance(proxies["https://"], httpx.AsyncHTTPTransport)
