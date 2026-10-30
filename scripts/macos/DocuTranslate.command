#!/bin/bash
# Run the backend in Terminal so that its logs and selected WebUI port are visible.
set -u

launcher_dir="$(cd -- "$(dirname -- "$0")" && pwd)" || exit 1
# The app may be running from a read-only DMG; use a writable working directory.
cd -- "$HOME" || exit 1

printf '%s\n' \
    '正在启动 DocuTranslate…' \
    '启动完成后，请在浏览器中打开日志中的 WebUI 地址。' \
    '关闭此终端窗口会停止 DocuTranslate 服务。' \
    ''

"$launcher_dir/DocuTranslate" "$@"
status=$?

# run_app also logs startup errors, so retain the window even on a clean exit.
printf '\n%s\n' 'DocuTranslate 已停止。按回车键关闭此窗口。'
read -r _ || true
exit "$status"
