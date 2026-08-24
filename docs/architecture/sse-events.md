# ResearchFlow SSE 事件契约

> 状态：M1.5 实现基线
> 更新日期：2026-08-24

## 1. 目标

SSE 用于从后端向 Research Workspace 单向推送运行进度。前端不消费 LangGraph 原始事件，只消费 ResearchFlow 定义的稳定领域事件。

## 2. 传输格式

持久化领域事件统一使用一个 SSE 传输类型：

```text
id: 12
event: research.event
data: {"sequence":12,"type":"stage.progress","run_id":"...","stage":"retrieving","message":"正在检索资料","progress":35,"created_at":"...","payload":{}}

```

- `id` 是运行内单调递增的事件序号；
- SSE 的 `event` 固定为 `research.event`，前端无需为每个新增领域事件注册监听器；
- JSON 的 `type` 才是 `run.completed`、`stage.started` 等领域事件类型；
- `stream.ready` 是未持久化的连接控制事件，仍使用独立 SSE 传输类型；
- 每个事件以空行结束，响应 Content-Type 为 `text/event-stream`；
- 服务端定期发送注释心跳，避免空闲连接被中间层关闭。

## 3. 当前领域事件类型

| `data.type` | 用途 |
| --- | --- |
| `run.queued` | 运行已创建并等待执行 |
| `run.started` | 工作流开始执行 |
| `stage.started` | 进入新的研究阶段 |
| `stage.progress` | 当前阶段产生进度 |
| `stage.completed` | 当前阶段完成 |
| `research.plan.completed` | 结构化研究计划已保存 |
| `report.completed` | 报告已生成 |
| `run.completed` | 整个运行成功完成 |
| `run.failed` | 运行失败，payload 含稳定错误代码 |

新增领域事件只需遵守通用 data 契约；前端基础研究事件列表会自动展示，不需要同步扩充 SSE 监听白名单。需要专门界面行为时，再根据 `data.type` 增加显式处理。

## 4. 通用 data 字段

```json
{
  "sequence": 12,
  "type": "stage.progress",
  "run_id": "uuid",
  "stage": "retrieving",
  "message": "正在检索资料",
  "progress": 35,
  "created_at": "2026-08-23T08:00:00Z",
  "payload": {}
}
```

`payload` 随事件变化，但不得成为展示基本进度的必要条件。客户端即使不认识新增 payload 字段，也应能继续工作。

## 5. 重连、终态与去重

- 页面先读取运行快照，再读取 `/events/history`；若快照已终结，对应终结事件已经原子提交，历史读取一定可见；
- 非终态页面使用 `?after={sequence}` 从历史最后序号继续 SSE；浏览器自动重连时还会发送 `Last-Event-ID`；
- 后端每轮先读取运行状态，再读取之后的事件。若状态已终结，随后的事件查询会补齐同一事务提交的终结事件，再关闭连接；
- 前端按 `sequence` 合并、排序和去重；
- 网络断开不自动将 Research Run 标记为失败；
- API 时间戳统一携带 `Z` 或 `+00:00` UTC 标记，浏览器转换为用户本地时区。

## 6. 错误原则

- 建立订阅前的 HTTP 错误使用统一的 `code`、`message`、`details` JSON；
- 建立订阅后的工作流错误使用 `data.type=run.failed`；
- 错误 payload 使用稳定 `code`，不向用户暴露堆栈或密钥；
- 前端区分“连接失败”和“研究运行失败”。
