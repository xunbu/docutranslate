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

- **DocuTranslate**: 标准版，使用在线的 `minerU` 引擎解析PDF文档，如果不需要本地解析pdf选这个版本（推荐）。
- **DocuTranslate_full**: 完整版，内置 `docling` 本地PDF解析引擎，需要本地解析pdf选这个版本。
> 1.5.1版本以后支持调用本地部署的mineru服务

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

新版 DocuTranslate 的核心是 **工作流 (Workflow)**。每个工作流都是一个专门为特定类型文件设计的、完整的端到端翻译管道。您不再与一个庞大的类交互，而是根据您的文件类型选择并配置一个合适的工作流。

**基本使用流程如下：**

1. **选择工作流**：根据您的输入文件类型（例如，PDF/Word 或 TXT）选择一个工作流，如 `MarkdownBasedWorkflow` 或 `TXTWorkflow`。
2. **构建配置**：为所选工作流创建相应的配置对象（如 `MarkdownBasedWorkflowConfig`）。此配置对象包含了所有需要的子配置，例如：
    * **转换器配置 (Converter Config)**: 定义如何将原始文件（如PDF）转换为 Markdown。
    * **翻译器配置 (Translator Config)**: 定义使用哪个 LLM、API-Key、目标语言等。
    * **导出器配置 (Exporter Config)**: 定义输出格式（如HTML）的特定选项。
3. **实例化工作流**：使用配置对象创建工作流实例。
4. **执行翻译**：调用工作流的 `.read_*()` 和 `.translate()` / `.translate_async()` 方法。
5. **导出/保存结果**：调用 `.export_to_*()` 或 `.save_as_*()` 方法获取或保存翻译结果。

## 可用工作流

| 工作流                         | 适用场景                                                    | 输入格式                                     | 输出格式                   | 核心配置类                         |
|:----------------------------|:--------------------------------------------------------|:-----------------------------------------|:-----------------------|:------------------------------|
| **`MarkdownBasedWorkflow`** | 处理富文本文档，如PDF、Word、图片等。流程为：`文件 -> Markdown -> 翻译 -> 导出`。 | `.pdf`, `.docx`, `.md`, `.png`, `.jpg` 等 | `.md`, `.zip`, `.html` | `MarkdownBasedWorkflowConfig` |
| **`TXTWorkflow`**           | 处理纯文本文档。流程为：`txt -> 翻译 -> 导出`。                          | `.txt` 及其他纯文本格式                          | `.txt`, `.html`        | `TXTWorkflowConfig`           |
| **`JsonWorkflow`**          | 处理json文件。流程为：`json -> 翻译 -> 导出`。                        | `.json`                                  | `.json`, `.html`       | `JsonWorkflowConfig`          |
| **`DocxWorkflow`**          | 处理docx文件。流程为：`docx -> 翻译 -> 导出`。                        | `.docx`                                  | `.docx`, `.html`       | `docxWorkflowConfig`          |
| **`XlsxWorkflow`**          | 处理xlsx文件。流程为：`xlsx -> 翻译 -> 导出`。                        | `.xlsx`、`.csv`                           | `.xlsx`, `.html`       | `XlsxWorkflowConfig`          |
| **`SrtWorkflow`**           | 处理srt文件。流程为：`srt -> 翻译 -> 导出`。                          | `.srt`                                   | `.srt`, `.html`        | `SrtWorkflowConfig`           |
| **`EpubWorkflow`**          | 处理epub文件。流程为：`epub -> 翻译 -> 导出`。                        | `.epub`                                  | `.epub`, `.html`       | `EpubWorkflowConfig`          |
| **`HtmlWorkflow`**          | 处理html文件。流程为：`html -> 翻译 -> 导出`。                        | `.html`, `.htm`                          | `.html`                | `HtmlWorkflowConfig`          |

> 在交互式界面中可以导出pdf格式

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

### 示例 1: 翻译一个 PDF 文件 (使用 `MarkdownBasedWorkflow`)

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
    
    # 使用本地部署mineru服务
    # from docutranslate.converter.x2md.converter_mineru_deploy import ConverterMineruDeployConfig
    # converter_config = ConverterMineruDeployConfig(
    #     base_url = "http://127.0.0.1:8000",
    #     output_dir= "./output",#受mineru限制，解析后的文件会保存到output_dir下，需要定期清理
    #     backend= "pipeline",
    #     start_page_id = 0,
    #     end_page_id = 99999,
    # )
    # workflow_config = MarkdownBasedWorkflowConfig(
    #     convert_engine="mineru_deploy",  # 指定解析引擎
    #     converter_config=converter_config,  # 传入转换器配置
    #     translator_config=translator_config,  # 传入翻译器配置
    #     html_exporter_config=MD2HTMLExporterConfig(cdn=True)  # HTML 导出配置
    # )

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

### 示例 2: 翻译一个 TXT 文件 (使用 `TXTWorkflow`)

对于纯文本文件，流程更简单，因为它不需要文档解析（转换）步骤。这里以异步方式为例。

