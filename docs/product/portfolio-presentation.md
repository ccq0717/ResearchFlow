# ResearchFlow 作品集展示材料

## 一句话介绍

ResearchFlow 是面向科研与技术预研的证据优先研究工作台：它把开放目标拆成计划，联合检索公开网页和本地资料，并生成每条关键主张都能追溯到证据与来源的报告。

## 两分钟演示

1. 在 Dashboard 选择一份本地资料并提交黄金研究目标；
2. 在工作区展示 LangGraph 阶段、SSE 进度和结构化计划；
3. 展示学术、官方、工业和本地来源，以及 Claim—Evidence—Source 关联；
4. 打开 Markdown 报告中的网页引用或本地文件定位；
5. 展示耗时、Token、来源构成和引用覆盖率；
6. 刷新页面证明状态可恢复，再简短展示取消、一次重试和历史管理。

固定输入与公开结果样例位于 `examples/`，演示前不需要临时设计问题。

## 简历描述

设计并实现 AI 深度研究工作台 ResearchFlow，使用 Next.js、FastAPI、LangGraph 与 SQLite 打通结构化规划、Exa 通用 Web 检索、Gemini Embedding 本地 RAG、证据提取和可追溯 Markdown 报告；通过自有 Provider 接口隔离外部服务，并补齐 SSE 状态恢复、取消/有限重试、运行度量、离线集成测试、浏览器 E2E、备份与容器化交付。

## 面试重点

- 为什么采用可控阶段工作流，而不是多个 Agent 自由对话；
- 为什么当前用 Exa 通用搜索而不额外接入学术 Provider；
- 为什么用 Embedding + SQLite，而不是词法匹配或独立向量数据库；
- Claim、Evidence、Source 为什么分开建模，以及引用覆盖率不能证明什么；
- 为什么失败重试创建新运行，而不伪装成尚未实现的 checkpoint 恢复；
- SQLite、进程内任务和单实例部署的适用边界，以及何时才需要队列和 PostgreSQL。

## 展示边界

这是受保护、低流量的作品集 Demo，不是多租户 SaaS。公开展示应使用可公开资料、固定任务上限和费用预算；未真实验证的在线能力、成本或高可用性不写入简历。
