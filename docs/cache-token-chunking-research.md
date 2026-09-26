# 输入缓存与 token 分块调查

日期：2026-09-26。范围：当前工作区代码、DeepSeek 官方文档、官方 `deepseek-ai/deepseek-harness`。本轮只调查，没有修改运行逻辑或调用付费模型 API；测试模块完善暂缓。

后续状态：依用户要求，已修复下文离线复现的“重试重复追加术语表”和“截断首轮 usage 漏计”，并增加同步/异步及流式/非流式回归测试。下文保留调查时的复现数据。分块仍使用字节单位，未实施 token 分块或改动超长单行策略。

## 结论

可以增加按 token 分块。优先采用“保留文档结构的切分 + 模型对应的本地 tokenizer + 完整请求预算检查”，保留现有字节模式兼容旧配置。缓存优化与分块优化需要分别衡量：前者减少重复前缀的计算/计费，后者控制请求大小、输出截断、重试成本和翻译上下文。

当前已经实现固定 system prompt、动态原文与术语表后置，不能把这些列为尚未实现的优化。最先值得处理的是重试提示词重复、截断请求 usage 漏计和超长单行不受分块上限约束。

## 当前代码证据

| 部位 | 实际行为 | 影响 |
| --- | --- | --- |
| `utils/json_utils.py:get_json_size` | JSON 使用 `ensure_ascii=False` 序列化后计算 UTF-8 字节数 | EPUB、TXT、Office 等分段流程按字节合并；不是字符或 token |
| `utils/markdown_splitter.py:MarkdownBlockSplitter` | 按 UTF-8 字节衡量，识别部分代码/公式/图片占位结构 | Markdown 也没有 token 预算 |
| `core/schemas.py:BaseWorkflowParams.chunk_size` | 文档描述为“字符” | 对外说明与实际单位不一致 |
| `agents/agent.py:_estimate_tokens` | 复杂文字约 1 token/字符，其余约 0.3；用于 TPM 限流 | 不是 tokenizer；没有参与分块或上下文硬上限检查 |
| `agents/segments_agent.py`、`markdown_agent.py` | 规则及自定义背景在 system；每块原文和匹配术语在 user | 已具有固定前缀；同一任务内无需重复重构它 |
| `glossary/glossary.py:build_incremental_prompt` | 只选择文本中出现的术语，按固定顺序排列 | 已减少无关输入；目前匹配范围包括包装提示词，不局限于原文 |
| `agents/agent.py:_prepare_request_data` | 每次主要发送 system/user 两条消息；允许 `extra_body` 覆盖 | 最终预算必须检查真正送出的 messages，不能只数原文 |

JSON 分块计量的序列化与最终发送的 `indent=0` 也不完全相同。原文块之外的规则、包装、术语、消息模板开销和预留输出都没有计入当前 `chunk_size`。

## 离线复现

以下均使用自制文本或 `httpx.MockTransport`，未请求真实服务。

1. **超长单行绕过上限**：`segments2json_chunks(['a' * 10000], 3000)` 返回一个 JSON 块，计量为 **10009 字节**。现有预处理只按换行切分，超长单行仍整体保留。迁移到 token 模式时不能只替换长度函数。
2. **重试重复追加术语表**：构造一次 HTTP 500、第二次成功的分段请求。两次 user prompt 的 `<incremental_glossary>` 数量分别为 **1、2**，字符数为 **262、432**。原因是递归重试传入已加工的 prompt，同时再次调用 `_pre_send_handler`。应从未加工的原始输入重新构造，或让一次请求的预处理结果只应用一次。
3. **输出截断时漏计首轮 usage**：模拟两次响应，首次 `finish_reason=length`、第二次 `stop`；每次 input=100、cached=50、output=10、total=110。应合计 **200/100/20/220**，当前仅记为 **100/50/10/110**。首次响应在统计之前进入续写分支并返回。该问题会污染优化前后的缓存命中率和成本比较。

上面第 2、3 项已通过异步请求实际复现；同步请求中存在对应控制流，需要实施时一并增加回归测试。

### 官方 tokenizer 对照

