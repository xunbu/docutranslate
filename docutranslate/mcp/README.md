# DocuTranslate MCP Server

[English](#english) | [简体中文](#简体中文)

---

## English

### Architecture

The DocuTranslate MCP Server now uses a **shared server layer** architecture. Both the Web backend (app.py) and MCP server use the same `TranslationService` instance, ensuring:

- **Unified Task Management**: Tasks submitted via Web UI can be monitored via MCP and vice versa
- **Full Workflow Support**: MCP uses the complete workflow engine from app.py, not just the SDK
- **Shared Resources**: Download files, attachments, and temp directories are managed in one place

```
┌─────────────────────────────────────────────────────────────┐
│         docutranslate/server/core.py                        │
│              TranslationService (singleton)                  │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ - tasks_state, tasks_log_queues, tasks_log_histories │ │
│  │ - start_translation(), _perform_translation()         │ │
│  │ - cancel_task(), release_task()                       │ │
│  │ - Full workflow engine, file/attachment management    │ │
│  └───────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
              ▲                    ▲
              │                    │
    ┌─────────┴──────┐    ┌────────┴──────────┐
    │   app.py        │    │  mcp/server.py    │
    │  (Web backend)  │    │   (MCP server)    │
    │                 │    │                   │
    │ All endpoints   │    │ All MCP tools     │
    │ use the shared  │    │ use the shared    │
    │ service         │    │ service           │
    └─────────────────┘    └───────────────────┘
```

### Features

- **Async Task Queue Mode**: Submit translation and get task_id immediately, no blocking
- **Task Status Query**: Check progress and status anytime
- **Multiple Transports**: stdio, sse, streamable-http
- **Mountable**: Can be mounted to existing FastAPI app (like app.py)
- **Shared Task State**: Tasks are shared between Web UI and MCP when using `--with-mcp` mode
- **Full Workflow Engine**: Access to all 11 workflow types (markdown_based, docx, xlsx, pptx, etc.)
- **Separate Download Step**: Translation completion and file download are separate steps for better control
- **Attachment Support**: Download both translation outputs and attachments (like glossary files)

### Installation

```bash
pip install docutranslate[mcp]
```

### Usage

#### Method 1: Stdio Mode (Recommended for Claude Desktop, Windsurf)

```bash
docutranslate --mcp
```

Add to your MCP configuration (use the full Python path from your virtual environment):

```json
{
  "mcpServers": {
    "docutranslate": {
      "command": "/path/to/your/venv/bin/python",
      "args": ["-m", "docutranslate.mcp"]
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
      "args": ["--mcp"]
    }
  }
}
```

#### Method 2: SSE Mode (Recommended for Cherry Studio)

```bash
docutranslate --mcp --transport sse --mcp-host 127.0.0.1 --mcp-port 8000
```

Or using the module directly:

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

### MCP Tools

| Tool | Description |
|------|-------------|
| `submit_task` | Submit a translation task, returns task_id immediately |
| `get_task_status` | Get current status, shows all formats and attachments when completed |
| `download_file` | Download translated file or attachment to local filesystem |
| `release_task` | Release task resources (temp files, etc.) |
| `cancel_task` | Cancel a pending or running task |
| `translate_file` | Translate a file (synchronous, waits for completion) |
| `translate_content` | Translate base64 content (synchronous) |
| `get_status` | Get server status and info |
| `get_supported_formats` | Get list of supported formats |

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

---

## 简体中文

### 架构说明

DocuTranslate MCP 服务器现在使用**共享服务器层**架构。Web 后端（app.py）和 MCP 服务器都使用同一个 `TranslationService` 实例，确保：

- **统一的任务管理**：通过 Web UI 提交的任务可以通过 MCP 监控，反之亦然
- **完整工作流支持**：MCP 使用 app.py 的完整工作流引擎，而不仅仅是 SDK
- **共享资源**：下载文件、附件和临时目录都在同一个地方管理

```
┌─────────────────────────────────────────────────────────────┐
│         docutranslate/server/core.py                        │
│              TranslationService (单例模式)                   │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ - tasks_state, tasks_log_queues, tasks_log_histories │ │
│  │ - start_translation(), _perform_translation()         │ │
│  │ - cancel_task(), release_task()                       │ │
│  │ - 完整工作流引擎、文件/附件管理                       │ │
│  └───────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
              ▲                    ▲
              │                    │
    ┌─────────┴──────┐    ┌────────┴──────────┐
    │   app.py        │    │  mcp/server.py    │
    │  (Web 后端)     │    │   (MCP 服务器)    │
    │                 │    │                   │
    │ 所有端点都使用   │    │ 所有 MCP 工具都使用│
    │ 共享服务         │    │ 共享服务           │
    └─────────────────┘    └───────────────────┘
```

### 功能特点

- **异步任务队列模式**：提交翻译立即返回 task_id，不阻塞
- **任务状态查询**：随时查看进度和状态，完成时显示所有可用格式和附件
- **多种传输协议**：stdio、sse、streamable-http
- **可挂载**：可以挂载到现有的 FastAPI 应用（如 app.py）
- **共享任务状态**：使用 `--with-mcp` 模式时，Web UI 和 MCP 共享任务
- **完整工作流引擎**：支持全部 11 种工作流类型（markdown_based、docx、xlsx、pptx 等）
- **分离的下载步骤**：翻译完成和文件下载是独立步骤，便于控制
- **附件支持**：可以下载翻译输出和附件（如术语表文件）

### 安装

```bash
pip install docutranslate[mcp]
```

### 使用方式

#### 方式一：Stdio 模式（推荐用于 Claude Desktop、Windsurf）

```bash
docutranslate --mcp
```

在 MCP 配置文件中添加（**推荐使用虚拟环境的完整 Python 路径**）：

```json
{
  "mcpServers": {
    "docutranslate": {
      "command": "/path/to/your/venv/bin/python",
      "args": ["-m", "docutranslate.mcp"]
    }
  }
}
```

Windows 示例：
```json
{
  "mcpServers": {
    "docutranslate": {
      "command": "C:\\path\\to\\your\\venv\\Scripts\\python.exe",
      "args": ["-m", "docutranslate.mcp"]
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
      "args": ["--mcp"]
    }
  }
}
```

#### 方式二：SSE 模式（推荐用于 Cherry Studio）

```bash
docutranslate --mcp --transport sse --mcp-host 127.0.0.1 --mcp-port 8000
```

或直接使用模块运行：

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

### MCP 工具

| 工具 | 说明 |
|------|------|
| `submit_task` | 提交翻译任务，立即返回 task_id |
| `get_task_status` | 获取任务状态，完成时显示所有格式和附件 |
| `download_file` | 下载翻译文件或附件到本地文件系统 |
| `release_task` | 释放任务资源（临时文件等） |
| `cancel_task` | 取消待处理或运行中的任务 |
| `translate_file` | 翻译文件（同步，等待完成） |
| `translate_content` | 翻译 base64 内容（同步） |
| `get_status` | 获取服务器状态和信息 |
| `get_supported_formats` | 获取支持的格式列表 |

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
