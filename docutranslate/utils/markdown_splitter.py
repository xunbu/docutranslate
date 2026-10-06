# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
import re
from typing import List, Tuple

# 定义一个特殊的合并标记，用于在 separators 中标记“这是一个被切断的代码块，需要无缝合并”
# 包含生僻字符防止冲突
MERGE_CODE_TOKEN = "\u0000<!--MD_SPLIT_MERGE-->\u0000"


def is_placeholder(text: str) -> bool:
    """判断文本块是否是图片占位符"""
    return bool(re.match(r'^\s*<ph-[a-zA-Z0-9]+>\s*$', text))


class MarkdownBlockSplitter:
    def __init__(self, max_block_size: int = 5000):
        self.max_block_size = max_block_size
        self.special_token_pattern = r'(```[\s\S]*?```|~~~[\s\S]*?~~~|\$\$[\s\S]*?\$\$|<ph-[a-zA-Z0-9]+>)'

    @staticmethod
    def _get_bytes(text: str) -> int:
        return len(text.encode('utf-8'))

    def _split_text_by_bytes(self, text: str, limit: int) -> List[str]:
        """兜底逻辑：按字节强制切分"""
        encoded = text.encode('utf-8')
        if len(encoded) <= limit:
            return [text]
        result = []
        start = 0
        total_len = len(encoded)
        while start < total_len:
            end = min(start + limit, total_len)
            if end < total_len:
                while end > start:
                    try:
                        encoded[start:end].decode('utf-8')
                        break
                    except UnicodeDecodeError:
                        end -= 1
            chunk_str = encoded[start:end].decode('utf-8')
            result.append(chunk_str)
            start = end
        return result

    def split_with_layout(self, markdown_text: str) -> Tuple[List[str], List[str]]:
        """切分为 chunks 与 separators。

        约定：``separators`` 长度为 ``len(chunks) + 1``——
        ``separators[0]`` 是首个块之前的原始文本，``separators[i]``（1..n-1）
        是块 i-1 与块 i 之间的原始文本，``separators[-1]`` 是末尾的原始文本。
        这样 ``join_markdown_with_layout(*split_markdown_with_layout(t)) == t``
        对任意输入成立（旧版本会丢掉首块缩进、尾随换行并改写 CRLF）。
        """
        raw_blocks, raw_separators = self._tokenize(markdown_text)

        if not raw_blocks:
            # 纯空白文本：没有块，但内容必须原样保留在 separator 里。
            return [], list(raw_separators)

        chunks = []
        final_separators = [raw_separators[0]]

        current_chunk = raw_blocks[0]
        current_size = self._get_bytes(current_chunk)

        for i in range(1, len(raw_blocks)):
            next_block = raw_blocks[i]
            separator = raw_separators[i]

            # 注意：合并标记本身不占翻译配额，为了安全仍按实际长度计算（它很短）
            separator_size = self._get_bytes(separator)
            next_block_size = self._get_bytes(next_block)

            if is_placeholder(current_chunk) or is_placeholder(next_block) or \
                    (current_size + separator_size + next_block_size > self.max_block_size):
                chunks.append(current_chunk)
                final_separators.append(separator)
                current_chunk = next_block
                current_size = next_block_size
            else:
                current_chunk += separator + next_block
                current_size += separator_size + next_block_size

        chunks.append(current_chunk)
        final_separators.append(raw_separators[-1])
        return chunks, final_separators

    def _tokenize(self, text: str) -> Tuple[List[str], List[str]]:
        parts = re.split(self.special_token_pattern, text)

        blocks = []
        separators = []
        pending_separator = ""

        def add_safe_block(content):
            """添加普通文本块（把 pending_separator 记为它之前的分隔符）"""
            nonlocal pending_separator
            if self._get_bytes(content) <= self.max_block_size:
                separators.append(pending_separator)
                pending_separator = ""
                blocks.append(content)
            else:
                # 文本如果还超限，只能强行字节切分（无法包裹，因为是普通文本）
                sub_chunks = self._split_text_by_bytes(content, self.max_block_size)
                for idx, sub in enumerate(sub_chunks):
                    separators.append(pending_separator if idx == 0 else "")
                    if idx == 0:
                        pending_separator = ""
                    blocks.append(sub)

        for part in parts:
            if not part: continue

            # === A. 特殊块 (代码/图片/公式) ===
            if re.match(self.special_token_pattern, part):
                # 1. 正常大小：直接添加
                if self._get_bytes(part) < self.max_block_size:
                    separators.append(pending_separator)
                    pending_separator = ""
                    blocks.append(part)
                    continue

                # 2. 超大代码块：进行“合成拆分”
                is_standard_code = part.startswith('```') or part.startswith('~~~')

                # 图片占位符、公式块($$)等非标准代码块不适合“拆头去尾”的合并逻辑
                if is_placeholder(part) or not is_standard_code:
                    add_safe_block(part)
                    continue

                # part 格式如： ```python\ncode...\n```
                lines = part.split('\n')
                header = lines[0]  # e.g., ```python
                footer = lines[-1]  # e.g., ```

                if len(lines) < 2:
                    add_safe_block(part)
                    continue

                inner_content = "\n".join(lines[1:-1])
                inner_parts = re.split(r'(\n)', inner_content)

                # 该代码块之前的分隔符
                separators.append(pending_separator)
                pending_separator = ""

                current_sub_block_content = ""

                for sub in inner_parts:
                    # 换行只做累积：绝不在换行处切分，否则下一块会以空行开头。
                    if sub == "\n":
                        current_sub_block_content += sub
                        continue

                    synthetic_block = f"{header}\n{current_sub_block_content}\n{footer}"
                    if current_sub_block_content and \
                            self._get_bytes(synthetic_block) > self.max_block_size:
                        # 切分点定在换行处：把 current 末尾的一个换行留给“接缝”，
                        # 由 join 时包装器本身的 \n 承担，因此不丢内容也不多空行。
                        if current_sub_block_content.endswith("\n"):
                            body = current_sub_block_content[:-1]
                        else:
                            body = current_sub_block_content
                        if body:
                            blocks.append(f"{header}\n{body}\n{footer}")
                            separators.append(MERGE_CODE_TOKEN)
                            current_sub_block_content = sub
                            continue

                    current_sub_block_content += sub

                if current_sub_block_content:
                    blocks.append(f"{header}\n{current_sub_block_content}\n{footer}")

                # 代码块处理完，无需 pending_separator，因为这是原子的
                continue

            # === B. 普通文本 ===
            sub_parts = re.split(r'(\n)', part)
            for sub in sub_parts:
                if not sub: continue
                if sub == '\n' or not sub.strip():
                    pending_separator += sub
                    continue

                lstripped = sub.lstrip()
                leading_ws = sub[:len(sub) - len(lstripped)]
                body = lstripped.rstrip()
                trailing_ws = lstripped[len(body):]

                pending_separator += leading_ws
                if body:
                    add_safe_block(body)
                pending_separator += trailing_ws

        # 末尾的原始文本（例如文档最后的换行）必须保留
        separators.append(pending_separator)

        # 安全网：保证 separators 长度为 len(blocks) + 1
        while len(separators) < len(blocks) + 1:
            separators.append("")

        return blocks, separators


