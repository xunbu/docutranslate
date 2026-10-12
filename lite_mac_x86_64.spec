# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files, collect_submodules
import docutranslate

datas = [
    ('./docutranslate/static', 'docutranslate/static'),
    ('./docutranslate/template', 'docutranslate/template'),
    *collect_data_files('pygments'),
]

# MCP 是可选依赖，但打包产物必须真的带上它：缺了不会报错，只会静默失去 MCP 能力。
# 因此构建期就要求可导入，并显式收集全部子模块（MCPServer 的部分实现是动态加载的）。
try:
    from mcp.server.mcpserver import MCPServer  # noqa: F401
except ImportError as exc:
    raise SystemExit(
        "构建缺少可用的 MCP 依赖：请先 `uv sync --extra mcp`（需要 mcp>=2.3.0，见 pyproject）"
    ) from exc

hiddenimports = [
    'markdown.extensions.tables',
    'pymdownx.arithmatex',
    'pymdownx.superfences',
    'pymdownx.highlight',
    'pygments',
    *collect_submodules('charset_normalizer'),
    *collect_submodules('mcp'),
]

a = Analysis(
    ['docutranslate/app.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # 保持原有的排除项
    excludes=[],
    noarchive=False,
    target_arch='x86_64',
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=f'DocuTranslate-{docutranslate.__version__}-mac-x86',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    codesign_identity=None,
    entitlements_file=None,
    icon='DocuTranslate.icns', # 保留 Mac 图标
)
