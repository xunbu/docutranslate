<p align="center">
<img src="./DocuTranslate.png" alt="项目Logo" style="width: 150px">
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
  <a href="/README_ZH.md"><strong>简体中文</strong></a> / <a href="/README.md"><strong>English</strong></a> / <a href="/README_JP.md"><strong>日本語</strong></a>
</p>

<p align="center">
  一个基于大语言模型的轻量级本地文件翻译工具
</p>

- ✅ **支持多种格式**：能翻译 `pdf`、`docx`、`xlsx`、`md`、`txt`、`json`、`epub`、`srt` 、`ass`等多种文件。
- ✅ **自动生成术语表**：支持自动生成术语表实现术语的对齐。
- ✅ **PDF表格、公式、代码识别**：凭借`docling`、`mineru`pdf解析引擎实现对学术论文中经常出现的表格、公式、代码的识别与翻译
- ✅ **json翻译**：支持通过json路径(`jsonpath-ng`语法规范)指定json中需要被翻译的值。
- ✅ **Word/Excel保持格式翻译**：支持`docx`、`xlsx`文件（暂不支持`doc`、`xls`文件）保持原格式进行翻译。
- ✅ **多ai平台支持**：支持绝大部分的ai平台，可以实现自定义提示词的并发高性能ai翻译。
- ✅ **异步支持**：专为高性能场景设计，提供完整的异步支持，实现了可以多任务并行的服务接口。
- ✅ **局域网、多人使用支持**：支持在局域网中多人同时使用。
- ✅ **交互式Web界面**：提供开箱即用的 Web UI 和 RESTful API，方便集成与使用。
- ✅ **小体积、多平台懒人包支持**：不到40M的windows、mac懒人包（不使用`docling`本地解析pdf的版本）。

> 在翻译`pdf`时会先转换为markdown，这会**丢失**原先的排版，对排版有要求的用户请注意

> QQ交流群：1047781902

**UI界面**：
![翻译效果](/images/UI界面.png)

**论文翻译**：
![翻译效果](/images/论文翻译.png)

**小说翻译**：
![翻译效果](/images/小说翻译.png)

## 整合包

