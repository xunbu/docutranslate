# DocuTranslate MCP Server 配置指南

## 概述

DocuTranslate 现在支持 MCP (Model Context Protocol)，可以将文档翻译功能提供给 AI 助手使用。

## 安装

### 安装带 MCP 支持的 DocuTranslate

```bash
# 使用 pip
pip install docutranslate[mcp]

# 使用 uv
uv add docutranslate[mcp]
```

## 配置方式

### 方式一：通过环境变量配置（推荐）

可以通过设置环境变量来预先配置 MCP 服务器，这样就不需要每次都调用 `configure_client` 工具了。

**支持的环境变量：**

| 环境变量 | 说明 | 必需 |
|----------|------|------|
| `DOCUTRANSLATE_API_KEY` | AI 平台 API 密钥 | 是 |
| `DOCUTRANSLATE_BASE_URL` | AI 平台基础 URL | 是 |
| `DOCUTRANSLATE_MODEL_ID` | 模型 ID | 是 |
| `DOCUTRANSLATE_TO_LANG` | 目标语言（默认：中文） | 否 |
| `DOCUTRANSLATE_CONCURRENT` | 并发请求数（默认：10） | 否 |
| `DOCUTRANSLATE_CONVERT_ENGINE` | PDF 转换引擎 | 否 |
| `DOCUTRANSLATE_MINERU_TOKEN` | MinerU API Token | 否 |

**在 Claude Desktop 配置中设置环境变量：**

```json
{
  "mcpServers": {
    "docutranslate": {
      "command": "python",
      "args": ["-m", "docutranslate", "--mcp"],
      "env": {
        "DOCUTRANSLATE_API_KEY": "sk-xxxxxx",
        "DOCUTRANSLATE_BASE_URL": "https://api.openai.com/v1",
        "DOCUTRANSLATE_MODEL_ID": "gpt-4o",
        "DOCUTRANSLATE_TO_LANG": "中文"
      }
    }
  }
}
```

### 方式二：通过工具配置

如果没有设置环境变量，可以使用 `configure_client` 工具来配置。

## MCP 客户端配置

### 在 Claude Desktop 中配置

编辑 Claude Desktop 配置文件：

### 在 Cherry Studio 中配置

Cherry Studio 是一个开源的 AI 助手应用，也支持 MCP 协议。

1. 打开 Cherry Studio
2. 进入设置 → 扩展服务 (或 MCP 设置)
3. 找到 "MCP 服务器" 或 "添加自定义服务器" 选项
4. 添加新的 MCP 服务器配置：

**配置方式一：使用 Python 模块（推荐）**

| 配置项 | 值 |
|--------|-----|
| 名称 | `docutranslate` |
| 命令 | `python` |
| 参数 | `-m docutranslate --mcp` |

或者使用 JSON 格式配置：

```json
{
  "mcpServers": {
    "docutranslate": {
      "command": "python",
      "args": ["-m", "docutranslate", "--mcp"]
    }
  }
}
```

**配置方式二：使用虚拟环境的 Python**

如果你使用虚拟环境，需要指定 Python 的完整路径：

**macOS/Linux:**
```json
{
  "mcpServers": {
    "docutranslate": {
      "command": "path/to/your/venv/bin/python",
      "args": ["-m", "docutranslate", "--mcp"]
    }
  }
}
```

**Windows:**
```json
{
  "mcpServers": {
    "docutranslate": {
      "command": "C:\\path\\to\\venv\\Scripts\\python.exe",
      "args": ["-m", "docutranslate", "--mcp"]
    }
  }
}
```

**验证连接：**

配置完成后：
1. 重启 Cherry Studio
2. 在聊天中查看是否有 DocuTranslate 工具可用
3. 尝试调用 `get_supported_formats` 工具测试连接

---

### 在 Claude Desktop 中配置

编辑 Claude Desktop 配置文件：

**Windows:**
```
%APPDATA%\Claude\claude_desktop_config.json
```

**macOS:**
```
~/Library/Application Support/Claude/claude_desktop_config.json
```

**Linux:**
```
~/.config/Claude/claude_desktop_config.json
```

### 配置方式一：使用 Python 模块（推荐，虚拟环境友好）

这种方式不要求全局安装，在虚拟环境中也能正常工作：

```json
{
  "mcpServers": {
    "docutranslate": {
      "command": "python",
      "args": ["-m", "docutranslate", "--mcp"]
    }
  }
}
```

如果需要指定特定的 Python 解释器（如虚拟环境中的 Python）：

**macOS/Linux:**
```json
{
  "mcpServers": {
    "docutranslate": {
      "command": "path/to/your/venv/bin/python",
      "args": ["-m", "docutranslate", "--mcp"]
    }
  }
}
```

**Windows:**
```json
{
  "mcpServers": {
    "docutranslate": {
      "command": "C:\\path\\to\\venv\\Scripts\\python.exe",
      "args": ["-m", "docutranslate", "--mcp"]
    }
  }
}
```

### 配置方式二：使用控制台脚本（全局安装）

如果已全局安装 docutranslate：

```json
{
  "mcpServers": {
    "docutranslate": {
      "command": "docutranslate",
      "args": ["--mcp"]
    }
  }
}
```

使用虚拟环境的完整路径：

**macOS/Linux:**
```json
{
  "mcpServers": {
    "docutranslate": {
      "command": "path/to/your/venv/bin/docutranslate",
      "args": ["--mcp"]
    }
  }
}
```

