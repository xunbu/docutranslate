# DocuTranslate 测试套件

## 环境配置

所有敏感配置信息通过环境变量传入，测试用例中默认使用模拟值：

| 环境变量名 | 说明 | 测试默认值 |
|-----------|------|-----------|
| `DOCUTRANSLATE_BASE_URL` | 大模型API地址 | `https://api.openai.com/v1` |
| `DOCUTRANSLATE_API_KEY` | 大模型API密钥 | `test-api-key` |
| `DOCUTRANSLATE_MODEL_ID` | 大模型ID | `gpt-4o` |
| `DOCUTRANSLATE_TO_LANG` | 目标语言 | `中文` |
| `DOCUTRANSLATE_CONCURRENT` | 并发请求数 | `10` |
| `DOCUTRANSLATE_CONVERT_ENGINE` | 转换引擎 | `` |
| `DOCUTRANSLATE_MINERU_TOKEN` | MinerU解析服务token | `test-mineru-token` |
| `DOCUTRANSLATE_PROXY_ENABLED` | 是否启用代理 | `false` |

## 运行测试

### 安装依赖
```bash
uv sync --group dev
```

### 运行所有单元测试
```bash
uv run pytest tests/ -v
```

### 运行特定模块测试
```bash
uv run pytest tests/test_global_values/ -v
```

### 接口兼容和已修复问题的回归测试
```bash
uv run pytest tests/test_contract/ tests/test_cacher/ tests/test_converter/test_converter_mineru_deploy.py -q
```

MinerU 协议使用 MockTransport 验证，不需要在线 Token 或本地模型服务。

### 前端测试与生产构建
```bash
cd frontend
npm ci
npm test
npm run build
```

前端测试覆盖术语表编码识别和任务参数（包括结束页为 0 的边界）。

### 运行单个测试文件
```bash
uv run pytest tests/test_global_values/test_global_values.py -v
```

### 运行单个测试用例
```bash
uv run pytest tests/test_global_values/test_global_values.py::test_use_proxy_disabled_by_default -v
```

## 覆盖率报告

### 生成覆盖率报告
```bash
uv run pytest tests/ -v --cov=docutranslate --cov-report=term --cov-report=html:htmlcov
```

覆盖率报告将生成在 `htmlcov/` 目录下，打开 `htmlcov/index.html` 查看详细报告。

### 覆盖率要求
- CI 门禁：全项目行覆盖率不低于 55%（`check.yml` 中 `--cov-fail-under=55`）。
  当前实测约 60%，核心模块（转换、工作流、缓存、加密、SDK 契约）明显更高；
  不要用单个总数推断“没有潜在问题”。

## 目录结构

```
tests/
├── conftest.py          # 全局fixture配置
├── test_agents/         # LLM Agent（重试预算、续写、用量统计）
├── test_utils/          # 通用工具函数测试
├── test_cacher/         # 缓存模块测试
├── test_context/        # 上下文处理模块测试
├── test_contract/       # 接口契约与可用性回归
├── test_converter/      # 格式转换模块测试
├── test_exporter/       # 导出模块测试
├── test_global_values/  # 全局配置模块测试
├── test_glossary/       # 术语表模块测试
├── test_ir/             # 中间表示层测试
├── test_logger/         # 日志模块测试
├── test_translator/     # 翻译器模块测试
├── test_workflow/       # 工作流模块测试
├── test_data/           # 测试数据文件（被 .gitignore 忽略）
└── README.md            # 测试文档
```

> 说明：`tests/` 下的测试代码全部纳入版本控制；只有 `tests/resource/` 与
> `tests/test_data/` 被忽略。此前 `.gitignore` 用白名单只放行了部分文件，
> 导致 8 个本地能通过的测试模块从没在 CI 里跑过。

## 测试编写规范

1. 每个测试文件对应源码中的一个模块
2. 测试用例命名采用 `test_<功能描述>` 格式
3. 每个测试用例应该是独立的，不依赖其他测试用例的执行结果
4. 所有外部API调用（大模型API、MinerU API）必须使用mock隔离
5. 文件IO操作使用临时目录fixture，避免影响真实文件
6. 全局配置在测试中通过fixture重置，避免测试用例互相影响

## Mock策略

1. 外部API调用：使用 `pytest-mock` 进行mock
2. 文件IO：使用 `tempfile` 创建临时文件/目录
3. 环境变量：使用 `monkeypatch` 进行修改和恢复
4. 全局状态：使用fixture在测试前后进行重置和清理

## 集成测试

集成测试需要真实的环境变量，在CI环境中配置：

```bash
# 设置真实环境变量
export DOCUTRANSLATE_BASE_URL=xxx
export DOCUTRANSLATE_API_KEY=xxx
export DOCUTRANSLATE_MODEL_ID=xxx
export DOCUTRANSLATE_MINERU_TOKEN=xxx

# 运行集成测试（marker 已在 pyproject.toml 注册；当前仓库尚无 integration 用例）
uv run pytest tests/ -v -m integration
```

注意：默认的 `pytest` 会带上 `pyproject.toml` 里的 `addopts`（含覆盖率）。
在事件循环/临时目录受限的环境里，可加 `-o addopts= --basetemp=<可写目录>`。
若看到 `PermissionError: ... pytest-of-<user>`，说明系统临时目录不可访问，
不是测试失败。
