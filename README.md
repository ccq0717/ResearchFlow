# ResearchFlow

ResearchFlow 是一个以证据为核心的 AI 深度研究工作台。它将开放式研究目标拆解为可执行计划，从网页、学术资料和个人知识库中收集信息，并生成带有可验证引用的结构化报告。

项目的首个演示场景是：调研 AI 代码生成工具的现有评测方法，并产出一份可以实际执行的评测方案。

## 当前进度

仓库目前已经完成第一条可运行的模拟纵向闭环：

- 在 Next.js Dashboard 中创建研究任务；
- 使用 SQLite 保存研究任务和工作流事件；
- 通过 SSE 实时推送工作流进度；
- 展示规划、检索、分析、写作和最终检查阶段；
- 从研究历史中重新打开已完成的任务；
- 在不调用外部模型的情况下生成模拟 Markdown 报告。

真实 LLM、学术搜索、网页检索、证据提取、RAG 和引用验证将在后续里程碑中逐步加入。

## 开发路线图

下面的清单是当前建议的实施顺序。`[x]` 表示已完成，`[ ]` 表示尚未完成；当前优先处理标有“下一步”的里程碑。每完成一个完整里程碑，或项目范围发生变化时，都应同步更新本节和上面的“当前进度”。

### M0：模拟全栈纵向闭环（已完成）

- [x] 初始化可直接上传 GitHub 的 monorepo；
- [x] 实现 Next.js Dashboard 和 Research Workspace；
- [x] 实现 FastAPI 研究任务 API；
- [x] 使用 SQLite 保存任务、事件和模拟报告；
- [x] 使用 SSE 推送模拟工作流进度；
- [x] 支持刷新后重新打开研究历史；
- [x] 添加后端基础测试、前后端检查和中文项目文档。

### M1：真实 LLM 最小接入（下一步）

- [ ] 定义 ResearchFlow 自有的 `ResearchWorkflow` 和 `LLMClient` 接口；
- [ ] 实现 OpenAI-compatible 远程 LLM 适配器；
- [ ] 正式读取并校验模型、Base URL 和 API Key 配置；
- [ ] 让 LLM 根据研究目标生成结构化研究计划；
- [ ] 保留模拟实现和 Fake LLM，使本地测试不依赖真实 API；
- [ ] 记录模型调用错误、耗时和基础 Token 用量。

### M2：LangGraph 与真实网页研究闭环

- [ ] 在 `ResearchWorkflow` 接口后实现 `LangGraphResearchWorkflow`；
- [ ] 建立规划、搜索、阅读、证据提取、写作和检查节点；
- [ ] 接入一个网页搜索 Provider；
- [ ] 读取、清洗和去重网页正文；
- [ ] 在数据库中保存 Source、Evidence 和研究子任务；
- [ ] 在 Research Workspace 展示真实来源和阶段性证据。

### M3：学术检索、引用和黄金演示场景

- [ ] 接入至少一个学术论文来源；
- [ ] 合并网页、论文和公开基准的检索结果；
- [ ] 建立主张与证据之间的引用关系；
- [ ] 生成带可点击引用的 Markdown 报告；
- [ ] 检查引用链接、来源覆盖度和无证据主张；
- [ ] 跑通“AI 代码生成工具评测方案”完整演示。

### M4：本地知识库与 RAG

- [ ] 支持上传首批文档格式，例如 PDF、Markdown 和纯文本；
- [ ] 实现文档解析、分块和处理状态；
- [ ] 选择低资源占用的 Embedding 与向量检索方案；
- [ ] 在研究任务中联合检索个人知识库与外部资料；
- [ ] 展示知识库来源，并支持删除或重新处理文档。

### M5：可靠性、测试与作品集交付

- [ ] 支持任务取消、有限重试和失败恢复；
- [ ] 增加 SSE、工作流、前端组件和浏览器 E2E 测试；
- [ ] 增加延迟、Token、费用和检索质量的基础度量；
- [ ] 完善日志、配置校验、安全说明和数据备份；
- [ ] 提供可选 Docker 或在线部署方案；
- [ ] 准备架构图、演示数据、截图、演示视频和简历项目描述。

登录鉴权、PostgreSQL、Redis、多用户协作和复杂部署不属于当前优先路径，只有在核心研究闭环稳定且确有展示价值时再加入。更详细的产品边界和待确认问题见[项目讨论记录](docs/product/project-discussion.md)。

## 技术栈

- Next.js 16、React 19、TypeScript、Tailwind CSS
- FastAPI、Python 3.12、SQLAlchemy
- 本地 MVP 使用 SQLite
- REST API 与 Server-Sent Events（SSE）
- 计划在 ResearchFlow 自有工作流接口后使用 LangGraph

## 仓库结构

```text
apps/web       Next.js 前端
apps/api       FastAPI 后端
docs           产品、架构、技术决策和调研文档
examples       可公开使用的演示输入
infra          可选部署配置
scripts        本地开发辅助脚本
var            本地运行数据（不提交到 Git）
```

建议先阅读 [MVP 技术规格](docs/product/mvp-spec.md)、[核心数据模型](docs/architecture/domain-model.md)、[SSE 事件契约](docs/architecture/sse-events.md)和[仓库结构设计](docs/architecture/repository-structure.md)。

## 环境要求

- Windows 10 或 Windows 11
- Git
- Node.js 20.9 或更高版本
- npm
- uv
- Python 3.12（也可以由 uv 管理）

本地开发不需要 Docker、Redis、GPU 或本地大模型。

## 初始化项目

在仓库根目录打开 PowerShell：

```powershell
uv sync --package researchflow-api
Copy-Item .env.example .env
npm install --prefix apps/web
```

Python 虚拟环境默认创建在 `.venv`，本地数据库和日志等运行数据创建在 `var/`。

## 本地运行

从仓库根目录打开两个 PowerShell 终端。

后端：

```powershell
.\.venv\Scripts\python.exe -m uvicorn researchflow.main:app `
  --app-dir apps/api/src `
  --host 127.0.0.1 `
  --port 8000 `
  --reload
```

前端：

```powershell
Set-Location apps/web
npm run dev -- --hostname 127.0.0.1
```

启动后访问：

- 前端：[http://localhost:3000](http://localhost:3000)
- 后端健康检查：[http://localhost:8000/health](http://localhost:8000/health)
- 后端接口文档：[http://localhost:8000/docs](http://localhost:8000/docs)

## 运行检查

后端测试与代码检查：

```powershell
.\.venv\Scripts\python.exe -m pytest apps/api/tests
.\.venv\Scripts\ruff.exe check apps/api
```

前端代码检查与生产构建：

```powershell
npm run lint --prefix apps/web
npm run build --prefix apps/web
```

## 配置与安全

请从 `.env.example` 复制本地配置，不要提交真实 API Key、访问令牌或个人资料。

当前模拟闭环不需要任何外部 API Key。后续接入模型和检索服务时，会继续使用环境变量管理敏感配置。

## 项目文档

- [使用、开发与运维手册](docs/guides/development-and-operations.md)
- [从零学习 ResearchFlow：前后端与 AI 工程课程](docs/learning/README.md)
- [项目讨论记录](docs/product/project-discussion.md)
- [MVP 技术规格](docs/product/mvp-spec.md)
- [核心数据模型](docs/architecture/domain-model.md)
- [SSE 事件契约](docs/architecture/sse-events.md)
- [仓库结构设计](docs/architecture/repository-structure.md)
- [LangGraph 架构决策](docs/decisions/0001-use-langgraph-behind-workflow-interface.md)
- [Hello-Agents 调研](docs/research/hello-agents-analysis.md)
