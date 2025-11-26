# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
import base64
import hashlib
import io
import mimetypes
import os
import re
import tempfile
import threading
import uuid
import zipfile
from pathlib import Path


class MaskDict:
    def __init__(self):
        self._dict = {}
        self._lock = threading.Lock()

    def create_id(self):
        with self._lock:
            while True:
                id = uuid.uuid1().hex[:6]
                if id not in self._dict:
                    return id

    def get(self, key):
        with self._lock:
            return self._dict.get(key)

    def set(self, key, value):
        with self._lock:
            self._dict[key] = value

    def delete(self, key):
        with self._lock:
            if key in self._dict:
                del self._dict[key]

    def __contains__(self, item):
        with self._lock:
            return item in self._dict


# def uris2placeholder(markdown:str, mask_dict:MaskDict):
##替换整个uri
#     def uri2placeholder(match: re.Match):
#         id = mask_dict.create_id()
#         mask_dict.set(id, match.group())
#         return f"<ph-{id}>"
#
#     uri_pattern = r'!?\[.*?\]\(.*?\)'
#     markdown = re.sub(uri_pattern, uri2placeholder, markdown)
#     return markdown

def uris2placeholder(markdown: str, mask_dict: MaskDict):
    ##只替换uri里的链接部分，保留标题
    def uri2placeholder(match: re.Match):
        id = mask_dict.create_id()
        # 只替换base64数据
        # mask_dict.set(id, match.group(2))
        # return f"{match.group(1)}(<ph-{id}>)"

        # 整个图片都替换为占位符
        mask_dict.set(id, match.group())
        print(f"生成占位符<ph-{id}>")
        return f"<ph-{id}>"

    uri_pattern = r'(!\[.*?\])\((.*?)\)'
    markdown = re.sub(uri_pattern, uri2placeholder, markdown)
    return markdown


def placeholder2uris(markdown: str, mask_dict: MaskDict):
    def placeholder2uri(match: re.Match):
        id = match.group(1)
        uri = mask_dict.get(id)
        if uri is None:
            return match.group()
        print(f"占位符<ph-{id}>已还原为图片")
        return uri

    ph_pattern = r"<\s*[pP][hH]\s*-\s*([a-zA-Z0-9]+)\s*>"
    markdown = re.sub(ph_pattern, placeholder2uri, markdown)
    return markdown


def find_markdown_in_zip(zip_bytes: bytes):
    zip_file_bytes = io.BytesIO(zip_bytes)
    with zipfile.ZipFile(zip_file_bytes, 'r') as zip_ref:
        # 获取 ZIP 中所有文件名
        all_files = zip_ref.namelist()
        # 筛选出 .md 文件
        md_files = [f for f in all_files if f.lower().endswith('.md')]

        if len(md_files) == 1:
            return md_files[0]
        elif len(md_files) > 1:
            raise ValueError("ZIP 中包含多个 Markdown 文件")
        else:
            raise ValueError("ZIP 中没有 Markdown 文件")


