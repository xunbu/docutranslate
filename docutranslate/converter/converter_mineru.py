import asyncio
import base64
import io
import mimetypes
import os
import re
import time
import zipfile
import httpx
from docutranslate.converter import Converter, Document
from docutranslate.logger import translater_logger

URL = 'https://mineru.net/api/v4/file-urls/batch'

client=httpx.Client(trust_env=False)

#TODO: 提供更详细的logger
class ConverterMineru(Converter):
    def __init__(self, token: str, formula=True):
        self.mineru_token = token.strip()
        self.client_async = httpx.AsyncClient()
        self.formula = formula

    def _get_header(self):
        return {
            'Content-Type': 'application/json',
            "Authorization": f"Bearer {self.mineru_token}"
        }

    def _get_upload_data(self, document: Document):
        return {
            "enable_formula": self.formula,
            "language": "auto",
            "enable_table": True,
            "files": [
                {"name": f"{document.filename}", "is_ocr": True}
            ]
        }

    def upload(self, document: Document):
        # 获取上传链接
        response = client.post(URL, headers=self._get_header(), json=self._get_upload_data(document))
        response.raise_for_status()
        result = response.json()
        # print('response success. result:{}'.format(result))
        if result["code"] == 0:
            batch_id = result["data"]["batch_id"]
            urls = result["data"]["file_urls"]
            # print('batch_id:{},urls:{}'.format(batch_id, urls))
            # 获取
            res_upload = client.put(urls[0], content=document.filebytes)
            res_upload.raise_for_status()
            # print(f"{urls[0]} upload success")
            return batch_id
        else:
            raise Exception('apply upload url failed,reason:{}'.format(result.msg))

    def get_file_url(self, batch_id: str) -> str:
        while True:
            url = f'https://mineru.net/api/v4/extract-results/batch/{batch_id}'
            header = self._get_header()
            res = client.get(url, headers=header)
            res.raise_for_status()
            fileinfo = res.json()["data"]["extract_result"][0]
            if fileinfo["state"] == "done":
                fileurl = fileinfo["full_zip_url"]
                return fileurl
            else:
                time.sleep(3)

    def convert(self, document: Document) -> str:
        translater_logger.info(f"正在将文档转换为markdown")
        time1=time.time()
        batch_id = self.upload(document)
        file_url = self.get_file_url(batch_id)
        result=get_md_from_zip_url_with_inline_images(zip_url=file_url)
        translater_logger.info(f"已转换为markdown，耗时{time.time()-time1}秒")
        return result

    # TODO: 实现细粒度更高的协程
    async def convert_async(self, document: Document) -> str:
        # 待优化
        return await asyncio.to_thread(
            self.convert,
            document
        )


def get_md_from_zip_url_with_inline_images(
        zip_url: str,
        filename_in_zip: str = "full.md",
        encoding: str = "utf-8"
) -> str | None:
    """
    从给定的ZIP文件URL中下载并提取指定文件的内容，
    并将Markdown文件中的相对路径图片转换为内联Base64图片。

    Args:
        zip_url (str): ZIP文件的下载链接。
        filename_in_zip (str): ZIP压缩包内目标Markdown文件的名称（包括路径）。
                               默认为 "full.md"。
        encoding (str): 目标文件的预期编码。默认为 "utf-8"。

    Returns:
        str | None: 如果成功，返回处理后的Markdown文本内容；否则返回 None。
    """
    try:
        print(f"正在从 {zip_url} 下载ZIP文件 (使用 httpx.get)...")
        response = client.get(zip_url, timeout=60.0)  # 增加超时
        response.raise_for_status()
        print("ZIP文件下载完成。")

        zip_file_bytes = io.BytesIO(response.content)

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

    except httpx.HTTPStatusError as e:
        print(f"HTTP 错误 (httpx): {e.response.status_code} - {e.request.url}")
        print(f"响应内容: {e.response.text[:200]}...")
        return None
    except httpx.RequestError as e:
        print(f"下载ZIP文件时发生错误 (httpx): {e}")
        return None
    except zipfile.BadZipFile:
        print("错误: 下载的文件不是一个有效的ZIP压缩文件或已损坏。")
        return None
    except UnicodeDecodeError:
        print(f"错误: 无法使用 '{encoding}' 编码解码文件 '{filename_in_zip}' 的内容。")
        print("请尝试其他编码，如 'gbk', 'latin1' 等，或确认文件本身的编码。")
        return None
    except Exception as e:
        print(f"发生未知错误: {e}")
        import traceback
        traceback.print_exc()  # 打印完整的堆栈跟踪，便于调试
        return None


if __name__ == '__main__':
    pass
