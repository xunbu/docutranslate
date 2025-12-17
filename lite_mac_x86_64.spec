# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files, collect_all
import docutranslate

# --- 核心修改开始：收集 tiktoken 及其扩展依赖 ---

# 1. 收集 tiktoken 主包
ret_tik = collect_all('tiktoken')
tik_datas = ret_tik[0]
tik_binaries = ret_tik[1]
tik_hiddenimports = ret_tik[2]

# 2. 核心修复：收集 tiktoken_ext
# cl100k_base 等编码定义文件位于此处，必须显式收集
ret_ext = collect_all('tiktoken_ext')
tik_datas += ret_ext[0]
tik_binaries += ret_ext[1]
tik_hiddenimports += ret_ext[2]

# 3. 强制加入具体的插件模块
# 解决 "ValueError: Unknown encoding cl100k_base"
tik_hiddenimports.append('tiktoken_ext.openai_public')

# --- 核心修改结束 ---

datas = [
    ('./docutranslate/static', 'docutranslate/static'),
    ('./docutranslate/template', 'docutranslate/template'),
    *collect_data_files('pygments'),
    *tik_datas
]

hiddenimports = [
    'markdown.extensions.tables',
    'pymdownx.arithmatex',
    'pymdownx.superfences',
    'pymdownx.highlight',
    'pygments',
    *tik_hiddenimports # 合并 tiktoken 和 tiktoken_ext 的隐式导入
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
    # 保持原有的排除项
    excludes=["docling", "docutranslate.converter.x2md.converter_docling"],
    noarchive=False,
    target_arch='universal2', # 保留 Mac 通用架构设置
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
    upx=True,
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    codesign_identity=None,
    entitlements_file=None,
    icon='DocuTranslate.icns', # 保留 Mac 图标
)