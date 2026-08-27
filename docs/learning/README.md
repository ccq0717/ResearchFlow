# ResearchFlow 学习区

这里不是项目规范文档，而是面向前后端初学者的配套课程。目标是让你在实现 ResearchFlow 的同时，逐步理解每一层代码为什么存在，并最终能独立向面试官解释项目。

## 使用方法

1. 每次只学习一课，不追求一次记住全部细节。
2. 结合课程中的结论和路径说明，回到项目代码中寻找对应实现。
3. 把不理解的地方直接提问；确认掌握后，再记录到 `learning-records/`。
4. 架构文档回答“项目规定是什么”，这里的课程回答“它为什么这样工作”。

## 当前课程

- [第 1 课：SSE 如何把后端进度实时送到网页](lessons/0001-understand-sse.html)
- [第 2 课：一次研究任务如何穿过前端、后端和数据库](lessons/0002-follow-a-research-request.html)
- [第 3 课：SQLite、SQLAlchemy 和 aiosqlite 分别做什么](lessons/0003-understand-sqlite-persistence.html)
- [第 4 课：真实 LLM 是怎样接入后端的](lessons/0004-understand-llm-adapters.html)
- [第 5 课：网页与本地资料怎样穿过 LangGraph](lessons/0005-understand-langgraph-web-research.html)
- [第 6 课：RAG 与 Embedding 在 ResearchFlow 中怎样工作](lessons/0006-understand-rag-embeddings.html)
- [第 7 课：检索结果怎样变成可追溯结论](lessons/0007-understand-evidence-and-citations.html)
- [第 8 课：Fake、Mock、集成测试与真实评测](lessons/0008-understand-testing-and-evaluation.html)
- [第 9 课：后台任务、失败恢复、日志与可靠性](lessons/0009-understand-run-reliability.html)
- [第 10 课：Docker、Secret、持久化与在线部署](lessons/0010-understand-deployment.html)

## 速查资料

- [Web 通信方式速查表](reference/web-communication-cheatsheet.html)
- [当前全栈实现地图](reference/current-full-stack-map.html)

## 后续学习路线

课程会跟随 ResearchFlow 的开发进度逐步补充，而不是脱离项目一次性讲完。

1. 浏览器、前端、后端和数据库分别负责什么（已有入门课）
2. HTTP 请求与响应、JSON 和 REST API
3. React 组件、状态与副作用
4. FastAPI 路由、数据校验与异步函数
5. SQLite、SQLAlchemy 和数据持久化（已有入门课）
6. SSE、任务进度和断线重连（已有入门课）
7. LLM 接口、适配器与结构化输出（已有入门课）
8. Agent 工作流、LangGraph 与状态管理（已有入门课）
9. RAG、Embedding 检索、证据和引用（已有专题课）
10. Fake、Mock、集成测试与真实评测（已有专题课）
11. 后台任务、失败恢复、日志与可靠性（已有专题课）
12. Docker、Secret、持久化与在线部署（已有专题课）

学习方向由 [MISSION.md](MISSION.md) 约束，资料来源记录在 [RESOURCES.md](RESOURCES.md)。
