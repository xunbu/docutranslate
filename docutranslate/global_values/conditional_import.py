import importlib

available_packages={}

def conditional_import(packagename,alias=None):
    try:
        imported= importlib.import_module(packagename)
        if alias:
            globals()[alias]=imported
        else:
            globals()[packagename]=imported
        available_packages[packagename]=True
        return True
    except ImportError:
        # print(f"package:{packagename}不存在")
        available_packages[packagename]=False
        return False
