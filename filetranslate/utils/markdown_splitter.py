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

        参数:
            markdown_text: 输入的markdown文本。

        返回:
            列表形式的markdown块，每个都是一个字符串。
        """
        # 使用更简单的方法：按Markdown块拆分
        # 这比使用AST解析更可靠

        # 模式用于识别markdown块（标题、段落、代码块等）
        blocks = self._split_into_logical_blocks(markdown_text)

        # 现在合并块以遵守max_block_size
        result_blocks = []
        current_block = ""

        for block in blocks:
            # 如果单个块大于最大大小，则进一步拆分
            if len(block) > self.max_block_size:
                # 如果已有累积内容，先添加
                if current_block:
                    result_blocks.append(current_block)
                    current_block = ""

                # 拆分大块
                large_block_parts = self._split_large_block(block)
                result_blocks.extend(large_block_parts)
                continue

            # 如果添加此块会超过限制，则开始新的结果块
            if len(current_block) + len(block) + 2 > self.max_block_size and current_block:
                result_blocks.append(current_block)
                current_block = block
            else:
                # 添加到当前块并适当换行
                if current_block:
                    current_block += "\n\n" + block
                else:
                    current_block = block

        # 如果不为空则添加最后一个块
        if current_block:
            result_blocks.append(current_block)

        return result_blocks

    def _split_into_logical_blocks(self, markdown_text: str) -> List[str]:
        """
        将markdown文本拆分为逻辑块（标题、段落、代码块等）

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
                # 对于非代码块，按空行拆分
                part_blocks = re.split(r'\n\s*\n', part)
                blocks.extend([b.strip() for b in part_blocks if b.strip()])

        return blocks

    def _split_large_block(self, block: str) -> List[str]:
        """
        拆分超过max_block_size的大块。

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
            # 对于其他块，按句子或行拆分
            if '.' in block or '!' in block or '?' in block:
                # 按句子拆分
                sentences = re.split(r'(?<=[.!?])\s+', block)

                current_part = []
                current_size = 0

                for sentence in sentences:
                    if current_size + len(sentence) + 1 > self.max_block_size and current_part:
                        result.append(' '.join(current_part))
                        current_part = [sentence]
                        current_size = len(sentence)
                    else:
                        current_part.append(sentence)
                        current_size += len(sentence) + 1  # +1表示空格

                if current_part:
                    result.append(' '.join(current_part))
            else:
                # 按行拆分
                lines = block.split('\n')

                current_part = []
                current_size = 0

                for line in lines:
                    if current_size + len(line) + 1 > self.max_block_size and current_part:
                        result.append('\n'.join(current_part))
                        current_part = [line]
                        current_size = len(line)
                    else:
                        current_part.append(line)
                        current_size += len(line) + 1  # +1表示换行符

                if current_part:
                    result.append('\n'.join(current_part))

        return result


def split_markdown_text(markdown_text, max_block_size=4096):
    """
    将markdown字符串拆分为不超过max_block_size的块。

    参数:
        markdown_text: 输入markdown文本
        max_block_size: 每个块的最大字符数

    返回:
        markdown块列表
    """
    splitter = MarkdownBlockSplitter(max_block_size=max_block_size)
    return splitter.split_markdown(markdown_text)