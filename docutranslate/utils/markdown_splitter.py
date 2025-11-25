# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
import re
from typing import List


def is_placeholder(text: str) -> bool:
    """
    判断文本块是否仅包含图片占位符
    匹配格式: <ph-abc123> (允许前后空白)
    """
    return bool(re.match(r'^\s*<ph-[a-zA-Z0-9]+>\s*$', text))


class MarkdownBlockSplitter:
    def __init__(self, max_block_size: int = 5000):
        """
        初始化Markdown分块器
        参数:
            max_block_size: 每个块的最大字节数
        """
        self.max_block_size = max_block_size
        self.placeholder_pattern = r'(<ph-[a-zA-Z0-9]+>)'

    @staticmethod
    def _get_bytes(text: str) -> int:
        return len(text.encode('utf-8'))

    def split_markdown(self, markdown_text: str) -> List[str]:
        """
        将Markdown文本分割成指定大小的块
        """
        logical_blocks = self._split_into_logical_blocks(markdown_text)

        chunks = []
        current_chunk_parts = []
        current_size = 0

        for block in logical_blocks:
            block_size = self._get_bytes(block)

            # 如果是占位符，必须单独成块，且强制切断当前累积的内容
            if is_placeholder(block):
                if current_chunk_parts:
                    chunks.append("".join(current_chunk_parts))
                    current_chunk_parts = []
                    current_size = 0
                chunks.append(block)
                continue

            # 情况1：块本身就过大
            if block_size > self.max_block_size:
                if current_chunk_parts:
                    chunks.append("".join(current_chunk_parts))
                    current_chunk_parts = []
                    current_size = 0
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

        if current_chunk_parts:
            chunks.append("".join(current_chunk_parts))

        return chunks

    def _split_into_logical_blocks(self, markdown_text: str) -> List[str]:
        text = markdown_text.replace('\r\n', '\n')
        # 分割代码块
        code_block_pattern = r'(```[\s\S]*?```|~~~[\s\S]*?~~~)'
        parts = re.split(code_block_pattern, text)

        blocks = []
        for i, part in enumerate(parts):
            if not part:
                continue

            # 代码块直接添加
            if i % 2 == 1:
                blocks.append(part)
            else:
                # 普通文本：先切分出占位符
                ph_parts = re.split(self.placeholder_pattern, part)
                for ph_part in ph_parts:
                    if not ph_part:
                        continue

                    if is_placeholder(ph_part):
                        blocks.append(ph_part)
                    else:
                        # 再按空行切分段落
                        sub_parts = re.split(r'(\n{2,})', ph_part)
                        blocks.extend([p for p in sub_parts if p])
        return blocks

    def _split_large_block(self, block: str) -> List[str]:
        # 代码块处理
        if block.startswith(('```', '~~~')):
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

        # 普通文本处理
        lines = block.split('\n')
        chunks = []
        current_chunk = []
        current_size = 0
        for line in lines:
            line_size = self._get_bytes(line) + 1
            if current_size + line_size > self.max_block_size and current_chunk:
                chunks.append('\n'.join(current_chunk))
                current_chunk = [line]
                current_size = line_size - 1
            else:
                current_chunk.append(line)
                current_size += line_size

        if current_chunk:
            chunks.append('\n'.join(current_chunk))
        return chunks


def split_markdown_text(markdown_text: str, max_block_size=5000) -> List[str]:
    splitter = MarkdownBlockSplitter(max_block_size=max_block_size)
    chunks = splitter.split_markdown(markdown_text)
    # 过滤空块，但保留占位符
    return [chunk for chunk in chunks if chunk.strip() or is_placeholder(chunk)]


def _needs_single_newline_join(prev_chunk: str, next_chunk: str) -> bool:
    """判断常规文本是否需要单换行连接"""
    if not prev_chunk.strip() or not next_chunk.strip():
        return False

    last_line_prev = prev_chunk.rstrip().split('\n')[-1].lstrip()
    first_line_next = next_chunk.lstrip().split('\n')[0].lstrip()

    # 表格
    if last_line_prev.startswith('|') and last_line_prev.endswith('|') and \
            first_line_next.startswith('|') and first_line_next.endswith('|'):
        return True

    # 列表
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

        # === 核心修复逻辑 ===
        # 如果前一块或后一块是占位符，强制使用单换行 '\n'
        # 这样可以保证：
        # 1. 连续的徽章/图片 [img1]\n[img2] 会紧凑排列（视为行内元素）
        # 2. HTML结构 <p>\n<img>\n</p> 不会被打断
        # 3. 标题后的图片 # Title\n<img> 也能正常渲染
        if is_placeholder(prev_chunk) or is_placeholder(current_chunk):
            separator = "\n"

        elif _needs_single_newline_join(prev_chunk, current_chunk):
            separator = "\n"
        else:
            # 只有两个纯文本段落之间才用双换行
            separator = "\n\n"

        joined_text += separator + current_chunk

    return joined_text