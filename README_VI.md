<p align="center">
<img src="./DocuTranslate.png" alt="Project Logo" style="width: 150px">
</p>

<h1 align="center">DocuTranslate</h1>

<p align="center">
  <a href="https://github.com/xunbu/docutranslate/stargazers"><img src="https://img.shields.io/github/stars/xunbu/docutranslate?style=flat-square&logo=github&color=blue" alt="GitHub stars"></a>
  <a href="https://github.com/xunbu/docutranslate/releases"><img src="https://img.shields.io/github/downloads/xunbu/docutranslate/total?logo=github&style=flat-square" alt="GitHub Downloads"></a>
  <a href="https://pypi.org/project/docutranslate/"><img src="https://img.shields.io/pypi/v/docutranslate?style=flat-square" alt="PyPI version"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white&style=flat-square" alt="Python Version"></a>
  <a href="./LICENSE"><img src="https://img.shields.io/github/license/xunbu/docutranslate?style=flat-square" alt="License"></a>
</p>

<p align="center">
  <a href="/README_ZH.md"><strong>简体中文</strong></a> / <a href="/README.md"><strong>English</strong></a> / <a href="/README_JP.md"><strong>日本語</strong></a> / <a href="/README_VI.md"><strong>Tiếng Việt</strong></a>
</p>

<p align="center">
Một công cụ dịch thuật tệp tin cục bộ gọn nhẹ dựa trên các Mô hình Ngôn ngữ Lớn (LLM).
</p>

* ✅ **Hỗ trợ Đa định dạng**: Dịch các file `pdf`, `docx`, `xlsx`, `md`, `txt`, `json`, `epub`, `srt`, `ass`, và nhiều hơn nữa.
* ✅ **Tự động Tạo Thuật ngữ (Glossary)**: Hỗ trợ tự động tạo bảng thuật ngữ để đảm bảo sự đồng nhất về thuật ngữ.
* ✅ **Nhận dạng Bảng, Công thức, Mã trong PDF**: Tận dụng các công cụ phân tích PDF như `docling` và `mineru` để nhận dạng và dịch các bảng, công thức và mã code thường thấy trong các bài báo học thuật.
* ✅ **Dịch thuật JSON**: Hỗ trợ chỉ định các giá trị cần dịch trong JSON bằng đường dẫn (sử dụng cú pháp `jsonpath-ng`).
* ✅ **Bảo toàn Định dạng Word/Excel**: Hỗ trợ file `docx` và `xlsx` (hiện chưa hỗ trợ `doc` hoặc `xls`) trong khi vẫn giữ nguyên định dạng gốc.
* ✅ **Hỗ trợ Đa Nền tảng AI**: Hỗ trợ hầu hết các nền tảng AI, cho phép dịch thuật AI đồng thời hiệu suất cao với các prompt tùy chỉnh.
* ✅ **Hỗ trợ Bất đồng bộ (Async)**: Được thiết kế cho các kịch bản hiệu suất cao, cung cấp hỗ trợ bất đồng bộ đầy đủ và các giao diện cho đa nhiệm song song.
* ✅ **Hỗ trợ Mạng LAN & Đa người dùng**: Hỗ trợ sử dụng đồng thời bởi nhiều người dùng trong cùng một mạng cục bộ (LAN).
* ✅ **Giao diện Web Tương tác**: Cung cấp sẵn Giao diện Web (Web UI) và RESTful API để dễ dàng tích hợp và sử dụng.
* ✅ **Các gói Portable Gọn nhẹ**: Các gói portable cho Windows và Mac dưới 40MB (các phiên bản không sử dụng `docling` để phân tích PDF cục bộ).

> Khi dịch `pdf`, tệp sẽ được chuyển đổi sang markdown trước. Điều này sẽ làm **mất** bố cục gốc. Người dùng có yêu cầu khắt khe về bố cục nên lưu ý điều này.

> Nhóm Cộng đồng QQ: 1047781902 1081128602

**Giao diện UI**:
![UI Interface](/images/UI界面.png)

**Dịch thuật Bài báo/Giấy tờ**:
![Paper Translation](/images/论文翻译.png)

**Dịch thuật Tiểu thuyết**:
![Novel Translation](/images/小说翻译.png)

## Các Gói Tích hợp

