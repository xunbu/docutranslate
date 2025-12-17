# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_data_files, collect_all
import docutranslate

# --- 核心修改开始：同时收集 tiktoken 和 tiktoken_ext ---

# 1. 收集 tiktoken 主包
ret_tik = collect_all('tiktoken')
tik_datas = ret_tik[0]
tik_binaries = ret_tik[1]
tik_hiddenimports = ret_tik[2]

# 2. 关键修复：收集 tiktoken_ext
# cl100k_base 等编码定义在这个扩展包里，必须显式收集
ret_ext = collect_all('tiktoken_ext')
tik_datas += ret_ext[0]
tik_binaries += ret_ext[1]
tik_hiddenimports += ret_ext[2]

# 3. 双重保险：强制加入具体的插件模块
# 有时候 collect_all 扫描不到动态加载的 openai_public，这里手动补上
tik_hiddenimports.append('tiktoken_ext.openai_public')

# --- 核心修改结束 ---

datas = [
    ('docutranslate/static', 'docutranslate/static'),
    ('docutranslate/template', 'docutranslate/template'),
    *collect_data_files('pygments'),
    *tik_datas
]

hiddenimports = [
    'markdown.extensions.tables',
    'pymdownx.arithmatex',
    'pymdownx.superfences',
    'pymdownx.highlight',
    'pygments',
    *tik_hiddenimports
]

a = Analysis(
    ['docutranslate/app.py'],
    pathex=[],
    binaries=tik_binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # 注意：exclude docling 可能导致部分依赖丢失，确保你真的不需要它
    excludes=["docling", "docutranslate.converter.x2md.converter_docling"],
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
    name=f'DocuTranslate-{docutranslate.__version__}-win',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='DocuTranslate.ico',
)