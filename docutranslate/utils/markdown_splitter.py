# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
import re
from typing import List


class MarkdownBlockSplitter:
    def __init__(self, max_block_size: int = 5000):
        """
        初始化Markdown分块器

        参数:
            max_block_size: 每个块的最大字节数
        """
        self.max_block_size = max_block_size
        # 匹配占位符的正则，例如 <ph-abc123>
        self.placeholder_pattern = r'(<ph-[a-zA-Z0-9]+>)'

    @staticmethod
    def _get_bytes(text: str) -> int:
        return len(text.encode('utf-8'))

    def _is_placeholder(self, text: str) -> bool:
        """判断文本是否纯粹是一个占位符"""
        return bool(re.match(r'^' + self.placeholder_pattern + r'$', text.strip()))

    def split_markdown(self, markdown_text: str) -> List[str]:
        """
        将Markdown文本分割成指定大小的块
        确保可以通过简单拼接重建原始文本（分割的代码块除外）
        尽量保持标题与其对应内容在同一个块中
        """
        # 1. 将文本分割成逻辑块
        logical_blocks = self._split_into_logical_blocks(markdown_text)

        # 2. 合并逻辑块，使其不超过 max_block_size
        chunks = []
        current_chunk_parts = []
        current_size = 0

        for block in logical_blocks:
            block_size = self._get_bytes(block)

            # 检查是否是占位符块（需要单独成块）
            if self._is_placeholder(block):
                # 如果当前有积累的块，先输出
                if current_chunk_parts:
                    chunks.append("".join(current_chunk_parts))
                    current_chunk_parts = []
                    current_size = 0

                # 占位符单独作为一个chunk
                chunks.append(block)
                continue

            # 情况1：块本身就过大
            if block_size > self.max_block_size:
                # 先将当前积累的块输出
                if current_chunk_parts:
                    chunks.append("".join(current_chunk_parts))
                    current_chunk_parts = []
                    current_size = 0

                # 分割这个超大块并直接添加到结果中
                chunks.extend(self._split_large_block(block))
                continue

            # 情况2：将此块添加到当前chunk会超限
            if current_size + block_size > self.max_block_size:
                if current_chunk_parts:
                    chunks.append("".join(current_chunk_parts))

                current_chunk_parts = [block]
                current_size = block_size
            # 情况3：正常添加
            else:
                current_chunk_parts.append(block)
                current_size += block_size

        # 添加最后一个剩余的chunk
        if current_chunk_parts:
            chunks.append("".join(current_chunk_parts))

        return chunks

    def _split_into_logical_blocks(self, markdown_text: str) -> List[str]:
        """
        将Markdown文本分割成逻辑块（标题、段落、代码块、空行分隔符、图片占位符等）
        """
        # 标准化换行符
        text = markdown_text.replace('\r\n', '\n')

        # 分割代码块和其他内容
        code_block_pattern = r'(```[\s\S]*?```|~~~[\s\S]*?~~~)'
        parts = re.split(code_block_pattern, text)

        blocks = []
        for i, part in enumerate(parts):
            if not part:
                continue

            if i % 2 == 1:  # 这是一个代码块
                blocks.append(part)
            else:  # 这是普通Markdown内容
                # 1. 先按占位符分割，确保占位符独立
                ph_parts = re.split(self.placeholder_pattern, part)

                for ph_part in ph_parts:
                    if not ph_part:
                        continue

                    if self._is_placeholder(ph_part):
                        blocks.append(ph_part)
                    else:
                        # 2. 对非占位符文本，按一个或多个空行分割，并保留分隔符
                        # 这能有效分离段落、列表、标题等，并保留它们之间的空行
                        sub_parts = re.split(r'(\n{2,})', ph_part)
                        # 过滤掉 re.split 可能产生的空字符串
                        blocks.extend([p for p in sub_parts if p])

        return blocks

    def _split_large_block(self, block: str) -> List[str]:
        """
        分割单个超过 max_block_size 的大块
        """
        # 优先处理代码块
        if block.startswith(('```', '~~~')):
            fence = '```' if block.startswith('```') else '~~~'
            lines = block.split('\n')
            header = lines[0]
            footer = lines[-1]
            content_lines = lines[1:-1]

            chunks = []
            current_chunk_lines = [header]
            current_size = self._get_bytes(header) + 1

            for line in content_lines:
                line_size = self._get_bytes(line) + 1
                if current_size + line_size + self._get_bytes(footer) > self.max_block_size:
                    current_chunk_lines.append(footer)
                    chunks.append('\n'.join(current_chunk_lines))
                    current_chunk_lines = [header, line]
                    current_size = self._get_bytes(header) + 1 + line_size
                else:
                    current_chunk_lines.append(line)
                    current_size += line_size

            if len(current_chunk_lines) > 1:
                current_chunk_lines.append(footer)
                chunks.append('\n'.join(current_chunk_lines))
            return chunks

        # 对普通大文本按行分割
        lines = block.split('\n')
        chunks = []
        current_chunk = []
        current_size = 0
        for line in lines:
            line_size = self._get_bytes(line) + 1
            if current_size + line_size > self.max_block_size and current_chunk:
                chunks.append('\n'.join(current_chunk))
                current_chunk = [line]
                current_size = line_size - 1  # -1 for the first line does not have a leading '\n'
            else:
                current_chunk.append(line)
                current_size += line_size

        if current_chunk:
            chunks.append('\n'.join(current_chunk))

        return chunks


