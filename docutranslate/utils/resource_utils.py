import sys
from pathlib import Path

def resource_path(relative_path):
    """ 获取资源的绝对路径，适用于开发环境和 PyInstaller 打包后的环境 """
    try:
        base_path = Path(sys._MEIPASS)/"docutranslate"
    except Exception:
        base_path = Path(__file__).resolve().parent.parent # 开发时
        # 更健壮的开发时路径（如果你的资源相对于项目根目录）
        # base_path = Path(os.path.abspath("."))
        # 或者，如果你的 static 目录总是和 app.py 在同一级（开发时）
        # base_path = Path(__file__).resolve().parent
    # print(f"base_path:{base_path}")
    return base_path / relative_path