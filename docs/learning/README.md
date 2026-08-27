# ResearchFlow 学习区

这里不是项目规范文档，而是面向前后端初学者的配套课程。目标是让你在实现 ResearchFlow 的同时，逐步理解每一层代码为什么存在，并最终能独立向面试官解释项目。

## 使用方法

1. 每次只学习一课，不追求一次记住全部细节。
2. 结合课程中的结论和路径说明，回到项目代码中寻找对应实现。
3. 遇到不理解的地方，结合课程给出的代码路径定位实现；
4. 架构文档回答“项目规定是什么”，这里的课程回答“它为什么这样工作”。

## 当前课程

- [第 0 课：先看懂浏览器、React、FastAPI 和 HTTP](lessons/0000-understand-full-stack-basics.html)
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

## 已覆盖的学习路径

课程已经覆盖理解、运行和讲解当前项目所需的主线知识：

1. 浏览器、HTTP/REST、React、FastAPI 和一次全栈请求；
2. SQLite、SQLAlchemy、SSE 和异步任务；
3. LLM 适配器、结构化输出、LangGraph 工作流；
4. RAG、Embedding、来源、证据、主张与引用；
5. 测试、评测、可靠性、安全和部署边界。

这些课程以“能读懂和解释 ResearchFlow”为完成边界，不替代系统的 React、FastAPI、数据库或机器学习教材。遇到代码细节时，先看对应课程给出的真实文件路径，再查 [RESOURCES.md](RESOURCES.md) 中的官方资料。

课程使用的规范、官方文档和论文记录在 [RESOURCES.md](RESOURCES.md)。
