# ResearchFlow 核心数据模型

> 状态：M1 实现基线
> 更新日期：2026-08-24

## 1. 建模原则

- 使用 ResearchFlow 自己的领域类型，不泄漏 FastAPI、SQLAlchemy、模型供应商或 LangGraph 类型；
- 研究运行、结构化计划和实时事件分开保存；
- 只建立当前里程碑实际使用的模型，不提前创建未来空表；
- 后续新增任务、来源、证据和知识库时保持兼容演进；
- 产品核心术语以仓库根目录的 [领域词汇表](../../CONTEXT.md) 为准。

## 2. ResearchRun

一次从用户研究目标到最终报告的完整运行。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | UUID | 全局唯一运行标识 |
| `goal` | string | 用户研究目标 |
| `title` | string | 用于列表展示的短标题 |
| `status` | enum | 当前生命周期状态 |
| `current_stage` | enum/null | 当前研究阶段 |
| `progress` | integer | 0～100 的展示进度 |
| `report_markdown` | string/null | 最终报告 |
| `error_code` | string/null | 稳定错误代码 |
| `error_message` | string/null | 可展示错误信息 |
| `created_at` | datetime | UTC 创建时间 |
| `updated_at` | datetime | UTC 最近更新时间 |
| `started_at` | datetime/null | 开始执行时间 |
| `completed_at` | datetime/null | 结束时间 |

### ResearchRunStatus

```text
queued → running → completed
                 ↘ failed
                 ↘ cancelled   # 后续阶段实现取消接口
```

终态为 `completed`、`failed`、`cancelled`。终态运行不得重新回到 `running`；重试应创建新的尝试记录或显式重试流程，而不是静默修改历史。

### ResearchRunOutcome

`ResearchRunOutcome` 表示一次运行不可再变化的领域结果，统一携带终态、最终进度、报告或可安全展示的错误，以及该结果必须产生的终结事件。Repository 在同一个 SQLite 事务中更新 `research_runs` 并追加全部终结事件，避免 SSE 观察到“运行已结束、终结事件尚未写入”的竞态。

### ResearchStage

```text
planning
retrieving
analyzing
writing
finalizing
```

阶段是产品语义，不等同于 LangGraph 节点名称。内部图可以增加或合并节点，而无需改变前端契约。

## 3. ResearchPlan 与 ResearchQuestion

`ResearchPlan` 是一次运行在检索前形成的结构化中间产物。M1 由 LLM 或 Fake LLM 产生并保存到 `research_plans`，一个运行至多对应一个当前计划。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `run_id` | UUID | 所属 Research Run，同时是计划主键 |
| `summary` | string | 研究计划摘要 |
| `questions` | JSON array | 有序 Research Question 列表 |
| `deliverables` | JSON array | 预期交付物 |
| `provider` | string | 生成计划的适配器或供应商标识 |
| `model` | string | 模型名 |
| `input_tokens` | integer/null | 输入 Token，用量不可得时为空 |
| `output_tokens` | integer/null | 输出 Token，用量不可得时为空 |
| `total_tokens` | integer/null | 总 Token，用量不可得时为空 |
| `duration_ms` | integer | 模型调用耗时 |
| `created_at` | datetime | UTC 生成时间 |

每个 `ResearchQuestion` 包含稳定的运行内 ID、可检索问题和提出该问题的原因。研究计划不是模型思维链，也不是证据；它只描述后续研究应该调查什么。

## 4. ResearchEvent

运行期间产生的不可变事件，用于 SSE 推送、恢复展示和审计。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `sequence` | integer | 单个运行内单调递增的事件序号 |
| `run_id` | UUID | 所属 Research Run |
| `type` | string | 事件类型 |
| `stage` | enum/null | 关联阶段 |
| `message` | string | 可展示说明 |
| `progress` | integer/null | 最新总体进度 |
| `payload` | JSON/null | 事件特有的结构化数据 |
| `created_at` | datetime | UTC 事件时间 |

事件只能追加，不能覆盖。客户端可通过最后收到的事件序号继续订阅。终结事件与对应 Research Outcome 原子提交；`research.plan.completed` 只携带模型元数据和读取提示，完整计划通过独立 REST API 获取。

## 5. ResearchWorkflowUpdate

`ResearchWorkflow` 不直接写数据库，而是以异步迭代器产生 `ResearchWorkflowUpdate`。更新可以携带运行状态、研究阶段、进度、结构化计划、领域事件或不可变终态；Application 是唯一消费方，并负责调用 Repository 持久化。这个小接口是 M2 `LangGraphResearchWorkflow` 的框架隔离 seam。

## 6. 当前持久化

SQLite 当前包含三张业务表：

- `research_runs`：运行状态和报告；
- `research_plans`：结构化研究计划与模型调用元数据；
- `research_events`：按运行排序的不可变事件。

`SqliteResearchRepository` 是当前具体的数据访问模块。应用层仍直接依赖这个具体类，因此文档不把它误称为已经具有两个适配器验证的 Repository seam；后续引入第二种存储或内存实现时再提取 Protocol。

## 7. 已验证的替换 seam

- `ResearchWorkflow`：`SimulatedResearchWorkflow` 与 `LLMResearchWorkflow`；
- `LLMClient`：`FakeLLMClient` 与 `OpenAICompatibleLLMClient`。

两处接口都至少有两个实际 adapter。FastAPI 路由只调用 Application；Application 消费工作流更新并依赖当前 SQLite Repository；工作流不导入 Repository，LLM 工作流也不依赖厂商 HTTP 响应类型。详细说明见 [LLM 接入架构](llm-integration.md)。

## 8. 后续模型

以下模型在真实研究工作流阶段加入，不提前建立空表：

- `ResearchTask`：规划得到的研究子任务；
- `Source`：网页、论文或知识库文档；
- `Evidence`：来自来源的可引用原文片段；
- `Claim`：报告中的关键主张及其证据关系；
- `KnowledgeDocument`：用户上传的原始文件；
- `DocumentChunk`：切分并建立索引的文档片段；
- `WorkflowAttempt`：重试、恢复和成本记录。
