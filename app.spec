# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# 收集 easyocr 的数据文件和子模块
datas_easyocr = collect_data_files('easyocr', include_py_files=True)
hiddenimports_easyocr = collect_submodules('easyocr')

# 收集 docling 的数据文件和子模块 (如果 docling 本身有数据文件)
# datas_docling = collect_data_files('docling', include_py_files=True) # 示例，如果 docling 有数据
hiddenimports_docling = collect_submodules('docling')


a = Analysis(
    ['docutranslate\\app.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('C:\\Users\\jxgm\\Desktop\\FileTranslate\\.venv\\Lib\\site-packages\\docling_parse\\pdf_resources_v2', 'docling_parse/pdf_resources_v2'),
        # *datas_docling, # 取消注释如果 docling 有自己的数据文件
        *datas_easyocr
    ],
    hiddenimports=[
        'easyocr',
        *hiddenimports_easyocr, # 确保 easyocr 的所有子模块都被包含
        'docling',
        *hiddenimports_docling, # 确保 docling 的所有子模块都被包含
        'docling.datamodel.pipeline_options', # 非常重要，为了 EasyOcrOptions
        'docling.models.easyocr_model', # 猜测的路径，你需要确认 docling 中 easyocr 集成模型的实际模块路径
        # 根据需要添加 easyocr 的其他依赖，例如：
        'cv2',
        'torch',
        'torchvision',
        'skimage',
        'yaml',
        'PIL',
        # 添加任何其他 docling 可能动态加载的模块或工厂类中引用的模块
    ],
    # collect_submodules 已经通过上面的 collect_submodules() 函数处理并添加到 hiddenimports
    # 所以这里可以简化，或者保留你原来的方式，但上面的方式更明确
    # collect_submodules=['docling','easyocr'],
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
    [],
    exclude_binaries=True,
    name='app',
    debug=False, # 编译时可以设为 True 或 '--debug=all' 运行打包后的程序以获取更多信息
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='app',
)