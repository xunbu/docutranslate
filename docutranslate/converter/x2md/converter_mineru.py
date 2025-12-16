# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0

import asyncio
import time
import zipfile
import io
from dataclasses import dataclass
from typing import Hashable, Literal, List, Tuple

import httpx

# 尝试导入 pypdf，用于处理 PDF 拆分
try:
    from pypdf import PdfReader, PdfWriter

    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False

from docutranslate.converter.x2md.base import X2MarkdownConverter, X2MarkdownConverterConfig
from docutranslate.ir.attachment_manager import AttachMent
from docutranslate.ir.document import Document
from docutranslate.ir.markdown_document import MarkdownDocument
from docutranslate.utils.markdown_utils import embed_inline_image_from_zip

URL = 'https://mineru.net/api/v4/file-urls/batch'


@dataclass(kw_only=True)
class ConverterMineruConfig(X2MarkdownConverterConfig):
    mineru_token: str
    formula_ocr: bool = True
    model_version: Literal["pipeline", "vlm"] = "vlm"

    def gethash(self) -> Hashable:
        return self.formula_ocr, self.model_version


timeout = httpx.Timeout(
    connect=5.0,  # 连接超时 (建立连接的最长时间)
    read=200.0,  # 读取超时 (等待服务器响应的最长时间)
    write=200.0,  # 写入超时 (发送数据的最长时间)
    pool=1.0  # 从连接池获取连接的超时时间
)

limits = httpx.Limits(max_connections=500, max_keepalive_connections=20)
client = httpx.Client(limits=limits, trust_env=False, timeout=timeout, proxy=None, verify=False)
client_async = httpx.AsyncClient(limits=limits, trust_env=False, timeout=timeout, proxy=None, verify=False)


