import base64
import io
import mimetypes
import os
import re
import threading
import uuid
import zipfile


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
        mask_dict.set(id, match.group(2))
        return f"{match.group(1)}(<ph-{id}>)"

    uri_pattern = r'(!?\[.*?\])\((.*?)\)'
    markdown = re.sub(uri_pattern, uri2placeholder, markdown)
    return markdown


def placeholder2_uris(markdown: str, mask_dict: MaskDict):
    def placeholder2uri(match: re.Match):
        id = match.group(1)
        uri = mask_dict.get(id)
        if uri is None:
            return match.group()
        return uri

    ph_pattern = r"<ph-([a-zA-Z0-9]+)>"
    markdown = re.sub(ph_pattern, placeholder2uri, markdown)
    return markdown


def embed_inline_image_from_zip(zip_bytes: bytes, filename_in_zip: str, encoding="utf-8"):
    zip_file_bytes = io.BytesIO(zip_bytes)

    print(f"正在尝试打开内存中的ZIP存档...")
    with zipfile.ZipFile(zip_file_bytes, 'r') as archive:
        print(f"ZIP存档已打开。正在查找文件 '{filename_in_zip}'...")

        if filename_in_zip not in archive.namelist():
            print(f"错误: 文件 '{filename_in_zip}' 在ZIP压缩包中未找到。")
            print(f"压缩包中的可用文件列表: {archive.namelist()}")
            return None

        md_content_bytes = archive.read(filename_in_zip)
        print(f"文件 '{filename_in_zip}' 已找到并读取。")
        md_content_text = md_content_bytes.decode(encoding)
        print(f"文件内容已使用 '{encoding}' 编码成功解码。")

        # --- 新增：处理图片 ---
        print("开始处理Markdown中的图片...")
        # 获取Markdown文件在ZIP包内的基本目录，用于解析相对图片路径
        # 例如，如果 filename_in_zip 是 "docs/guide/full.md", base_md_path_in_zip 是 "docs/guide"
        # 如果 filename_in_zip 是 "full.md", base_md_path_in_zip 是 ""
        base_md_path_in_zip = os.path.dirname(filename_in_zip)

        def replace_image_with_base64(match):
            alt_text = match.group(1)
            original_image_path = match.group(2)

            # 检查是否是外部链接或已经是data URI
            if original_image_path.startswith(('http://', 'https://', 'data:')):
                print(f"  跳过外部或已内联图片: {original_image_path}")
                return match.group(0)  # 返回原始匹配

            # 构建图片在ZIP文件中的绝对路径
            # os.path.join 会正确处理 base_md_path_in_zip 为空字符串的情况
            image_path_in_zip = os.path.join(base_md_path_in_zip, original_image_path)
            # zipfile 使用正斜杠，并且路径是相对于zip根目录的，os.path.normpath确保路径格式正确
            image_path_in_zip = os.path.normpath(image_path_in_zip).replace(os.sep, '/')

            # 确保路径不是以 './' 开头，如果filename_in_zip在根目录且图片路径也是相对的
            if image_path_in_zip.startswith('./'):
                image_path_in_zip = image_path_in_zip[2:]

            # print(f"  尝试内联图片: '{original_image_path}' (解析为ZIP内路径: '{image_path_in_zip}')")

            try:
                image_bytes = archive.read(image_path_in_zip)

                # 猜测MIME类型
                mime_type, _ = mimetypes.guess_type(image_path_in_zip)
                if not mime_type:
                    # 备用：根据扩展名手动判断一些常见类型
                    ext = os.path.splitext(image_path_in_zip)[1].lower()
                    if ext == '.png':
                        mime_type = 'image/png'
                    elif ext in ['.jpg', '.jpeg']:
                        mime_type = 'image/jpeg'
                    elif ext == '.gif':
                        mime_type = 'image/gif'
                    elif ext == '.svg':
                        mime_type = 'image/svg+xml'
                    elif ext == '.webp':
                        mime_type = 'image/webp'
                    else:
                        print(f"    警告: 无法确定图片 '{image_path_in_zip}' 的MIME类型。跳过内联。")
                        return match.group(0)  # 返回原始匹配

                base64_encoded_data = base64.b64encode(image_bytes).decode('utf-8')
                new_image_tag = f"![{alt_text}](data:{mime_type};base64,{base64_encoded_data})"
                # print(f"    成功内联图片: {original_image_path} -> data:{mime_type[:20]}...")
                return new_image_tag
            except KeyError:
                print(f"    警告: 图片 '{image_path_in_zip}' 在ZIP压缩包中未找到。原始链接将被保留。")
                return match.group(0)  # 图片不在zip中，返回原始匹配
            except Exception as e_img:
                print(f"    错误: 处理图片 '{image_path_in_zip}' 时发生错误: {e_img}。原始链接将被保留。")
                return match.group(0)

        # 正则表达式查找Markdown图片: ![alt text](path/to/image.ext)
        # 修改了正则表达式，使其不贪婪地匹配alt文本和路径
        image_regex = r"!\[(.*?)\]\((.*?)\)"
        modified_md_content = re.sub(image_regex, replace_image_with_base64, md_content_text)

        print("图片处理完成。")
        return modified_md_content


if __name__ == '__main__':
    pass
