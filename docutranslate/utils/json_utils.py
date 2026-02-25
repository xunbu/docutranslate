# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
import json
import re

from json_repair import json_repair


def get_json_size(js: dict) -> int:
    """计算字典转换成JSON字符串并以UTF-8编码后的字节大小"""
    return len(json.dumps(js, ensure_ascii=False).encode('utf-8'))


def segments2json_chunks(segments: list[str], chunk_size_max: int) -> tuple[dict[str, str],
list[dict[str, str]], list[tuple[int, int]]]:
    """
    将文本段列表（segments）转换为多个JSON块。
    (函数注释不变)
    """

    # === 第一部分：预处理 (这部分逻辑可以保持不变) ===
    new_segments = []
    merged_indices_list = []

    for segment in segments:
        # 检查单个segment（作为一个JSON对象的值）是否已超限
        # 使用一个较长的key来预估，避免key长度变化带来的误差
        long_key_estimate = str(len(segments) + len(new_segments))
        if get_json_size({long_key_estimate: segment}) > chunk_size_max:
            sub_segments = []
            lines = segment.splitlines(keepends=True)
            current_sub_segment = ""
            for line in lines:
                next_sub_segment = current_sub_segment + line

                if get_json_size({long_key_estimate: next_sub_segment}) > chunk_size_max:
                    if current_sub_segment:
                        sub_segments.append(current_sub_segment)

                    # 即使单行超限，也必须作为一个独立的子段添加
                    sub_segments.append(line)
                    current_sub_segment = ""
                else:
                    current_sub_segment = next_sub_segment

            if current_sub_segment:
                sub_segments.append(current_sub_segment)

            if not sub_segments and segment == "":
                sub_segments.append("")

            start_index = len(new_segments)
            new_segments.extend(sub_segments)
            end_index = len(new_segments)
            if end_index - start_index > 1:
                merged_indices_list.append((start_index, end_index))
        else:
            new_segments.append(segment)

    # === 第二部分：组合成 JSON 块 (修正部分) ===
    json_chunks_list = []
    if not new_segments:
        return {}, [], []

    chunk = {}
    for key, val in enumerate(new_segments):
        prospective_chunk = chunk.copy()
        prospective_chunk[str(key)] = val

        # 修复bug: 即使chunk为空，如果 prospective_chunk（即单个元素）已超限，
        # 也应该先提交旧的chunk。
        if get_json_size(prospective_chunk) > chunk_size_max and chunk:
            json_chunks_list.append(chunk)
            chunk = {str(key): val}
        else:
            chunk = prospective_chunk

    if chunk:
        json_chunks_list.append(chunk)

    # ==================== 核心修正 ====================
    # 根据完整的 new_segments 列表构建最终的、完整的 js 字典
    # 这确保了第一个返回值是完整的
    js = {str(i): segment for i, segment in enumerate(new_segments)}
    # ================================================

    return js, json_chunks_list, merged_indices_list


def fix_json_string(json_string):
    def repl(m:re.Match):
        return f"""{'"' if m.group(1) else ""},\n"{m.group(2)}":{'"' if m.group(3) else ""}"""
    fixed_json = re.sub(
        r"""([“”"])?\s*[，,]\s*["“”]\s*(\d+)\s*["“”]\s*[：:]\s*(["“”])?""",
        repl,
        json_string,
        re.MULTILINE
    )
    return fixed_json


if __name__ == '__main__':
    print(get_json_size({"0": ""}))


def parse_json_response(result: str) -> dict | list:
    """
    统一解析JSON响应，兼容以下格式：
    1. ```json 代码块 ``` 格式
    2. 纯 JSON 格式（force_json 模式）
    3. 被截断的 JSON（使用 json_repair 尝试修复）

    Args:
        result: 模型返回的原始响应

    Returns:
        解析后的 dict 或 list
    """
    # 1. 尝试从 ```json 代码块 ``` 中提取
    match = re.search(r'```json(.*)```', result, re.DOTALL)
    if match:
        text = match.group(1)
    else:
        text = result

    # 2. 使用 json_repair 修复并解析
    return json_repair.loads(text)