class ConverterMineru(X2MarkdownConverter):
    def __init__(self, config: ConverterMineruConfig):
        super().__init__(config=config)
        self.mineru_token = config.mineru_token.strip()
        self.formula = config.formula_ocr
        self.model_version = config.model_version
        self.attachments: list[AttachMent] = []
        self.max_pages = 600  # Mineru 的限制

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
            "model_version": self.model_version,
            "files": [
                {"name": f"{document.name}", "is_ocr": True}
            ]
        }

    def _split_pdf(self, content: bytes) -> List[bytes]:
        """
        检查 PDF 页数，如果超过限制则进行拆分。
        返回拆分后的 bytes 列表。如果不超限，返回包含原内容的单元素列表。
        """
        if not HAS_PYPDF:
            self.logger.warning("未安装 pypdf，无法进行 PDF 页数检查和拆分。如果文件超过 600 页可能会失败。")
            return [content]

        try:
            reader = PdfReader(io.BytesIO(content))
            total_pages = len(reader.pages)

            if total_pages <= self.max_pages:
                return [content]

            self.logger.info(f"PDF 页数 ({total_pages}) 超过限制 ({self.max_pages})，正在进行拆分...")
            chunks = []

            for i in range(0, total_pages, self.max_pages):
                writer = PdfWriter()
                end_page = min(i + self.max_pages, total_pages)

                for page_num in range(i, end_page):
                    writer.add_page(reader.pages[page_num])

                with io.BytesIO() as output_stream:
                    writer.write(output_stream)
                    chunks.append(output_stream.getvalue())

            self.logger.info(f"PDF 已拆分为 {len(chunks)} 个部分。")
            return chunks

        except Exception as e:
            self.logger.error(f"PDF 拆分失败: {e}")
            # 如果拆分出错，尝试按原文件上传（兜底）
            return [content]

    def upload(self, document: Document):
        # 获取上传链接
        response = client.post(URL, headers=self._get_header(), json=self._get_upload_data(document))
        response.raise_for_status()
        result = response.json()
        if result["code"] == 0:
            batch_id = result["data"]["batch_id"]
            urls = result["data"]["file_urls"]
            # 获取
            res_upload = client.put(urls[0], content=document.content)
            res_upload.raise_for_status()
            return batch_id
        else:
            raise Exception('apply upload url failed,reason:{}'.format(result))

    async def upload_async(self, document: Document):
        # 获取上传链接
        response = await client_async.post(URL, headers=self._get_header(), json=self._get_upload_data(document))
        response.raise_for_status()
        result = response.json()
        if result["code"] == 0:
            batch_id = result["data"]["batch_id"]
            urls = result["data"]["file_urls"]
            # 获取
            res_upload = await client_async.put(urls[0], content=document.content)
            res_upload.raise_for_status()
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
                file_url = fileinfo["full_zip_url"]
                return file_url
            elif fileinfo["state"] == "failed":
                raise Exception(f"Mineru 处理失败: {fileinfo.get('message', 'Unknown error')}")
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
                file_url = fileinfo["full_zip_url"]
                return file_url
            elif fileinfo["state"] == "failed":
                raise Exception(f"Mineru 处理失败: {fileinfo.get('message', 'Unknown error')}")
            else:
                await asyncio.sleep(3)

    def _process_single_chunk(self, content: bytes, original_doc: Document, index: int = 0) -> Tuple[str, bytes]:
        """
        处理单个分片：构造Document -> 上传 -> 等待 -> 下载 -> 提取 Markdown
        """
        # 根据 Document 类的定义，name 是属性，由 stem+suffix 组成
        # 所以我们需要构造正确的 stem 来改变文件名
        new_stem = original_doc.stem
        if index > 0:
            new_stem = f"{original_doc.stem}_part{index}"

        chunk_doc = Document.from_bytes(content=content, suffix=original_doc.suffix, stem=new_stem)

        batch_id = self.upload(chunk_doc)
        file_url = self.get_file_url(batch_id)
        md_content, mineru_parsed = get_md_from_zip_url_with_inline_images(zip_url=file_url)
        return md_content, mineru_parsed

    async def _process_single_chunk_async(self, content: bytes, original_doc: Document, index: int = 0) -> Tuple[
        str, bytes]:
        """
        异步处理单个分片
        """
        new_stem = original_doc.stem
        if index > 0:
            new_stem = f"{original_doc.stem}_part{index}"

        chunk_doc = Document.from_bytes(content=content, suffix=original_doc.suffix, stem=new_stem)

        batch_id = await self.upload_async(chunk_doc)
        file_url = await self.get_file_url_async(batch_id)
        md_content, mineru_parsed = await get_md_from_zip_url_with_inline_images_async(zip_url=file_url)
        return md_content, mineru_parsed

    def convert(self, document: Document) -> MarkdownDocument:
        self.logger.info(f"正在将文档转换为markdown,model_version:{self.model_version}")
        time1 = time.time()

        # 1. 检查是否需要拆分 (仅针对 PDF)
        chunks = [document.content]
        is_split = False
        if document.suffix.lower() == '.pdf':
            chunks = self._split_pdf(document.content)
            if len(chunks) > 1:
                is_split = True

        combined_md = []

        # 2. 依次处理每个分片
        for i, chunk_content in enumerate(chunks):
            if is_split:
                self.logger.info(f"正在处理分片 {i + 1}/{len(chunks)}...")

            md_content, mineru_parsed = self._process_single_chunk(chunk_content, document, i)
            combined_md.append(md_content)

            # 保存对应的原始解析包
            suffix_name = "" if not is_split else f"_part{i + 1}"
            if mineru_parsed:
                self.attachments.append(
                    AttachMent(f"mineru{suffix_name}",
                               Document.from_bytes(content=mineru_parsed, suffix=".zip", stem=f"mineru{suffix_name}"))
                )

        # 3. 合并 Markdown
        final_content = "\n\n".join(combined_md)

        self.logger.info(f"已转换为markdown，耗时{time.time() - time1}秒")
        md_document = MarkdownDocument.from_bytes(content=final_content.encode("utf-8"), suffix=".md",
                                                  stem=document.stem)
        return md_document

    async def convert_async(self, document: Document) -> MarkdownDocument:
        self.logger.info(f"正在将文档转换为markdown (Async), model_version:{self.model_version}")
        time1 = time.time()

        # 1. 检查是否需要拆分
        chunks = [document.content]
        is_split = False
        if document.suffix.lower() == '.pdf':
            # 这里的拆分操作是 CPU 密集型，如果是超大 PDF，建议放到 thread pool 中运行
            # chunks = await asyncio.to_thread(self._split_pdf, document.content)
            chunks = self._split_pdf(document.content)
            if len(chunks) > 1:
                is_split = True

        # 2. 并发处理所有分片
        tasks = []
        for i, chunk_content in enumerate(chunks):
            tasks.append(self._process_single_chunk_async(chunk_content, document, i))

        # 等待所有分片处理完成
        results = await asyncio.gather(*tasks)

        combined_md = []
        for i, (md_content, mineru_parsed) in enumerate(results):
            combined_md.append(md_content)

            suffix_name = "" if not is_split else f"_part{i + 1}"
            if mineru_parsed:
                self.attachments.append(
                    AttachMent(f"mineru{suffix_name}",
                               Document.from_bytes(content=mineru_parsed, suffix=".zip", stem=f"mineru{suffix_name}"))
                )

        # 3. 合并 Markdown
        final_content = "\n\n".join(combined_md)

        self.logger.info(f"已转换为markdown，耗时{time.time() - time1}秒")
        md_document = MarkdownDocument.from_bytes(content=final_content.encode("utf-8"), suffix=".md",
                                                  stem=document.stem)
        return md_document

    def support_format(self) -> list[str]:
        return [".pdf", ".doc", ".docx", ".ppt", ".pptx", ".png", ".jpg", ".jpeg"]


def get_md_from_zip_url_with_inline_images(
        zip_url: str,
        filename_in_zip: str = "full.md",
        encoding: str = "utf-8"
) -> tuple[str, bytes]:
    """
    从给定的ZIP文件URL中下载并提取指定文件的内容，
    并将Markdown文件中的相对路径图片转换为内联Base64图片。
    """
    try:
        # print(f"正在从 {zip_url} 下载ZIP文件 (使用 httpx.get)...")
        response = client.get(zip_url)  # 增加超时
        response.raise_for_status()
        # print("ZIP文件下载完成。")
        return embed_inline_image_from_zip(response.content, filename_in_zip=filename_in_zip,
                                           encoding=encoding), response.content


    except httpx.HTTPStatusError as e:
        raise Exception(
            f"HTTP 错误 (httpx): {e.response.status_code} - {e.request.url}\n响应内容: {e.response.text[:200]}...")
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
) -> tuple[str, bytes]:
    """
    从给定的ZIP文件URL中下载并提取指定文件的内容，
    并将Markdown文件中的相对路径图片转换为内联Base64图片。
    """
    try:
        # print(f"正在从 {zip_url} 下载ZIP文件 (使用 httpx.get)...")
        response = await client_async.get(zip_url)  # 增加超时
        response.raise_for_status()
        # print("ZIP文件下载完成。")
        return await asyncio.to_thread(embed_inline_image_from_zip, response.content, filename_in_zip=filename_in_zip,
                                       encoding=encoding), response.content


    except httpx.HTTPStatusError as e:
        raise Exception(
            f"HTTP 错误 (httpx): {e.response.status_code} - {e.request.url}\n响应内容: {e.response.text[:200]}...")
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