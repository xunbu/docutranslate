import argparse
import sys # 用于检查命令行参数数量


def main():
    parser = argparse.ArgumentParser(
        description="DocuTranslate: 一个文档翻译工具。",
        epilog="示例: docutranslate -i  (启动图形界面)" # epilog 会显示在帮助信息的末尾
    )
    parser.add_argument(
        "-i", "--interactive",  # 添加一个长选项，更友好
        action="store_true",    # 当出现 -i 或 --interactive 时，args.interactive 将为 True
        help="打开图形化用户界面 (GUI)。"
    )

    # 如果你想在未来添加其他非GUI的命令行功能，可以在这里添加更多参数
    # parser.add_argument("input_file", help="要翻译的文件路径", nargs="?") # nargs="?" 使其可选
    # parser.add_argument("-l", "--language", help="目标语言")

    # 检查是否没有提供任何参数 (除了脚本名本身)
    # sys.argv[0] 是脚本名, len(sys.argv) == 1 表示只运行了命令本身，没有附加参数
    if len(sys.argv) == 1:
        # 如果用户只输入了 'docutranslate' 而没有任何参数
        print("欢迎使用 DocuTranslate！")
        print("请使用 '-i' 或 '--interactive' 选项来启动图形化界面。")
        print("\n示例:")
        print("  docutranslate -i")
        print("  docutranslate --interactive")
        print("\n如需查看所有可用选项，请运行:")
        sys.exit(0) # 正常退出

    args = parser.parse_args()

    # 调用核心逻辑
    if args.interactive: # 注意这里是 args.interactive，对应 "--interactive"
        from docutranslate.app import run_app
        run_app()
    else:
        print("提示：若要启动 DocuTranslate 图形界面，请使用 -i 或 --interactive 选项。")
        print("\n用法示例:")
        print("  docutranslate -i")
        print("  docutranslate --interactive")
        print("\n如需查看所有可用选项，请运行:")
        print("  docutranslate --help")
        # 或者直接显示帮助信息:
        # parser.print_help()
        sys.exit(1) # 以错误码退出，表明命令未按预期执行

if __name__ == "__main__":
    main()