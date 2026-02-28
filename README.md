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
  A lightweight local file translation tool based on Large Language Models.
</p>

- ✅ **Support Multiple Formats**: Translates `pdf`, `docx`, `xlsx`, `md`, `txt`, `json`, `epub`, `srt`, `ass`, and more.
- ✅ **Auto-Generate Glossary**: Supports automatic glossary generation to ensure term alignment.
- ✅ **PDF Table, Formula, Code Recognition**: Leverages `docling` and `mineru` PDF parsing engines to recognize and translate tables, formulas, and code often found in academic papers.
- ✅ **JSON Translation**: Supports specifying values to translate within JSON using paths (`jsonpath-ng` syntax).
- ✅ **Word/Excel Format Preservation**: Supports `docx` and `xlsx` files (currently does not support `doc` or `xls`) while maintaining original formatting.
- ✅ **Multi-AI Platform Support**: Supports most AI platforms, allowing for high-performance concurrent AI translation with custom prompts.
- ✅ **Async Support**: Designed for high-performance scenarios, providing full asynchronous support and interfaces for parallel multi-tasking.
- ✅ **LAN & Multi-user Support**: Supports simultaneous use by multiple users within a local area network (LAN).
- ✅ **Interactive Web Interface**: Provides an out-of-the-box Web UI and RESTful API for easy integration and usage.
- ✅ **Compact, Portable Packages**: Windows and Mac portable packages under 40MB (versions that do not use `docling` for local PDF parsing).

> When translating `pdf`, it is first converted to markdown. This will **lose** the original layout. Users with strict layout requirements should take note.

> QQ Community Group: 1047781902 1081128602

**UI Interface**:
![UI Interface](/images/UI界面.png)

**Paper Translation**:
![Paper Translation](/images/论文翻译.png)

**Novel Translation**:
![Novel Translation](/images/小说翻译.png)

## Integration Packages

