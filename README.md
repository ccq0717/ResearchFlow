# ResearchFlow

ResearchFlow 是一个正在分阶段实现的 AI 深度研究工作台。当前版本能把开放式研究目标转成结构化计划，检索和读取开放 Web 中的公开资料，保存来源与证据，并展示可恢复的研究过程；后续将加入来源分类、可追溯引用和个人知识库。

项目的首个演示场景是：调研 AI 代码生成工具的现有评测方法，并产出一份可以实际执行的评测方案。

## 当前进度

仓库目前已完成 M0、M1 和 M2，已经具备第一条可重新打开的真实网页研究闭环：

- 在 Next.js Dashboard 创建任务，并在 Research Workspace 查看 SSE 实时进度；
- 使用 SQLite 持久化运行、事件、结构化计划、检索子任务、网页来源、证据和报告；
- `simulation` 模式完全离线，`llm` 模式只生成真实计划；
- `langgraph` 模式执行规划、搜索、阅读、证据提取、写作和检查六个节点；
- 真实网页来源使用 Exa Search API 检索论文页面、官方文档、企业技术博客和其他公开网页；
- 中文研究问题与英文检索词分开保存，兼顾界面可读性和通用 Web 检索效果；
- 前端展示研究计划、检索来源、证据摘要与原文片段，刷新后仍可恢复；
- 外部能力均有 Fake/Mock，常规测试不联网、不消耗模型额度；
- 后端、前端、Ruff、ESLint 和生产构建纳入 GitHub Actions。

M2 已建立通用网页研究闭环，但尚不等同于完整的学术研究与引用系统。专业学术元数据、Claim—Evidence 引用关系、黄金演示报告和引用覆盖检查属于 M3。

## 开发路线图

当前已完成 M2“LangGraph 与真实网页研究闭环”，下一步是 M3“来源质量、可追溯引用和黄金演示场景”。

- [x] M0：模拟全栈纵向闭环；
- [x] M1：真实 LLM 接入与工程加固；
- [x] M2：LangGraph 与真实网页研究闭环；
- [ ] M3：来源质量、可追溯引用和黄金演示场景；
- [ ] M4：本地知识库与 RAG；
- [ ] M5：可靠性、测试与作品集交付。

每个里程碑的详细任务、实施顺序、完成标准和待确认选择见[项目路线图](docs/product/roadmap.md)。

## 技术栈

- Next.js 16、React 19、TypeScript、Tailwind CSS
- FastAPI、Python 3.12、SQLAlchemy、SQLite
- LangGraph `StateGraph`
- REST API 与 Server-Sent Events（SSE）
- HTTPX、Exa Search API
- OpenAI-compatible JSON Schema 结构化输出
- ResearchFlow 自有 `ResearchWorkflow`、`LLMClient`、`SearchProvider` 与 `WebPageReader` 接口

## 仓库结构

```text
apps/web       Next.js 前端
apps/api       FastAPI 后端
docs           产品、架构、技术决策和调研文档
examples       可公开使用的演示输入
var            本地运行数据（不提交到 Git）
```

建议先阅读 [MVP 技术规格](docs/product/mvp-spec.md)、[核心数据模型](docs/architecture/domain-model.md)、[LLM 接入架构](docs/architecture/llm-integration.md)、[SSE 事件契约](docs/architecture/sse-events.md)和[仓库结构设计](docs/architecture/repository-structure.md)。

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
.\.venv\Scripts\ruff.exe format --check apps/api
```

前端测试、代码检查与生产构建：

```powershell
npm test --prefix apps/web
npm run lint --prefix apps/web
npm run build --prefix apps/web
```

## 配置与安全

请从 `.env.example` 复制本地配置，不要提交真实 API Key、访问令牌或个人资料。

默认 `simulation` 模式不需要任何外部服务。若要启用 M2 真实网页研究，在本地 `.env` 中设置：

```dotenv
RESEARCHFLOW_WORKFLOW_MODE=langgraph
RESEARCHFLOW_LLM_PROVIDER=openai-compatible
RESEARCHFLOW_LLM_MODEL=你的模型名
RESEARCHFLOW_LLM_API_KEY=你的密钥
RESEARCHFLOW_LLM_BASE_URL=https://你的兼容服务/v1
RESEARCHFLOW_WEB_SEARCH_PROVIDER=exa
RESEARCHFLOW_WEB_SEARCH_API_KEY=你的Exa密钥
```

LLM Base URL 应填写 API 根地址，客户端会自动追加 `/chat/completions`。`RESEARCHFLOW_LLM_PROVIDER` 当前是协议/来源标签，使用兼容服务时保持 `openai-compatible`。目标服务需支持 Chat Completions 和 JSON Schema 结构化输出；Exa Key 可从 Exa Dashboard 的免费 Starter 获取。本地兼容模型服务若不要求鉴权，LLM Key 可留空，但 `langgraph` 模式必须配置网页搜索 Key。修改配置后重启后端；真实密钥不得提交到 Git。完整说明见[使用、开发与运维手册](docs/guides/development-and-operations.md)。

## 项目文档

- [使用、开发与运维手册](docs/guides/development-and-operations.md)
- [作品集在线 Demo 部署指南](docs/guides/online-demo-deployment.md)
- [从零学习 ResearchFlow：前后端与 AI 工程课程](docs/learning/README.md)
- [项目讨论记录](docs/product/project-discussion.md)
- [项目路线图](docs/product/roadmap.md)
- [M1 阶段复盘](docs/product/retrospectives/m1.md)
- [M1 可用性跟进复盘](docs/product/retrospectives/m1-usability-follow-up.md)
- [M1 工程加固复盘](docs/product/retrospectives/pre-m2-hardening.md)
- [M2 阶段复盘](docs/product/retrospectives/m2.md)
- [MVP 技术规格](docs/product/mvp-spec.md)
- [领域词汇表](CONTEXT.md)
- [核心数据模型](docs/architecture/domain-model.md)
- [LLM 接入架构](docs/architecture/llm-integration.md)
- [SSE 事件契约](docs/architecture/sse-events.md)
- [仓库结构设计](docs/architecture/repository-structure.md)
- [LangGraph 架构决策](docs/decisions/0001-use-langgraph-behind-workflow-interface.md)
- [Hello-Agents 调研](docs/research/hello-agents-analysis.md)
- [OpenCode Zen API 配置调研](docs/research/opencode-zen-api.md)
- [通用网页搜索 Provider 比较](docs/research/general-web-search-provider-comparison.md)

## 许可证

本项目使用 [MIT License](LICENSE)。
