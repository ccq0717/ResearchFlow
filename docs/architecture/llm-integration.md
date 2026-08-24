# LLM 接入架构

> 状态：M1.5 实现基线
> 更新日期：2026-08-24

## 1. 目标与边界

M1 只让真实模型负责把用户的研究目标转换成结构化研究计划。网页检索、论文检索、证据提取、RAG 和引用验证尚未接入，因此模型生成的计划不是研究结论，也不能作为来源证据。

默认 `simulation` 模式完全不调用外部服务；`llm` 模式才调用配置的 OpenAI-compatible HTTP 服务。

## 2. 两个可替换接口

```text
ResearchRunApplication
        │ 持久化 ResearchWorkflowUpdate
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

`ResearchWorkflow` 以异步迭代器产生 `ResearchWorkflowUpdate`，隔离“怎样执行一次研究”；Application 统一保存状态、计划、事件和终态。`LLMClient` 隔离提示词、HTTP、鉴权、结构化输出解析和供应商错误。应用层不导入模型 SDK，也不认识厂商响应格式。

两个接口各有两个实际 adapter，模拟运行和自动化测试持续验证这些 seam。工作流不导入 Repository，也不负责提交数据库事务；未来 `LangGraphResearchWorkflow` 只需产生相同的 ResearchFlow 更新类型。

## 3. 结构化输出契约

远程 adapter 调用 `/chat/completions`，通过 `response_format.type=json_schema` 要求模型返回：

- `summary`：计划摘要；
- `questions`：3～8 个研究问题，每项包含问题和提出原因；
- `deliverables`：1～8 个预期交付物。

Pydantic 同时负责生成 JSON Schema 和校验响应。即使 HTTP 状态为 200，只要 JSON 不完整、类型不正确或违反数量限制，本次调用仍会以 `LLM_INVALID_RESPONSE` 失败。

## 4. 数据怎样流动

1. 用户创建 `ResearchRun`；
2. `LLMResearchWorkflow` 进入 `planning`；
3. `LLMClient` 返回与厂商无关的 `LLMPlanResult`；
4. 工作流转换为 `ResearchPlan`，并产生 `ResearchWorkflowUpdate`；
5. Application 接收更新，由 Repository 保存到 `research_plans` 和 `research_events`；
6. SSE 以统一的 `research.event` 传输类型发送领域事件；
7. 前端根据 JSON 的 `type` 处理 `research.plan.completed`，再调用 `/plan` 读取计划；
8. M1 的其余检索、分析和写作阶段继续使用轻量模拟。

模型调用记录 provider、model、耗时和可获得的 Token 数，不把 API Key 或原始错误响应写入事件。

## 5. 配置、错误与安全

`RESEARCHFLOW_LLM_BASE_URL` 是 API 根地址，HTTP adapter 自动追加 `/chat/completions`。`RESEARCHFLOW_LLM_PROVIDER` 用于记录接口协议和来源，不是动态 adapter 选择器。

| 错误代码 | 含义 | 对用户暴露的内容 |
| --- | --- | --- |
| `LLM_TIMEOUT` | 模型服务超时 | 建议稍后重试 |
| `LLM_CONNECTION_ERROR` | 无法连接服务 | 通用连接错误 |
| `LLM_HTTP_ERROR` | 服务返回非成功状态 | 只显示状态码 |
| `LLM_INVALID_RESPONSE` | 输出不满足计划 Schema | 通用格式错误 |
| `WORKFLOW_FAILED` | 非预期工作流错误 | 安全的通用提示 |

API Key 使用 `SecretStr`，只在构造 Authorization 头时取出。测试从无副作用的 `researchflow.app_factory` 导入工厂，显式禁用 `.env`，并只使用 Fake 或 Mock。真实供应商兼容性由单独、人工授权的冒烟测试验证。

## 6. 为什么当前不直接引入模型 SDK

M1 只有一次标准 HTTP 请求。使用 `httpx` 能保持依赖轻量，并让 OpenAI-compatible 服务共用 adapter。以后若供应商必须使用专有 SDK，可新增 adapter，不改变 `LLMClient` 和工作流。