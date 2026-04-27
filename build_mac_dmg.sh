#!/bin/bash
# ============================================================
# DocuTranslate Mac ARM64 DMG 构建脚本
# 用法: bash build_mac_dmg.sh
# ============================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# 确保常用工具在 PATH 中
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

# 使用项目虚拟环境
VENV_PYTHON="$SCRIPT_DIR/.venv/bin/python"
UV="/usr/local/bin/uv"

if [ ! -f "$VENV_PYTHON" ]; then
    echo "错误: 未找到虚拟环境 $VENV_PYTHON"
    exit 1
fi

VERSION=$("$VENV_PYTHON" -c "import docutranslate; print(docutranslate.__version__)")
echo "=========================================="
echo "  DocuTranslate Mac ARM64 DMG 构建"
echo "  版本: ${VERSION}"
echo "=========================================="

# ---------- 第 1 步：清理旧构建 ----------
echo "[1/5] 清理旧构建产物..."
rm -rf build dist

# ---------- 第 2 步：构建前端 ----------
echo "[2/5] 构建前端..."
cd frontend
npm ci
npm run build
cd ..

# ---------- 第 3 步：PyInstaller 打包 ----------
echo "[3/5] PyInstaller 打包..."
"$VENV_PYTHON" -m PyInstaller --clean lite_mac_arm64.spec

# ---------- 第 4 步：验证 ----------
echo "[4/5] 验证 .app 结构..."
APP_PATH="dist/DocuTranslate.app"
if [ ! -d "$APP_PATH" ]; then
    echo "错误: ${APP_PATH} 不存在，打包可能失败"
    exit 1
fi

echo "  .app 路径: ${APP_PATH}"
echo "  .app 大小: $(du -sh "$APP_PATH" | cut -f1)"
echo "  .app 结构:"
find "$APP_PATH" -maxdepth 3 -type f \
    -not -path "*/Contents/MacOS/*" \
    -not -path "*/Contents/Frameworks/*" \
    -not -path "*/Contents/Resources/*" \
    | sed 's/^/    /'

# ---------- 第 5 步：创建 DMG ----------
echo "[5/5] 创建 DMG..."

DMG_NAME="DocuTranslate-${VERSION}-arm64"
DMG_PATH="dist/${DMG_NAME}.dmg"
DMG_TEMP="dist/dmg_temp"

mkdir -p "$DMG_TEMP"
cp -R "$APP_PATH" "$DMG_TEMP/"
ln -s /Applications "$DMG_TEMP/Applications"

hdiutil create \
    -volname "DocuTranslate" \
    -srcfolder "$DMG_TEMP" \
    -ov -format UDZO \
    "$DMG_PATH"

rm -rf "$DMG_TEMP"

echo "=========================================="
echo "  构建完成！"
echo "  DMG: ${DMG_PATH}"
echo "  DMG 大小: $(du -sh "$DMG_PATH" | cut -f1)"
echo "=========================================="
echo ""
echo "提示：首次启动请右键 App →「打开」以绕过 Gatekeeper"
