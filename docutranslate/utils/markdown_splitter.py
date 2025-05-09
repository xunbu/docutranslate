import re
from typing import List


class MarkdownBlockSplitter:
    def __init__(self, max_block_size: int = 4096):
        """
        初始化MarkdownBlockSplitter。

        参数:
            max_block_size: 每个块的最大大小（以字符为单位）。
        """
        self.max_block_size = max_block_size

    def split_markdown(self, markdown_text: str) -> List[str]:
        """
        将markdown文本拆分为指定最大大小的块。
        确保拆分后可以重新拼接回原文（除了被拆分的代码块）。
        尽量保持标题和其内容在同一块中。

        参数:
            markdown_text: 输入的markdown文本。

        返回:
            列表形式的markdown块，每个都是一个字符串。
        """
        # 按Markdown块拆分
        blocks = self._split_into_logical_blocks(markdown_text)

        # 现在合并块以遵守max_block_size，同时尽量保持标题和内容在一起
        result_blocks = []
        current_block = ""
        header_waiting = False  # 标记是否有待处理的标题

        for block in blocks:
            # 检查块是否为空行分隔符
            is_separator = block.strip() == "" and block.count("\n") > 0

            # 检查是否是标题
            is_header = bool(re.match(r'^#{1,6}\s+.+', block.strip()))

            # 如果单个块大于最大大小，则进一步拆分
            if len(block) > self.max_block_size:
                # 如果已有累积内容，先添加
                if current_block:
                    result_blocks.append(current_block)
                    current_block = ""
                    header_waiting = False

                # 拆分大块
                large_block_parts = self._split_large_block(block)
                result_blocks.extend(large_block_parts)
                continue

            # 确定适当的连接符
            connector = "" if is_separator or not current_block else "\n"

            # 如果当前块是标题，且之前的块已经很大，先结束之前的块
            if is_header and len(current_block) + len(block) + len(
                    connector) > self.max_block_size * 0.9 and current_block:
                result_blocks.append(current_block)
                current_block = block
                header_waiting = True
                continue

            # 如果添加此块会超过限制，则开始新的结果块
            if len(current_block) + len(block) + len(connector) > self.max_block_size and current_block:
                # 如果当前块以标题开始，我们会尝试将整个块放入下一个块
                if header_waiting and not is_header:
                    # 检查是否能添加到当前块而不超出太多
                    if len(current_block) + len(block) + len(connector) <= self.max_block_size * 1.1:
                        current_block += connector + block
                        header_waiting = False
                        continue

                result_blocks.append(current_block)
                current_block = block
                header_waiting = is_header
            else:
                # 添加到当前块并适当连接
                if current_block:
                    current_block += connector + block
                else:
                    current_block = block

                # 如果刚添加了标题，标记等待内容
                if is_header:
                    header_waiting = True
                elif header_waiting and not is_separator:
                    # 如果添加了内容到标题后，不再是等待状态
                    header_waiting = False

        # 如果不为空则添加最后一个块
        if current_block:
            result_blocks.append(current_block)

        return result_blocks

    def _split_into_logical_blocks(self, markdown_text: str) -> List[str]:
        """
        将markdown文本拆分为逻辑块（标题、段落、代码块等）
        保留原始的空行数量，确保能重新拼接回原文

        参数:
            markdown_text: 输入markdown文本

        返回:
            markdown块列表
        """
        # 将Windows换行符替换为Unix风格
        markdown_text = markdown_text.replace('\r\n', '\n')

        # 匹配代码块的模式（用```或~~~围起来）
        code_block_pattern = r'(```[\s\S]*?```|~~~[\s\S]*?~~~)'

        # 将文本拆分为代码块和非代码块
        parts = re.split(code_block_pattern, markdown_text)

        blocks = []
        for i, part in enumerate(parts):
            # 如果是代码块（拆分结果中的奇数索引）
            if i % 2 == 1:
                blocks.append(part)
            else:
                # 对于非代码块，保留原始文本结构
                if not part:  # 跳过空字符串
                    continue

                # 识别并单独处理标题
                lines = part.split('\n')
                current_lines = []

                for line in lines:
                    # 检查是否是标题行
                    if re.match(r'^#{1,6}\s+.+', line):
                        # 如果有累积的内容，先添加到块
                        if current_lines:
                            blocks.append('\n'.join(current_lines))
                            current_lines = []

                        # 将标题作为单独的块
                        blocks.append(line)
                    else:
                        current_lines.append(line)

                # 处理剩余的行
                if current_lines:
                    # 按段落分隔符拆分剩余的内容
                    remaining_content = '\n'.join(current_lines)
                    parts_with_sep = re.split(r'(\n\s*\n)', remaining_content)

                    for j, p in enumerate(parts_with_sep):
                        if j % 2 == 0:  # 这是正文内容
                            if p.strip():  # 只添加非空内容
                                blocks.append(p)
                        else:  # 这是分隔符
                            # 添加分隔符作为单独的块以保持原始格式
                            if j > 0 and parts_with_sep[j - 1].strip():  # 确保前面有内容
                                blocks.append(p)

        return blocks

    def _split_large_block(self, block: str) -> List[str]:
        """
        拆分超过max_block_size的大块。
        只按行拆分，不按句子拆分。

        参数:
            block: 一个大的markdown块

        返回:
            较小的块列表
        """
        result = []

        # 检查是否是代码块
        if block.startswith('```') or block.startswith('~~~'):
            # 对于代码块，我们需要保留围栏标记
            fence_marker = '```' if block.startswith('```') else '~~~'

            # 提取语言说明符（如果存在）
            first_line_end = block.find('\n')
            first_line = block[:first_line_end]
            language_spec = first_line[3:].strip()

            # 拆分代码内容
            code_content = block[first_line_end + 1:-3].strip()

            # 按行拆分
            lines = code_content.split('\n')

            current_part = [first_line]
            current_size = len(first_line) + 1  # +1表示换行符

            for line in lines:
                line_size = len(line) + 1  # +1表示换行符

                if current_size + line_size + 3 > self.max_block_size:  # +3表示关闭围栏
                    # 关闭当前代码块
                    current_part.append(fence_marker)
                    result.append('\n'.join(current_part))

                    # 开始新的代码块
                    current_part = [f"{fence_marker}{language_spec}"]
                    current_size = len(current_part[0]) + 1

                current_part.append(line)
                current_size += line_size

            # 在最后部分添加关闭围栏
            current_part.append(fence_marker)
            result.append('\n'.join(current_part))

        else:
            # 检查是否是标题
            is_header = bool(re.match(r'^#{1,6}\s+.+', block.strip()))

            # 对于所有非代码块，统一按行拆分
            lines = block.split('\n')

            current_part = []
            current_size = 0

            for line in lines:
                line_size = len(line) + 1  # +1表示换行符

                # 如果这是标题行，并且当前块已经很大，先结束当前块
                if re.match(r'^#{1,6}\s+.+', line) and current_size > 0:
                    if current_part:
                        result.append('\n'.join(current_part))
                    current_part = [line]
                    current_size = line_size
                    continue

                if current_size + line_size > self.max_block_size and current_part:
                    result.append('\n'.join(current_part))
                    current_part = [line]
                    current_size = line_size
                else:
                    current_part.append(line)
                    current_size += line_size

            if current_part:
                result.append('\n'.join(current_part))

        return result


def split_markdown_text(markdown_text, max_block_size=4096):
    """
    将markdown字符串拆分为不超过max_block_size的块。
    拆分后可以通过简单的字符串连接重新组合回原始文本（除了被拆分的代码块）。
    尽量保持标题和其内容在同一块中。

    参数:
        markdown_text: 输入markdown文本
        max_block_size: 每个块的最大字符数

    返回:
        markdown块列表，可以通过''.join(chunks)重新组合（如果没有代码块被拆分）
    """
    splitter = MarkdownBlockSplitter(max_block_size=max_block_size)
    return splitter.split_markdown(markdown_text)


if __name__ == '__main__':
    with open(r"C:\Users\jxgm\Desktop\FileTranslate\tests\resource\regex.md", "r") as f:
        md = f.read()
    a = split_markdown_text(md)
    pass