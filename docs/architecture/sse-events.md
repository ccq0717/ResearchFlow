# ResearchFlow SSE 事件契约

> 状态：M1 实现基线
> 更新日期：2026-08-24

## 1. 目标

SSE 用于从后端向 Research Workspace 单向推送运行进度。前端不消费 LangGraph 原始事件，只消费 ResearchFlow 定义的稳定领域事件。

## 2. 传输格式

```text
id: 12
event: stage.progress
data: {"run_id":"...","stage":"retrieving","message":"正在检索资料","progress":35,"created_at":"...","payload":{}}

```

- `id` 是运行内单调递增的事件序号；
- `event` 是稳定事件类型；
- `data` 是 JSON，其中持久化事件包含 `sequence` 和 `type`；
- 每个事件以空行结束；
- 响应 Content-Type 为 `text/event-stream`；
- 服务端定期发送注释心跳，避免空闲连接被中间层关闭。

## 3. 事件类型

| 事件 | 用途 |
| --- | --- |
| `run.queued` | 运行已创建并等待执行 |
| `run.started` | 工作流开始执行 |
| `stage.started` | 进入新的研究阶段 |
| `stage.progress` | 当前阶段产生进度或日志 |
| `stage.completed` | 当前阶段完成 |
| `research.plan.completed` | 结构化研究计划已保存，payload 含模型、耗时和 Token 摘要 |
| `report.completed` | 报告已生成，payload 含报告摘要或读取提示 |
| `run.completed` | 整个运行成功完成 |
| `run.failed` | 运行失败，payload 含稳定错误代码 |
| `stream.ready` | 订阅建立，包含当前快照信息 |

当前不发送 Token 级模型文本流；研究计划完成后通过 `/plan` API 读取，报告完成后通过任务详情读取。后续如确有体验需求，再增加独立的 `report.delta` 事件。

## 4. 通用 data 字段

```json
{
  "run_id": "uuid",
  "stage": "planning",
  "message": "正在生成研究计划",
  "progress": 10,
  "created_at": "2026-08-23T08:00:00Z",
  "payload": {}
}
```

`payload` 随事件变化，但其内容不得成为展示基本进度的必要条件。客户端即使不认识新增 payload 字段，也应能继续工作。

## 5. 重连与去重

- 浏览器重连时发送 `Last-Event-ID`；
- 后端先补发该序号之后的持久化事件，再订阅新事件；
- 前端按事件序号去重；
- 页面首次打开时通过 `GET /api/research-runs/{id}/events/history` 读取完整持久化历史；
- 实时订阅可使用 `?after={sequence}` 从历史最后序号继续，避免重复事件；
- 运行状态和终结事件在同一个数据库事务中提交；运行已到终态时，补发终结事件后关闭连接；
- 网络断开不自动将 Research Run 标记为失败；
- API 时间戳统一携带 `Z` 或 `+00:00` UTC 标记，浏览器负责转换为用户本地时区。

## 6. 错误原则

- 建立订阅前的 HTTP 错误使用普通 JSON 错误响应；
- 建立订阅后的工作流错误使用 `run.failed`；
- 错误 payload 使用稳定 `code`，不向用户暴露堆栈或密钥；
- 前端区分“连接失败”和“研究运行失败”。
