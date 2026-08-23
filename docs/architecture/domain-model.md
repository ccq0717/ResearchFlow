# ResearchFlow 核心数据模型

> 状态：第一阶段最小模型
> 更新日期：2026-08-23

## 1. 建模原则

- 使用 ResearchFlow 自己的领域类型，不泄漏 FastAPI、SQLAlchemy 或 LangGraph 类型；
- 研究运行状态和实时事件分开保存；
- 第一阶段只建立模拟闭环必需字段；
- 后续新增任务、来源、证据和知识库时保持兼容演进。

## 2. ResearchRun

一次从用户研究目标到最终报告的完整运行。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | UUID | 全局唯一运行标识 |
| `goal` | string | 用户原始研究目标 |
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

### ResearchStage

第一阶段使用：

```text
planning
retrieving
analyzing
writing
finalizing
```

阶段是产品语义，不等同于 LangGraph 节点名称。内部图可以增加或合并节点，而无需改变前端契约。

## 3. ResearchEvent

运行期间产生的不可变事件，用于 SSE 推送、断线重连和审计。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | integer | 单个运行内单调递增的事件序号 |
| `run_id` | UUID | 所属 Research Run |
| `type` | enum | 事件类型 |
| `stage` | enum/null | 关联阶段 |
| `message` | string | 可展示说明 |
| `progress` | integer/null | 最新总体进度 |
| `payload` | JSON/null | 事件特有的结构化数据 |
| `created_at` | datetime | UTC 事件时间 |

事件只能追加，不能覆盖。客户端以 `run_id + id` 去重，并可通过最后收到的事件序号恢复订阅。

## 4. 后续模型

以下模型在真实研究工作流阶段加入，不提前建立空表：

- `ResearchTask`：规划得到的研究子任务；
- `Source`：网页、论文或知识库文档；
- `Evidence`：来自来源的可引用原文片段；
- `Claim`：报告中的关键主张及其证据关系；
- `KnowledgeDocument`：用户上传的原始文件；
- `DocumentChunk`：切分并建立索引的文档片段；
- `WorkflowAttempt`：重试、恢复和成本记录。

## 5. 持久化 seam

应用层依赖 `ResearchRepository` 接口，不直接依赖 SQLAlchemy Session。第一阶段提供两个适配器：

- SQLite 适配器：本地运行；
- 内存适配器：快速、确定性的应用测试。

核心操作应保持精简：创建运行、读取单个运行、列出运行、保存状态转换、追加/读取事件。