对于希望快速上手的用户，我们在 [GitHub Releases](https://github.com/xunbu/docutranslate/releases) 上提供整合包。您只需下载、解压，并填入您的
AI 平台 API-Key 即可开始使用。

- **DocuTranslate**: 标准版，使用 `minerU`（在线或本地部署）解析PDF文档，支持调用本地部署的 minerU API。（推荐）
- **DocuTranslate_full**: 完整版，内置 `docling` 本地PDF解析引擎，无需 minerU 即可进行离线PDF解析时选择此版本。

## 安装

### 使用 pip

```bash
# 基础安装
pip install docutranslate

# 如需使用 docling 本地解析PDF
pip install docutranslate[docling]
```

### 使用 uv

```bash
# 初始化环境
uv init

# 基础安装
uv add docutranslate

# 安装 docling 扩展
uv add docutranslate[docling]
```

### 使用 git

```bash
# 初始化环境
git clone https://github.com/xunbu/docutranslate.git

cd docutranslate

uv sync

```

### 使用docker

```bash
docker run -d -p 8010:8010 xunbu/docutranslate:latest
# docker run -it -p 8010:8010 xunbu/docutranslate:latest
# docker run -it -p 8010:8010 xunbu/docutranslate:v1.5.4
```

## 核心概念：工作流 (Workflow)

DocuTranslate 使用 **工作流 (Workflow)** 系统，每个工作流都是针对特定文件类型的完整翻译管道。

**基本流程：**
1. 根据文件类型选择工作流
2. 配置工作流（LLM、解析引擎、输出格式）
3. 执行翻译
4. 保存结果

## 启动 Web UI 和 API 服务

为了方便使用，DocuTranslate 提供了一个功能齐全的 Web 界面和 RESTful API。

**启动服务:**

```bash
# 启动服务，默认监听 8010 端口
docutranslate -i

# 指定端口启动
docutranslate -i -p 8011

# 允许跨域请求
docutranslate -i --cors


# 也可以通过环境变量指定端口
export DOCUTRANSLATE_PORT=8011
docutranslate -i
```

- **交互式界面**: 启动服务后，请在浏览器中访问 `http://127.0.0.1:8010` (或您指定的端口)。
- **API 文档**: 完整的 API 文档（Swagger UI）位于 `http://127.0.0.1:8010/docs`。

## 使用方式

### 使用简单的 Client SDK (推荐)

使用 `Client` 类是开始翻译最简单的方式，它提供了简洁直观的 API：

```python
from docutranslate.sdk import Client

# 使用您的 AI 平台设置初始化客户端
client = Client(
    api_key="YOUR_OPENAI_API_KEY",  # 或其他 AI 平台 API key
    base_url="https://api.openai.com/v1/",
    model_id="gpt-4o",
    to_lang="中文",
    concurrent=10,  # 并发请求数
)

# 翻译单个文件 (自动检测文件类型)
result = client.translate("path/to/your/document.pdf")

# 使用默认格式保存 (PDF -> markdown with embedded images)
print(f"翻译完成！保存位置: {result.save()}")

# 或显式指定输出格式
# PDF/markdown_based 支持:
#   - "markdown": Markdown 格式，内嵌 base64 图片 (默认)
#   - "markdown_zip": Markdown 格式，图片分离存储 (ZIP 压缩包)
#   - "html": HTML 格式
# docx 支持: "docx"
# xlsx 支持: "xlsx"
result.save(fmt="html")  # 保存为 HTML
result.save(fmt="markdown")  # 保存为 Markdown（内嵌图片）
result.save(fmt="markdown_zip")  # 保存为 ZIP（图片分离）

# 保存到自定义位置
result.save(output_dir="./my_translations", name="my_document.html")

# 导出为 Base64 编码字符串
base64_content = result.export(fmt="html")
print(f"导出内容长度: {len(base64_content)}")

# 您还可以访问底层工作流以进行高级操作
# workflow = result.workflow
```

**Client 功能特点:**
- **自动检测**: 自动检测文件类型并选择合适的工作流
- **灵活配置**: 可在每次翻译调用时覆盖默认设置
- **多种输出选项**: 保存到磁盘或导出为 Base64 字符串
- **异步支持**: 使用 `translate_async()` 进行并发翻译任务

#### Client SDK 参数说明

| 参数 | 类型 | 默认值 | 说明 |
|:---|:---|:---|:---|
| **api_key** | `str` | - | AI 平台 API 密钥 |
| **base_url** | `str` | - | AI 平台基础 URL（如 `https://api.openai.com/v1/`） |
| **model_id** | `str` | - | 翻译使用的模型 ID |
| **to_lang** | `str` | - | 目标语言（如 `"中文"`、`"English"`、`"日本語"`） |
| **concurrent** | `int` | 10 | 并发 LLM 请求数 |
| **convert_engine** | `str` | `"mineru"` | PDF 解析引擎：`"mineru"`、`"docling"`、`"mineru_deploy"` |
| **mineru_deploy_base_url** | `str` | - | 本地 minerU API 地址（当 `convert_engine="mineru_deploy"` 时） |
| **mineru_token** | `str` | - | minerU API Token（使用在线 minerU 时） |
| **skip_translate** | `bool` | `False` | 跳过翻译，仅解析文档 |
| **output_dir** | `str` | `"./output"` | `save()` 方法的默认输出目录 |
| **chunk_size** | `int` | 3000 | LLM 处理的文本分块大小 |
| **temperature** | `float` | 0.3 | LLM 温度参数 |
| **timeout** | `int` | 60 | 请求超时时间（秒） |
| **retry** | `int` | 3 | 失败重试次数 |
| **provider** | `str` | `"auto"` | AI 提供商类型（auto、openai、azure 等） |
| **force_json** | `bool` | `False` | 强制 JSON 输出模式 |
| **rpm** | `int` | - | 每分钟请求数限制 |
| **tpm** | `int` | - | 每分钟 Token 数限制 |

#### Result 方法说明

| 方法 | 参数 | 说明 |
|:---|:---|:---|
| **save()** | `output_dir`, `name`, `fmt` | 将翻译结果保存到磁盘 |
| **export()** | `fmt` | 导出为 Base64 编码的字符串 |
| **supported_formats** | - | 获取支持的输出格式列表 |
| **workflow** | - | 访问底层工作流对象 |

```python
import asyncio
from docutranslate.sdk import Client

async def translate_multiple():
    client = Client(
        api_key="YOUR_API_KEY",
        base_url="https://api.openai.com/v1/",
        model_id="gpt-4o",
        to_lang="中文",
    )

    # 并发翻译多个文件
    files = ["doc1.pdf", "doc2.docx", "notes.txt"]
    results = await asyncio.gather(
        *[client.translate_async(f) for f in files]
    )

    for r in results:
        print(f"保存位置: {r.save()}")

asyncio.run(translate_multiple())
```

### 使用 Workflow API（高级控制）

如需更精细的控制，可直接使用 Workflow API。所有工作流遵循相同模式：

```python
# 模式:
# 1. 创建 TranslatorConfig（LLM 设置）
# 2. 创建 WorkflowConfig（工作流设置）
# 3. 创建 Workflow 实例
# 4. workflow.read_path(文件)
# 5. await workflow.translate_async()
# 6. workflow.save_as_*(name=...) 或 export_to_*(...)
```

#### 可用工作流及输出方法

| 工作流 | 输入格式 | save_as_* | export_to_* | 关键配置选项 |
|:---|:---|:---|:---|:---|
| **MarkdownBasedWorkflow** | `.pdf`, `.docx`, `.md`, `.png`, `.jpg` | `html`, `markdown`, `markdown_zip` | `html`, `markdown`, `markdown_zip` | `convert_engine`, `translator_config` |
| **TXTWorkflow** | `.txt` | `txt`, `html` | `txt`, `html` | `translator_config` |
| **JsonWorkflow** | `.json` | `json`, `html` | `json`, `html` | `translator_config`, `json_paths` |
| **DocxWorkflow** | `.docx` | `docx`, `html` | `docx`, `html` | `translator_config`, `insert_mode` |
| **XlsxWorkflow** | `.xlsx`, `.csv` | `xlsx`, `html` | `xlsx`, `html` | `translator_config`, `insert_mode` |
| **SrtWorkflow** | `.srt` | `srt`, `html` | `srt`, `html` | `translator_config` |
| **EpubWorkflow** | `.epub` | `epub`, `html` | `epub`, `html` | `translator_config`, `insert_mode` |
| **HtmlWorkflow** | `.html`, `.htm` | `html` | `html` | `translator_config`, `insert_mode` |
| **AssWorkflow** | `.ass` | `ass`, `html` | `ass`, `html` | `translator_config` |

#### 关键配置选项

**通用 TranslatorConfig 选项：**

| 选项 | 类型 | 默认值 | 说明 |
|:---|:---|:---|:---|
| `base_url` | `str` | - | AI 平台基础 URL |
| `api_key` | `str` | - | AI 平台 API 密钥 |
| `model_id` | `str` | - | 模型 ID |
| `to_lang` | `str` | - | 目标语言 |
| `chunk_size` | `int` | 3000 | 文本分块大小 |
| `concurrent` | `int` | 10 | 并发请求数 |
| `temperature` | `float` | 0.3 | LLM 温度 |
| `timeout` | `int` | 60 | 请求超时（秒） |
| `retry` | `int` | 3 | 重试次数 |

**格式特定选项：**

| 选项 | 适用工作流 | 说明 |
|:---|:---|:---|
| `insert_mode` | Docx, Xlsx, Html, Epub | `"replace"`（默认）, `"append"`, `"prepend"` |
| `json_paths` | Json | JSONPath 表达式（如 `["$.*", "$.name"]`） |
| `separator` | Docx, Xlsx, Html, Epub | append/prepend 模式的文本分隔符 |
| `convert_engine` | MarkdownBased | `"mineru"`（默认）, `"docling"`, `"mineru_deploy"` |

#### 示例 1: 翻译一个 PDF 文件 (使用 `MarkdownBasedWorkflow`)

这是最常见的用例。我们将使用 `minerU` 引擎将 PDF 转换为 Markdown，然后使用 LLM 进行翻译。这里以异步方式为例。

```python
import asyncio
from docutranslate.workflow.md_based_workflow import MarkdownBasedWorkflow, MarkdownBasedWorkflowConfig
from docutranslate.converter.x2md.converter_mineru import ConverterMineruConfig
from docutranslate.translator.ai_translator.md_translator import MDTranslatorConfig
from docutranslate.exporter.md.md2html_exporter import MD2HTMLExporterConfig


async def main():
    # 1. 构建翻译器配置
    translator_config = MDTranslatorConfig(
        base_url="https://open.bigmodel.cn/api/paas/v4",  # AI 平台 Base URL
        api_key="YOUR_ZHIPU_API_KEY",  # AI 平台 API Key
        model_id="glm-4-air",  # 模型 ID
        to_lang="English",  # 目标语言
        chunk_size=3000,  # 文本分块大小
        concurrent=10,  # 并发数
        # glossary_generate_enable=True, # 启用自动生成术语表
        # glossary_dict={"Jobs":"乔布斯"}, # 传入术语表
        # system_proxy_enable=True,# 启用系统代理
    )

    # 2. 构建转换器配置 (使用 minerU)
    converter_config = ConverterMineruConfig(
        mineru_token="YOUR_MINERU_TOKEN",  # 你的 minerU Token
        formula_ocr=True  # 开启公式识别
    )

    # 3. 构建主工作流配置
    workflow_config = MarkdownBasedWorkflowConfig(
        convert_engine="mineru",  # 指定解析引擎
        converter_config=converter_config,  # 传入转换器配置
        translator_config=translator_config,  # 传入翻译器配置
        html_exporter_config=MD2HTMLExporterConfig(cdn=True)  # HTML 导出配置
    )

    # 4. 实例化工作流
    workflow = MarkdownBasedWorkflow(config=workflow_config)

    # 5. 读取文件并执行翻译
    print("开始读取和翻译文件...")
    workflow.read_path("path/to/your/document.pdf")
    await workflow.translate_async()
    # 或者使用同步的方式
    # workflow.translate()
    print("翻译完成！")

    # 6. 保存结果
    workflow.save_as_html(name="translated_document.html")
    workflow.save_as_markdown_zip(name="translated_document.zip")
    workflow.save_as_markdown(name="translated_document.md")  # 嵌入图片的markdown
    print("文件已保存到 ./output 文件夹。")

    # 或者直接获取内容字符串
    html_content = workflow.export_to_html()
    html_content = workflow.export_to_markdown()
    # print(html_content)


if __name__ == "__main__":
    asyncio.run(main())
```

### 其他工作流

所有工作流都遵循相同的模式。导入对应的配置和工作流，然后进行配置：

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

主要配置选项：
- **insert_mode**: `"replace"`, `"append"`, `"prepend"` (用于 docx/xlsx/html/epub)
- **json_paths**: JSONPath 表达式用于 JSON 翻译 (例如 `["$.*", "$.name"]`)
- **separator**: 用于 `"append"` / `"prepend"` 模式的文本分隔符

## 前置条件与配置详解

### 1. 获取大模型 API Key

翻译功能依赖于大型语言模型，您需要从相应的 AI 平台获取 `base_url`, `api_key` 和 `model_id`。

> 推荐模型：火山引擎的`doubao-seed-1-6-flash`、`doubao-seed-1-6`系列、智谱的`glm-4-flash`，阿里云的 `qwen-plus`、`qwen-flash`
> ，deepseek的`deepseek-chat`等。

> [302.AI](https://share.302.ai/BgRLAe)👈从该链接注册可享1美元免费额度

| 平台名称       | 获取APIkey                                                                              | baseurl                                                  |
|------------|---------------------------------------------------------------------------------------|----------------------------------------------------------|
| ollama     |                                                                                       | http://127.0.0.1:11434/v1                                |
| lm studio  |                                                                                       | http://127.0.0.1:1234/v1                                 |
| 302.AI     | [点击获取](https://share.302.ai/BgRLAe)                                                   | https://api.302.ai/v1                                    |
| openrouter | [点击获取](https://openrouter.ai/settings/keys)                                           | https://openrouter.ai/api/v1                             |
| openai     | [点击获取](https://platform.openai.com/api-keys)                                          | https://api.openai.com/v1/                               |
| gemini     | [点击获取](https://aistudio.google.com/u/0/apikey)                                        | https://generativelanguage.googleapis.com/v1beta/openai/ |
| deepseek   | [点击获取](https://platform.deepseek.com/api_keys)                                        | https://api.deepseek.com/v1                              |
| 智谱ai       | [点击获取](https://open.bigmodel.cn/usercenter/apikeys)                                   | https://open.bigmodel.cn/api/paas/v4                     |
| 腾讯混元       | [点击获取](https://console.cloud.tencent.com/hunyuan/api-key)                             | https://api.hunyuan.cloud.tencent.com/v1                 |
| 阿里云百炼      | [点击获取](https://bailian.console.aliyun.com/?tab=model#/api-key)                        | https://dashscope.aliyuncs.com/compatible-mode/v1        |
| 火山引擎       | [点击获取](https://console.volcengine.com/ark/region:ark+cn-beijing/apiKey?apikey=%7B%7D) | https://ark.cn-beijing.volces.com/api/v3                 |
| 硅基流动       | [点击获取](https://cloud.siliconflow.cn/account/ak)                                       | https://api.siliconflow.cn/v1                            |
| DMXAPI     | [点击获取](https://www.dmxapi.cn/token)                                                   | https://www.dmxapi.cn/v1                                 |
| 聚光AI       | [点击获取](https://ai.juguang.chat/console/token)                                         | https://ai.juguang.chat/v1                               |

### 2. PDF解析引擎（不需要翻译PDF的无需关心此处）

### 2.1 获取 minerU Token (在线解析PDF，免费，推荐)

如果您选择 `mineru`作为文档解析引擎（`convert_engine="mineru"`），则需要申请一个免费的 Token。

1. 访问 [minerU 官网](https://mineru.net/apiManage/docs) 注册并申请 API。
2. 在 [API Token 管理界面](https://mineru.net/apiManage/token) 创建一个新的 API Token。

> **注意**: minerU Token 有 14 天有效期，过期后请重新创建。

### 2.2. docling 引擎配置 (本地解析PDF)

如果您选择 `docling` 作为文档解析引擎（`convert_engine="docling"`），它会在首次使用时从 Hugging Face 下载所需的模型。

> 更好的选择是在[github releases](https://github.com/xunbu/docutranslate/releases)下载`docling_artifact.zip`解压到工作目录下。

**下载`docling`模型网络问题解决方案:**

1. **设置 Hugging Face 镜像 (推荐)**:

* **方法 A (环境变量)**: 设置系统环境变量 `HF_ENDPOINT` 并重启您的IDE或终端。
   ```
   HF_ENDPOINT=https://hf-mirror.com
   ```
* **方法 B (代码中设置)**: 在您的 Python 脚本开头添加以下代码。

```python
import os

os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
```

2. **离线使用 (提前下载模型包)**:

* 从 [GitHub Releases](https://github.com/xunbu/docutranslate/releases) 下载 `docling_artifact.zip`。
* 将其解压到您的项目目录中。
* 在配置中指定模型路径（若模型不在脚本同级目录里）：

```python
from docutranslate.converter.x2md.converter_docling import ConverterDoclingConfig

converter_config = ConverterDoclingConfig(
    artifact="./docling_artifact",  # 指向解压后的文件夹
    code_ocr=True,
    formula_ocr=True
)
```

### 2.3. 本地部署 MinerU 服务

在离线或内网环境中，推荐使用本地部署的 `minerU`，性能更好且无 API 限制。设置 `mineru_deploy_base_url` 为您的 minerU API 地址。

**Client SDK:**
```python
from docutranslate.sdk import Client

client = Client(
    api_key="YOUR_LLM_API_KEY",
    model_id="llama3",
    to_lang="中文",
    convert_engine="mineru_deploy",
    mineru_deploy_base_url="http://127.0.0.1:8000",  # 您的 minerU API 地址
)
result = client.translate("document.pdf")
result.save(fmt="markdown")
```

## FAQ

**Q: 翻译出来的还是原文？**
A: 查看日志报错，通常是 AI 平台欠费或网络问题。

**Q: 8010 端口被占用？**
A: 使用 `docutranslate -i -p 8011` 或设置 `DOCUTRANSLATE_PORT=8011`。

**Q: 支持 PDF 扫描件？**
A: 支持，使用 `mineru` 引擎具备 OCR 能力。

**Q: 第一次翻译 PDF 很慢？**
A: `docling` 首次需要下载模型。使用 Hugging Face 镜像或预下载 artifact。

**Q: 内网/离线环境使用？**
A: 可以。使用本地 LLM（Ollama/LM Studio）和本地 minerU 或 docling。

**Q: PDF 缓存机制？**
A: `MarkdownBasedWorkflow` 在内存中缓存解析结果（最近 10 次）。可通过 `DOCUTRANSLATE_CACHE_NUM` 配置。

**Q: 启用代理？**
A: 在 TranslatorConfig 中设置 `system_proxy_enable=True`。

## Star History

<a href="https://www.star-history.com/#xunbu/docutranslate&Date">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=xunbu/docutranslate&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=xunbu/docutranslate&type=Date" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=xunbu/docutranslate&type=Date" />
 </picture>
</a>

## 赞赏支持

欢迎支持作者，烦请在备注中说明一下赞赏原因哟

<p align="center">
  <img src="./images/赞赏码.jpg" alt="赞赏码" style="width: 250px;">
</p>