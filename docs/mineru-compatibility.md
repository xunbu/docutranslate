# MinerU 接口兼容性

适配依据为 [MinerU 在线接口](https://mineru.net/apiManage/docs)、[4.x 迁移说明](https://opendatalab.github.io/MinerU/reference/migration_4/)和官方 V1 HTTP 示例。在线精准解析 API 的 `/api/v4` 与本地 MinerU 软件的 `4.x` 是两套独立协议。

## 现有调用

SDK 的 `Client.translate/translate_async`、HTTP JSON/表单接口、MCP 和前端继续使用原有 `convert_engine`、`mineru_token`、`model_version`、`mineru_deploy_*` 参数。未移除或改名任何 MinerU 参数，默认后端仍为 `hybrid-engine`，旧的 `*-auto-engine` 别名继续有效。返回的工作流结果、Markdown 图片内联和 ZIP 附件格式保持不变。

- `convert_engine="mineru"`：沿用在线精准解析 API 和原有 Token。PDF 超过 200 页或 180 MB 时仍自动拆分（大小上限低于服务端的 200 MB，以留出余量）；HTML/HTM 自动选择 `MinerU-HTML`。原有 `pipeline`、`vlm` 可继续使用。未切换到功能和额度不同的免 Token Agent API。
- `convert_engine="mineru_deploy"`：保持原有服务根地址（例如 `http://127.0.0.1:8000`，不包含 `/v1`）。先尝试 3.x `/tasks`；仅在 404/405 时检查 `/v1/health` 并执行 4.x 上传、提交、轮询、ZIP 下载。如果 V1 也不存在，沿用 2.x `/file_parse`。鉴权错误、限流、服务错误或已提交任务失败均不会触发重复提交或降级。
- 如果本地服务启用了 Bearer 鉴权（如 4.x 的 `--api-key`），可在前端“本地服务 API Key”中填写密钥，或通过 SDK、HTTP JSON/文件上传/扁平表单、MCP 的 `mineru_deploy_api_key` 传入。MCP `configure_client` 可保存默认值，`submit_task` 可按任务覆盖，配置查询只显示脱敏值。前端沿用现有配置保存、导入和导出方式。
- 环境变量 `DOCUTRANSLATE_MINERU_DEPLOY_API_KEY` 提供默认值：参数省略或为空时回退到环境变量，非空参数优先；启用 `DOCUTRANSLATE_ENV_FORCE_OVERRIDE` 且该变量已设置时，强制使用环境变量值。跳过翻译、仅解析时同样生效。环境变量中的密钥不会通过前端默认参数接口回传。
- 直接使用 workflow/转换器配置时可设置 `ConverterMineruDeployConfig(api_key=...)`。此密钥只发往服务本身，不发送给外部对象存储；未启用鉴权的服务无需填写。此密钥与在线 `mineru_token`、翻译模型 `api_key` 相互独立。

SDK 示例：

```python
from docutranslate.sdk import Client

client = Client(convert_engine="mineru_deploy", mineru_deploy_api_key="YOUR_LOCAL_SERVICE_KEY")
result = client.translate("paper.pdf", skip_translate=True)
# 单次调用也可通过 mineru_deploy_api_key 覆盖实例默认值。
```

## 本地 4.x 的参数转换

4.x 移除了旧版 backend 表单及按请求设置模型的方式。以下是 DocuTranslate 的兼容映射，不代表不同版本的解析效果完全相同：

| 原配置 | 4.x 请求档位 |
| --- | --- |
| `pipeline` | `basic` |
| `vlm-engine`、`vlm-auto-engine`、`vlm-http-client` | `standard` |
| `hybrid-engine`、`hybrid-auto-engine`、`hybrid-http-client` | `standard`；`effort="high"` 时为 `advanced` |
| `flash`、`basic`、`standard`、`advanced` | 同名档位 |
| Office、HTML、EPUB 等原生格式 | `flash`，处理整个文档 |

新增档位也可通过原有 `mineru_deploy_backend` 参数设置。旧版服务收到这些新增值时，Flash/Basic 映射为 Pipeline，Standard/Advanced 映射为 Hybrid（Advanced 使用 high effort）。

`parse_method` 转换为 `ocr_mode`。PDF 的零基、闭区间 `start_page_id/end_page_id` 转换为一基页码范围；默认 `0/99999` 明确表示 `all`，不受部分命令行默认只解析前 10 页的行为影响。`99999` 表示解析到最后一页。

旧参数仍可传入，但 4.x V1 请求不支持 `formula_enable`、`table_enable`、`image_analysis`、`lang_list`、`server_url`、`output_dir` 等字段，无法逐项重现它们的旧效果。模型和推理服务地址须在 MinerU 服务端配置；解析使用所选档位。遇到相关非默认设置时日志会提示。旧 2.x/3.x 服务继续接收原有字段。为保持翻译结果和图片完整，4.x 始终请求 ZIP 输出。

## 验证范围

在线任务轮询默认最多等待 3600 秒，可通过 `DOCUTRANSLATE_MINERU_TASK_TIMEOUT` 调整。连接、读写超时仍由原来的超时配置控制；该上限按每个解析切片的轮询计算，不包含上传、下载或翻译时间。任务失败、未知状态或成功响应缺少下载地址会明确报错。

测试使用 `httpx.MockTransport` 覆盖在线 API 和本地 2.x/3.x/4.x 的同步、异步流程、页码、别名、上传去重、图片内联、错误状态和凭证隔离。对外契约测试校验 SDK 参数继承及工作流 schema。另用自制单页 PDF 做了一次在线 MinerU 及 DeepSeek 小样本调用，结果见 `test-audit.md`；没有上传用户文档。本地 4.x 仍需在目标服务上核对鉴权、可用档位及解析质量。
