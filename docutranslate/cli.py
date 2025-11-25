# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
import argparse
import sys # 用于检查命令行参数数量


def main():
    parser = argparse.ArgumentParser(
        description="DocuTranslate: 一个文档翻译工具。",
        # 更新示例，展示如何使用 host 参数
        epilog="示例:\n"
               "  docutranslate -i                     (启动图形界面，默认本地访问)\n"
               "  docutranslate -i --host 0.0.0.0      (允许局域网内其他设备访问)\n"
               "  docutranslate -i -p 8081             (指定端口号)\n"
               "  docutranslate -i --cors              (启用默认的跨域设置)\n",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        "-i", "--interactive",
        action="store_true",
        help="打开图形化用户界面 (GUI) 并启动后端服务。"
    )

    # --- 新增 host 参数 ---
    parser.add_argument(
        "--host",
        type=str,
        default=None,
        help="指定服务监听的主机地址。默认为 '127.0.0.1' (仅本地)。若需局域网访问请设为 '0.0.0.0'。"
    )
    # ---------------------

    parser.add_argument(
        "-p", "--port",
        type=int,
        default=None,
        help="指定服务监听的端口号（默认：8010）。"
    )

    parser.add_argument(
        "--cors",
        action="store_true",
        help="启用跨域资源共享 (CORS)。如果是前后端分离开发或需跨域调用 API，请开启此选项。"
    )

    parser.add_argument(
        "--cors-regex",
        type=str,
        default=r"^https?://.*$",
        help="设置 CORS 允许的 Origin 正则表达式。默认为允许所有 HTTP 和 HTTPS 请求。"
    )

    parser.add_argument(
         "--version",
        action="store_true",
        help="查看版本号。"
    )

    # 检查是否没有提供任何参数
    if len(sys.argv) == 1:
        print("欢迎使用 DocuTranslate！")
        print("请使用 '-i' 或 '--interactive' 选项来启动图形化界面。")
        print("\n示例:")
        print("  docutranslate -i")
        print("  docutranslate -i --host 0.0.0.0 (局域网共享)")
        print("\n如需查看所有可用选项，请运行:")
        print("  docutranslate --help")
        sys.exit(0)

    args = parser.parse_args()

    # 调用核心逻辑
    if args.interactive:
        from docutranslate.app import run_app
        run_app(
            host=args.host,
            port=args.port,
            enable_CORS=args.cors,
            allow_origin_regex=args.cors_regex
        )
    elif args.version:
        from docutranslate import  __version__
        print(__version__)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()