For users who want to get started quickly, we provide integration packages on [GitHub Releases](https://github.com/xunbu/docutranslate/releases). Simply download, unzip, and enter your AI platform API-Key to start using it.

- **DocuTranslate**: Standard version. Uses `minerU` (online or locally deployed) for PDF parsing. Supports local minerU API calls. (Recommended)
- **DocuTranslate_full**: Full version. Includes the built-in `docling` local PDF parsing engine. Choose this version if you need offline PDF parsing without minerU.

## Installation

### Using pip

```bash
# Basic installation
pip install docutranslate

# If you need to use docling for local PDF parsing
pip install docutranslate[docling]
```

### Using uv

```bash
# Initialize environment
uv init

# Basic installation
uv add docutranslate

# Install docling extension
uv add docutranslate[docling]
```

### Using git

```bash
# Initialize environment
git clone https://github.com/xunbu/docutranslate.git

cd docutranslate

uv sync

```

### Using docker

```bash
docker run -d -p 8010:8010 xunbu/docutranslate:latest
# docker run -it -p 8010:8010 xunbu/docutranslate:latest
# docker run -it -p 8010:8010 xunbu/docutranslate:v1.5.4
```

## Core Concept: Workflow

DocuTranslate uses a **Workflow** system - each workflow is a complete translation pipeline for a specific file type.

**Basic flow:**
1. Select workflow based on file type
2. Configure the workflow (LLM, parsing engine, output format)
3. Execute translation
4. Save results

## Start Web UI and API Service

For ease of use, DocuTranslate provides a fully functional Web Interface and RESTful API.

**Start the Service:**

```bash
# Start service, defaults to listening on port 8010
docutranslate -i

# Start on a specific port
docutranslate -i -p 8011

# Allow CORS requests
docutranslate -i --cors


# You can also specify the port via environment variable
export DOCUTRANSLATE_PORT=8011
docutranslate -i
```

- **Interactive Interface**: After starting the service, please visit `http://127.0.0.1:8010` (or your specified port) in your browser.
- **API Documentation**: Full API documentation (Swagger UI) is located at `http://127.0.0.1:8010/docs`.

## Usage Examples

### Using the Simple Client SDK (Recommended)

The easiest way to get started is using the `Client` class, which provides a simple and intuitive API for translation:

```python
from docutranslate.sdk import Client

# Initialize the client with your AI platform settings
client = Client(
    api_key="YOUR_OPENAI_API_KEY",  # or any other AI platform API key
    base_url="https://api.openai.com/v1/",
    model_id="gpt-4o",
    to_lang="Chinese",
    concurrent=10,  # Number of concurrent requests
)

# Example 1: Translate plain text files (no PDF parsing engine needed)
result = client.translate("path/to/your/document.txt")
print(f"Translation complete! Saved to: {result.save()}")

# Example 2: Translate PDF files (requires mineru_token or local deployment)
# Option A: Use online MinerU (token required: https://mineru.net/apiManage/token)
result = client.translate(
    "path/to/your/document.pdf",
    convert_engine="mineru",
    mineru_token="YOUR_MINERU_TOKEN",  # Replace with your MinerU Token
    formula_ocr=True,  # Enable formula recognition
)
result.save(fmt="html")

# Option B: Use locally deployed MinerU (recommended for intranet/offline)
# First start local MinerU service, reference: https://github.com/opendatalab/MinerU
result = client.translate(
    "path/to/your/document.pdf",
    convert_engine="mineru_deploy",
    mineru_deploy_base_url="http://127.0.0.1:8000",  # Your local MinerU address
    mineru_deploy_backend="hybrid-auto-engine",  # Backend type
)
result.save(fmt="markdown")

# Example 3: Translate Docx files (preserve formatting)
result = client.translate(
    "path/to/your/document.docx",
    insert_mode="replace",  # replace/append/prepend
)
result.save(fmt="docx")  # Save as docx format

# Example 4: Export as base64 encoded string (for API transmission)
base64_content = result.export(fmt="html")
print(f"Exported content length: {len(base64_content)}")

# You can also access the underlying workflow for advanced operations
# workflow = result.workflow
```

**Client Features:**
- **Auto-detection**: Automatically detects file type and selects the appropriate workflow
- **Flexible Configuration**: Override any default settings per translation call
- **Multiple Output Options**: Save to disk or export as Base64 string
- **Async Support**: Use `translate_async()` for concurrent translation tasks

#### Client SDK Parameters

| Parameter | Type | Default | Description |
|:---|:---|:---|:---|
| **api_key** | `str` | - | AI platform API key |
| **base_url** | `str` | - | AI platform base URL (e.g., `https://api.openai.com/v1/`) |
| **model_id** | `str` | - | Model ID to use for translation |
| **to_lang** | `str` | - | Target language (e.g., `"Chinese"`, `"English"`, `"Japanese"`) |
| **concurrent** | `int` | 10 | Number of concurrent LLM requests |
| **convert_engine** | `str` | `"mineru"` | PDF parsing engine: `"mineru"`, `"docling"`, `"mineru_deploy"` |
| **md2docx_engine** | `str` | `"auto"` | Markdown to Docx engine: `"python"` (pure Python), `"pandoc"` (use Pandoc), `"auto"` (use Pandoc if installed, otherwise Python), `null` (do not generate docx) |
| **mineru_deploy_base_url** | `str` | - | Local minerU API address (when `convert_engine="mineru_deploy"`) |
| **mineru_deploy_parse_method** | `str` | `"auto"` | Local minerU parsing method: `"auto"`, `"txt"`, `"ocr"` |
| **mineru_deploy_table_enable** | `bool` | `True` | Enable table recognition for local minerU |
| **mineru_token** | `str` | - | minerU API token (when using online minerU) |
| **skip_translate** | `bool` | `False` | Skip translation, only parse document |
| **output_dir** | `str` | `"./output"` | Default output directory for `save()` |
| **chunk_size** | `int` | 3000 | Text chunk size for LLM processing |
| **temperature** | `float` | 0.3 | LLM temperature parameter |
| **timeout** | `int` | 60 | Request timeout in seconds |
| **retry** | `int` | 3 | Number of retry attempts on failure |
| **provider** | `str` | `"auto"` | AI provider type (auto, openai, azure, etc.) |
| **force_json** | `bool` | `False` | Force JSON output mode |
| **rpm** | `int` | - | Requests per minute limit |
| **tpm** | `int` | - | Tokens per minute limit |
| **extra_body** | `str` | - | Additional request body parameters in JSON string format, will be merged into API request |
| **thinking** | `str` | `"auto"` | Thinking mode: `"auto"`, `"none"`, `"block"` |
| **custom_prompt** | `str` | - | Custom prompt for translation |
| **system_proxy_enable** | `bool` | `False` | Enable system proxy |
| **insert_mode** | `str` | `"replace"` | Docx/Xlsx/Txt insertion mode: `"replace"`, `"append"`, `"prepend"` |
| **separator** | `str` | `"\n"` | Text separator for append/prepend modes |
| **segment_mode** | `str` | `"line"` | Segmentation mode: `"line"`, `"paragraph"`, `"none"` |
| **translate_regions** | `list` | - | Excel translation regions (e.g., `"Sheet1!A1:B10"`) |
| **model_version** | `str` | `"vlm"` | MinerU model version: `"pipeline"`, `"vlm"` |
| **formula_ocr** | `bool` | `True` | Enable formula OCR for PDF parsing |
| **code_ocr** | `bool` | `True` | Enable code OCR for PDF parsing |
| **mineru_deploy_backend** | `str` | `"hybrid-auto-engine"` | MinerU local backend: `"pipeline"`, `"vlm-auto-engine"`, `"vlm-http-client"`, `"hybrid-auto-engine"`, `"hybrid-http-client"` |
| **mineru_deploy_formula_enable** | `bool` | `True` | Enable formula recognition for local MinerU |
| **mineru_deploy_start_page_id** | `int` | 0 | Start page ID for local MinerU parsing |
| **mineru_deploy_end_page_id** | `int` | 99999 | End page ID for local MinerU parsing |
| **mineru_deploy_lang_list** | `list` | - | Language list for local MinerU parsing |
| **mineru_deploy_server_url** | `str` | - | MinerU local server URL |
| **json_paths** | `list` | - | JSONPath expressions for JSON translation (e.g., `"$.data.*"`) |
| **glossary_generate_enable** | `bool` | - | Enable auto glossary generation |
| **glossary_dict** | `dict` | - | Glossary dictionary (e.g., `{"Jobs": "Steve Jobs"}`) |
| **glossary_agent_config** | `dict` | - | Glossary agent configuration |

#### Result Methods

| Method | Parameters | Description |
|:---|:---|:---|
| **save()** | `output_dir`, `name`, `fmt` | Save translation result to disk |
| **export()** | `fmt` | Export as Base64 encoded string |
| **supported_formats** | - | Get list of supported output formats |
| **workflow** | - | Access underlying workflow object |

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

    # Translate multiple files concurrently
    files = ["doc1.pdf", "doc2.docx", "notes.txt"]
    results = await asyncio.gather(
        *[client.translate_async(f) for f in files]
    )

    for r in results:
        print(f"Saved: {r.save()}")

asyncio.run(translate_multiple())
```

### Using Workflow API (For Advanced Control)

For more control, use the Workflow API directly. Each workflow follows the same pattern:

```python
# Pattern:
# 1. Create TranslatorConfig (LLM settings)
# 2. Create WorkflowConfig (workflow settings)
# 3. Create Workflow instance
# 4. workflow.read_path(file)
# 5. await workflow.translate_async()
# 6. workflow.save_as_*(name=...) or export_to_*(...)
```

#### Available Workflows and Output Methods

| Workflow | Inputs | save_as_* | export_to_* | Key Config Options |
|:---|:---|:---|:---|:---|
| **MarkdownBasedWorkflow** | `.pdf`, `.docx`, `.md`, `.png`, `.jpg` | `html`, `markdown`, `markdown_zip`, `docx` | `html`, `markdown`, `markdown_zip`, `docx` | `convert_engine`, `md2docx_engine`, `translator_config` |
| **TXTWorkflow** | `.txt` | `txt`, `html` | `txt`, `html` | `translator_config` |
| **JsonWorkflow** | `.json` | `json`, `html` | `json`, `html` | `translator_config`, `json_paths` |
| **DocxWorkflow** | `.docx` | `docx`, `html` | `docx`, `html` | `translator_config`, `insert_mode` |
| **XlsxWorkflow** | `.xlsx`, `.csv` | `xlsx`, `html` | `xlsx`, `html` | `translator_config`, `insert_mode` |
| **SrtWorkflow** | `.srt` | `srt`, `html` | `srt`, `html` | `translator_config` |
| **EpubWorkflow** | `.epub` | `epub`, `html` | `epub`, `html` | `translator_config`, `insert_mode` |
| **HtmlWorkflow** | `.html`, `.htm` | `html` | `html` | `translator_config`, `insert_mode` |
| **AssWorkflow** | `.ass` | `ass`, `html` | `ass`, `html` | `translator_config` |

#### Key Configuration Options

**Common TranslatorConfig Options:**

| Option | Type | Default | Description |
|:---|:---|:---|:---|
| `base_url` | `str` | - | AI platform base URL |
| `api_key` | `str` | - | AI platform API key |
| `model_id` | `str` | - | Model ID |
| `to_lang` | `str` | - | Target language |
| `chunk_size` | `int` | 3000 | Text chunk size |
| `concurrent` | `int` | 10 | Concurrent requests |
| `temperature` | `float` | 0.3 | LLM temperature |
| `timeout` | `int` | 60 | Request timeout (seconds) |
| `retry` | `int` | 3 | Retry attempts |

**Format-Specific Options:**

| Option | Applicable Workflows | Description |
|:---|:---|:---|
| `insert_mode` | Docx, Xlsx, Html, Epub | `"replace"` (default), `"append"`, `"prepend"` |
| `json_paths` | Json | JSONPath expressions (e.g., `["$.*", "$.name"]`) |
| `separator` | Docx, Xlsx, Html, Epub | Text separator for append/prepend modes |
| `convert_engine` | MarkdownBased | `"mineru"` (default), `"docling"`, `"mineru_deploy"` |

#### Example 1: Translate a PDF File (Using `MarkdownBasedWorkflow`)

This is the most common use case. We will use the `minerU` engine to convert the PDF to Markdown, and then translate it using an LLM. This example uses asynchronous execution.

```python
import asyncio
from docutranslate.workflow.md_based_workflow import MarkdownBasedWorkflow, MarkdownBasedWorkflowConfig
from docutranslate.converter.x2md.converter_mineru import ConverterMineruConfig
from docutranslate.translator.ai_translator.md_translator import MDTranslatorConfig
from docutranslate.exporter.md.md2html_exporter import MD2HTMLExporterConfig


async def main():
    # 1. Build Translator Configuration
    translator_config = MDTranslatorConfig(
        base_url="https://open.bigmodel.cn/api/paas/v4",  # AI Platform Base URL
        api_key="YOUR_ZHIPU_API_KEY",  # AI Platform API Key
        model_id="glm-4-air",  # Model ID
        to_lang="English",  # Target Language
        chunk_size=3000,  # Text chunk size
        concurrent=10,  # Concurrency level
        # glossary_generate_enable=True, # Enable auto-glossary generation
        # glossary_dict={"Jobs":"Steve Jobs"}, # Pass in a glossary dictionary
        # system_proxy_enable=True, # Enable system proxy
    )

    # 2. Build Converter Configuration (Using minerU)
    converter_config = ConverterMineruConfig(
        mineru_token="YOUR_MINERU_TOKEN",  # Your minerU Token
        formula_ocr=True  # Enable formula recognition
    )

    # 3. Build Main Workflow Configuration
    workflow_config = MarkdownBasedWorkflowConfig(
        convert_engine="mineru",  # Specify parsing engine
        converter_config=converter_config,  # Pass converter config
        translator_config=translator_config,  # Pass translator config
        html_exporter_config=MD2HTMLExporterConfig(cdn=True)  # HTML export config
    )

    # 4. Instantiate Workflow
    workflow = MarkdownBasedWorkflow(config=workflow_config)

    # 5. Read file and execute translation
    print("Starting to read and translate file...")
    workflow.read_path("path/to/your/document.pdf")
    await workflow.translate_async()
    # Or use synchronous method
    # workflow.translate()
    print("Translation complete!")

    # 6. Save results
    workflow.save_as_html(name="translated_document.html")
    workflow.save_as_markdown_zip(name="translated_document.zip")
    workflow.save_as_markdown(name="translated_document.md")  # Markdown with embedded images
    print("Files saved to ./output folder.")

    # Or get content strings directly
    html_content = workflow.export_to_html()
    html_content = workflow.export_to_markdown()
    # print(html_content)


if __name__ == "__main__":
    asyncio.run(main())
```

### Other Workflows

All workflows follow the same pattern. Import the corresponding config and workflow, then configure:

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

Key config options:
- **insert_mode**: `"replace"`, `"append"`, or `"prepend"` (for docx/xlsx/html/epub)
- **json_paths**: JSONPath expressions for JSON translation (e.g., `["$.*", "$.name"]`)
- **separator**: Text separator for `"append"` / `"prepend"` modes

## Prerequisites and Detailed Configuration

### 1. Get Large Model API Key

Translation functionality relies on Large Language Models. You need to obtain a `base_url`, `api_key`, and `model_id` from the corresponding AI platform.

> Recommended Models: Volcengine's `doubao-seed-1-6-flash`, `doubao-seed-1-6` series, Zhipu's `glm-4-flash`, Alibaba Cloud's `qwen-plus`, `qwen-flash`, Deepseek's `deepseek-chat`, etc.

> [302.AI](https://share.302.ai/BgRLAe) 👈 Register via this link to get $1 free credit.

| Platform Name | Get API Key | Base URL |
|:---|:---|:---|
| ollama | | http://127.0.0.1:11434/v1 |
| lm studio | | http://127.0.0.1:1234/v1 |
| 302.AI | [Click to Get](https://share.302.ai/BgRLAe) | https://api.302.ai/v1 |
| openrouter | [Click to Get](https://openrouter.ai/settings/keys) | https://openrouter.ai/api/v1 |
| openai | [Click to Get](https://platform.openai.com/api-keys) | https://api.openai.com/v1/ |
| gemini | [Click to Get](https://aistudio.google.com/u/0/apikey) | https://generativelanguage.googleapis.com/v1beta/openai/ |
| deepseek | [Click to Get](https://platform.deepseek.com/api_keys) | https://api.deepseek.com/v1 |
| Zhipu AI | [Click to Get](https://open.bigmodel.cn/usercenter/apikeys) | https://open.bigmodel.cn/api/paas/v4 |
| Tencent Hunyuan | [Click to Get](https://console.cloud.tencent.com/hunyuan/api-key) | https://api.hunyuan.cloud.tencent.com/v1 |
| Alibaba Bailian | [Click to Get](https://bailian.console.aliyun.com/?tab=model#/api-key) | https://dashscope.aliyuncs.com/compatible-mode/v1 |
| Volcengine | [Click to Get](https://console.volcengine.com/ark/region:ark+cn-beijing/apiKey?apikey=%7B%7D) | https://ark.cn-beijing.volces.com/api/v3 |
| SiliconFlow | [Click to Get](https://cloud.siliconflow.cn/account/ak) | https://api.siliconflow.cn/v1 |
| DMXAPI | [Click to Get](https://www.dmxapi.cn/token) | https://www.dmxapi.cn/v1 |
| Juguang AI | [Click to Get](https://ai.juguang.chat/console/token) | https://ai.juguang.chat/v1 |

### 2. PDF Parsing Engine (Skip if you don't need to translate PDFs)

### 2.1 Get minerU Token (Online PDF Parsing, Free, Recommended)

If you choose `mineru` as the document parsing engine (`convert_engine="mineru"`), you need to apply for a free Token.

1. Visit [minerU Website](https://mineru.net/apiManage/docs) to register and apply for the API.
2. Create a new API Token in the [API Token Management Interface](https://mineru.net/apiManage/token).

> **Note**: The minerU Token is valid for 14 days. Please recreate it after expiration.

### 2.2. docling Engine Configuration (Local PDF Parsing)

If you choose `docling` as the document parsing engine (`convert_engine="docling"`), it will download the required models from Hugging Face upon first use.

> A better option is to download `docling_artifact.zip` from [GitHub Releases](https://github.com/xunbu/docutranslate/releases) and unzip it into your working directory.

**Solutions for `docling` Model Download Network Issues:**

1.  **Set Hugging Face Mirror (Recommended)**:

*   **Method A (Environment Variable)**: Set the system environment variable `HF_ENDPOINT` and restart your IDE or terminal.
    ```
    HF_ENDPOINT=https://hf-mirror.com
    ```
*   **Method B (In Code)**: Add the following code at the beginning of your Python script.

```python
import os

os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
```

2.  **Offline Use (Pre-download Model Package)**:

*   Download `docling_artifact.zip` from [GitHub Releases](https://github.com/xunbu/docutranslate/releases).
*   Unzip it into your project directory.
*   Specify the model path in the configuration (if the model is not in the same directory as the script):

```python
from docutranslate.converter.x2md.converter_docling import ConverterDoclingConfig

converter_config = ConverterDoclingConfig(
    artifact="./docling_artifact",  # Point to the unzipped folder
    code_ocr=True,
    formula_ocr=True
)
```

### 2.3. Locally Deployed MinerU Service

For offline/intranet environments, deploy `minerU` locally with API enabled. Set `mineru_deploy_base_url` to your minerU API endpoint.

**Client SDK:**
```python
from docutranslate.sdk import Client

client = Client(
    api_key="YOUR_LLM_API_KEY",
    model_id="llama3",
    to_lang="Chinese",
    convert_engine="mineru_deploy",
    mineru_deploy_base_url="http://127.0.0.1:8000",  # Your minerU API address
)
result = client.translate("document.pdf")
result.save(fmt="markdown")
```

## FAQ

**Q: Output is in original language?**
A: Check logs for errors. Usually due to exhausted API credits or network issues.

**Q: Port 8010 occupied?**
A: Use `docutranslate -i -p 8011` or set `DOCUTRANSLATE_PORT=8011`.

**Q: Scanned PDFs supported?**
A: Yes, use `mineru` engine with OCR capabilities.

**Q: First PDF translation slow?**
A: `docling` needs to download models on first run. Use Hugging Face mirror or pre-download artifact.

**Q: Use in intranet/offline?**
A: Yes. Use local LLM (Ollama/LM Studio) and local minerU or docling.

**Q: PDF cache mechanism?**
A: `MarkdownBasedWorkflow` caches parsing results in memory (last 10 parses). Configure via `DOCUTRANSLATE_CACHE_NUM`.

**Q: Enable proxy?**
A: Set `system_proxy_enable=True` in TranslatorConfig.

## Star History

<a href="https://www.star-history.com/#xunbu/docutranslate&Date">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=xunbu/docutranslate&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=xunbu/docutranslate&type=Date" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=xunbu/docutranslate&type=Date" />
 </picture>
</a>

## Donation Support

Welcome to support the author. Please specify the reason for the donation in the comments!

<p align="center">
  <img src="./images/赞赏码.jpg" alt="Donation Code" style="width: 250px;">
</p>