Dành cho những người dùng muốn bắt đầu nhanh chóng, chúng tôi cung cấp các gói tích hợp trên [GitHub Releases](https://github.com/xunbu/docutranslate/releases). Chỉ cần tải xuống, giải nén và nhập API-Key nền tảng AI của bạn để bắt đầu sử dụng.

* **DocuTranslate**: Phiên bản tiêu chuẩn. Sử dụng `minerU` (online hoặc triển khai cục bộ) để phân tích PDF. Hỗ trợ gọi API minerU cục bộ. (Được khuyến nghị)
* **DocuTranslate_full**: Phiên bản đầy đủ. Bao gồm công cụ phân tích PDF cục bộ tích hợp sẵn là `docling`. Chọn phiên bản này nếu bạn cần phân tích PDF offline mà không cần minerU.

## Bắt đầu Nhanh chóng

### Sử dụng pip

```bash
# Cài đặt cơ bản
pip install docutranslate

# Cài đặt phần mở rộng mcp
pip install docutranslate[mcp]

# Cài đặt phần mở rộng docling
pip install docutranslate[docling]

docutranslate -i

#docutranslate -i --with-mcp
```

### Sử dụng uv

```bash
# Khởi tạo môi trường
uv init

# Cài đặt cơ bản
uv add docutranslate

# Cài đặt phần mở rộng mcp
uv add docutranslate[mcp]

# Cài đặt phần mở rộng docling
uv add docutranslate[docling]

uv run --no-dev docutranslate -i

#uv run --no-dev docutranslate -i --with-mcp
```

### Sử dụng git

```bash
# Khởi tạo môi trường
git clone https://github.com/xunbu/docutranslate.git

cd docutranslate

uv sync --no-dev
# uv sync --no-dev --extra mcp
# uv sync --no-dev --extra docling
# uv sync --no-dev --all-extras

```

### Sử dụng docker

```bash
docker run -d -p 8010:8010 xunbu/docutranslate:latest #không hỗ trợ docling
# docker run -it -p 8010:8010 xunbu/docutranslate:latest
# docker run -it -p 8010:8010 xunbu/docutranslate:v1.5.4
```

## Khởi chạy Web UI và Dịch vụ API

Để thuận tiện cho việc sử dụng, DocuTranslate cung cấp Giao diện Web đầy đủ chức năng và RESTful API.

**Khởi chạy Dịch vụ:**

```bash
  docutranslate -i                           (Khởi chạy GUI, truy cập cục bộ mặc định)
  docutranslate -i --host 0.0.0.0            (Cho phép truy cập từ các thiết bị khác trên LAN)
  docutranslate -i -p 8081                   (Chỉ định số cổng)
  docutranslate -i --cors                    (Bật cài đặt CORS mặc định)
  docutranslate -i --with-mcp                (Khởi chạy GUI cùng với endpoint MCP SSE, chia sẻ hàng đợi, chia sẻ cổng)
  docutranslate --mcp                         (Khởi chạy máy chủ MCP, chế độ stdio)
  docutranslate --mcp --transport sse         (Khởi chạy máy chủ MCP, chế độ SSE)
  docutranslate --mcp --transport sse --mcp-host MCP_HOST   --mcp-port MCP_PORT  (Khởi chạy máy chủ MCP, chế độ SSE)
  docutranslate --mcp --transport streamable-http  (Khởi chạy máy chủ MCP, chế độ Streamable HTTP)
```

* **Giao diện Tương tác**: Sau khi khởi chạy dịch vụ, vui lòng truy cập `http://127.0.0.1:8010` (hoặc cổng bạn đã chỉ định) trên trình duyệt.
* **Tài liệu API**: Tài liệu API đầy đủ (Swagger UI) nằm tại `http://127.0.0.1:8010/docs`.
* MCP: Endpoint dịch vụ SSE nằm tại `http://127.0.0.1:8010/mcp/sse` (khởi chạy với --with-mcp) hoặc `http://127.0.0.1:8000/mcp/sse` (khởi chạy với --mcp)

## Ví dụ Sử dụng

### Sử dụng Client SDK Đơn giản (Được khuyến nghị)

Cách dễ nhất để bắt đầu là sử dụng lớp `Client`, cung cấp một API đơn giản và trực quan cho việc dịch thuật:

```python
from docutranslate.sdk import Client

# Khởi tạo client với cài đặt nền tảng AI của bạn
client = Client(
    api_key="YOUR_OPENAI_API_KEY",  # hoặc bất kỳ API key nền tảng AI nào khác
    base_url="https://api.openai.com/v1/",
    model_id="gpt-4o",
    to_lang="Chinese", # Ngôn ngữ đích
    concurrent=10,  # Số lượng yêu cầu đồng thời
)

# Ví dụ 1: Dịch các tệp văn bản thuần túy (không cần công cụ phân tích PDF)
result = client.translate("path/to/your/document.txt")
print(f"Dịch hoàn tất! Đã lưu tại: {result.save()}")

# Ví dụ 2: Dịch tệp PDF (yêu cầu mineru_token hoặc triển khai cục bộ)
# Tùy chọn A: Sử dụng MinerU online (yêu cầu token: https://mineru.net/apiManage/token)
result = client.translate(
    "path/to/your/document.pdf",
    convert_engine="mineru",
    mineru_token="YOUR_MINERU_TOKEN",  # Thay thế bằng MinerU Token của bạn
    formula_ocr=True,  # Bật nhận dạng công thức
)
result.save(fmt="html")

# Tùy chọn B: Sử dụng MinerU triển khai cục bộ (khuyên dùng cho mạng nội bộ/offline)
# Đầu tiên khởi chạy dịch vụ MinerU cục bộ, tham khảo: https://github.com/opendatalab/MinerU
result = client.translate(
    "path/to/your/document.pdf",
    convert_engine="mineru_deploy",
    mineru_deploy_base_url="http://127.0.0.1:8000",  # Địa chỉ MinerU cục bộ của bạn
    mineru_deploy_backend="hybrid-auto-engine",  # Loại backend
)
result.save(fmt="markdown")

# Ví dụ 3: Dịch tệp Docx (giữ nguyên định dạng)
result = client.translate(
    "path/to/your/document.docx",
    insert_mode="replace",  # replace (thay thế)/append (thêm vào sau)/prepend (thêm vào trước)
)
result.save(fmt="docx")  # Lưu dưới định dạng docx

# Ví dụ 4: Xuất dưới dạng chuỗi mã hóa base64 (để truyền qua API)
base64_content = result.export(fmt="html")
print(f"Độ dài nội dung đã xuất: {len(base64_content)}")

# Bạn cũng có thể truy cập workflow bên dưới để thực hiện các thao tác nâng cao
# workflow = result.workflow
```

**Các tính năng của Client:**

* **Tự động phát hiện**: Tự động phát hiện loại tệp và chọn workflow phù hợp
* **Cấu hình linh hoạt**: Ghi đè bất kỳ cài đặt mặc định nào cho mỗi lần gọi dịch
* **Nhiều tùy chọn đầu ra**: Lưu vào đĩa hoặc xuất dưới dạng chuỗi Base64
* **Hỗ trợ Bất đồng bộ**: Sử dụng `translate_async()` cho các tác vụ dịch đồng thời

#### Tham số Client SDK

| Tham số | Loại | Mặc định | Mô tả |
| --- | --- | --- | --- |
| **api_key** | `str` | - | API key nền tảng AI |
| **base_url** | `str` | - | Base URL nền tảng AI (ví dụ: `https://api.openai.com/v1/`) |
| **model_id** | `str` | - | ID Model sử dụng để dịch |
| **to_lang** | `str` | - | Ngôn ngữ đích (ví dụ: `"Chinese"`, `"English"`, `"Japanese"`) |
| **concurrent** | `int` | 10 | Số lượng yêu cầu LLM đồng thời |
| **convert_engine** | `str` | `"mineru"` | Công cụ phân tích PDF: `"mineru"`, `"docling"`, `"mineru_deploy"` |
| **md2docx_engine** | `str` | `"auto"` | Công cụ chuyển đổi Markdown sang Docx: `"python"` (Python thuần), `"pandoc"` (sử dụng Pandoc), `"auto"` (sử dụng Pandoc nếu đã cài đặt, nếu không thì dùng Python), `null` (không tạo docx) |
| **mineru_deploy_base_url** | `str` | - | Địa chỉ API minerU cục bộ (khi dùng `convert_engine="mineru_deploy"`) |
| **mineru_deploy_parse_method** | `str` | `"auto"` | Phương pháp phân tích minerU cục bộ: `"auto"`, `"txt"`, `"ocr"` |
| **mineru_deploy_table_enable** | `bool` | `True` | Bật nhận dạng bảng cho minerU cục bộ |
| **mineru_token** | `str` | - | Token API minerU (khi sử dụng minerU online) |
| **skip_translate** | `bool` | `False` | Bỏ qua dịch thuật, chỉ phân tích tài liệu |
| **output_dir** | `str` | `"./output"` | Thư mục đầu ra mặc định cho `save()` |
| **chunk_size** | `int` | 3000 | Kích thước đoạn văn bản (chunk) để LLM xử lý |
| **temperature** | `float` | 0.3 | Tham số temperature của LLM |
| **timeout** | `int` | 60 | Thời gian chờ yêu cầu tính bằng giây |
| **retry** | `int` | 3 | Số lần thử lại khi thất bại |
| **provider** | `str` | `"auto"` | Loại nhà cung cấp AI (auto, openai, azure, v.v.) |
| **force_json** | `bool` | `False` | Bắt buộc chế độ đầu ra JSON |
| **rpm** | `int` | - | Giới hạn số yêu cầu mỗi phút |
| **tpm** | `int` | - | Giới hạn số token mỗi phút |
| **extra_body** | `str` | - | Tham số body yêu cầu bổ sung ở định dạng chuỗi JSON, sẽ được hợp nhất vào yêu cầu API |
| **thinking** | `str` | `"auto"` | Chế độ suy nghĩ: `"auto"`, `"none"`, `"block"` |
| **custom_prompt** | `str` | - | Prompt tùy chỉnh cho dịch thuật |
| **system_proxy_enable** | `bool` | `False` | Bật proxy hệ thống |
| **insert_mode** | `str` | `"replace"` | Chế độ chèn Docx/Xlsx/Txt: `"replace"`, `"append"`, `"prepend"` |
| **separator** | `str` | `"\n"` | Dấu phân cách văn bản cho chế độ append/prepend |
| **segment_mode** | `str` | `"line"` | Chế độ phân đoạn: `"line"`, `"paragraph"`, `"none"` |
| **translate_regions** | `list` | - | Vùng dịch Excel (ví dụ: `"Sheet1!A1:B10"`) |
| **model_version** | `str` | `"vlm"` | Phiên bản model MinerU: `"pipeline"`, `"vlm"` |
| **formula_ocr** | `bool` | `True` | Bật nhận dạng công thức OCR khi phân tích PDF |
| **code_ocr** | `bool` | `True` | Bật nhận dạng mã OCR khi phân tích PDF |
| **mineru_deploy_backend** | `str` | `"hybrid-auto-engine"` | Backend MinerU cục bộ: `"pipeline"`, `"vlm-auto-engine"`, `"vlm-http-client"`, `"hybrid-auto-engine"`, `"hybrid-http-client"` |
| **mineru_deploy_formula_enable** | `bool` | `True` | Bật nhận dạng công thức cho MinerU cục bộ |
| **mineru_deploy_start_page_id** | `int` | 0 | ID trang bắt đầu phân tích MinerU cục bộ |
| **mineru_deploy_end_page_id** | `int` | 99999 | ID trang kết thúc phân tích MinerU cục bộ |
| **mineru_deploy_lang_list** | `list` | - | Danh sách ngôn ngữ phân tích MinerU cục bộ |
| **mineru_deploy_server_url** | `str` | - | URL máy chủ MinerU cục bộ |
| **json_paths** | `list` | - | Biểu thức JSONPath cho dịch JSON (ví dụ: `"$.data.*"`) |
| **glossary_generate_enable** | `bool` | - | Bật tự động tạo bảng thuật ngữ |
| **glossary_dict** | `dict` | - | Từ điển thuật ngữ (ví dụ: `{"Jobs": "Steve Jobs"}`) |
| **glossary_agent_config** | `dict` | - | Cấu hình agent thuật ngữ |

#### Các phương thức Kết quả (Result Methods)

| Phương thức | Tham số | Mô tả |
| --- | --- | --- |
| **save()** | `output_dir`, `name`, `fmt` | Lưu kết quả dịch vào đĩa |
| **export()** | `fmt` | Xuất dưới dạng chuỗi mã hóa Base64 |
| **supported_formats** | - | Lấy danh sách các định dạng đầu ra được hỗ trợ |
| **workflow** | - | Truy cập đối tượng workflow bên dưới |

```python
import asyncio
from docutranslate.sdk import Client

async def translate_multiple():
    client = Client(
        api_key="YOUR_API_KEY",
        base_url="https://api.openai.com/v1/",
        model_id="gpt-4o",
        to_lang="Chinese",
    )

    # Dịch nhiều file đồng thời
    files = ["doc1.pdf", "doc2.docx", "notes.txt"]
    results = await asyncio.gather(
        *[client.translate_async(f) for f in files]
    )

    for r in results:
        print(f"Đã lưu: {r.save()}")

asyncio.run(translate_multiple())

```

### Sử dụng Workflow API (Để Kiểm soát Nâng cao)

Để kiểm soát nhiều hơn, hãy sử dụng trực tiếp Workflow API. Mỗi workflow tuân theo cùng một mẫu:

```python
# Mẫu:
# 1. Tạo TranslatorConfig (cài đặt LLM)
# 2. Tạo WorkflowConfig (cài đặt workflow)
# 3. Tạo instance Workflow
# 4. workflow.read_path(file)
# 5. await workflow.translate_async()
# 6. workflow.save_as_*(name=...) hoặc export_to_*(...)

```

#### Các Workflow và Phương thức Đầu ra có sẵn

| Workflow | Đầu vào | save_as_* | export_to_* | Các tùy chọn Config chính |
| --- | --- | --- | --- | --- |
| **MarkdownBasedWorkflow** | `.pdf`, `.docx`, `.md`, `.png`, `.jpg` | `html`, `markdown`, `markdown_zip`, `docx` | `html`, `markdown`, `markdown_zip`, `docx` | `convert_engine`, `md2docx_engine`, `translator_config` |
| **TXTWorkflow** | `.txt` | `txt`, `html` | `txt`, `html` | `translator_config` |
| **JsonWorkflow** | `.json` | `json`, `html` | `json`, `html` | `translator_config`, `json_paths` |
| **DocxWorkflow** | `.docx` | `docx`, `html` | `docx`, `html` | `translator_config`, `insert_mode` |
| **XlsxWorkflow** | `.xlsx`, `.csv` | `xlsx`, `html` | `xlsx`, `html` | `translator_config`, `insert_mode` |
| **SrtWorkflow** | `.srt` | `srt`, `html` | `srt`, `html` | `translator_config` |
| **EpubWorkflow** | `.epub` | `epub`, `html` | `epub`, `html` | `translator_config`, `insert_mode` |
| **HtmlWorkflow** | `.html`, `.htm` | `html` | `html` | `translator_config`, `insert_mode` |
| **AssWorkflow** | `.ass` | `ass`, `html` | `ass`, `html` | `translator_config` |

#### Các Tùy chọn Cấu hình Chính

**Các tùy chọn TranslatorConfig chung:**

| Tùy chọn | Loại | Mặc định | Mô tả |
| --- | --- | --- | --- |
| `base_url` | `str` | - | Base URL của nền tảng AI |
| `api_key` | `str` | - | API key của nền tảng AI |
| `model_id` | `str` | - | ID Model |
| `to_lang` | `str` | - | Ngôn ngữ đích |
| `chunk_size` | `int` | 3000 | Kích thước đoạn văn bản (chunk) |
| `concurrent` | `int` | 10 | Số lượng yêu cầu đồng thời |
| `temperature` | `float` | 0.3 | Nhiệt độ LLM |
| `timeout` | `int` | 60 | Thời gian chờ yêu cầu (giây) |
| `retry` | `int` | 3 | Số lần thử lại |

**Các tùy chọn Dành riêng cho Định dạng:**

| Tùy chọn | Các Workflow áp dụng | Mô tả |
| --- | --- | --- |
| `insert_mode` | Docx, Xlsx, Html, Epub | `"replace"` (mặc định), `"append"`, `"prepend"` |
| `json_paths` | Json | Biểu thức JSONPath (ví dụ: `["$.*", "$.name"]`) |
| `separator` | Docx, Xlsx, Html, Epub | Dấu phân cách văn bản cho các chế độ `"append"` / `"prepend"` |
| `convert_engine` | MarkdownBased | `"mineru"` (mặc định), `"docling"`, `"mineru_deploy"` |

#### Ví dụ 1: Dịch một tệp PDF (Sử dụng `MarkdownBasedWorkflow`)

Đây là trường hợp sử dụng phổ biến nhất. Chúng tôi sẽ sử dụng engine `mineru` để chuyển đổi PDF sang Markdown, và sau đó dịch nó bằng LLM. Ví dụ này sử dụng thực thi bất đồng bộ.

```python
import asyncio
from docutranslate.workflow.md_based_workflow import MarkdownBasedWorkflow, MarkdownBasedWorkflowConfig
from docutranslate.converter.x2md.converter_mineru import ConverterMineruConfig
from docutranslate.translator.ai_translator.md_translator import MDTranslatorConfig
from docutranslate.exporter.md.md2html_exporter import MD2HTMLExporterConfig


async def main():
    # 1. Xây dựng Cấu hình Translator
    translator_config = MDTranslatorConfig(
        base_url="https://open.bigmodel.cn/api/paas/v4",  # Base URL Nền tảng AI
        api_key="YOUR_ZHIPU_API_KEY",  # API Key Nền tảng AI
        model_id="glm-4-air",  # ID Model
        to_lang="English",  # Ngôn ngữ đích
        chunk_size=3000,  # Kích thước đoạn văn bản
        concurrent=10,  # Mức độ đồng thời
        # glossary_generate_enable=True, # Bật tự động tạo thuật ngữ
        # glossary_dict={"Jobs":"Steve Jobs"}, # Truyền vào từ điển thuật ngữ
        # system_proxy_enable=True, # Bật proxy hệ thống
    )

    # 2. Xây dựng Cấu hình Converter (Sử dụng minerU)
    converter_config = ConverterMineruConfig(
        mineru_token="YOUR_MINERU_TOKEN",  # MinerU Token của bạn
        formula_ocr=True  # Bật nhận dạng công thức
    )

    # 3. Xây dựng Cấu hình Workflow Chính
    workflow_config = MarkdownBasedWorkflowConfig(
        convert_engine="mineru",  # Chỉ định engine phân tích
        converter_config=converter_config,  # Truyền cấu hình converter
        translator_config=translator_config,  # Truyền cấu hình translator
        html_exporter_config=MD2HTMLExporterConfig(cdn=True)  # Cấu hình xuất HTML
    )

    # 4. Khởi tạo Workflow
    workflow = MarkdownBasedWorkflow(config=workflow_config)

    # 5. Đọc file và thực thi dịch thuật
    print("Đang bắt đầu đọc và dịch file...")
    workflow.read_path("path/to/your/document.pdf")
    await workflow.translate_async()
    # Hoặc sử dụng phương thức đồng bộ
    # workflow.translate()
    print("Dịch hoàn tất!")

    # 6. Lưu kết quả
    workflow.save_as_html(name="translated_document.html")
    workflow.save_as_markdown_zip(name="translated_document.zip")
    workflow.save_as_markdown(name="translated_document.md")  # Markdown với hình ảnh được nhúng
    print("Các file đã được lưu vào thư mục ./output.")

    # Hoặc lấy trực tiếp chuỗi nội dung
    html_content = workflow.export_to_html()
    html_content = workflow.export_to_markdown()
    # print(html_content)


if __name__ == "__main__":
    asyncio.run(main())

```

### Các Workflow khác

Tất cả các workflow đều tuân theo cùng một mẫu. Import config và workflow tương ứng, sau đó cấu hình:

```python
# TXT: from docutranslate.workflow.txt_workflow import TXTWorkflow, TXTWorkflowConfig
# JSON: from docutranslate.workflow.json_workflow import JsonWorkflow, JsonWorkflowConfig
# DOCX: from docutranslate.workflow.docx_workflow import DocxWorkflow, DocxWorkflowConfig
# XLSX: from docutranslate.workflow.xlsx_workflow import XlsxWorkflow, XlsxWorkflowConfig
# EPUB: from docutranslate.workflow.epub_workflow import EpubWorkflow, EpubWorkflowConfig
# HTML: from docutranslate.workflow.html_workflow import HtmlWorkflow, HtmlWorkflowConfig
# SRT:  from docutranslate.workflow.srt_workflow import SrtWorkflow, SrtWorkflowConfig
# ASS:   from docutranslate.workflow.ass_workflow import AssWorkflow, AssWorkflowConfig

```

Các tùy chọn config chính:

* **insert_mode**: `"replace"`, `"append"`, hoặc `"prepend"` (cho docx/xlsx/html/epub)
* **json_paths**: Biểu thức JSONPath cho dịch thuật JSON (ví dụ: `["$.*", "$.name"]`)
* **separator**: Dấu phân cách văn bản cho các chế độ `"append"` / `"prepend"`

## Điều kiện tiên quyết và Cấu hình chi tiết

### 1. Lấy API Key Mô hình Lớn

Chức năng dịch thuật dựa vào các Mô hình Ngôn ngữ Lớn (LLM). Bạn cần lấy `base_url`, `api_key`, và `model_id` từ nền tảng AI tương ứng.

> Các model được khuyến nghị: `doubao-seed-1-6-flash` của Volcengine, dòng `doubao-seed-1-6`, `glm-4-flash` của Zhipu, `qwen-plus`, `qwen-flash` của Alibaba Cloud, `deepseek-chat` của Deepseek, v.v.

> [302.AI](https://share.302.ai/BgRLAe) 👈 Đăng ký qua link này để nhận $1 tín dụng miễn phí.

| Tên Nền tảng | Lấy API Key | Base URL |
| --- | --- | --- |
| ollama |  | http://127.0.0.1:11434/v1 |
| lm studio |  | http://127.0.0.1:1234/v1 |
| 302.AI | [Nhấn để lấy](https://share.302.ai/BgRLAe) | https://api.302.ai/v1 |
| openrouter | [Nhấn để lấy](https://openrouter.ai/settings/keys) | https://openrouter.ai/api/v1 |
| openai | [Nhấn để lấy](https://platform.openai.com/api-keys) | https://api.openai.com/v1/ |
| gemini | [Nhấn để lấy](https://aistudio.google.com/u/0/apikey) | https://generativelanguage.googleapis.com/v1beta/openai/ |
| deepseek | [Nhấn để lấy](https://platform.deepseek.com/api_keys) | https://api.deepseek.com/v1 |
| Zhipu AI | [Nhấn để lấy](https://open.bigmodel.cn/usercenter/apikeys) | https://open.bigmodel.cn/api/paas/v4 |
| Tencent Hunyuan | [Nhấn để lấy](https://console.cloud.tencent.com/hunyuan/api-key) | https://api.hunyuan.cloud.tencent.com/v1 |
| Alibaba Bailian | [Nhấn để lấy](https://bailian.console.aliyun.com/?tab=model#/api-key) | https://dashscope.aliyuncs.com/compatible-mode/v1 |
| Volcengine | [Nhấn để lấy](https://console.volcengine.com/ark/region:ark+cn-beijing/apiKey?apikey=%7B%7D) | https://ark.cn-beijing.volces.com/api/v3 |
| SiliconFlow | [Nhấn để lấy](https://cloud.siliconflow.cn/account/ak) | https://api.siliconflow.cn/v1 |
| DMXAPI | [Nhấn để lấy](https://www.dmxapi.cn/token) | https://www.dmxapi.cn/v1 |
| Juguang AI | [Nhấn để lấy](https://ai.juguang.chat/console/token) | https://ai.juguang.chat/v1 |

### 2. Công cụ Phân tích PDF (Bỏ qua nếu bạn không cần dịch PDF)

### 2.1 Lấy Token minerU (Phân tích PDF Online, Miễn phí, Được khuyến nghị)

Nếu bạn chọn `mineru` làm engine phân tích tài liệu (`convert_engine="mineru"`), bạn cần đăng ký nhận Token miễn phí.

1. Truy cập [Trang web minerU](https://mineru.net/apiManage/docs) để đăng ký và nộp đơn xin API.
2. Tạo API Token mới trong [Giao diện Quản lý API Token](https://mineru.net/apiManage/token).

> **Lưu ý**: Token minerU có giá trị trong 14 ngày. Vui lòng tạo lại sau khi hết hạn.

### 2.2. Cấu hình Engine docling (Phân tích PDF Cục bộ)

Nếu bạn chọn `docling` làm engine phân tích tài liệu (`convert_engine="docling"`), nó sẽ tải xuống các model cần thiết từ Hugging Face trong lần sử dụng đầu tiên.

> Một lựa chọn tốt hơn là tải xuống `docling_artifact.zip` từ [GitHub Releases](https://github.com/xunbu/docutranslate/releases) và giải nén nó vào thư mục làm việc của bạn.

**Giải pháp cho Vấn đề Mạng khi Tải Model `docling`:**

1. **Thiết lập Hugging Face Mirror (Được khuyến nghị)**:

* **Phương pháp A (Biến môi trường)**: Đặt biến môi trường hệ thống `HF_ENDPOINT` và khởi động lại IDE hoặc terminal của bạn.
```
HF_ENDPOINT=https://hf-mirror.com

```


* **Phương pháp B (Trong Code)**: Thêm đoạn mã sau vào đầu tập lệnh Python của bạn.

```python
import os

os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

```

2. **Sử dụng Offline (Tải trước Gói Model)**:

* Tải xuống `docling_artifact.zip` từ [GitHub Releases](https://github.com/xunbu/docutranslate/releases).
* Giải nén nó vào thư mục dự án của bạn.
* Chỉ định đường dẫn model trong cấu hình (nếu model không nằm trong cùng thư mục với tập lệnh):

```python
from docutranslate.converter.x2md.converter_docling import ConverterDoclingConfig

converter_config = ConverterDoclingConfig(
    artifact="./docling_artifact",  # Trỏ đến thư mục đã giải nén
    code_ocr=True,
    formula_ocr=True
)

```

### 2.3. Dịch vụ MinerU Triển khai Cục bộ

Đối với môi trường offline/mạng nội bộ, hãy triển khai `minerU` cục bộ với API được kích hoạt. Đặt `mineru_deploy_base_url` thành endpoint API minerU của bạn.

**Client SDK:**

```python
from docutranslate.sdk import Client

client = Client(
    api_key="YOUR_LLM_API_KEY",
    model_id="llama3",
    to_lang="Chinese",
    convert_engine="mineru_deploy",
    mineru_deploy_base_url="http://127.0.0.1:8000",  # Địa chỉ API minerU của bạn
)
result = client.translate("document.pdf")
result.save(fmt="markdown")

```

## Câu hỏi thường gặp (FAQ)

**H: Đầu ra vẫn là ngôn ngữ gốc?**
Đ: Kiểm tra nhật ký (logs) để tìm lỗi. Thường là do hết tín dụng API hoặc vấn đề mạng.

**H: Cổng 8010 bị chiếm dụng?**
Đ: Sử dụng `docutranslate -i -p 8011` hoặc thiết lập `DOCUTRANSLATE_PORT=8011`.

**H: PDF scan có được hỗ trợ không?**
Đ: Có, sử dụng engine `mineru` với khả năng OCR.

**H: Dịch PDF lần đầu tiên rất chậm?**
Đ: `docling` cần tải xuống các model trong lần chạy đầu tiên. Hãy sử dụng Hugging Face mirror hoặc tải trước gói artifact.

**H: Sử dụng trong mạng nội bộ/offline được không?**
Đ: Có. Sử dụng LLM cục bộ (Ollama/LM Studio) và minerU hoặc docling cục bộ.

**H: Cơ chế cache PDF?**
Đ: `MarkdownBasedWorkflow` lưu trữ kết quả phân tích trong bộ nhớ (10 lần phân tích gần nhất). Cấu hình qua `DOCUTRANSLATE_CACHE_NUM`.

**H: Bật proxy?**
Đ: Thiết lập `system_proxy_enable=True` trong TranslatorConfig.

## Lịch sử Sao

<a href="https://www.star-history.com/#xunbu/docutranslate&Date">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=xunbu/docutranslate&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=xunbu/docutranslate&type=Date" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=xunbu/docutranslate&type=Date" />
 </picture>
</a>

## Hỗ trợ Quyên góp

Hoan nghênh ủng hộ tác giả. Vui lòng ghi rõ lý do quyên góp trong phần bình luận!

<p align="center">
<img src="./images/赞赏码.jpg" alt="Donation Code" style="width: 250px;">
</p>
