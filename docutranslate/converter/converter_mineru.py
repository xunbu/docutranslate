import asyncio
import logging
import time
import zipfile
import httpx
from docutranslate.converter import Converter, Document
from docutranslate.logger import global_logger
from docutranslate.utils.markdown_utils import embed_inline_image_from_zip

URL = 'https://mineru.net/api/v4/file-urls/batch'

timeout = httpx.Timeout(
    connect=5.0,      # 连接超时 (建立连接的最长时间)
    read=200.0,        # 读取超时 (等待服务器响应的最长时间)
    write=200.0,       # 写入超时 (发送数据的最长时间)
    pool=1.0          # 从连接池获取连接的超时时间
)


client = httpx.Client(trust_env=False,timeout=timeout,proxy=None,verify=False)
client_async=httpx.AsyncClient(trust_env=False,timeout=timeout,proxy=None,verify=False)

# TODO: 提供更详细的logger
class ConverterMineru(Converter):
    def __init__(self, token: str, formula=True,logger:logging.Logger|None=None):
        self.mineru_token = token.strip()
        self.formula = formula
        self.logger=logger if logger else global_logger

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
            raise Exception('apply upload url failed,reason:{}'.format(result))

    async def upload_async(self, document: Document):
        # 获取上传链接
        response = await client_async.post(URL, headers=self._get_header(), json=self._get_upload_data(document))
        response.raise_for_status()
        result = response.json()
        # print('response success. result:{}'.format(result))
        if result["code"] == 0:
            batch_id = result["data"]["batch_id"]
            urls = result["data"]["file_urls"]
            # print('batch_id:{},urls:{}'.format(batch_id, urls))
            # 获取
            res_upload = await client_async.put(urls[0], content=document.filebytes)
            res_upload.raise_for_status()
            # print(f"{urls[0]} upload success")
            return batch_id
        else:
            raise Exception('apply upload url failed,reason:{}'.format(result))

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

    async def get_file_url_async(self, batch_id: str) -> str:
        while True:
            url = f'https://mineru.net/api/v4/extract-results/batch/{batch_id}'
            header = self._get_header()
            res = await client_async.get(url, headers=header)
            res.raise_for_status()
            fileinfo = res.json()["data"]["extract_result"][0]
            if fileinfo["state"] == "done":
                fileurl = fileinfo["full_zip_url"]
                return fileurl
            else:
                await asyncio.sleep(3)

    def convert(self, document: Document) -> str:
        self.logger.info(f"正在将文档转换为markdown")
        time1 = time.time()
        batch_id = self.upload(document)
        file_url = self.get_file_url(batch_id)
        result = get_md_from_zip_url_with_inline_images(zip_url=file_url)
        self.logger.info(f"已转换为markdown，耗时{time.time() - time1}秒")
        return result

    async def convert_async(self, document: Document) -> str:
        # 待优化
        self.logger.info(f"正在将文档转换为markdown")
        time1 = time.time()
        batch_id = await self.upload_async(document)
        file_url = await self.get_file_url_async(batch_id)
        result = await get_md_from_zip_url_with_inline_images_async(zip_url=file_url)
        self.logger.info(f"已转换为markdown，耗时{time.time() - time1}秒")
        return result


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
        response = client.get(zip_url)  # 增加超时
        response.raise_for_status()
        print("ZIP文件下载完成。")
        return embed_inline_image_from_zip(response.content, filename_in_zip=filename_in_zip, encoding=encoding)


    except httpx.HTTPStatusError as e:
        raise Exception(f"HTTP 错误 (httpx): {e.response.status_code} - {e.request.url}\n响应内容: {e.response.text[:200]}...")
    except httpx.RequestError as e:
        raise Exception(f"下载ZIP文件时发生错误 (httpx): {e}")
    except zipfile.BadZipFile:
        raise Exception("错误: 下载的文件不是一个有效的ZIP压缩文件或已损坏。")
    except UnicodeDecodeError:
        raise Exception(f"错误: 无法使用 '{encoding}' 编码解码文件 '{filename_in_zip}' 的内容。")
    except Exception as e:
        import traceback
        traceback.print_exc()  # 打印完整的堆栈跟踪，便于调试
        raise Exception(f"发生未知错误: {e}")


async def get_md_from_zip_url_with_inline_images_async(
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
        response = await client_async.get(zip_url)  # 增加超时
        response.raise_for_status()
        print("ZIP文件下载完成。")
        return await asyncio.to_thread(embed_inline_image_from_zip,response.content, filename_in_zip=filename_in_zip, encoding=encoding)


    except httpx.HTTPStatusError as e:
        raise Exception(f"HTTP 错误 (httpx): {e.response.status_code} - {e.request.url}\n响应内容: {e.response.text[:200]}...")
    except httpx.RequestError as e:
        raise Exception(f"下载ZIP文件时发生错误 (httpx): {e}")
    except zipfile.BadZipFile:
        raise Exception("错误: 下载的文件不是一个有效的ZIP压缩文件或已损坏。")
    except UnicodeDecodeError:
        raise Exception(f"错误: 无法使用 '{encoding}' 编码解码文件 '{filename_in_zip}' 的内容。")
    except Exception as e:
        import traceback
        traceback.print_exc()  # 打印完整的堆栈跟踪，便于调试
        raise Exception(f"发生未知错误: {e}")

if __name__ == '__main__':
    pass