def split_markdown_with_layout(markdown_text: str, max_block_size=5000) -> Tuple[List[str], List[str]]:
    splitter = MarkdownBlockSplitter(max_block_size=max_block_size)
    return splitter.split_with_layout(markdown_text)


def join_markdown_with_layout(chunks: List[str], separators: List[str]) -> str:
    """
    还原 Markdown。

    ``separators`` 采用 ``split_markdown_with_layout`` 的约定：长度为
    ``len(chunks) + 1``，首尾分别是首块之前与末块之后的原始文本。
    同时兼容旧调用（只传 len(chunks)-1 个块间分隔符）。

    重点：检测 MERGE_CODE_TOKEN，如果遇到，则剥离 Chunk A 的尾巴和 Chunk B 的头，
    实现无缝拼接。
    """
    if not chunks:
        return separators[0] if separators else ""

    if len(separators) == len(chunks) + 1:
        leading, trailing = separators[0], separators[-1]
        between = list(separators[1:-1])
    else:
        leading, trailing = "", ""
        between = list(separators[: len(chunks) - 1])
        while len(between) < len(chunks) - 1:
            between.append("\n")

    result = leading + chunks[0]

    for i, sep in enumerate(between):
        next_chunk = chunks[i + 1] if i + 1 < len(chunks) else ""

        if sep == MERGE_CODE_TOKEN:
            # === 执行代码块无缝合并 ===
            # 上一块：剥离末尾的 ```
            result = re.sub(r'```\s*$', '', result.rstrip())

            # 下一块：剥离开头的 ```lang
            next_chunk = re.sub(r'^\s*```.*\n', '', next_chunk, count=1)

            result += next_chunk
        else:
            result += sep + next_chunk

    return result + trailing


# 兼容旧接口
def split_markdown_text(markdown_text: str, max_block_size=5000) -> List[str]:
    chunks, _ = split_markdown_with_layout(markdown_text, max_block_size)
    return chunks


def join_markdown_texts(markdown_texts: List[str]) -> str:
    return "\n\n".join(markdown_texts)