# ResearchFlow 核心数据模型

> 状态：当前实现
> 更新日期：2026-08-28

## 1. 建模原则

- 领域层只使用 ResearchFlow 类型，不泄漏 FastAPI、SQLAlchemy、模型供应商或 LangGraph 类型；
- Research Question、Research Task、Source 与 Evidence 是不同概念，定义以[领域词汇表](../../CONTEXT.md)为准；
- 工作流产生不可变更新，Application 统一负责事务和持久化；
- 只创建当前里程碑实际使用的模型。

## 2. 运行、计划与问题

`ResearchRun` 表示从目标到报告的一次完整运行，状态为 `queued`、`running`、`completed`、`failed` 或 `cancelled`。失败运行最多创建一个新的第二次运行；`retry_of` 和 `attempt` 保存谱系，原失败记录不被覆盖。这是任务级恢复，不声称从 LangGraph 节点断点续跑。`ResearchRunOutcome` 把终态和终结事件放在同一事务中，避免 SSE 竞态。

`ResearchPlan` 是检索前的结构化中间产物，包含摘要、交付物、模型元数据和有序 `ResearchQuestion`。每个问题包含：

| 字段 | 作用 |
| --- | --- |
| `id` | 运行内稳定标识 |
| `question` | 展示给用户的研究问题 |
| `rationale` | 为什么调查该问题 |
| `search_query` | 面向当前网页 Provider 的英文检索词 |

问题不是证据；检索词也不是新的研究问题。旧数据库中没有 `search_query` 的计划会回退使用原问题文本。

## 3. 研究材料与可追溯引用

| 模型 | 关键字段 | 语义 |
| --- | --- | --- |
| `ResearchTask` | `question_id`、`query`、`status` | 为某个问题执行的一次检索活动 |
| `Source` | `task_id`、`title`、`origin`、可选 `url`、可选 `knowledge_document_id`、`locator` | 某次运行实际读取的网页或本地材料 |
| `Evidence` | `task_id`、`question_id`、`source_id`、`excerpt`、`summary` | 来源原文片段及其对问题的解释 |
| `Claim` | `question_id`、`text`、`evidence_ids` | 报告中需要证据支持、可以独立检查的关键主张 |
| `CitationAudit` | 主张数、已支持主张数、覆盖率、来源类型计数 | 从当前材料确定性计算的引用完整性摘要 |

Evidence 必须同时关联已有 Source 和 Research Question，且原文片段必须能在对应来源正文中找到；Claim 通过显式关系关联一条或多条 Evidence。确定性检查保证每条结构化 Claim 都有完整的 Claim—Evidence—Source 链路，并且报告的可追溯章节包含相邻的网页链接或本地文件定位。

引用覆盖率按 `拥有完整 Evidence—Source 链路的结构化 Claim 数 ÷ Claim 总数 × 100%` 计算。它衡量关系完整性；100% 不代表每条主张在语义上必然正确，也不代表报告中的每句话都被统计。

来源类型是 `academic`、`official`、`industry`、`community` 或保守回退的 `other`。分类使用可解释的 URL 规则，作者和发布时间来自 Provider 可用元数据，发布机构从来源域名归一化；缺失值不会由模型猜测补齐。

`KnowledgeDocument`、`DocumentChunk` 与 `ChunkEmbedding` 描述可复用本地资料。文档保存原始文件名、系统生成的存储名、内容哈希、大小和 `processing` / `ready` / `failed` 状态；片段保存正文、顺序以及 PDF 页码或文本行号；Embedding 保存模型名、维度和浮点向量。用户为一次运行选择文档后，`research_run_documents` 固定该范围。本地检索命中会先转换成 `origin=local` 的运行内 Source，再进入原有 Evidence 与 Claim 链路，因此引用检查不需要维护两套模型。删除知识文档会清理片段、向量和运行选择关系；已完成运行中的 Source、Evidence 与报告快照仍保留，但原文件不再可打开。

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
- `research_run_controls`
- `schema_migrations`
- `research_plans`
- `research_events`
- `research_tasks`
- `research_sources`
- `research_source_metadata`
- `research_source_origins`
- `research_evidence`
- `research_claims`
- `research_claim_evidence`
- `knowledge_documents`
- `document_chunks`
- `document_chunk_embeddings`
- `research_run_documents`

`research_run_controls` 以附属表保存归档和重试谱系，使已有数据库可无损补表。`schema_migrations` 记录兼容版本；SQLite 的回滚策略是恢复更新前备份，而不是原地降级。

## 7. 已验证的替换 seam

- `ResearchWorkflow`：模拟、仅 LLM 规划、LangGraph 网页与本地联合研究；
- `LLMClient`：Fake 与 OpenAI-compatible；
- `SearchProvider`：Fake 与 Exa；
- `WebPageReader`：Fake 与供应商无关的搜索结果正文读取器；
- `EmbeddingClient`：Fake、Gemini 原生与 OpenAI-compatible；
- `KnowledgeRetriever`：基于持久化 Embedding 的余弦相似度检索；
- `KnowledgeLibrary`：封装上传校验、安全存储、解析、状态、重处理和删除生命周期；
- SQLite 研究仓储与知识库仓储按职责拆分，测试使用临时数据库，不提前抽象不存在的第二种持久化实现。
