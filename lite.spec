# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_data_files, collect_all
import docutranslate

# --- 核心修改开始：收集 tiktoken 的所有依赖 ---
# tiktoken 依赖动态加载的插件和二进制文件，必须全部收集
tmp_ret = collect_all('tiktoken')
tik_datas = tmp_ret[0]
tik_binaries = tmp_ret[1]
tik_hiddenimports = tmp_ret[2]
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
    *tik_hiddenimports # 合并 tiktoken 的隐式导入 (包含 tiktoken_ext.openai_public 等)
]

a = Analysis(
    ['docutranslate/app.py'],
    pathex=[],
    binaries=tik_binaries, # 确保包含了 tiktoken 的二进制文件
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
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