**Windows:**
```json
{
  "mcpServers": {
    "docutranslate": {
      "command": "C:\\path\\to\\venv\\Scripts\\docutranslate.exe",
      "args": ["--mcp"]
    }
  }
}
```

### 配置方式三：直接运行 mcp 模块

也可以直接运行 mcp 模块：

```json
{
  "mcpServers": {
    "docutranslate": {
      "command": "python",
      "args": ["-m", "docutranslate.mcp"]
    }
  }
}
```

## 可用工具

### 1. `configure_client` - 配置客户端

配置 LLM 设置。如果已经通过环境变量配置，此工具可以覆盖环境变量配置。

**参数：**
- `api_key`: AI 平台 API 密钥
- `base_url`: AI 平台基础 URL
- `model_id`: 模型 ID
- `to_lang`: 目标语言（默认：中文）
- `concurrent`: 并发请求数（默认：10）
- `convert_engine`: PDF 转换引擎
- `mineru_token`: MinerU API Token

**示例：**
```
请配置 DocuTranslate，使用以下设置：
- API Key: sk-xxxxxx
- Base URL: https://api.openai.com/v1
- Model: gpt-4o
- 目标语言: 中文
```

### 2. `get_status` - 获取服务器状态

查看当前服务器状态、配置信息和环境变量状态。

**示例：**
```
请查看 DocuTranslate 的当前状态。
```

### 3. `translate_file` - 翻译文件

翻译本地文件系统中的文档。

**参数：**
- `file_path` (必需): 文件路径
- `to_lang`: 目标语言（覆盖客户端配置）
- `workflow_type`: 工作流类型
- `skip_translate`: 仅解析不翻译
- `output_format`: 输出格式
- `output_dir`: 输出目录（默认：./output）
- `output_name`: 输出文件名（可选，自动生成）
- `save_to_file`: 是否保存到文件（默认：True）

**示例：**
```
请翻译这个文件：/path/to/document.pdf
输出格式使用 HTML，保存到 /tmp/translated 目录。
```

### 4. `translate_content` - 翻译内容

翻译 base64 编码的文件内容。

**参数：**
- `content` (必需): base64 编码的文件内容
- `filename` (必需): 文件名（用于格式检测）
- `to_lang`: 目标语言
- `output_format`: 输出格式
- `output_dir`: 输出目录（默认：./output）
- `output_name`: 输出文件名（可选，自动生成）
- `save_to_file`: 是否保存到文件（默认：True）

### 5. `get_supported_formats` - 获取支持的格式

查看支持的文件格式列表。

### 6. `get_client_config` - 获取客户端配置

查看当前配置（不包含敏感数据）。

## 可用资源

### `docutranslate://info`

服务器信息，包含版本和状态。

### `docutranslate://formats`

支持的格式信息。

## 支持的文件格式

### 输入格式
PDF, DOCX, DOC, XLSX, XLS, CSV, MD, Markdown, TXT, JSON, EPUB, SRT, ASS, PPTX, PPT, HTML, HTM, PNG, JPG

### 输出格式
- PDF/图片: HTML, Markdown, Markdown+Zip, DOCX
- DOCX: DOCX, HTML
- XLSX: XLSX, HTML
- PPTX: PPTX
- TXT: TXT, HTML
- JSON: JSON, HTML
- 字幕: SRT/ASS, HTML
- EPUB: EPUB, HTML

## 完整使用示例

### 示例 1: 翻译 PDF 文档

1. 首先配置客户端：
```
请使用 configure_client 配置 DocuTranslate：
- api_key: 你的-api-key
- base_url: https://api.openai.com/v1
- model_id: gpt-4o
- to_lang: 中文
- convert_engine: mineru
- mineru_token: 你的-mineru-token
```

2. 然后翻译文件：
```
请翻译 /Users/me/Documents/paper.pdf，输出格式为 HTML。
```

### 示例 2: 翻译 Word 文档

```
请翻译 /path/to/document.docx，保持 DOCX 格式。
```

### 示例 3: 仅解析文档不翻译

```
请处理 /path/to/scan.pdf，但跳过翻译步骤，只进行 OCR 解析。
```

## 故障排除

### 问题: "MCP dependencies not installed"

**解决:** 安装 MCP 依赖：
```bash
pip install docutranslate[mcp]
```

### 问题: "Client not configured"

**解决:**
1. 可以通过设置环境变量 `DOCUTRANSLATE_API_KEY`、`DOCUTRANSLATE_BASE_URL`、`DOCUTRANSLATE_MODEL_ID` 来配置
2. 或者调用 `configure_client` 工具配置 LLM 设置
3. 使用 `get_status` 工具查看当前配置状态

### 问题: Claude Desktop 无法连接

**解决:**
1. 检查 `docutranslate` 命令是否在 PATH 中
2. 尝试使用绝对路径
3. 重启 Claude Desktop
4. 查看日志：Help > Debug > Logs

## AI 平台配置参考

| 平台 | base_url | 示例 model_id |
|------|----------|---------------|
| OpenAI | https://api.openai.com/v1 | gpt-4o, gpt-4o-mini |
| 智谱 | https://open.bigmodel.cn/api/paas/v4 | glm-4-flash, glm-4-air |
| DeepSeek | https://api.deepseek.com/v1 | deepseek-chat |
| 硅基流动 | https://api.siliconflow.cn/v1 | Qwen/Qwen2.5-7B-Instruct |
| Ollama | http://127.0.0.1:11434/v1 | llama3.2 |
