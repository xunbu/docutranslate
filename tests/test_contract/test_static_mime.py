"""静态资源的 Content-Type 不能交给 mimetypes / Windows 注册表决定。

背景：Starlette 的 FileResponse 在未指定 media_type 时用
``mimetypes.guess_type(...)[0] or "text/plain"``。Windows 上 mimetypes 会读注册表
``HKEY_CLASSES_ROOT\\<ext>\\Content Type`` 并覆盖 Python 内置表，把 .js 注册成
text/plain 的机器上，``type="module"`` 的主脚本会以 text/plain 发出，浏览器按规范
拒绝执行，界面直接白屏：

    Failed to load module script: Expected a JavaScript module script but the
    server responded with a MIME type of "text/plain".
"""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from docutranslate.app import STATIC_DIR, app


@pytest.fixture
def client():
    return TestClient(app)


def _simulate_broken_registry(monkeypatch):
    """模拟受害机器：mimetypes 对任何扩展名都返回 text/plain。

    Starlette 在模块导入时就 `from mimetypes import guess_type` 绑定了名字，
    所以要打它模块里的引用，而不是 mimetypes.guess_type。
    """
    monkeypatch.setattr("starlette.responses.guess_type", lambda *a, **k: ("text/plain", None))


def _first_module_script() -> Path:
    assets = sorted((Path(STATIC_DIR) / "assets").glob("index-*.js"))
    assets = [p for p in assets if "legacy" not in p.name]
    assert assets, "前端构建产物缺失，无法验证 /static"
    return assets[0]


def test_module_script_is_served_as_javascript(client):
    name = _first_module_script().name
    response = client.get(f"/static/assets/{name}")

    assert response.status_code == 200
    assert "javascript" in response.headers["content-type"]


def test_module_script_survives_broken_registry(client, monkeypatch):
    """回归：注册表把 .js 标成 text/plain 时，模块脚本仍必须是 JS MIME。"""
    target = _first_module_script()
    url = f"/static/assets/{target.name}"
    healthy = client.get(url)
    assert "javascript" in healthy.headers["content-type"]

    _simulate_broken_registry(monkeypatch)
    broken = client.get(url)

    assert broken.status_code == 200
    assert broken.content == healthy.content, "文件内容不应受影响，只是响应头问题"
    assert "javascript" in broken.headers["content-type"], (
        "静态资源必须自己决定 Content-Type，不能依赖 mimetypes / 注册表"
    )


def test_css_and_index_are_not_affected_by_registry(client, monkeypatch):
    css = sorted((Path(STATIC_DIR) / "assets").glob("index-*.css"))[0]
    _simulate_broken_registry(monkeypatch)

    assert "text/css" in client.get(f"/static/assets/{css.name}").headers["content-type"]
    assert "text/html" in client.get("/").headers["content-type"]


def test_media_type_map_covers_web_assets():
    from docutranslate.app import _STATIC_MEDIA_TYPES

    for ext, expected in {
        ".js": "text/javascript",
        ".mjs": "text/javascript",
        ".css": "text/css",
        ".woff2": "font/woff2",
        ".wasm": "application/wasm",
    }.items():
        assert _STATIC_MEDIA_TYPES[ext] == expected
