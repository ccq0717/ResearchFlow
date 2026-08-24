# ResearchFlow

ResearchFlow 是一个正在分阶段实现的 AI 深度研究工作台。当前版本能把开放式研究目标转成结构化计划并展示可恢复的研究过程；后续将接入网页、学术资料和个人知识库，生成带可验证引用的报告。

项目的首个演示场景是：调研 AI 代码生成工具的现有评测方法，并产出一份可以实际执行的评测方案。

## 当前进度

仓库目前已完成 M0 全栈闭环、M1 真实 LLM 最小接入和进入 M2 前的工程加固：

- 在 Next.js Dashboard 中创建任务，并在 Research Workspace 查看 SSE 实时进度；重新进入任务时会恢复持久化研究事件；
- 使用 SQLite 持久化研究任务、事件、结构化研究计划和演示报告；
- 默认模拟模式无需 API Key、外部服务、Docker 或 GPU；
- LLM 模式可通过 OpenAI-compatible HTTP 服务生成结构化研究计划；
- 前端展示计划摘要、核心研究问题、交付物、模型、人类可读耗时和 Token 用量；
- API 始终输出带 UTC 标记的时间，前端按浏览器本地时区显示事件与研究记录时间；
- 无副作用的应用工厂、Fake LLM 与 Mock HTTP 测试隔离本机 `.env`，保证自动化测试不联网、不产生 API 费用；
- OpenCode Zen `mimo-v2.5-free` 已通过一次不含敏感内容的真实 API 冒烟测试；
- 后端集成测试、前端 Vitest、Ruff、ESLint 和生产构建已纳入 GitHub Actions。

当前真实 LLM 只负责规划，检索、分析和报告生成仍为轻量演示。学术搜索、网页检索、证据提取、RAG 和引用验证将在 M2～M4 逐步加入。

## 开发路线图

当前已完成 M0“模拟全栈纵向闭环”、M1“真实 LLM 最小接入”和 M1.5“进入 M2 前工程加固”，下一步是 M2“LangGraph 与真实网页研究闭环”。

- [x] M0：模拟全栈纵向闭环；
- [x] M1：真实 LLM 最小接入；
- [x] M1.5：进入 M2 前工程加固；
- [ ] M2：LangGraph 与真实网页研究闭环；
- [ ] M3：学术检索、引用和黄金演示场景；
- [ ] M4：本地知识库与 RAG；
- [ ] M5：可靠性、测试与作品集交付。

每个里程碑的详细任务、实施顺序、完成标准和待确认选择见[项目路线图](docs/product/roadmap.md)。完成里程碑或调整范围时，应同步更新本节和上面的“当前进度”。

## 技术栈

- Next.js 16、React 19、TypeScript、Tailwind CSS
- FastAPI、Python 3.12、SQLAlchemy
- 本地 MVP 使用 SQLite
- REST API 与 Server-Sent Events（SSE）
- HTTPX、OpenAI-compatible JSON Schema 结构化输出
- ResearchFlow 自有 `ResearchWorkflow` / `LLMClient` 接口，计划在其后使用 LangGraph

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

默认 `simulation` 模式不需要任何外部 API Key。若要启用真实规划，在本地 `.env` 中设置：

```dotenv
RESEARCHFLOW_WORKFLOW_MODE=llm
RESEARCHFLOW_LLM_PROVIDER=openai-compatible
RESEARCHFLOW_LLM_MODEL=你的模型名
RESEARCHFLOW_LLM_API_KEY=你的密钥
RESEARCHFLOW_LLM_BASE_URL=https://你的兼容服务/v1
```

Base URL 应填写 API 根地址，客户端会自动追加 `/chat/completions`。`RESEARCHFLOW_LLM_PROVIDER` 当前是协议/来源标签，使用兼容服务时保持 `openai-compatible`。目标服务需支持 Chat Completions 和 JSON Schema 结构化输出。本地兼容服务若不要求鉴权，可将 API Key 留空。修改配置后重启后端；真实密钥不得提交到 Git。完整说明见[使用、开发与运维手册](docs/guides/development-and-operations.md)。

## 项目文档

- [使用、开发与运维手册](docs/guides/development-and-operations.md)
- [从零学习 ResearchFlow：前后端与 AI 工程课程](docs/learning/README.md)
- [项目讨论记录](docs/product/project-discussion.md)
- [项目路线图](docs/product/roadmap.md)
- [M1 阶段复盘](docs/product/retrospectives/m1.md)
- [M1 可用性跟进复盘](docs/product/retrospectives/m1-usability-follow-up.md)
- [进入 M2 前工程加固复盘](docs/product/retrospectives/pre-m2-hardening.md)
- [MVP 技术规格](docs/product/mvp-spec.md)
- [领域词汇表](CONTEXT.md)
- [核心数据模型](docs/architecture/domain-model.md)
- [LLM 接入架构](docs/architecture/llm-integration.md)
- [SSE 事件契约](docs/architecture/sse-events.md)
- [仓库结构设计](docs/architecture/repository-structure.md)
- [LangGraph 架构决策](docs/decisions/0001-use-langgraph-behind-workflow-interface.md)
- [Hello-Agents 调研](docs/research/hello-agents-analysis.md)
- [OpenCode Zen API 配置调研](docs/research/opencode-zen-api.md)

## 许可证

本项目使用 [MIT License](LICENSE)。