def split_markdown_text(markdown_text: str, max_block_size=5000) -> List[str]:
    """
    将Markdown字符串分割成不超过max_block_size的块
    """
    splitter = MarkdownBlockSplitter(max_block_size=max_block_size)
    chunks = splitter.split_markdown(markdown_text)
    # 过滤掉仅由空白字符组成的块，但保留占位符块
    return [chunk for chunk in chunks if chunk.strip() or splitter._is_placeholder(chunk)]


def _needs_single_newline_join(prev_chunk: str, next_chunk: str) -> bool:
    """
    判断两个块是否应该用单个换行符连接
    这通常发生在列表、表格、引用块的连续行之间
    """
    if not prev_chunk.strip() or not next_chunk.strip():
        return False

    # 如果其中一个是占位符，通常建议使用双换行以确保它是独立的块，
    # 除非原格式非常紧凑，但在翻译场景下，分隔开更安全。
    # 这里不额外处理占位符，走默认逻辑（最后会返回False，从而使用\n\n）
    if re.match(r'^\s*<ph-[a-zA-Z0-9]+>\s*$', prev_chunk) or \
            re.match(r'^\s*<ph-[a-zA-Z0-9]+>\s*$', next_chunk):
        return False

    last_line_prev = prev_chunk.rstrip().split('\n')[-1].lstrip()
    first_line_next = next_chunk.lstrip().split('\n')[0].lstrip()

    # 表格
    if last_line_prev.startswith('|') and last_line_prev.endswith('|') and \
            first_line_next.startswith('|') and first_line_next.endswith('|'):
        return True

    # 列表 (无序和有序)
    list_markers = r'^\s*([-*+]|\d+\.)\s+'
    if re.match(list_markers, last_line_prev) and re.match(list_markers, first_line_next):
        return True

    # 引用
    if last_line_prev.startswith('>') and first_line_next.startswith('>'):
        return True

    return False


def join_markdown_texts(markdown_texts: List[str]) -> str:
    """
    智能地拼接Markdown块列表
    """
    if not markdown_texts:
        return ""

    joined_text = markdown_texts[0]
    for i in range(1, len(markdown_texts)):
        prev_chunk = markdown_texts[i - 1]
        current_chunk = markdown_texts[i]

        # 判断是否应该用单换行还是双换行
        if _needs_single_newline_join(prev_chunk, current_chunk):
            separator = "\n"
        else:
            # 默认使用双换行来分隔不同的块
            separator = "\n\n"

        joined_text += separator + current_chunk

    return joined_text
