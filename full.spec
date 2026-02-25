# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_all, copy_metadata
import docutranslate

# 初始化列表
datas = []
binaries = []

# --- 核心修改 1: 添加 tiktoken_ext.openai_public 到隐式导入 ---
# 必须显式导入这个模块，否则 tiktoken 找不到 cl100k_base 编码
hiddenimports = [
    'markdown.extensions.tables',
    'pymdownx.arithmatex',
    'pymdownx.superfences',
    'pymdownx.highlight',
    'pygments',
    'docling_ibm_models',
    'docling_parse',
    'cv2',
    'tiktoken_ext.openai_public'  # <--- 新增：确保编码插件被识别
]

# --- 核心修改 2: 在列表中添加 'tiktoken_ext' ---
# tiktoken: 核心库
# tiktoken_ext: 包含编码定义文件 (解决 Unknown encoding 问题)
# easyocr, docling 等: 其他依赖
packages_to_collect = [
    'easyocr',
    'docling',
    'pygments',
    'docling_ibm_models',
]

for package in packages_to_collect:
    try:
        tmp_ret = collect_all(package)
        datas += tmp_ret[0]
        binaries += tmp_ret[1]
        hiddenimports += tmp_ret[2]
    except Exception as e:
        print(f"Warning: Failed to collect resources for {package}: {e}")


try:
    datas += copy_metadata('docling-ibm-models') # 这里必须用连字符(pip名)
    datas += copy_metadata('docling-parse')      # 预防性添加
except Exception as e:
    print(f"Warning: Failed to copy metadata: {e}")

# 然后添加您的自定义资源（避免重复）
# 注意：确保 .venv 路径在您当前的构建环境中是存在的
custom_datas = [
    ('./.venv/Lib/site-packages/docling_parse/pdf_resources_v2', 'docling_parse/pdf_resources_v2'),
    ('./docutranslate/static', 'docutranslate/static'),
    ('./docutranslate/template', 'docutranslate/template')
]

# 避免添加重复的数据
for data in custom_datas:
    # 简单的去重检查，防止完全相同的源路径和目标路径被再次添加
    if data not in datas:
        datas.append(data)

a = Analysis(
    ['docutranslate/app.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=list(set(hiddenimports)),  # 去重
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=f'DocuTranslate_full-{docutranslate.__version__}-win',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='DocuTranslate.ico',
)