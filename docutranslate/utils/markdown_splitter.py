# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
import re
from typing import List, Tuple, Optional


def is_placeholder(text: str) -> bool:
    """判断文本块是否是图片占位符"""
    return bool(re.match(r'^\s*<ph-[a-zA-Z0-9]+>\s*$', text))


class MarkdownBlockSplitter:
    def __init__(self, max_block_size: int = 5000):
        self.max_block_size = max_block_size
        # 匹配 代码块 或 占位符
        self.special_token_pattern = r'(```[\s\S]*?```|~~~[\s\S]*?~~~|<ph-[a-zA-Z0-9]+>)'

    @staticmethod
    def _get_bytes(text: str) -> int:
        return len(text.encode('utf-8'))

    def split_with_layout(self, markdown_text: str) -> Tuple[List[str], List[str]]:
        """
        分割Markdown，并返回 (内容块列表, 分隔符列表)
        separators[i] 是 chunks[i] 和 chunks[i+1] 之间的原始文本
        """
        # 1. 细粒度切分：将文本切分为 [Block, Separator, Block, Separator...]
        raw_blocks, raw_separators = self._tokenize(markdown_text)

        # 2. 聚合：将小的 Block 合并为大的 Chunk，同时合并中间的 Separator
        chunks = []
        final_separators = []

        if not raw_blocks:
            return [], []

        current_chunk = raw_blocks[0]
        current_size = self._get_bytes(current_chunk)

        for i in range(len(raw_separators)):
            next_block = raw_blocks[i + 1]
            separator = raw_separators[i]

            next_block_size = self._get_bytes(next_block)
            separator_size = self._get_bytes(separator)

            # 判断是否需要切分
            # 1. 遇到占位符，强制切分（为了保护图片不被混入翻译文本中）
            # 2. 当前块 + 分隔符 + 下一块 超过最大限制
            if is_placeholder(current_chunk) or is_placeholder(next_block) or \
                    (current_size + separator_size + next_block_size > self.max_block_size):

                # 结束当前块
                chunks.append(current_chunk)
                # 记录连接到下一块的分隔符
                final_separators.append(separator)

                # 开始新块
                current_chunk = next_block
                current_size = next_block_size
            else:
                # 合并
                # 新的当前块 = 旧当前块 + 分隔符 + 下一块
                current_chunk += separator + next_block
                current_size += separator_size + next_block_size

        # 添加最后一个块
        chunks.append(current_chunk)

        return chunks, final_separators

    def _tokenize(self, text: str) -> Tuple[List[str], List[str]]:
        """
        将文本初步标记化为逻辑单元。
        逻辑单元包括：代码块、占位符、普通段落。
        单元之间的所有字符（通常是空白）都被视为分隔符。
        """
        text = text.replace('\r\n', '\n')

        # 1. 按 代码块 和 占位符 初步切分
        # re.split 包含捕获组时，结果列表为: [Text, Token, Text, Token, Text]
        parts = re.split(self.special_token_pattern, text)

        blocks = []  # 存储逻辑内容块
        separators = []  # 存储块之间的分隔符

        # 临时缓冲区，用于处理 split 产生的纯文本部分
        def process_text_part(text_part):
            if not text_part:
                return []
            # 对普通文本，按段落（双换行）再次切分
            # 我们需要保留切分符，所以用捕获组
            sub_parts = re.split(r'(\n{2,})', text_part)
            return sub_parts

        # 初始化：处理第一个部分
        # 整个流程是一个状态机，我们在寻找 "Content" -> "Separator" -> "Content" 的链条

        # 为了简化逻辑，我们先把 parts 扁平化为一个 token 流
        # 流中的元素要么是重要Token(Code/PH)，要么是普通文本(Text)
        flat_tokens = []
        for i, part in enumerate(parts):
            if not part:
                continue
            if re.match(self.special_token_pattern, part):
                flat_tokens.append({'type': 'special', 'text': part})
            else:
                # 普通文本，继续细分段落
                sub_parts = process_text_part(part)
                for sp in sub_parts:
                    if not sp: continue
                    # 只有双换行才被明确视为分隔符逻辑，单换行通常归于段落内
                    # 但为了精准还原，我们把所有 re.split 出来的项都视为独立单元
                    flat_tokens.append({'type': 'text', 'text': sp})

        if not flat_tokens:
            return [], []

        # 接下来进行 "Whitespace Shifting" (空白归约)
        # 我们希望 block 是纯净的内容，separator 是 block 之间的空白
        # 例如: "Text \n <ph>" -> Block="Text", Sep=" \n ", Block="<ph>"

        normalized_blocks = []
        normalized_separators = []

        current_block_text = ""
        pending_separator = ""

        for i, token in enumerate(flat_tokens):
            content = token['text']

            # 如果是特殊块（代码/占位符），它本身就是核心内容，前后不能有粘连
            if token['type'] == 'special':
                if current_block_text:
                    normalized_blocks.append(current_block_text)
                    normalized_separators.append(pending_separator)
                    current_block_text = ""
                    pending_separator = ""

                normalized_blocks.append(content)
                # 特殊块处理完，它的位置占住了，接下来的空白应该算作 separator
                # 但我们需要看下一个 token 是啥。
                # 简单处理：将特殊块直接加入，接下来的文本如果是空白，就是 separator
                continue

            # 如果是普通文本
            # 检查是否全是空白（这是分隔符候选）
            if not content.strip():
                # 如果当前没有积累的 block，这可能是开头的空白，或者是两个 special 块之间的空白
                if not normalized_blocks and not current_block_text:
                    # 忽略文件开头的空白，或者附加到下一个块？
                    # 为了对齐 list 长度，通常忽略开头，或者视为第一个块的一部分(如果不翻译)
                    pass
                elif normalized_blocks and not current_block_text:
                    # 前面已经有一个完整块，现在还没开始新块，这个空白是 separator
                    # 如果之前已经有 pending_separator，则叠加
                    if len(normalized_separators) < len(normalized_blocks):
                        normalized_separators.append(content)
                    else:
                        # 这种情况应该少见，追加到上一个 separator
                        normalized_separators[-1] += content
                else:
                    # current_block_text 正在积累，遇到了空白
                    # 比如 "Hello \n\n World" 中的 \n\n
                    # 结束当前块
                    normalized_blocks.append(current_block_text)
                    current_block_text = ""
                    normalized_separators.append(content)
            else:
                # 是有内容的文本
                # 剥离前导空白（归入上一个分隔符）和尾随空白（归入下一个分隔符）？
                # 简单起见，利用 rstrip 将尾部空白视为分隔符的一部分

                # 更好的策略：
                # 文本 token 自身可能包含换行（段落内）。
                # 我们只在 tokenize 阶段切分了 \n{2,}。
                # 所以 content 基本是一个完整的段落或代码块周围的文本。

                # 如果上一个块已经结束 (normalized_blocks > normalized_separators)，说明缺分隔符
                if len(normalized_blocks) > len(normalized_separators):
                    # 这意味着两个非空文本紧挨着？理论上 tokenize 阶段应该切开了
                    normalized_separators.append("")

                    # 剥离尾部空白作为 potential separator
                stripped = content.rstrip()
                trailing_space = content[len(stripped):]

                if current_block_text:
                    # 合并到当前正在构建的段落（极少发生，因为我们按split切分）
                    current_block_text += content
                else:
                    # 新的文本块
                    # 但要注意，如果这个文本块前面有空白，那个空白已经在上面处理了
                    # 这里只需要处理自己
                    normalized_blocks.append(stripped)
                    if trailing_space:
                        # 这个尾部空白暂时存起来，看后面接什么
                        # 实际上在我们的循环模型里，直接视为 separator 比较安全
                        # 除非它是文件结尾
                        if i < len(flat_tokens) - 1:
                            normalized_separators.append(trailing_space)
                        else:
                            # 文件末尾的空白，可以忽略或加回 block
                            normalized_blocks[-1] += trailing_space

        # 修正长度：separators 数量应该是 blocks - 1
        while len(normalized_separators) < len(normalized_blocks) - 1:
            normalized_separators.append("\n\n")  # 默认 fallback

        return normalized_blocks, normalized_separators


def split_markdown_with_layout(markdown_text: str, max_block_size=5000) -> Tuple[List[str], List[str]]:
    """
    外部调用的主入口
    返回: (chunks, separators)
    """
    splitter = MarkdownBlockSplitter(max_block_size=max_block_size)
    return splitter.split_with_layout(markdown_text)


def join_markdown_with_layout(chunks: List[str], separators: List[str]) -> str:
    """
    使用保存的分隔符还原 Markdown
    """
    if not chunks:
        return ""

    result = chunks[0]
    for i in range(len(separators)):
        # 安全检查，防止索引越界（虽然 split 保证了长度对应）
        sep = separators[i] if i < len(separators) else "\n\n"
        next_chunk = chunks[i + 1] if i + 1 < len(chunks) else ""
        result += sep + next_chunk

    return result


# 兼容旧接口，防止其他地方报错
def split_markdown_text(markdown_text: str, max_block_size=5000) -> List[str]:
    chunks, _ = split_markdown_with_layout(markdown_text, max_block_size)
    return chunks


def join_markdown_texts(markdown_texts: List[str]) -> str:
    # 旧接口只能猜，建议尽量使用新接口
    return "\n\n".join(markdown_texts)