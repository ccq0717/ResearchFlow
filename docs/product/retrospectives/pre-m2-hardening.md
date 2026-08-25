# M1 工程加固复盘

> 日期：2026-08-24
> 状态：实现完成并通过本地验证，远程 CI 将在推送后验证

## 1. 为什么 M1 包含工程加固

M0/M1 主流程可以演示，但阶段门审查发现了输入校验、错误契约、SSE 终态竞态、测试环境副作用和架构职责偏离。这些修复属于完成 M1 所必需的工程质量工作；若直接进入 M2，问题会被更多工作流节点和领域事件放大。

## 2. 关键修复

- 输入在 Pydantic seam 先规范化，再校验有效长度；API 错误统一为 `code/message/details`；
- `researchflow.app_factory` 只定义工厂，`researchflow.main` 才创建服务器应用，测试导入不再读取 `.env`；
- 后端按“状态 → 事件”顺序读取，前端按“状态 → 历史”顺序初始化，消除终态事件可见性竞态；
- SSE 用固定 `research.event` 传输类型，真实领域类型位于 JSON `type`；
- `ResearchWorkflow` 以异步迭代器产生 `ResearchWorkflowUpdate`，Application 是唯一持久化消费方；
- 前端使用 Vitest 验证研究事件合并、排序、去重与终态识别；
- 新增 Windows 后端 CI、前端 CI、MIT License 和公开黄金演示输入。

## 3. 设计取舍

- 当前 Repository 仍只有 SQLite 一个 adapter，因此不为假想存储提前提取 Protocol；
- 中间进度更新暂未全部做成单事务，终态继续由 `ResearchRunOutcome` 原子提交；M2 出现并行节点后再评估更强的幂等与事务接口；
- CI 配置已本地检查，但只有推送到 GitHub 后才能确认托管 runner 的实际结果。

## 4. 进入 M2 的约束

- LangGraph adapter 只能产生 ResearchFlow 自有更新，不得导入 FastAPI 或 Repository；
- 搜索与网页读取必须使用可替换 adapter，并由 Fake 覆盖自动化测试；
- 新领域事件必须遵守统一 SSE data 契约；
- 完成 M2 后再次执行阶段门审查并同步 README、Roadmap、学习与运维文档。
