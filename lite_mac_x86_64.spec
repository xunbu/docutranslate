# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files, collect_submodules
import docutranslate

datas = [
    ('./docutranslate/static', 'docutranslate/static'),
    ('./docutranslate/template', 'docutranslate/template'),
    *collect_data_files('pygments'),
]

hiddenimports = [
    'markdown.extensions.tables',
    'pymdownx.arithmatex',
    'pymdownx.superfences',
    'pymdownx.highlight',
    'pygments',
    *collect_submodules('charset_normalizer'),
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
    excludes=["docling", "docutranslate.converter.x2md.converter_docling"],
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
    upx=True,
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    codesign_identity=None,
    entitlements_file=None,
    icon='DocuTranslate.icns', # 保留 Mac 图标
)