```python
import asyncio
from docutranslate.workflow.txt_workflow import TXTWorkflow, TXTWorkflowConfig
from docutranslate.translator.ai_translator.txt_translator import TXTTranslatorConfig
from docutranslate.exporter.txt.txt2html_exporter import TXT2HTMLExporterConfig


async def main():
    # 1. 构建翻译器配置
    translator_config = TXTTranslatorConfig(
        base_url="https://api.openai.com/v1/",
        api_key="YOUR_OPENAI_API_KEY",
        model_id="gpt-4o",
        to_lang="中文",
    )

    # 2. 构建主工作流配置
    workflow_config = TXTWorkflowConfig(
        translator_config=translator_config,
        html_exporter_config=TXT2HTMLExporterConfig(cdn=True)
    )

    # 3. 实例化工作流
    workflow = TXTWorkflow(config=workflow_config)

    # 4. 读取文件并执行翻译
    workflow.read_path("path/to/your/notes.txt")
    await workflow.translate_async()
    # 或者使用同步的方法
    # workflow.translate()

    # 5. 保存结果
    workflow.save_as_txt(name="translated_notes.txt")
    print("TXT 文件已保存。")

    # 也可以导出翻译后的纯文本
    text = workflow.export_to_txt()


if __name__ == "__main__":
    asyncio.run(main())
```

### 示例 3: 翻译一个 json 文件 (使用 `JsonWorkflow`)

这里以异步方式为例。其中JsonTranslatorConfig的json_paths项需要指明要翻译的json路径(满足jsonpath-ng语法规范)
，仅与json路径匹配的值会被翻译。

```python
import asyncio

from docutranslate.exporter.js.json2html_exporter import Json2HTMLExporterConfig
from docutranslate.translator.ai_translator.json_translator import JsonTranslatorConfig
from docutranslate.workflow.json_workflow import JsonWorkflowConfig, JsonWorkflow


async def main():
    # 1. 构建翻译器配置
    translator_config = JsonTranslatorConfig(
        base_url="https://api.openai.com/v1/",
        api_key="YOUR_OPENAI_API_KEY",
        model_id="gpt-4o",
        to_lang="中文",
        json_paths=["$.*", "$.name"]  # 满足jsonpath-ng路径语法,匹配路径的值都会被翻译
    )

    # 2. 构建主工作流配置
    workflow_config = JsonWorkflowConfig(
        translator_config=translator_config,
        html_exporter_config=Json2HTMLExporterConfig(cdn=True)
    )

    # 3. 实例化工作流
    workflow = JsonWorkflow(config=workflow_config)

    # 4. 读取文件并执行翻译
    workflow.read_path("path/to/your/notes.json")
    await workflow.translate_async()
    # 或者使用同步的方法
    # workflow.translate()

    # 5. 保存结果
    workflow.save_as_json(name="translated_notes.json")
    print("json文件已保存。")

    # 也可以导出翻译后的json文本
    text = workflow.export_to_json()


if __name__ == "__main__":
    asyncio.run(main())
```

### 示例 4: 翻译一个 docx 文件 (使用 `DocxWorkflow`)

这里以异步方式为例。

```python
import asyncio

from docutranslate.exporter.docx.docx2html_exporter import Docx2HTMLExporterConfig
from docutranslate.translator.ai_translator.docx_translator import DocxTranslatorConfig
from docutranslate.workflow.docx_workflow import DocxWorkflowConfig, DocxWorkflow


async def main():
    # 1. 构建翻译器配置
    translator_config = DocxTranslatorConfig(
        base_url="https://api.openai.com/v1/",
        api_key="YOUR_OPENAI_API_KEY",
        model_id="gpt-4o",
        to_lang="中文",
        insert_mode="replace",  # 备选项 "replace", "append", "prepend"
        separator="\n",  # "append", "prepend"模式时使用的分隔符
    )

    # 2. 构建主工作流配置
    workflow_config = DocxWorkflowConfig(
        translator_config=translator_config,
        html_exporter_config=Docx2HTMLExporterConfig(cdn=True)
    )

    # 3. 实例化工作流
    workflow = DocxWorkflow(config=workflow_config)

    # 4. 读取文件并执行翻译
    workflow.read_path("path/to/your/notes.docx")
    await workflow.translate_async()
    # 或者使用同步的方法
    # workflow.translate()

    # 5. 保存结果
    workflow.save_as_docx(name="translated_notes.docx")
    print("docx文件已保存。")

    # 也可以导出翻译后的docx的二进制
    text_bytes = workflow.export_to_docx()


if __name__ == "__main__":
    asyncio.run(main())
```

### 示例 5: 翻译一个 xlsx 文件 (使用 `XlsxWorkflow`)

这里以异步方式为例。