使用 [DeepSeek Token 文档](https://api-docs.deepseek.com/quick_start/token_usage/)当前链接的 [V4 tokenizer 数据](https://cdn.deepseek.com/api-docs/deepseek_v4_tokenizer.zip)，通过本地 `tokenizers 0.22.2` 的 `Tokenizer.from_file` 加载数据，未执行下载的 Python 示例。计数使用 `add_special_tokens=False`。

每类自制短段重复 120 次，用现有 `chunk_size=4000` 分块；排除最后一个不足额的块，下表是中位数。token 数计量实际发送的 JSON 文本（`ensure_ascii=False, indent=0`），不含 system、user 包装及聊天模板。这是有限样本比较，不是所有语言的固定换算系数。

| 文本 | JSON 字节中位数 | JSON token 中位数 |
| --- | ---: | ---: |
| 英文图书馆说明 | 3894 | 827 |
| 中文图书馆说明 | 3924 | 866 |
| 含 HTML 标签的段落 | 3931 | 1355 |
| JavaScript/JSON 风格代码 | 3939 | 1211 |

相同测量下，当前简体中文目标的分段翻译 system prompt 本身为 **288 个文本 token**，尚未计算消息模板。不能把 4000 字节直接改成 4000 tokens 而声称兼容；请求负载会明显变化。

tokenizer.json SHA-256：`89085f12ef79460ac5f66d1119325ddfc694b4ab209d80bbd81d35f081dc9614`。离线计数并不证明第三方代理使用同一 tokenizer；服务端返回的 usage 仍是账单依据。

## deepseek-harness 值得借鉴的实现

本次源码快照：`477b4f420553e8a52c2fbccc464d7561b239c443`。以下链接固定到该提交，避免后续主分支变化影响结论。

- [system-prompt](https://github.com/deepseek-ai/deepseek-harness/blob/477b4f420553e8a52c2fbccc464d7561b239c443/packages/core/system-prompt/src/index.ts)：确定提示词各部分和工具的顺序，把固定规则与动态上下文分离。可以借鉴确定性构造；本项目没有必要引入整套插件系统。
- [estimate.ts](https://github.com/deepseek-ai/deepseek-harness/blob/477b4f420553e8a52c2fbccc464d7561b239c443/packages/llm/token-meter/src/estimate.ts)：文本采用 **4 字符约 1 token** 的启发式并增加结构开销，并非精确 tokenizer。不能照搬它来宣称支持精确的中文 token 分块。
- [token-meter](https://github.com/deepseek-ai/deepseek-harness/blob/477b4f420553e8a52c2fbccc464d7561b239c443/packages/llm/token-meter/src/index.ts)：共享计量口径，在兼容的请求配置下参考成功调用的 usage，再衡量后续变化；配置不匹配则重新估算。本项目可以借鉴“区分估算与实际统计、按模型/服务隔离校准”，但独立翻译块不能直接当作它的连续会话增量。
- [summarizer](https://github.com/deepseek-ai/deepseek-harness/blob/477b4f420553e8a52c2fbccc464d7561b239c443/packages/compaction/compaction-basic/src/summarizer.ts)：保留原会话前缀，把摘要指令追加到末尾以复用缓存。适合连续会话或同一输入的后续任务；不能据此把整本书或全部历史译文附在每个并发翻译请求前。

## 输入缓存的改进空间

[DeepSeek 官方缓存说明](https://api-docs.deepseek.com/guides/kv_cache/)说明缓存自动启用，依赖已持久化的匹配前缀；当前规则还涉及公共前缀检测、请求边界和固定 token 间隔，缓存建立需要时间且不保证命中。不能套用旧版固定“64 token”规则，也不能把本地相同字符串长度直接当成实际命中 token 数。

建议按优先级处理：

1. **先保证请求与统计正确。** 修复上述重试重复和 usage 漏计；每次有 usage 的模型响应分别计入，避免流式最终统计重复累加。
2. **稳定构造输入。** 任务开始后固定规则、目标语言、背景和术语快照；JSON、术语顺序确定。维持“固定规则 → 可复用的任务背景 → 每块术语与原文”的顺序。重试前缀保持一致。
3. **术语策略做对照测试。** 当前按块筛选适合大术语表。小而频繁使用的术语集合可以考虑固定前缀，剩余术语仍按块追加；是否有利取决于重复成本、命中价格、预热和上下文占用，不能默认整张术语表更便宜。应只在原文上匹配，避免规则中的常见词误触发术语。
4. **重试/续写尽量复用原输入。** 当前续写会重构 user prompt。可以评估“原 system/user + 已产生 assistant 内容 + 续写指令”，但必须处理各 provider 的角色、思考模式兼容和历史输出预算。改善分块、减少截断应先于复杂会话改造。
5. **谨慎评估并发预热。** 大量请求同时首次进入服务时缓存可能还未建立。可对照少量真实业务请求先行的调度，不应默认额外发送付费预热请求或串行化全部分块。

不同原文块的正文天然不同，可复用部分主要是规则和任务背景。不要为提高命中率增加无用公共文本。指标应看每份完整文档的总输入/未命中输入/输出、实际成本、耗时、重试和质量，而非单看缓存百分比。

## 建议的 token 分块设计（尚未实施）

### 兼容接口

保留 `chunk_size` 的现有字节语义并纠正文案；新增可选 `max_input_tokens`，启用时按完整模型输入预算规划分块。不要把现有用户保存的 4000 无提示地解释为 4000 tokens。模型上下文上限、输出预留和 tokenizer 来源单独配置，支持第三方服务明确覆盖。

### 统一计数与预算

- `TokenCounter` 抽象供分块、TPM 估算及日志共用；当前同名类是用量累计器，实施时需要避免混淆命名。
- 有匹配模型 tokenizer：本地精确计量文本，按适配器的消息模板计入结构开销；缺少精确模板时明确标注总请求仍为估算。
- 没有匹配 tokenizer：提供显式的近似模式与保守余量，使用服务端 usage 校准，按服务/模型/语言类别隔离；不保证它是硬上限。不得把另一模型的 tokenizer 标为精确。
- 发送前必须满足 `输入 tokens + 预留输出 tokens + 安全余量 <= 模型上下文窗口`，并约束 provider 的独立输出上限。缓存命中的输入仍占上下文空间，不能扣掉。思考模型还需为推理输出留余量。
- 计量最终 system/user 内容、术语和 JSON 包装；使用 `extra_body` 覆盖 messages 等字段时应纳入最终校验，或明确不支持这种覆盖与自动分块组合。
- 官方 tokenizer 数据可本地配置或作为可选资源，避免强制引入整套深度学习运行时；需要核对 tokenizer 文件许可、打包及版本更新策略。

### 保留结构

先按章节/段落/句子、表格行和原有段落 ID 边界分解，再按预算合并。超长单段递归拆到句子或 Unicode 安全边界，保存子段到原段映射用于回填。不要直接对 token ID 每 N 个切片后解码，可能破坏 Unicode、标签、占位符和代码围栏。

JSON 开销和 token 合并不是严格可加的；可以缓存候选片段的计量减少重复计算，但最终拼接后的输入必须复算。无法容纳的不可分割结构应明确报错或走专门策略，不能静默突破上限。过小预算应快速拒绝，避免零进度循环。

## 后续测试与验收建议

1. 重试多次仍只有一份术语；同步/异步一致；正文、目标语言和规则不会被重复包装。
2. `length → stop`、多轮续写、失败后重试及流式尾部 usage 全部正确计量；缺失 usage 标记未知而非当成实测零。
3. 中文、英文、混排、emoji、超长单行、JSON 转义、HTML、代码围栏和公式能分块并完整回填。
4. 所有最终请求满足预算；超小预算、过大术语表、未知 tokenizer、模型切换都给出明确行为。
5. 原文分块、预估输入与实际 usage 分开记录；旧字节配置保持兼容，SDK/HTTP/MCP/前端使用同一语义。
6. 后续获得有效测试凭据时，对同一批自制文档做字节/近似 token/精确 token 对照，再比较按块术语与固定术语前缀。分冷启动和缓存已建立两组记录，并发保持相同，比较整篇成本、耗时、截断率和格式/翻译质量。

本轮没有测得真实缓存优化收益，不承诺具体省费或加速比例。建议实施顺序：请求与统计正确性 → token 计量抽象和预算 → 结构分块 → 术语及并发策略实测。
