# ResearchFlow SSE 事件契约

> 状态：当前实现
> 更新日期：2026-08-26

## 1. 传输原则

SSE 从后端向 Research Workspace 单向推送运行进度。持久化事件统一使用 `event: research.event`，具体领域类型放在 JSON `data.type`；前端不消费 LangGraph 原始事件。`id` 是运行内单调事件序号，`stream.ready` 是未持久化的连接控制事件。

## 2. 当前领域事件

| `data.type` | 用途 |
| --- | --- |
| `run.queued` / `run.started` | 排队与开始 |
| `stage.started` / `stage.completed` | simulation/llm 兼容模式的通用阶段事件 |
| `research.plan.completed` | 计划已保存，前端重新读取 `/plan` |
| `research.tasks.completed` | 检索任务已保存 |
| `research.sources.completed` | 来源正文、类型和可用元数据已保存 |
| `research.evidence.completed` | 证据与 Claim—Evidence 关系已保存 |
| `report.draft.completed` | 草稿已生成 |
| `report.completed` / `run.completed` | 检查通过并结束 |
| `run.failed` | 运行失败，payload 含稳定错误代码 |

任务、来源或证据事件到达时，前端重新读取 `/api/research-runs/{id}/materials`。事件只传计数、引用覆盖率和来源类型计数等摘要，不重复传输正文。

`langgraph` 模式使用 `research.*.completed` 表达持久化检查点，不额外发送 `stage.completed`。所有持久化领域事件在线路上的 SSE `event` 都是 `research.event`；业务类型位于 `data.type`。

## 3. 通用数据

```json
{
  "sequence": 12,
  "type": "research.sources.completed",
  "run_id": "uuid",
  "stage": "retrieving",
  "message": "已读取并保存 6 个网页与本地来源",
  "progress": 56,
  "created_at": "2026-08-25T08:00:00Z",
  "payload": {"source_count": 6, "warning_count": 0}
}
```

客户端不认识新增 payload 字段时仍应能显示基本事件。错误不得包含堆栈、密钥或原始供应商响应。

## 4. 重连与终态

页面先读取快照和历史，再以 `?after={sequence}` 订阅。前端按 sequence 合并、排序和去重。终态与终结事件同事务提交，因此重新进入任务能恢复完整记录。网络断开不等于研究运行失败；后端进程中断遗留的运行会在下次启动时标记为 `RUN_INTERRUPTED`。
