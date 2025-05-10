import re
from typing import List


class MarkdownBlockSplitter:
    def __init__(self, max_block_size: int = 4096):
        """
        初始化Markdown分块器

        参数:
            max_block_size: 每个块的最大字符数
        """
        self.max_block_size = max_block_size

    def split_markdown(self, markdown_text: str) -> List[str]:
        """
        将Markdown文本分割成指定大小的块
        确保可以通过简单拼接重建原始文本（分割的代码块除外）
        尽量保持标题与其对应内容在同一个块中

        参数:
            markdown_text: 输入的Markdown文本

        返回:
            Markdown块组成的列表
        """
        # 首先将文本分割成逻辑块并保持结构
        blocks = self._split_into_logical_blocks(markdown_text)

        # 然后合并块，同时遵守大小限制并保持标题与内容在一起
        result_blocks = []
        current_block = []
        current_size = 0
        pending_heading = None  # 等待内容的标题

        for block in blocks:
            block_size = len(block)
            is_heading = bool(re.match(r'^#{1,6}\s+.+', block.strip()))
            is_separator = block.strip() == '' and block.count('\n') > 0

            # 情况1：块本身过大，无法单独放入
            if block_size > self.max_block_size:
                # 先输出已积累的内容
                if current_block:
                    result_blocks.append('\n'.join(current_block))
                    current_block = []
                    current_size = 0
                    pending_heading = None

                # 分割大块并添加所有部分
                large_block_parts = self._split_large_block(block)
                result_blocks.extend(large_block_parts)
                continue

            # 情况2：添加此块会超出大小限制
            if current_size + block_size + (1 if current_block else 0) > self.max_block_size:
                # 如果有等待内容的标题，尝试将其与内容保持在一起
                if pending_heading and not is_heading and not is_separator:
                    # 如果只添加标题和此块能放下，则这样做
                    if len(pending_heading) + block_size + 1 <= self.max_block_size:
                        result_blocks.append('\n'.join(current_block[:-1]))  # 输出不含标题的内容
                        current_block = [pending_heading, block]
                        current_size = len(pending_heading) + 1 + block_size
                        pending_heading = None
                        continue

                # 否则输出当前块并开始新块
                if current_block:
                    result_blocks.append('\n'.join(current_block))

                current_block = [block]
                current_size = block_size
                pending_heading = block if is_heading else None
                continue

            # 情况3：正常情况 - 添加到当前块
            if current_block:
                current_block.append(block)
                current_size += 1 + block_size  # 加1是因为换行符
            else:
                current_block.append(block)
                current_size = block_size

            # 更新等待标题状态
            if is_heading:
                pending_heading = block
            elif not is_separator and pending_heading:
                # 已在标题后添加内容，清除等待状态
                pending_heading = None

        # 添加最后一个块（如果存在）
        if current_block:
            result_blocks.append('\n'.join(current_block))

        return result_blocks

    def _split_into_logical_blocks(self, markdown_text: str) -> List[str]:
        """
        将Markdown文本分割成逻辑块（标题、段落、代码块等）
        同时保持原始结构包括空行

        参数:
            markdown_text: 输入的Markdown文本

        返回:
            Markdown块列表
        """
        # 标准化换行符
        markdown_text = markdown_text.replace('\r\n', '\n')

        # 首先将代码块与其他内容分开
        code_block_pattern = r'(```[\s\S]*?```|~~~[\s\S]*?~~~)'
        parts = re.split(code_block_pattern, markdown_text)

        blocks = []
        for i, part in enumerate(parts):
            if i % 2 == 1:  # 代码块
                blocks.append(part)
            elif part:  # 非代码内容
                # 分割成行同时保留空行
                lines = part.split('\n')
                current_block = []

                for line in lines:
                    # 检查是否是标题
                    if re.match(r'^#{1,6}\s+.+', line.strip()):
                        # 输出已积累的内容
                        if current_block:
                            blocks.append('\n'.join(current_block))
                            current_block = []
                        # 将标题作为单独块添加
                        blocks.append(line)
                    else:
                        # 对于非标题行，用适当的换行符积累
                        if current_block:
                            current_block.append(line)
                        else:
                            current_block = [line]

                # 添加剩余内容
                if current_block:
                    blocks.append('\n'.join(current_block))

        return blocks

    def _split_large_block(self, block: str) -> List[str]:
        """
        分割超过max_block_size的大块
        总是在行边界处分割

        参数:
            block: 大的Markdown块

        返回:
            小块组成的列表
        """
        # 特殊处理代码块
        if block.startswith('```') or block.startswith('~~~'):
            fence = '```' if block.startswith('```') else '~~~'
            parts = block.split('\n')

            # 提取语言说明符（如果存在）
            first_line = parts[0]
            remaining_lines = parts[1:-1]  # 排除开始和结束标记
            closing_fence = parts[-1]

            result = []
            current_chunk = [first_line]
            current_size = len(first_line)

            for line in remaining_lines:
                line_len = len(line) + 1  # +1是因为换行符

                if current_size + line_len + len(closing_fence) > self.max_block_size:
                    # 关闭当前块并开始新块
                    result.append('\n'.join(current_chunk + [closing_fence]))
                    current_chunk = [first_line]  # 新块使用相同的开始标记
                    current_size = len(first_line)

                current_chunk.append(line)
                current_size += line_len

            # 添加最后的块
            if len(current_chunk) > 1:  # 有超出开始标记的内容
                result.append('\n'.join(current_chunk + [closing_fence]))

            return result

        # 对于非代码块，简单地在行边界处分割
        lines = block.split('\n')
        result = []
        current_chunk = []
        current_size = 0

        for line in lines:
            line_len = len(line) + 1  # +1是因为换行符

            if current_size + line_len > self.max_block_size and current_chunk:
                result.append('\n'.join(current_chunk))
                current_chunk = [line]
                current_size = line_len
            else:
                if current_chunk:
                    current_chunk.append(line)
                    current_size += line_len
                else:
                    current_chunk = [line]
                    current_size = line_len

        if current_chunk:
            result.append('\n'.join(current_chunk))

        return result


def split_markdown_text(markdown_text, max_block_size=4096):
    """
    将Markdown字符串分割成不超过max_block_size的块
    可以通过简单拼接重建原始文本（分割的代码块除外）
    尽量保持标题与其对应内容在一起

    参数:
        markdown_text: 输入的Markdown文本
        max_block_size: 每个块的最大字符数

    返回:
        可以通过''.join(chunks)重建的Markdown块列表
    """
    splitter = MarkdownBlockSplitter(max_block_size=max_block_size)
    return splitter.split_markdown(markdown_text)


if __name__ == '__main__':
    pass