# Hello-Agents Deep Research 对 ResearchFlow 的参考分析

> 调研日期：2026-08-23
> 范围：仅使用 Datawhale 官方 Hello-Agents 文档与官方 GitHub 仓库。下文明确区分“官方事实”和“分析推断”。

## 结论摘要

ResearchFlow 的方向可行，Hello-Agents 第十四章适合作为 **研究工作流原型与教学参考**，但不应直接复制成求职项目。官方案例已经验证了“前端输入研究主题 → 规划子任务 → 搜索 → 分任务总结 → 汇总报告 → SSE 实时展示”的最小闭环；ResearchFlow 的简历价值应来自在此基础上补齐真正的产品与工程能力：用户与研究历史、可恢复任务状态、RAG 知识库、引用可验证性、失败重试、成本控制、测试、部署和 Windows 友好的轻量运行方式。

## 1. Hello-Agents 官方案例实际包含什么

### 1.1 产品与架构

**官方事实：** 第十四章把深度研究的核心能力概括为问题拆解、多轮信息采集、反思与总结；其示例系统采用四层结构：Vue 3 + TypeScript 前端、FastAPI 后端、HelloAgents 智能体层、外部搜索与 LLM 服务。一次研究请求经 SSE 进入后端，规划成若干 TODO，依次搜索和总结，最后生成 Markdown 报告并把进度推送给前端。文档给出的 Agent 分工是 TODO Planner、Task Summarizer、Report Writer，工具是 SearchTool 和 NoteTool。
来源：[第十四章：项目概述与数据流](https://github.com/datawhalechina/hello-agents/blob/main/docs/chapter14/%E7%AC%AC%E5%8D%81%E5%9B%9B%E7%AB%A0%20%E8%87%AA%E5%8A%A8%E5%8C%96%E6%B7%B1%E5%BA%A6%E7%A0%94%E7%A9%B6%E6%99%BA%E8%83%BD%E4%BD%93.md#141-%E9%A1%B9%E7%9B%AE%E6%A6%82%E8%BF%B0%E4%B8%8E%E6%9E%B6%E6%9E%84%E8%AE%BE%E8%AE%A1)

**官方事实：** TODO 驱动范式是“规划 → 执行 → 整合”。规划器输出 3–5 个带 `title`、`intent`、`query` 的子任务；执行器为每个任务搜索并总结；报告生成器合并重复信息并整理引用。文档强调线性流程、明确输入输出与易调试性。
来源：[TODO 驱动的研究范式](https://github.com/datawhalechina/hello-agents/blob/main/docs/chapter14/%E7%AC%AC%E5%8D%81%E5%9B%9B%E7%AB%A0%20%E8%87%AA%E5%8A%A8%E5%8C%96%E6%B7%B1%E5%BA%A6%E7%A0%94%E7%A9%B6%E6%99%BA%E8%83%BD%E4%BD%93.md#142-todo-%E9%A9%B1%E5%8A%A8%E7%9A%84%E7%A0%94%E7%A9%B6%E8%8C%83%E5%BC%8F)

**官方事实：** 当前仓库代码的同步 `run()` 路径逐个执行任务，但 `run_stream()` 会为每个 TODO 启动一个线程，并通过队列汇集事件，随后统一生成最终报告。因此，“官方文档所述无并发”与“当前流式实现并发子任务”存在版本差异。
来源：[当前 `DeepResearchAgent` 实现](https://github.com/datawhalechina/hello-agents/blob/main/code/chapter14/helloagents-deepresearch/backend/src/agent.py)

### 1.2 搜索、笔记与流式交互

**官方事实：** SearchTool 统一封装 Tavily、DuckDuckGo、Perplexity、SearXNG 和组合模式；文档展示了 URL 去重、来源文本截断、错误通知与配置化选择。NoteTool 把子任务笔记和最终报告保存为本地 Markdown，用于记录、审计和中断后的进度查看。
来源：[搜索工具与 NoteTool](https://github.com/datawhalechina/hello-agents/blob/main/docs/chapter14/%E7%AC%AC%E5%8D%81%E5%9B%9B%E7%AB%A0%20%E8%87%AA%E5%8A%A8%E5%8C%96%E6%B7%B1%E5%BA%A6%E7%A0%94%E7%A9%B6%E6%99%BA%E8%83%BD%E4%BD%93.md#144-%E5%B7%A5%E5%85%B7%E7%B3%BB%E7%BB%9F%E9%9B%86%E6%88%90)

**官方事实：** FastAPI 使用 `StreamingResponse` 返回 `text/event-stream`，前端根据计划、进度、任务摘要、报告和错误事件更新界面。
来源：[SSE 实时进度展示](https://github.com/datawhalechina/hello-agents/blob/main/docs/chapter14/%E7%AC%AC%E5%8D%81%E5%9B%9B%E7%AB%A0%20%E8%87%AA%E5%8A%A8%E5%8C%96%E6%B7%B1%E5%BA%A6%E7%A0%94%E7%A9%B6%E6%99%BA%E8%83%BD%E4%BD%93.md#1462-%E5%AE%9E%E6%97%B6%E8%BF%9B%E5%BA%A6%E5%B1%95%E7%A4%BA)

### 1.3 依赖与运行方式

**官方事实：** 后端要求 Python 3.10+，主要依赖 FastAPI、Hello-Agents 0.2.9、Tavily SDK、OpenAI SDK、Uvicorn、DDGS、Requests 和 Loguru；没有数据库、向量数据库或本地嵌入模型依赖。
来源：[后端 `pyproject.toml`](https://github.com/datawhalechina/hello-agents/blob/main/code/chapter14/helloagents-deepresearch/backend/pyproject.toml)

**官方事实：** 前端依赖很少，核心是 Vue 3、Axios、Vite 和 TypeScript。
来源：[前端 `package.json`](https://github.com/datawhalechina/hello-agents/blob/main/code/chapter14/helloagents-deepresearch/frontend/package.json)

**官方事实：** 示例配置支持 API 型 LLM，也支持 Ollama 和 LM Studio；默认搜索项写为 DuckDuckGo，并可选 Tavily、Perplexity 或本地 SearXNG。配置还暴露了研究循环上限与是否抓取全文。
来源：[后端 `.env.example`](https://github.com/datawhalechina/hello-agents/blob/main/code/chapter14/helloagents-deepresearch/backend/.env.example)

**官方事实：** 官方快速开始仅要求 Python、Node/npm、安装依赖并分别启动 FastAPI 与 Vite，没有要求 Docker、Redis、PostgreSQL 或 GPU。文档示例的研究过程约 1–3 分钟，但这只是官方示例陈述，不应视为性能保证。
来源：[快速体验](https://github.com/datawhalechina/hello-agents/blob/main/docs/chapter14/%E7%AC%AC%E5%8D%81%E5%9B%9B%E7%AB%A0%20%E8%87%AA%E5%8A%A8%E5%8C%96%E6%B7%B1%E5%BA%A6%E7%A0%94%E7%A9%B6%E6%99%BA%E8%83%BD%E4%BD%93.md#1413-%E5%BF%AB%E9%80%9F%E4%BD%93%E9%AA%8C5-%E5%88%86%E9%92%9F%E8%BF%90%E8%A1%8C%E9%A1%B9%E7%9B%AE)

## 2. ResearchFlow 可以复用的思想

以下均为基于上述官方实现的 **分析推断**：

1. **保留可控的阶段式工作流。** 将 Planner、Retriever、Evidence Extractor、Writer、Citation Verifier 设计为明确节点，比“多个 Agent 自由聊天”更容易测试、重试、观测和解释。
2. **保留统一搜索适配器。** SearchTool 的统一结果结构和可切换后端值得沿用，但 ResearchFlow 应把搜索结果、抓取正文、证据片段和最终引用分别建模，避免只依赖搜索摘要。
3. **保留 SSE 作为 MVP 流式协议。** 研究流程主要是服务器单向推送状态，SSE 比 WebSocket 更简单；事件应有稳定 schema，并包含 `run_id`、`stage`、`task_id`、进度、错误码和可重放序号。
4. **保留中间产物持久化。** Hello-Agents 用 Markdown 笔记验证了思路；产品化版本应写入持久化存储，并允许刷新页面后恢复运行状态。
5. **把并发做成显式配置。** 当前代码会按 TODO 数启动线程。ResearchFlow 应设置较小并发上限，既防止 API 限流和费用激增，也照顾资源有限的 Windows 电脑。

## 3. 不应直接照搬、需要自行补齐的部分

### 3.1 官方案例的边界

**官方事实：** 第十四章代码依赖中没有关系数据库、向量数据库、鉴权、任务队列或 RAG 组件；其持久化重点是本地 Markdown 笔记。
来源：[后端依赖](https://github.com/datawhalechina/hello-agents/blob/main/code/chapter14/helloagents-deepresearch/backend/pyproject.toml)、[NoteTool 说明](https://github.com/datawhalechina/hello-agents/blob/main/docs/chapter14/%E7%AC%AC%E5%8D%81%E5%9B%9B%E7%AB%A0%20%E8%87%AA%E5%8A%A8%E5%8C%96%E6%B7%B1%E5%BA%A6%E7%A0%94%E7%A9%B6%E6%99%BA%E4%BD%93.md#1442-notetool-%E4%BD%BF%E7%94%A8)

**分析推断：** 因此该案例更接近教学 Demo，而不是多用户 AI SaaS。ResearchFlow 若想作为 AI 全栈求职项目，应至少补齐：

- 用户登录、权限隔离、研究历史；
- 可恢复的 Research Run 状态机与失败重试；
- 文档上传、切分、嵌入、检索与来源定位组成的 RAG 知识库；
- 网页正文抓取、证据片段保存、引用与原文对应关系；
- 限流、超时、取消、预算上限和模型/搜索成本记录；
- 后端单元测试、工作流集成测试、前端关键交互测试；
- 一键本地启动、配置说明、架构图、演示数据和线上 Demo。

### 3.2 “反思式深度研究”仍需真正实现

**官方事实：** 章节开头提出“根据阶段结果识别知识空白，决定是否继续检索”，但章节展开的主要流程和当前协调器代码仍以预先规划 TODO、各任务搜索一次/总结一次、最后写报告为主；代码中的 `research_loop_count` 更直接参与搜索调度参数，并不能单独证明存在一个评估知识空白并重新规划的反思闭环。
来源：[章节目标](https://github.com/datawhalechina/hello-agents/blob/main/docs/chapter14/%E7%AC%AC%E5%8D%81%E5%9B%9B%E7%AB%A0%20%E8%87%AA%E5%8A%A8%E5%8C%96%E6%B7%B1%E5%BA%A6%E7%A0%94%E7%A9%B6%E6%99%BA%E4%BD%93.md)、[协调器源码](https://github.com/datawhalechina/hello-agents/blob/main/code/chapter14/helloagents-deepresearch/backend/src/agent.py)

**分析推断：** ResearchFlow 可通过显式 `CoverageEvaluator` 节点形成差异化能力：评估“哪些主张证据不足 / 哪些子问题未覆盖 / 是否达到最大轮数与预算”，再决定补充检索或进入报告阶段。

## 4. Windows 与低资源方案

### 4.1 有来源支持的事实

- 官方样例本身是普通 Python + Node Web 应用，未声明 GPU 为前置条件，也不要求数据库或容器。来源同上方快速开始和依赖清单。
- 配置允许把 LLM 放在云端 API，也允许 Ollama / LM Studio 本地推理。来源：[`.env.example`](https://github.com/datawhalechina/hello-agents/blob/main/code/chapter14/helloagents-deepresearch/backend/.env.example)。
- DuckDuckGo 搜索路径对应 `ddgs` Python 依赖；Tavily 与 Perplexity 需要各自 API 配置。来源：[后端依赖](https://github.com/datawhalechina/hello-agents/blob/main/code/chapter14/helloagents-deepresearch/backend/pyproject.toml)、[`.env.example`](https://github.com/datawhalechina/hello-agents/blob/main/code/chapter14/helloagents-deepresearch/backend/.env.example)。
- 官方示例的 `pyproject.toml` 使用 `packages = ["src"]` 与 `package-dir` 的组合；仓库中已有 Windows 用户报告 editable install 寻找 `src\\src` 失败，且存在尚未合并的修复 PR。因此 ResearchFlow 不应原样复制该打包配置。来源：[官方 issue #330](https://github.com/datawhalechina/hello-agents/issues/330)、[官方 PR #627](https://github.com/datawhalechina/hello-agents/pull/627)。

### 4.2 面向 ResearchFlow 的推断与建议

- **最低资源默认方案：** Windows 原生运行前后端，LLM 与嵌入模型优先调用远程 API；MVP 使用 SQLite + 本地文件存储，暂不启 Redis、PostgreSQL 和本地大模型。这样本机主要承担 Web 服务、文本处理和少量检索。
- **RAG 起步方案：** 小规模个人知识库可先用进程内/文件型向量索引；等需要展示生产架构时，再提供可选 PostgreSQL + pgvector 配置，而非设为本地开发硬依赖。
- **本地模型不是“轻量默认值”：** 官方虽然支持 Ollama/LM Studio，但模型的内存、显存和磁盘需求取决于具体模型；在未知用户硬件时，不应承诺轻量。远程模型更符合“不占太多电脑资源”的目标。
- **限制并发与上下文：** 默认 2 个并发研究任务、每个子任务 3–5 个来源、最大 1 次补充检索，并对全文长度和总 Token 设预算。该数值是产品建议，不是官方基准。
- **Windows 体验：** 提供 PowerShell 启动脚本或单一开发命令，并避免把 Docker Desktop 设为必需项；Docker 可作为部署/可选完整环境。

## 5. 对简历价值的判断

**分析推断：** 项目方向适合写入 AI 全栈简历，但前提是成果不只是复刻界面和三个 Prompt。能形成可信项目故事的能力证据包括：

- 前端：复杂异步任务的实时状态、取消/重试、来源与报告交互；
- 后端：API、SSE、鉴权、数据建模、持久化、并发与错误恢复；
- AI 工程：结构化规划、Web + RAG 混合检索、证据链、反思闭环、引用验证与评估；
- 工程化：测试、可观测性、配置、CI、部署和成本/延迟权衡；
- 产品表达：公开 Demo、清晰 README、架构图和可复现的评测样例。

一句合适的项目定位是：

> ResearchFlow 是一个可追溯的 AI 深度研究工作台：将开放研究目标拆解为可执行任务，联合网页与个人知识库收集证据，实时展示执行过程，并生成逐条可核验引用的结构化报告。

## 6. 建议的 MVP 边界

**分析推断：** 第一版保持单机、低依赖，同时展示完整闭环：

1. 输入研究目标与可选约束；
2. 生成 3–5 个结构化子任务；
3. Web 搜索 + 一个小型本地知识库检索；
4. 保存来源、证据片段和子任务摘要；
5. SSE 展示任务进度；
6. 生成带可点击引用的 Markdown 报告；
7. 保存并重新打开研究历史；
8. 支持取消、一次重试和明确错误状态。

首版暂缓：多租户计费、复杂多 Agent 自由协作、大规模爬虫、Redis 队列、Kubernetes、本地大模型训练。它们会显著扩大范围，却不是证明 AI 全栈基本能力的必要条件。

## 7. 官方来源索引

- [Hello-Agents 官方仓库首页](https://github.com/datawhalechina/Hello-Agents)
- [官方在线文档](https://hello-agents.datawhale.cc/#/)
- [第十四章：自动化深度研究智能体](https://github.com/datawhalechina/hello-agents/blob/main/docs/chapter14/%E7%AC%AC%E5%8D%81%E5%9B%9B%E7%AB%A0%20%E8%87%AA%E5%8A%A8%E5%8C%96%E6%B7%B1%E5%BA%A6%E7%A0%94%E7%A9%B6%E6%99%BA%E4%BD%93.md)
- [第十四章配套代码](https://github.com/datawhalechina/hello-agents/tree/main/code/chapter14/helloagents-deepresearch)
- [后端协调器](https://github.com/datawhalechina/hello-agents/blob/main/code/chapter14/helloagents-deepresearch/backend/src/agent.py)
- [后端依赖](https://github.com/datawhalechina/hello-agents/blob/main/code/chapter14/helloagents-deepresearch/backend/pyproject.toml)
- [后端示例配置](https://github.com/datawhalechina/hello-agents/blob/main/code/chapter14/helloagents-deepresearch/backend/.env.example)
- [前端依赖](https://github.com/datawhalechina/hello-agents/blob/main/code/chapter14/helloagents-deepresearch/frontend/package.json)
