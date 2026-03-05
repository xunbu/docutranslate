# DocuTranslate MCP Server

[English](#english) | [简体中文](#简体中文)

---

## English

### Installation

```bash
pip install docutranslate[mcp]
```

### Usage

#### Important: Use Virtual Environment Interpreter

Always use the Python interpreter from your virtual environment in MCP configurations. This ensures all dependencies are available.

#### Method 1: Stdio Mode (Recommended for Claude Desktop, Windsurf)

```bash
docutranslate --mcp
```

##### Using uvx (No Installation Required)

```json
{
  "mcpServers": {
    "docutranslate": {
      "command": "uvx",
      "args": ["--from", "docutranslate[mcp]", "docutranslate", "--mcp"],
      "env": {
        "DOCUTRANSLATE_API_KEY": "sk-xxxxxx",
        "DOCUTRANSLATE_BASE_URL": "https://api.openai.com/v1",
        "DOCUTRANSLATE_MODEL_ID": "gpt-4o",
        "DOCUTRANSLATE_TO_LANG": "Chinese",
        "DOCUTRANSLATE_CONCURRENT": "10",
        "DOCUTRANSLATE_CONVERT_ENGINE": "mineru",
        "DOCUTRANSLATE_MINERU_TOKEN": "your-mineru-token"
      }
    }
  }
}
```

Add to your MCP configuration (**use the full Python path from your virtual environment**):

```json
{
  "mcpServers": {
    "docutranslate": {
      "command": "/path/to/your/venv/bin/python",
      "args": ["-m", "docutranslate.mcp"],
      "env": {
        "DOCUTRANSLATE_API_KEY": "sk-xxxxxx",
        "DOCUTRANSLATE_BASE_URL": "https://api.openai.com/v1",
        "DOCUTRANSLATE_MODEL_ID": "gpt-4o",
        "DOCUTRANSLATE_TO_LANG": "Chinese",
        "DOCUTRANSLATE_CONCURRENT": "10",
        "DOCUTRANSLATE_CONVERT_ENGINE": "mineru",
        "DOCUTRANSLATE_MINERU_TOKEN": "your-mineru-token"
      }
    }
  }
}
```

**Windows example:**

```json
{
  "mcpServers": {
    "docutranslate": {
      "command": "C:\\path\\to\\your\\venv\\Scripts\\python.exe",
      "args": ["-m", "docutranslate.mcp"],
      "env": {
        "DOCUTRANSLATE_API_KEY": "sk-xxxxxx",
        "DOCUTRANSLATE_BASE_URL": "https://api.openai.com/v1",
        "DOCUTRANSLATE_MODEL_ID": "gpt-4o",
        "DOCUTRANSLATE_TO_LANG": "Chinese",
        "DOCUTRANSLATE_CONCURRENT": "10",
        "DOCUTRANSLATE_CONVERT_ENGINE": "mineru",
        "DOCUTRANSLATE_MINERU_TOKEN": "your-mineru-token"
      }
    }
  }
}
```

Or if you have `docutranslate` available in PATH:

```json
{
  "mcpServers": {
    "docutranslate": {
      "command": "docutranslate",
      "args": ["--mcp"],
      "env": {
        "DOCUTRANSLATE_API_KEY": "sk-xxxxxx",
        "DOCUTRANSLATE_BASE_URL": "https://api.openai.com/v1",
        "DOCUTRANSLATE_MODEL_ID": "gpt-4o",
        "DOCUTRANSLATE_TO_LANG": "Chinese",
        "DOCUTRANSLATE_CONCURRENT": "10",
        "DOCUTRANSLATE_CONVERT_ENGINE": "mineru",
        "DOCUTRANSLATE_MINERU_TOKEN": "your-mineru-token"
      }
    }
  }
}
```

#### Method 2: SSE Mode (Recommended for Cherry Studio)

```bash
docutranslate --mcp --transport sse --mcp-host 127.0.0.1 --mcp-port 8000
```

Or using the module directly with virtual environment Python:

```bash
/path/to/your/venv/bin/python -m docutranslate.mcp --transport sse --host 127.0.0.1 --port 8000
```

Configure the SSE endpoint in your client: `http://127.0.0.1:8000/mcp/sse`

#### Method 3: Streamable HTTP Mode

```bash
docutranslate --mcp --transport streamable-http --mcp-host 127.0.0.1 --mcp-port 8000
```

#### Method 4: Combined Mode with Web UI (Recommended!)

Run both Web UI and MCP server together, sharing the same task queue:

```bash
docutranslate -i --with-mcp
```

This starts:
- Web UI at `http://127.0.0.1:8010`
- MCP SSE endpoint at `http://127.0.0.1:8010/mcp/sse`
- **Tasks are shared between Web UI and MCP!**

**Note**: In this mode, MCP uses the same host and port as the Web backend automatically.

### Configuration via Environment Variables

You can pre-configure the MCP server using environment variables, so you don't need to call the configuration tool every time.

**Supported environment variables:**

| Environment Variable | Description | Required |
|---------------------|-------------|----------|
| `DOCUTRANSLATE_API_KEY` | AI platform API key | Yes |
| `DOCUTRANSLATE_BASE_URL` | AI platform base URL | Yes |
| `DOCUTRANSLATE_MODEL_ID` | Model ID | Yes |
| `DOCUTRANSLATE_TO_LANG` | Target language (default: Chinese) | No |
| `DOCUTRANSLATE_CONCURRENT` | Concurrent requests (default: 10) | No |
| `DOCUTRANSLATE_CONVERT_ENGINE` | PDF conversion engine | No |
| `DOCUTRANSLATE_MINERU_TOKEN` | MinerU API Token | No |

### MCP Tools Reference

| Tool | Description |
|------|-------------|
| `submit_task` | Submit a translation task, returns task_id immediately |
| `get_task_status` | Get current status, shows all formats and attachments when completed |
| `download_file` | Download translated file or attachment to local filesystem |
| `release_task` | Release task resources (temp files, etc.) |
| `cancel_task` | Cancel a pending or running task |
| `load_glossary_file` | Load a glossary file (JSON or CSV) for use in submit_task |
| `configure_client` | Configure client LLM settings |
| `get_client_config` | Get current configuration (without sensitive data) |
| `get_status` | Get server status and info |
| `get_supported_formats` | Get list of supported formats |

#### `submit_task` - Submit Translation Task

Submit a file for translation in async mode, returns task_id immediately without blocking.

**Parameters:**
- `file_path` (required): Path to the file, or a URL starting with http:// or https://
- `api_key`: AI platform API key (overrides client config)
- `base_url`: AI platform base URL (overrides client config)
- `model_id`: Model ID (overrides client config)
- `to_lang`: Target language (overrides client config)
- `workflow_type`: Workflow type
- `convert_engine`: PDF conversion engine
- `mineru_token`: MinerU API Token
- And many other advanced parameters...

**Example workflow:**
```
1. submit_task(file_path="doc.pdf", api_key="sk-...", model_id="gpt-4o")
   → task_id="abc-123"

2. get_task_status("abc-123")
   → { "status": "running", "progress_percent": 45 }

3. get_task_status("abc-123")  # when complete
   → Translation completed!
   → Available formats: docx, html, markdown
   → Attachments: glossary
   → Use download_file to save files

4. download_file(task_id="abc-123", file_name="docx", output_dir="./output")
   → File saved to ./output/doc_translated.docx

5. download_file(task_id="abc-123", file_name="glossary", output_dir="./output")
   → File saved to ./output/glossary.csv

6. release_task("abc-123")  # cleanup temp files
```

#### `get_task_status` - Get Task Status

Query the current status of a task.

**Parameters:**
- `task_id` (required): The task ID to query
- `wait_seconds`: Maximum seconds to wait for status change before returning (0 = return immediately)

**Returns:**
- Current status: `idle`, `running`, `completed`, `error`
- Progress percentage (0-100)
- Available formats when completed
- Attachments when completed

#### `download_file` - Download Translated File

Download a translated file or attachment to your local filesystem.

**Parameters:**
- `task_id` (required): The task ID
- `file_name` (required): File name to download (e.g., "docx", "html", "markdown", "glossary")
- `output_dir` (required): Output directory
- `output_name`: Custom output filename (optional, auto-generated if not provided)

#### `release_task` - Release Task Resources

Clean up temporary files and release resources for a completed task.

**Parameters:**
- `task_id` (required): The task ID to release

#### `cancel_task` - Cancel a Task

Cancel a pending or running task.

**Parameters:**
- `task_id` (required): The task ID to cancel

#### `load_glossary_file` - Load Glossary File

Load a glossary file (JSON or CSV) and return it as a JSON string for use in submit_task.

**Supports:**
- JSON files with format: `{"原文": "译文", "Original": "Translated"}`
- CSV files with two columns: first column = original, second column = translated

**Parameters:**
- `file_path` (required): Path to the glossary file (.json or .csv), or a URL starting with http:// or https://

#### `configure_client` - Configure Client

Configure LLM settings. If already configured via environment variables, this tool can override them.

**Parameters:**
- `api_key`: AI platform API key
- `base_url`: AI platform base URL
- `model_id`: Model ID
- `to_lang`: Target language (default: Chinese)
- `concurrent`: Concurrent requests (default: 10)
- `convert_engine`: PDF conversion engine
- `mineru_token`: MinerU API Token

**Example:**
```
Please configure DocuTranslate with these settings:
- API Key: sk-xxxxxx
- Base URL: https://api.openai.com/v1
- Model: gpt-4o
- Target language: Chinese
```

#### `get_client_config` - Get Client Configuration

Get the current client configuration (without sensitive data like API keys).

**Returns:** Current settings with API keys masked.

#### `get_status` - Get Server Status

Get server status and information.

**Returns:**
- Server status
- Version information
- Configuration status (whether client is configured)
- Active task count

#### `get_supported_formats` - Get Supported Formats

Get list of supported input and output formats.

**Returns:**
- Input formats
- Output formats by file type

### Supported File Formats

#### Input Formats
PDF, DOCX, DOC, XLSX, XLS, CSV, MD, Markdown, TXT, JSON, EPUB, SRT, ASS, PPTX, PPT, HTML, HTM, PNG, JPG

#### Output Formats
- PDF/Images: HTML, Markdown, Markdown+Zip, DOCX
- DOCX: DOCX, HTML
- XLSX: XLSX, HTML
- PPTX: PPTX
- TXT: TXT, HTML
- JSON: JSON, HTML
- Subtitles: SRT/ASS, HTML
- EPUB: EPUB, HTML

### AI Platform Configuration Reference

| Platform | base_url | Example model_id |
|----------|----------|------------------|
| OpenAI | https://api.openai.com/v1 | gpt-4o, gpt-4o-mini |
| Zhipu | https://open.bigmodel.cn/api/paas/v4 | glm-4-flash, glm-4-air |
| DeepSeek | https://api.deepseek.com/v1 | deepseek-chat |
| SiliconFlow | https://api.siliconflow.cn/v1 | Qwen/Qwen2.5-7B-Instruct |
| Ollama | http://127.0.0.1:11434/v1 | llama3.2 |

### Troubleshooting

#### Issue: "MCP dependencies not installed"

**Solution:** Install MCP dependencies:
```bash
pip install docutranslate[mcp]
```

#### Issue: "Client not configured"

**Solution:**
1. You can configure via environment variables `DOCUTRANSLATE_API_KEY`, `DOCUTRANSLATE_BASE_URL`, `DOCUTRANSLATE_MODEL_ID`
2. Or call `configure_client` tool to configure LLM settings
3. Use `get_status` tool to check current configuration status

#### Issue: Claude Desktop cannot connect

**Solution:**
1. Check if `docutranslate` command is in PATH
2. Try using the absolute path from your virtual environment
3. Restart Claude Desktop
4. View logs: Help > Debug > Logs

---

## 简体中文

### 安装

```bash
pip install docutranslate[mcp]
```

### 使用说明

#### 重要：使用虚拟环境解释器

在 MCP 配置中始终使用虚拟环境中的 Python 解释器，这样可以确保所有依赖都可用。

#### 方式一：Stdio 模式（推荐用于 Claude Desktop、Windsurf）

```bash
docutranslate --mcp
```

##### 使用 uvx（无需安装）

```json
{
  "mcpServers": {
    "docutranslate": {
      "command": "uvx",
      "args": ["--from", "docutranslate[mcp]", "docutranslate", "--mcp"],
      "env": {
        "DOCUTRANSLATE_API_KEY": "sk-xxxxxx",
        "DOCUTRANSLATE_BASE_URL": "https://api.openai.com/v1",
        "DOCUTRANSLATE_MODEL_ID": "gpt-4o",
        "DOCUTRANSLATE_TO_LANG": "中文",
        "DOCUTRANSLATE_CONCURRENT": "10",
        "DOCUTRANSLATE_CONVERT_ENGINE": "mineru",
        "DOCUTRANSLATE_MINERU_TOKEN": "your-mineru-token"
      }
    }
  }
}
```

在 MCP 配置文件中添加（**推荐使用虚拟环境的完整 Python 路径**）：

```json
{
  "mcpServers": {
    "docutranslate": {
      "command": "/path/to/your/venv/bin/python",
      "args": ["-m", "docutranslate.mcp"],
      "env": {
        "DOCUTRANSLATE_API_KEY": "sk-xxxxxx",
        "DOCUTRANSLATE_BASE_URL": "https://api.openai.com/v1",
        "DOCUTRANSLATE_MODEL_ID": "gpt-4o",
        "DOCUTRANSLATE_TO_LANG": "中文",
        "DOCUTRANSLATE_CONCURRENT": "10",
        "DOCUTRANSLATE_CONVERT_ENGINE": "mineru",
        "DOCUTRANSLATE_MINERU_TOKEN": "your-mineru-token"
      }
    }
  }
}
```

**Windows 示例：**

```json
{
  "mcpServers": {
    "docutranslate": {
      "command": "C:\\path\\to\\your\\venv\\Scripts\\python.exe",
      "args": ["-m", "docutranslate.mcp"],
      "env": {
        "DOCUTRANSLATE_API_KEY": "sk-xxxxxx",
        "DOCUTRANSLATE_BASE_URL": "https://api.openai.com/v1",
        "DOCUTRANSLATE_MODEL_ID": "gpt-4o",
        "DOCUTRANSLATE_TO_LANG": "中文",
        "DOCUTRANSLATE_CONCURRENT": "10",
        "DOCUTRANSLATE_CONVERT_ENGINE": "mineru",
        "DOCUTRANSLATE_MINERU_TOKEN": "your-mineru-token"
      }
    }
  }
}
```

如果 PATH 中已有 `docutranslate`，也可以使用：

```json
{
  "mcpServers": {
    "docutranslate": {
      "command": "docutranslate",
      "args": ["--mcp"],
      "env": {
        "DOCUTRANSLATE_API_KEY": "sk-xxxxxx",
        "DOCUTRANSLATE_BASE_URL": "https://api.openai.com/v1",
        "DOCUTRANSLATE_MODEL_ID": "gpt-4o",
        "DOCUTRANSLATE_TO_LANG": "中文",
        "DOCUTRANSLATE_CONCURRENT": "10",
        "DOCUTRANSLATE_CONVERT_ENGINE": "mineru",
        "DOCUTRANSLATE_MINERU_TOKEN": "your-mineru-token"
      }
    }
  }
}
```

#### 方式二：SSE 模式（推荐用于 Cherry Studio）

```bash
docutranslate --mcp --transport sse --mcp-host 127.0.0.1 --mcp-port 8000
```

或直接使用虚拟环境 Python 运行模块：

```bash
/path/to/your/venv/bin/python -m docutranslate.mcp --transport sse --host 127.0.0.1 --port 8000
```

在客户端中配置 SSE 端点：`http://127.0.0.1:8000/mcp/sse`

#### 方式三：Streamable HTTP 模式

```bash
docutranslate --mcp --transport streamable-http --mcp-host 127.0.0.1 --mcp-port 8000
```

#### 方式四：Web UI + MCP 组合模式（推荐！）

同时运行 Web UI 和 MCP 服务器，共享同一个任务队列：

```bash
docutranslate -i --with-mcp
```

这会启动：
- Web UI 界面：`http://127.0.0.1:8010`
- MCP SSE 端点：`http://127.0.0.1:8010/mcp/sse`
- **任务在 Web UI 和 MCP 之间共享！**

**注意**：在此模式下，MCP 自动使用与 Web 后端相同的 host 和 port。

### 通过环境变量配置

可以通过设置环境变量来预先配置 MCP 服务器，这样就不需要每次都调用配置工具了。

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

### MCP 工具参考

| 工具 | 说明 |
|------|------|
| `submit_task` | 提交翻译任务，立即返回 task_id |
| `get_task_status` | 获取任务状态，完成时显示所有格式和附件 |
| `download_file` | 下载翻译文件或附件到本地文件系统 |
| `release_task` | 释放任务资源（临时文件等） |
| `cancel_task` | 取消待处理或运行中的任务 |
| `load_glossary_file` | 加载术语表文件（JSON 或 CSV）用于 submit_task |
| `configure_client` | 配置客户端 LLM 设置 |
| `get_client_config` | 获取当前配置（不包含敏感数据） |
| `get_status` | 获取服务器状态和信息 |
| `get_supported_formats` | 获取支持的格式列表 |

#### `submit_task` - 提交翻译任务

以异步模式提交文件进行翻译，立即返回 task_id 不阻塞。

**参数：**
- `file_path` (必需): 文件路径，或 http:// 或 https:// 开头的 URL
- `api_key`: AI 平台 API 密钥（覆盖客户端配置）
- `base_url`: AI 平台基础 URL（覆盖客户端配置）
- `model_id`: 模型 ID（覆盖客户端配置）
- `to_lang`: 目标语言（覆盖客户端配置）
- `workflow_type`: 工作流类型
- `convert_engine`: PDF 转换引擎
- `mineru_token`: MinerU API Token
- 以及其他高级参数...

**示例工作流：**
```
1. submit_task(file_path="doc.pdf", api_key="sk-...", model_id="gpt-4o")
   → task_id="abc-123"

2. get_task_status("abc-123")
   → { "status": "running", "progress_percent": 45 }

3. get_task_status("abc-123")  # 完成时
   → 翻译完成！
   → 可用格式：docx, html, markdown
   → 附件：glossary
   → 使用 download_file 保存文件

4. download_file(task_id="abc-123", file_name="docx", output_dir="./output")
   → 文件已保存到 ./output/doc_translated.docx

5. download_file(task_id="abc-123", file_name="glossary", output_dir="./output")
   → 文件已保存到 ./output/glossary.csv

6. release_task("abc-123")  # 清理临时文件
```

#### `get_task_status` - 获取任务状态

查询任务的当前状态。

**参数：**
- `task_id` (必需): 要查询的任务 ID
- `wait_seconds`: 等待状态更改的最大秒数（0 = 立即返回）

**返回：**
- 当前状态：`idle`、`running`、`completed`、`error`
- 进度百分比 (0-100)
- 完成时的可用格式
- 完成时的附件

#### `download_file` - 下载翻译文件

将翻译文件或附件下载到本地文件系统。

**参数：**
- `task_id` (必需): 任务 ID
- `file_name` (必需): 要下载的文件名（例如 "docx"、"html"、"markdown"、"glossary"）
- `output_dir` (必需): 输出目录
- `output_name`: 自定义输出文件名（可选，未提供则自动生成）

#### `release_task` - 释放任务资源

清理临时文件并释放已完成任务的资源。

**参数：**
- `task_id` (必需): 要释放的任务 ID

#### `cancel_task` - 取消任务

取消待处理或运行中的任务。

**参数：**
- `task_id` (必需): 要取消的任务 ID

#### `load_glossary_file` - 加载术语表文件

加载术语表文件（JSON 或 CSV）并返回 JSON 字符串供 submit_task 使用。

**支持：**
- JSON 文件格式：`{"原文": "译文", "Original": "Translated"}`
- CSV 文件两列格式：第一列 = 原文，第二列 = 译文

**参数：**
- `file_path` (必需): 术语表文件路径（.json 或 .csv），或 http:// 或 https:// 开头的 URL

#### `configure_client` - 配置客户端

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

#### `get_client_config` - 获取客户端配置

获取当前客户端配置（不包含 API 密钥等敏感数据）。

**返回：**当前设置，API 密钥已脱敏。

#### `get_status` - 获取服务器状态

获取服务器状态和信息。

**返回：**
- 服务器状态
- 版本信息
- 配置状态（客户端是否已配置）
- 活动任务数

#### `get_supported_formats` - 获取支持的格式

获取支持的输入和输出格式列表。

**返回：**
- 输入格式
- 按文件类型的输出格式

### 支持的文件格式

#### 输入格式
PDF, DOCX, DOC, XLSX, XLS, CSV, MD, Markdown, TXT, JSON, EPUB, SRT, ASS, PPTX, PPT, HTML, HTM, PNG, JPG

#### 输出格式
- PDF/图片: HTML, Markdown, Markdown+Zip, DOCX
- DOCX: DOCX, HTML
- XLSX: XLSX, HTML
- PPTX: PPTX
- TXT: TXT, HTML
- JSON: JSON, HTML
- 字幕: SRT/ASS, HTML
- EPUB: EPUB, HTML

### AI 平台配置参考

| 平台 | base_url | 示例 model_id |
|------|----------|---------------|
| OpenAI | https://api.openai.com/v1 | gpt-4o, gpt-4o-mini |
| 智谱 | https://open.bigmodel.cn/api/paas/v4 | glm-4-flash, glm-4-air |
| DeepSeek | https://api.deepseek.com/v1 | deepseek-chat |
| 硅基流动 | https://api.siliconflow.cn/v1 | Qwen/Qwen2.5-7B-Instruct |
| Ollama | http://127.0.0.1:11434/v1 | llama3.2 |

### 故障排除

#### 问题："MCP dependencies not installed"

**解决：** 安装 MCP 依赖：
```bash
pip install docutranslate[mcp]
```

#### 问题："Client not configured"

**解决：**
1. 可以通过设置环境变量 `DOCUTRANSLATE_API_KEY`、`DOCUTRANSLATE_BASE_URL`、`DOCUTRANSLATE_MODEL_ID` 来配置
2. 或者调用 `configure_client` 工具配置 LLM 设置
3. 使用 `get_status` 工具查看当前配置状态

#### 问题：Claude Desktop 无法连接

**解决：**
1. 检查 `docutranslate` 命令是否在 PATH 中
2. 尝试使用虚拟环境的绝对路径
3. 重启 Claude Desktop
4. 查看日志：Help > Debug > Logs
