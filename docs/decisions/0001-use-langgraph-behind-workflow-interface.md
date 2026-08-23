# ADR-0001：在 ResearchWorkflow 接口后使用 LangGraph

- 状态：接受
- 日期：2026-08-23

## 背景

ResearchFlow 需要处理长时间运行的研究流程，包括条件分支、有限循环、并行检索、重试、流式状态和中断恢复。项目同时需要保持容易测试，并避免 FastAPI、数据库和前端依赖某个特定 Agent 框架。

## 决策

真实研究工作流使用 LangGraph Graph API 编排，但 LangGraph 只存在于后端 `workflows` 模块内部。

应用层通过 ResearchFlow 自己的 `ResearchWorkflow` 接口启动或恢复研究，并接收 ResearchFlow 自己的领域事件。LangGraph State、Graph、Node、Command 和 checkpoint 类型不得出现在 FastAPI 路由、领域模型或前端契约中。

第一阶段模拟纵向闭环可以使用 `SimulatedResearchWorkflow`。接入真实能力时新增 `LangGraphResearchWorkflow`，两者满足相同接口。

## 结果

积极结果：

- 可以展示并实际使用 LangGraph；
- 流程图、循环和恢复语义更加明确；
- 模拟实现与真实实现可替换；
- 应用测试不需要调用模型或启动完整图；
- 框架升级或替换不会扩散到整个项目。

代价：

- 需要维护领域状态与 LangGraph 状态之间的转换；
- 必须避免同时建立两套互相冲突的状态来源；
- 团队需要理解 checkpoint、幂等性和事件重放。

## 约束

- SQLite 中的 Research Run 是产品状态的权威来源；
- LangGraph checkpoint 是工作流恢复机制，不直接作为前端查询模型；
- 所有外部调用必须封装为可重试、尽量幂等的任务；
- 工作流产生领域事件，由应用层持久化并通过 SSE 发布；
- 不因为采用 LangGraph 而强制使用 LangSmith 或 LangGraph Cloud。
