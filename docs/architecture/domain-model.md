# ResearchFlow 核心数据模型

> 状态：M2 实现基线
> 更新日期：2026-08-25

## 1. 建模原则

- 领域层只使用 ResearchFlow 类型，不泄漏 FastAPI、SQLAlchemy、模型供应商或 LangGraph 类型；
- Research Question、Research Task、Source 与 Evidence 是不同概念，定义以[领域词汇表](../../CONTEXT.md)为准；
- 工作流产生不可变更新，Application 统一负责事务和持久化；
- 只创建当前里程碑实际使用的模型。

## 2. 运行、计划与问题

`ResearchRun` 表示从目标到报告的一次完整运行，状态为 `queued`、`running`、`completed`、`failed` 或预留的 `cancelled`。`ResearchRunOutcome` 把终态和终结事件放在同一事务中，避免 SSE 竞态。

`ResearchPlan` 是检索前的结构化中间产物，包含摘要、交付物、模型元数据和有序 `ResearchQuestion`。每个问题包含：

| 字段 | 作用 |
| --- | --- |
| `id` | 运行内稳定标识 |
| `question` | 展示给用户的研究问题 |
| `rationale` | 为什么调查该问题 |
| `search_query` | 面向当前网页 Provider 的英文检索词 |

问题不是证据；检索词也不是新的研究问题。旧数据库中没有 `search_query` 的 M1 计划会回退使用原问题文本。

## 3. M2 研究材料

| 模型 | 关键字段 | 语义 |
| --- | --- | --- |
| `ResearchTask` | `question_id`、`query`、`status` | 为某个问题执行的一次检索活动 |
| `Source` | `task_id`、`title`、`url`、`snippet` | 实际读取并保存元数据的外部材料 |
| `Evidence` | `task_id`、`question_id`、`source_id`、`excerpt`、`summary` | 来源原文片段及其对问题的解释 |

Evidence 必须同时关联 Source 和 Research Question。M2 的检查保证证据引用已有来源，且报告至少包含一个实际来源链接；它尚未建立报告主张级的 `Claim` 模型。

## 4. 阶段与事件

产品阶段保持稳定：

```text
planning → retrieving → analyzing → writing → finalizing
```

它们不等同于 LangGraph 节点。`ResearchEvent` 是按运行追加、带单调 `sequence` 的不可变记录，用于 SSE、恢复展示和审计。

## 5. ResearchWorkflowUpdate

`ResearchWorkflow` 以异步迭代器产生 `ResearchWorkflowUpdate`。更新可以携带状态、阶段、进度、计划、任务、来源、证据、事件或终态。Application 是唯一消费方，并调用 Repository 持久化；工作流不导入 Repository。

这使 `LangGraphResearchWorkflow` 能在内部使用 Graph State，同时 FastAPI、领域模型、数据库接口和前端都只看 ResearchFlow 类型。

## 6. 当前 SQLite 表

- `research_runs`
- `research_plans`
- `research_events`
- `research_tasks`
- `research_sources`
- `research_evidence`

后端启动时使用 SQLAlchemy `create_all` 补齐新表。当前没有正式迁移工具，因此公开部署前仍需加入迁移和回滚方案。

## 7. 已验证的替换 seam

- `ResearchWorkflow`：模拟、仅 LLM 规划、LangGraph 网页研究；
- `LLMClient`：Fake 与 OpenAI-compatible；
- `SearchProvider`：Fake 与 Exa；
- `WebPageReader`：Fake 与供应商无关的搜索结果正文读取器；
- Repository 暂时只有 SQLite 真实实现，测试使用临时数据库，不提前抽象第二种存储。

## 8. 后续模型

M3～M5 再引入 `Claim`、`KnowledgeDocument`、`DocumentChunk` 和 `WorkflowAttempt`，分别承载主张引用、本地资料、向量片段和重试恢复信息。
