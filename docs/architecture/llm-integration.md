# LLM 接入架构

> 状态：M1 实现基线
> 更新日期：2026-08-24

## 1. 目标与边界

M1 只让真实模型负责把用户的研究目标转换成结构化研究计划。网页检索、论文检索、证据提取、RAG 和引用验证尚未接入，因此模型生成的计划不是研究结论，也不能作为来源证据。

默认 `simulation` 模式完全不调用外部服务；`llm` 模式才调用配置的 OpenAI-compatible HTTP 服务。

## 2. 两个可替换接口

```text
ResearchRunApplication
        │
        ▼
ResearchWorkflow
   ├── SimulatedResearchWorkflow
   └── LLMResearchWorkflow
                │
                ▼
             LLMClient
               ├── FakeLLMClient
               └── OpenAICompatibleLLMClient
```

`ResearchWorkflow` 隔离“怎样执行一次研究”，`LLMClient` 隔离提示词、HTTP、鉴权、结构化输出解析和供应商错误。应用层不导入模型 SDK，也不认识厂商响应格式。

只有一个实现的抽象不是已验证的替换缝。这里两个接口各有两个实际适配器，模拟运行和自动化测试都在持续验证边界。

## 3. 结构化输出契约

远程适配器调用 `/chat/completions`，通过 `response_format.type=json_schema` 要求模型返回：

- `summary`：计划摘要；
- `questions`：3～8 个研究问题，每项包含问题和提出原因；
- `deliverables`：1～8 个预期交付物。

Pydantic 同时负责生成 JSON Schema 和校验响应。即使 HTTP 状态为 200，只要 JSON 不完整、类型不正确或违反数量限制，本次调用仍会以 `LLM_INVALID_RESPONSE` 失败。

结构化输出的设计依据可参考 [OpenAI Structured Outputs 官方说明](https://developers.openai.com/api/docs/guides/structured-outputs)。

## 4. 数据怎样流动

1. 用户创建 `ResearchRun`；
2. `LLMResearchWorkflow` 进入 `planning`；
3. `LLMClient` 返回与厂商无关的 `LLMPlanResult`；
4. 工作流将它转换为领域对象 `ResearchPlan`；
5. Repository 保存到 `research_plans`；
6. 后端发送 `research.plan.completed` 事件；
7. 前端调用 `GET /api/research-runs/{id}/plan` 读取并展示计划；
8. M1 的其余检索、分析和写作阶段继续使用轻量模拟。

模型调用同时记录 provider、model、耗时和可获得的输入/输出/总 Token 数。这些数据用于调试和后续成本分析，不把 API Key 或原始错误响应写入事件。

配置中的 `RESEARCHFLOW_LLM_BASE_URL` 是 API 根地址，HTTP 适配器会自动追加 `/chat/completions`。`RESEARCHFLOW_LLM_PROVIDER` 当前用于记录接口协议和来源，不是动态适配器选择器；OpenAI-compatible 服务应保持 `openai-compatible`。

## 5. 错误与安全

| 错误代码 | 含义 | 对用户暴露的内容 |
| --- | --- | --- |
| `LLM_TIMEOUT` | 模型服务超时 | 建议稍后重试 |
| `LLM_CONNECTION_ERROR` | 无法连接服务 | 通用连接错误 |
| `LLM_HTTP_ERROR` | 服务返回非成功 HTTP 状态 | 只显示状态码 |
| `LLM_INVALID_RESPONSE` | 输出无法满足计划 Schema | 通用格式错误 |
| `WORKFLOW_FAILED` | 非预期工作流错误 | 提示检查后端日志 |

API Key 使用 Pydantic `SecretStr` 读取，只在构造 HTTP Authorization 头时取出。代码、事件、报告和已提交的 `.env.example` 都不得包含真实密钥。

自动化测试显式禁用 `.env` 加载，只使用 Fake 或 Mock，不得读取开发者密钥或访问外部模型。真实供应商兼容性通过单独、人工授权的冒烟测试验证。

## 6. 为什么当前不直接引入模型 SDK

M1 需要的远程能力只有一次标准 HTTP 请求。使用 `httpx` 能保持依赖轻量，并让 OpenAI-compatible 服务共用适配器。以后若某个供应商必须依赖专有 SDK，可以新增适配器，不改变 `LLMClient` 和工作流。

这不是在承诺所有“兼容”服务都支持同样的 JSON Schema 能力；实际启用前仍应确认服务支持 Chat Completions 和严格结构化输出。