def embed_inline_image_from_zip(zip_bytes: bytes, filename_in_zip: str | None = None, encoding="utf-8"):
    """
    从ZIP文件的字节流中读取一个Markdown文件，并将其中的相对路径图片内联为Base64编码的data URI。

    Args:
        zip_bytes (bytes): ZIP文件的字节内容。
        filename_in_zip (str | None, optional):
            要处理的Markdown文件名。如果为 None，则自动查找并使用ZIP包中的第一个.md或.markdown文件。
            默认为 None。
        encoding (str, optional): Markdown文件的编码格式。默认为 "utf-8"。

    Returns:
        str | None: 包含内联图片的Markdown文本内容，如果发生错误则返回None。
    """
    zip_file_bytes = io.BytesIO(zip_bytes)
    print("正在尝试打开内存中的ZIP存档...")
    with zipfile.ZipFile(zip_file_bytes, 'r') as archive:
        print("ZIP存档已打开。")

        # --- 新增和修改的逻辑 ---
        target_md_filename = filename_in_zip

        # 如果未指定文件名，则自动查找第一个Markdown文件
        if target_md_filename is None:
            print("`正在自动查找第一个Markdown文件...")
            found_md = None
            for name in archive.namelist():
                # 确保它是一个文件（不是目录），并检查扩展名
                if not name.endswith('/') and name.lower().endswith(('.md', '.markdown')):
                    found_md = name
                    break  # 找到第一个就停止

            if found_md:
                target_md_filename = found_md
                print(f"已自动选择Markdown文件: '{target_md_filename}'")
            else:
                print("错误: ZIP压缩包中未找到任何Markdown文件 (.md 或 .markdown)。")
                print(f"压缩包中的可用文件列表: {archive.namelist()}")
                return None

        # 统一检查最终确定的文件是否存在于压缩包中
        if target_md_filename not in archive.namelist():
            print(f"错误: 文件 '{target_md_filename}' 在ZIP压缩包中未找到。")
            print(f"压缩包中的可用文件列表: {archive.namelist()}")
            return None

        # --- 后续代码使用 target_md_filename ---
        print(f"正在读取文件 '{target_md_filename}'...")
        md_content_bytes = archive.read(target_md_filename)
        print(f"文件 '{target_md_filename}' 已读取。")
        md_content_text = md_content_bytes.decode(encoding)
        print(f"文件内容已使用 '{encoding}' 编码成功解码。")

        print("开始处理Markdown中的图片...")
        # 获取Markdown文件在ZIP包内的基本目录
        base_md_path_in_zip = os.path.dirname(target_md_filename)

        def replace_image_with_base64(match):
            alt_text = match.group(1)
            original_image_path = match.group(2)

            if original_image_path.startswith(('http://', 'https://', 'data:')):
                # print(f"  跳过外部或已内联图片: {original_image_path}")
                return match.group(0)

            image_path_in_zip = os.path.join(base_md_path_in_zip, original_image_path)
            image_path_in_zip = os.path.normpath(image_path_in_zip).replace(os.sep, '/')

            if image_path_in_zip.startswith('./'):
                image_path_in_zip = image_path_in_zip[2:]

            try:
                image_bytes = archive.read(image_path_in_zip)
                mime_type, _ = mimetypes.guess_type(image_path_in_zip)
                if not mime_type:
                    ext = os.path.splitext(image_path_in_zip)[1].lower()
                    mime_map = {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
                                '.gif': 'image/gif', '.svg': 'image/svg+xml', '.webp': 'image/webp'}
                    mime_type = mime_map.get(ext)

                if not mime_type:
                    print(f"    警告: 无法确定图片 '{image_path_in_zip}' 的MIME类型。跳过内联。")
                    return match.group(0)

                base64_encoded_data = base64.b64encode(image_bytes).decode('utf-8')
                new_image_tag = f"![{alt_text}](data:{mime_type};base64,{base64_encoded_data})"
                return new_image_tag
            except KeyError:
                print(f"    警告: 图片 '{image_path_in_zip}' 在ZIP压缩包中未找到。原始链接将被保留。")
                return match.group(0)
            except Exception as e_img:
                print(f"    错误: 处理图片 '{image_path_in_zip}' 时发生错误: {e_img}。原始链接将被保留。")
                return match.group(0)

        image_regex = r"!\[(.*?)\]\((.*?)\)"
        modified_md_content = re.sub(image_regex, replace_image_with_base64, md_content_text)

        print("图片处理完成。")
        return modified_md_content


def unembed_base64_images_to_zip(markdown: str, markdown_name: str, image_folder_name="images") -> bytes:
    with tempfile.TemporaryDirectory() as temp_dir:
        image_folder = os.path.join(temp_dir, image_folder_name)
        os.makedirs(image_folder, exist_ok=True)

        pattern = r"!\[(.*?)\]\(data:(.*?);.*base64,(.*?)\)"

        def unembed_base64_images(match: re.Match) -> str:
            alt_text = match.group(1)
            mime_type = match.group(2)
            b64data_raw = match.group(3)

            # 【修改点2】强制清洗数据：移除所有非 Base64 合法字符（如中文、空格、换行符等）
            # Base64 字符集只包含 A-Z, a-z, 0-9, +, /, =
            b64data_clean = re.sub(r'[^A-Za-z0-9+/=]', '', b64data_raw)

            # 简单的扩展名推断
            extension = mimetypes.guess_extension(mime_type)
            if not extension:
                if 'png' in mime_type:
                    extension = '.png'
                elif 'jpeg' in mime_type or 'jpg' in mime_type:
                    extension = '.jpg'
                elif 'gif' in mime_type:
                    extension = '.gif'
                elif 'svg' in mime_type:
                    extension = '.svg'
                elif 'webp' in mime_type:
                    extension = '.webp'
                else:
                    extension = '.bin'

            try:
                # 【修改点3】添加异常捕获
                image_bytes = base64.b64decode(b64data_clean)
                image_id = hashlib.md5(image_bytes).hexdigest()[:8]
                image_name = f"{image_id}{extension}"
                url = f"./{image_folder_name}/{image_name}"

                with open(os.path.join(image_folder, image_name), "wb") as f:
                    f.write(image_bytes)

                # 返回替换后的 Markdown 图片链接
                return f"![{alt_text}]({url})"
            except Exception as e:
                print(f"Warning: Failed to decode base64 image in markdown. Error: {e}")
                # 如果解码失败，返回原始匹配文本（不做替换），保证文档不丢失内容
                return match.group(0)

        modified_md_content = re.sub(pattern, unembed_base64_images, markdown)

        with open(os.path.join(temp_dir, f"{markdown_name}"), "w", encoding="utf-8") as f:
            f.write(modified_md_content)

        zip_buffer = io.BytesIO()
        folder_path = Path(temp_dir)
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file in folder_path.rglob('*'):
                if file.is_file():
                    zipf.write(file, file.relative_to(folder_path))
    return zip_buffer.getvalue()

if __name__ == '__main__':
    pass
