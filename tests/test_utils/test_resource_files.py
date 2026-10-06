"""
回归测试：代码中通过 resource_path(...) / _get_local_content(...) 引用的资源文件必须真实存在。

背景：docutranslate/static/pico.css 曾在“清理不再使用的静态文件”提交中被删除，
但 md/json/srt 三个导出器仍在引用它，导致关闭 CDN（离线）时导出 HTML 直接 FileNotFoundError。
"""
import re
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[2] / "docutranslate"

_RESOURCE_REF_PATTERN = re.compile(
    r"""(?:resource_path|_get_local_content)\(\s*["']([^"']+)["']\s*\)"""
)


def test_referenced_resource_files_exist():
    missing = set()
    for py_file in PACKAGE_ROOT.rglob("*.py"):
        content = py_file.read_text(encoding="utf-8")
        for relative_path in _RESOURCE_REF_PATTERN.findall(content):
            if not (PACKAGE_ROOT / relative_path).exists():
                missing.add(f"{py_file.relative_to(PACKAGE_ROOT)} -> {relative_path}")
    assert not missing, f"代码引用了不存在的资源文件: {sorted(missing)}"
