# ResearchFlow 核心数据模型

> 状态：M3 实现基线
> 更新日期：2026-08-26

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

## 3. M2/M3 研究材料与可追溯引用

| 模型 | 关键字段 | 语义 |
| --- | --- | --- |
| `ResearchTask` | `question_id`、`query`、`status` | 为某个问题执行的一次检索活动 |
| `Source` | `task_id`、`title`、`url`、`snippet`、`source_type`、作者/日期/机构 | 实际读取并归一化元数据的外部材料 |
| `Evidence` | `task_id`、`question_id`、`source_id`、`excerpt`、`summary` | 来源原文片段及其对问题的解释 |
| `Claim` | `question_id`、`text`、`evidence_ids` | 报告中需要证据支持、可以独立检查的关键主张 |
| `CitationAudit` | 主张数、已支持主张数、覆盖率、来源类型计数 | 从当前材料确定性计算的引用完整性摘要 |

Evidence 必须同时关联已有 Source 和 Research Question，且原文片段必须能在对应来源正文中找到；Claim 通过显式关系关联一条或多条 Evidence。M3 检查保证每条结构化 Claim 都有完整的 Claim—Evidence—Source 链路，并且报告的可追溯章节包含相邻的来源链接。

来源类型是 `academic`、`official`、`industry`、`community` 或保守回退的 `other`。分类使用可解释的 URL 规则，作者和发布时间来自 Provider 可用元数据，发布机构从来源域名归一化；缺失值不会由模型猜测补齐。

## 4. 阶段与事件

产品阶段保持稳定：

```text
planning → retrieving → analyzing → writing → finalizing
```

它们不等同于 LangGraph 节点。`ResearchEvent` 是按运行追加、带单调 `sequence` 的不可变记录，用于 SSE、恢复展示和审计。

## 5. ResearchWorkflowUpdate

`ResearchWorkflow` 以异步迭代器产生 `ResearchWorkflowUpdate`。更新可以携带状态、阶段、进度、计划、任务、来源、证据、主张、事件或终态。Application 是唯一消费方，并调用 Repository 持久化；工作流不导入 Repository。

这使 `LangGraphResearchWorkflow` 能在内部使用 Graph State，同时 FastAPI、领域模型、数据库接口和前端都只看 ResearchFlow 类型。

## 6. 当前 SQLite 表

- `research_runs`
- `research_plans`
- `research_events`
- `research_tasks`
- `research_sources`
- `research_source_metadata`
- `research_evidence`
- `research_claims`
- `research_claim_evidence`

后端启动时使用 SQLAlchemy `create_all` 补齐新表。当前没有正式迁移工具，因此公开部署前仍需加入迁移和回滚方案。

## 7. 已验证的替换 seam

- `ResearchWorkflow`：模拟、仅 LLM 规划、LangGraph 网页研究；
- `LLMClient`：Fake 与 OpenAI-compatible；
- `SearchProvider`：Fake 与 Exa；
- `WebPageReader`：Fake 与供应商无关的搜索结果正文读取器；
- Repository 暂时只有 SQLite 真实实现，测试使用临时数据库，不提前抽象第二种存储。

## 8. 后续模型

M4 引入 `KnowledgeDocument` 和 `DocumentChunk`：前者表示可跨研究运行复用的用户资料，后者表示保留文件名、页码或段落定位的可检索片段。检索命中必须先转换成某次 Research Run 使用的 Source，再生成现有 Evidence，避免让 Evidence 同时维护网页和文件两套关联规则。`WorkflowAttempt` 继续留到 M5 承载重试恢复信息。
