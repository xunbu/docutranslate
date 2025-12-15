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
        self.special_token_pattern = r'(```[\s\S]*?```|~~~[\s\S]*?~~~|<ph-[a-zA-Z0-9]+>)'

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
        raw_blocks, raw_separators = self._tokenize(markdown_text)
        chunks = []
        final_separators = []

        if not raw_blocks:
            return [], []

        current_chunk = raw_blocks[0]
        current_size = self._get_bytes(current_chunk)

        for i in range(len(raw_separators)):
            next_block = raw_blocks[i + 1]
            separator = raw_separators[i]

            # 注意：合并标记本身不占翻译配额，计算大小时可以忽略或按0计算
            # 但为了安全，我们按实际长度算（它很短）
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
        return chunks, final_separators

    def _tokenize(self, text: str) -> Tuple[List[str], List[str]]:
        text = text.replace('\r\n', '\n')
        parts = re.split(self.special_token_pattern, text)

        blocks = []
        separators = []
        pending_separator = ""

        def add_safe_block(content):
            """添加普通文本块"""
            nonlocal pending_separator
            if self._get_bytes(content) <= self.max_block_size:
                if blocks:
                    separators.append(pending_separator)
                    pending_separator = ""
                blocks.append(content)
            else:
                # 文本如果还超限，只能强行字节切分（无法包裹，因为是普通文本）
                sub_chunks = self._split_text_by_bytes(content, self.max_block_size)
                for idx, sub in enumerate(sub_chunks):
                    sep = pending_separator if idx == 0 else ""
                    if blocks: separators.append(sep)
                    if idx == 0: pending_separator = ""
                    blocks.append(sub)

        for part in parts:
            if not part: continue

            # === A. 特殊块 (代码/图片) ===
            if re.match(self.special_token_pattern, part):
                # 1. 正常大小：直接添加
                if self._get_bytes(part) < self.max_block_size:
                    if blocks:
                        separators.append(pending_separator)
                        pending_separator = ""
                    else:
                        pending_separator = ""
                    blocks.append(part)
                    continue

                # 2. 超大代码块：进行“合成拆分”
                # 判断是否是图片占位符（图片占位符理论上不会超大，但为了严谨）
                if is_placeholder(part):
                    # 图片无法拆分，只能强制字节切断（极罕见情况）
                    add_safe_block(part)
                    continue

                # 是超大代码块，解析头尾
                # part 格式如： ```python\ncode...\n```
                lines = part.split('\n')
                header = lines[0]  # e.g., ```python
                footer = lines[-1]  # e.g., ```

                # 获取中间的纯代码内容
                # 注意：如果 split 后只有一行或两行，说明结构有问题，直接降级
                if len(lines) < 2:
                    add_safe_block(part)
                    continue

                inner_content = "\n".join(lines[1:-1])

                # 将中间内容按行切分
                inner_parts = re.split(r'(\n)', inner_content)

                # 重新组合成多个小的完整代码块
                current_sub_block_content = ""

                # 结算 pending_separator (代码块之前的文本分隔符)
                if blocks:
                    separators.append(pending_separator)
                    pending_separator = ""
                else:
                    pending_separator = ""

                # 遍历代码内容行
                first_chunk = True

                for sub in inner_parts:
                    # 尝试构建当前块：Header + Current + sub + Footer
                    # 我们需要预估加上这一行后，是否会超限
                    # 预估大小 = Header + \n + Current + sub + \n + Footer
                    potential_content = current_sub_block_content + sub

                    # 构造一个假想的完整块来测大小
                    synthetic_block = f"{header}\n{potential_content}\n{footer}"

                    if self._get_bytes(synthetic_block) > self.max_block_size:
                        # 如果加上这行就超了，先把之前的 current_sub_block_content 封包
                        if current_sub_block_content:
                            wrapped_block = f"{header}\n{current_sub_block_content}\n{footer}"
                            blocks.append(wrapped_block)

                            # 添加特殊合并标记（不是空字符串，而是 MERGE_CODE_TOKEN）
                            separators.append(MERGE_CODE_TOKEN)

                            first_chunk = False

                        # 新的一块开始
                        current_sub_block_content = sub
                    else:
                        current_sub_block_content += sub

                # 添加最后剩余的部分
                if current_sub_block_content:
                    wrapped_block = f"{header}\n{current_sub_block_content}\n{footer}"
                    blocks.append(wrapped_block)

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
                add_safe_block(body)
                pending_separator = trailing_ws

        while len(separators) < len(blocks) - 1:
            separators.append("\n")

        return blocks, separators


def split_markdown_with_layout(markdown_text: str, max_block_size=5000) -> Tuple[List[str], List[str]]:
    splitter = MarkdownBlockSplitter(max_block_size=max_block_size)
    return splitter.split_with_layout(markdown_text)


def join_markdown_with_layout(chunks: List[str], separators: List[str]) -> str:
    """
    还原 Markdown。
    重点：检测 MERGE_CODE_TOKEN，如果遇到，则剥离 Chunk A 的尾巴和 Chunk B 的头，
    实现无缝拼接。
    """
    if not chunks:
        return ""

    result = chunks[0]

    for i in range(len(separators)):
        sep = separators[i] if i < len(separators) else "\n\n"
        next_chunk = chunks[i + 1] if i + 1 < len(chunks) else ""

        if sep == MERGE_CODE_TOKEN:
            # === 执行代码块无缝合并 ===
            # 上一块：剥离末尾的 ```
            # 下一块：剥离包含语言标识的 ```lang

            # 1. 处理 result (当前累积的文本，结尾应该是 ```)
            # 使用 rstrip 仅仅去掉空白，然后去掉最后三个反引号
            # 正则：匹配末尾的 ``` 以及可能的空白
            result = re.sub(r'```\s*$', '', result.rstrip())

            # 2. 处理 next_chunk (开头应该是 ```python 或 ```)
            # 正则：匹配开头的 ```加可选语言标识 加换行
            # 注意：翻译后的 next_chunk 可能包含前面多余的空行，先 lstrip 比较安全
            # 但也不能 lstrip 太多导致缩进丢失。代码块的 fence 通常顶格或跟随缩进。
            # 这里简单处理顶格的情况。
            next_chunk = re.sub(r'^\s*```.*\n', '', next_chunk, count=1)

            # 直接拼接，不加换行符，因为 split 时 content 包含了换行
            result += next_chunk
        else:
            # 普通拼接
            result += sep + next_chunk

    return result


# 兼容旧接口
def split_markdown_text(markdown_text: str, max_block_size=5000) -> List[str]:
    chunks, _ = split_markdown_with_layout(markdown_text, max_block_size)
    return chunks


def join_markdown_texts(markdown_texts: List[str]) -> str:
    return "\n\n".join(markdown_texts)