```python
import asyncio

from docutranslate.exporter.xlsx.xlsx2html_exporter import Xlsx2HTMLExporterConfig
from docutranslate.translator.ai_translator.xlsx_translator import XlsxTranslatorConfig
from docutranslate.workflow.xlsx_workflow import XlsxWorkflowConfig, XlsxWorkflow


async def main():
    # 1. 构建翻译器配置
    translator_config = XlsxTranslatorConfig(
        base_url="https://api.openai.com/v1/",
        api_key="YOUR_OPENAI_API_KEY",
        model_id="gpt-4o",
        to_lang="中文",
        insert_mode="replace",  # 备选项 "replace", "append", "prepend"
        separator="\n",  # "append", "prepend"模式时使用的分隔符
    )

    # 2. 构建主工作流配置
    workflow_config = XlsxWorkflowConfig(
        translator_config=translator_config,
        html_exporter_config=Xlsx2HTMLExporterConfig(cdn=True)
    )

    # 3. 实例化工作流
    workflow = XlsxWorkflow(config=workflow_config)

    # 4. 读取文件并执行翻译
    workflow.read_path("path/to/your/notes.xlsx")
    await workflow.translate_async()
    # 或者使用同步的方法
    # workflow.translate()

    # 5. 保存结果
    workflow.save_as_xlsx(name="translated_notes.xlsx")
    print("xlsx文件已保存。")

    # 也可以导出翻译后的xlsx的二进制
    text_bytes = workflow.export_to_xlsx()


if __name__ == "__main__":
    asyncio.run(main())
```

### 示例 5: 其它workflow的配置项(使用 `HtmlWorkflow`、`EpubWorkflow`)

这里以异步方式为例。

```python
# HtmlWorkflow
from docutranslate.translator.ai_translator.html_translator import HtmlTranslatorConfig
from docutranslate.workflow.html_workflow import HtmlWorkflowConfig, HtmlWorkflow


async def html():
    # 1. 构建翻译器配置
    translator_config = HtmlTranslatorConfig(
        base_url="https://api.openai.com/v1/",
        api_key="YOUR_OPENAI_API_KEY",
        model_id="gpt-4o",
        to_lang="中文",
        insert_mode="replace",  # 备选项 "replace", "append", "prepend"
        separator="\n",  # "append", "prepend"模式时使用的分隔符
    )

    # 2. 构建主工作流配置
    workflow_config = HtmlWorkflowConfig(
        translator_config=translator_config,
    )
    workflow_html = HtmlWorkflow(config=workflow_config)


# EpubWorkflow
from docutranslate.exporter.epub.epub2html_exporter import Epub2HTMLExporterConfig
from docutranslate.translator.ai_translator.epub_translator import EpubTranslatorConfig
from docutranslate.workflow.epub_workflow import EpubWorkflowConfig, EpubWorkflow


async def epub():
    # 1. 构建翻译器配置
    translator_config = EpubTranslatorConfig(
        base_url="https://api.openai.com/v1/",
        api_key="YOUR_OPENAI_API_KEY",
        model_id="gpt-4o",
        to_lang="中文",
        insert_mode="replace",  # 备选项 "replace", "append", "prepend"
        separator="\n",  # "append", "prepend"模式时使用的分隔符
    )

    # 2. 构建主工作流配置
    workflow_config = EpubWorkflowConfig(
        translator_config=translator_config,
        html_exporter_config=Epub2HTMLExporterConfig(cdn=True),
    )
    workflow_epub = EpubWorkflow(config=workflow_config)
```

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

## FAQ

**Q: 为什么翻译出来的还是原文**  
A: 查看一下日志报了什么错，一般是AI平台欠费或网络有问题（查看是否需要开启系统代理）。

**Q: 8010 端口被占用了怎么办？**  
A: 使用 `-p` 参数指定一个新端口，或设置 `DOCUTRANSLATE_PORT` 环境变量。

**Q: 支持PDF扫描件的翻译吗？**  
A: 支持。请使用 `mineru` 解析引擎，它具备强大的 OCR 能力。

**Q: 第一次翻译PDF为什么很慢？**  
A: 如果您使用 `docling` 引擎，它首次运行时需要从 Hugging Face 下载模型。请参考上文的“网络问题解决方案”来加速此过程。

**Q: 如何在内网（离线）环境使用？**  
A: 完全可以。您需要满足以下条件：

1. **本地 LLM**: 使用 [Ollama](https://ollama.com/) 或 [LM Studio](https://lmstudio.ai/) 等工具在本地部署语言模型，并在
   `TranslatorConfig` 中填入本地模型的 `base_url`。
2. **本地PDF解析引擎**（仅解析pdf需要）: 使用 `docling` 引擎，并按照上文“离线使用”的指引提前下载模型包。

**Q: PDF解析缓存机制是如何工作的？**  
A: `MarkdownBasedWorkflow` 会自动缓存文档解析（文件到Markdown的转换）的结果，以避免重复解析消耗时间和资源。缓存默认保存在内存中，并会记录最近的10次解析。您可以通过
`DOCUTRANSLATE_CACHE_NUM` 环境变量来修改缓存数量。

**Q: 如何让软件可以经过代理**  
A: 软件默认不使用系统代理，可以在`TranslatorConfig中令system_proxy_enable=True` 启用系统代理

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