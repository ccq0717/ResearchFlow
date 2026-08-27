# ResearchFlow 使用、开发与运维手册

> 适用范围：Windows 本地使用、开发、测试与排错
>
> 最后更新：2026-08-27

ResearchFlow 由 Next.js 前端、FastAPI 后端、SQLite、本地上传目录以及远程 LLM、网页搜索和 Embedding 服务组成。在线部署另见[作品集 Demo 部署指南](online-demo-deployment.md)。

## 1. 使用产品

1. 打开 `http://localhost:3000`；
2. 可选：上传 PDF、Markdown 或 UTF-8 文本，等待状态变为 `ready`；
3. 输入不少于 10 个字符的研究目标，并选择需要使用的本地文档；
4. 创建任务后查看计划、进度、来源、证据、主张、度量和报告；运行期间可取消；
5. 刷新或重新打开任务不会丢失已持久化内容。

失败任务可重新运行一次。Dashboard 支持重命名、归档和删除已结束记录。

三种工作流模式：

| 模式 | 行为 | 外部依赖 |
| --- | --- | --- |
| `simulation` | 完全模拟研究流程 | 无 |
| `llm` | 真实生成研究计划，其余步骤模拟 | LLM |
| `langgraph` | 联合网页和所选本地资料完成研究 | LLM、Exa；使用本地资料时还需 Embedding |

PDF 只读取已有文本层，不执行 OCR。扫描件会进入 `DOCUMENT_NO_TEXT` 失败状态。

## 2. 初始化与启动

### 环境要求

- Windows 10/11；
- Git；
- Node.js 20.9 或更高版本；
- npm；
- uv；
- Python 3.12，可由 uv 管理。

项目不要求 Docker、Docker Compose、Redis、GPU 或本地大模型。仓库中的容器文件只用于可选的干净环境验证和在线部署。

### 首次安装

在仓库根目录运行：

```powershell
uv sync --package researchflow-api
Copy-Item .env.example .env
npm install --prefix apps/web
```

`.env` 保存本机配置且已被 Git 忽略。不要把真实密钥写入 `.env.example`、文档、截图或前端变量。

### 日常启动

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
npm --prefix apps/web run dev -- --hostname 127.0.0.1
```

启动后检查：

- 前端：`http://localhost:3000`
- 后端健康检查：`http://localhost:8000/health`
- API 文档：`http://localhost:8000/docs`

停止服务时，在对应终端按 `Ctrl+C`。修改 `.env` 或依赖后必须重启；普通 Python、React 和 CSS 修改通常会自动重载。

若端口被占用，可查看监听进程：

```powershell
Get-NetTCPConnection -State Listen |
  Where-Object LocalPort -in 3000,8000 |
  Select-Object LocalAddress,LocalPort,OwningProcess
```

确认是旧 ResearchFlow 进程后再结束它，不要关闭来源不明的进程。

## 3. 配置真实服务

`.env.example` 只列出日常启动需要的核心项。其余设置使用 `Settings` 中的默认值，需要部署调优时才覆盖。

### 联合研究示例

```dotenv
RESEARCHFLOW_WORKFLOW_MODE=langgraph

RESEARCHFLOW_LLM_MODEL=供应商提供的模型名
RESEARCHFLOW_LLM_API_KEY=本机真实密钥
RESEARCHFLOW_LLM_BASE_URL=https://供应商地址/v1
RESEARCHFLOW_LLM_TIMEOUT_SECONDS=180

RESEARCHFLOW_WEB_SEARCH_API_KEY=本机真实Exa密钥

RESEARCHFLOW_EMBEDDING_PROVIDER=gemini
RESEARCHFLOW_EMBEDDING_MODEL=gemini-embedding-2
RESEARCHFLOW_EMBEDDING_API_KEY=本机真实Gemini密钥
RESEARCHFLOW_EMBEDDING_DIMENSIONS=768
```

LLM Base URL 填 API 根地址，不要包含 `/chat/completions`；客户端会自动追加该路径。LLM 服务必须支持 Chat Completions 和严格 JSON Schema 结构化输出。

Gemini 原生适配器默认使用 `https://generativelanguage.googleapis.com/v1beta`。它会按模型版本处理检索用途：`gemini-embedding-2` 使用官方推荐的文本任务指令，`gemini-embedding-001` 使用 `RETRIEVAL_DOCUMENT` / `RETRIEVAL_QUERY` 任务类型。也可以改用 `openai-compatible` Embedding 适配器，并同时覆盖 Base URL。更换 Provider、模型、维度或指令策略后必须在 Dashboard 重新处理已有文档。

### 常用高级设置

| 变量 | 默认值 | 何时调整 |
| --- | --- | --- |
| `RESEARCHFLOW_DATABASE_URL` | `sqlite+aiosqlite:///./var/researchflow.db` | 改变数据库位置 |
| `RESEARCHFLOW_CORS_ORIGINS` | 本地 3000 端口 | 前后端分域部署 |
| `RESEARCHFLOW_WEB_SEARCH_RESULT_LIMIT` | `3` | 调整每个问题的网页数量与费用 |
| `RESEARCHFLOW_WEB_REQUEST_TIMEOUT_SECONDS` | `20` | 网页服务经常超时 |
| `RESEARCHFLOW_MAX_CONCURRENT_RUNS` | `2` | 限制同时运行的研究任务 |
| `RESEARCHFLOW_MAX_RUNS_PER_DAY` | `20` | 限制每日任务及外部服务费用 |
| `RESEARCHFLOW_DEMO_ACCESS_CODE` | 未启用 | 为共享在线 Demo 设置访问码 |
| `RESEARCHFLOW_KNOWLEDGE_UPLOAD_DIRECTORY` | `./var/uploads` | 使用持久磁盘 |
| `RESEARCHFLOW_KNOWLEDGE_MAX_DOCUMENT_BYTES` | `10485760` | 调整单文件上限 |
| `RESEARCHFLOW_KNOWLEDGE_MAX_DOCUMENT_COUNT` | `50` | 调整文档总数上限 |
| `RESEARCHFLOW_KNOWLEDGE_MAX_SELECTION_COUNT` | `10` | 调整单次研究选择上限 |
| `RESEARCHFLOW_KNOWLEDGE_RESULTS_PER_QUESTION` | `2` | 调整每个问题的本地命中数 |
| `RESEARCHFLOW_EMBEDDING_BASE_URL` | Gemini `v1beta` | 更换 Embedding 服务 |
| `RESEARCHFLOW_EMBEDDING_TIMEOUT_SECONDS` | `60` | Embedding 服务经常超时 |
| `RESEARCHFLOW_EMBEDDING_BATCH_SIZE` | `32` | 供应商限制批大小 |

如需在运行页估算模型费用，可配置输入、输出每百万 Token 的美元单价：`RESEARCHFLOW_LLM_INPUT_COST_PER_MILLION_TOKENS` 和 `RESEARCHFLOW_LLM_OUTPUT_COST_PER_MILLION_TOKENS`。未配置时显示“未配置单价”，不会错误显示零费用。

完整默认值以 [`core/config.py`](../../apps/api/src/researchflow/core/config.py) 为准。

### 前端 API 地址

前端默认访问 `http://localhost:8000`。需要覆盖时，在 `apps/web/.env.local` 设置：

```dotenv
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

`NEXT_PUBLIC_*` 会进入浏览器，不能存放密钥。

## 4. 数据、备份与重置

默认运行数据：

```text
var/
├── researchflow.db
└── uploads/
```

数据库保存任务、事件、计划、来源、证据、主张、文档片段和 Embedding；上传目录保存原始文件。两者必须作为同一个数据集备份。

停止后端后执行备份，脚本输出带时间戳的目录：

```powershell
.\scripts\backup_data.ps1
```

恢复到空目录后检查：

```powershell
.\scripts\restore_data.ps1 -BackupDirectory .\backups\时间戳 -DataDirectory .\var-restored
```

`backups/` 可能包含私人资料，不应提交。恢复目标必须是空目录，避免把两套数据混合。需要清空数据时，先停止后端并保留备份，再删除明确的数据库和上传目录。

数据库保存 `schema_migrations` 版本。当前基线可为旧数据库无损补齐附属表；不兼容版本会拒绝启动。SQLite 回滚使用更新前备份恢复，不在原库上执行破坏性降级。

## 5. 检查与测试

后端：

```powershell
.\.venv\Scripts\python.exe -m pytest apps/api/tests
.\.venv\Scripts\ruff.exe check apps/api scripts
.\.venv\Scripts\ruff.exe format --check apps/api scripts
```

前端：

```powershell
npm test --prefix apps/web
npm run lint --prefix apps/web
npm run build --prefix apps/web
npm run test:e2e --prefix apps/web
```

真实服务评测不会进入常规测试，需手动执行并消耗少量额度：

```powershell
.\.venv\Scripts\python.exe scripts\evaluate_exa_coverage.py
.\.venv\Scripts\python.exe scripts\evaluate_local_retrieval.py
```

自动化测试显式禁用仓库 `.env`，并使用 Fake 或 HTTP Mock，不会读取真实密钥或访问外部服务。
浏览器 E2E 会在专用端口启动模拟工作流，验证创建、完成、报告、度量和刷新恢复，并在结束后关闭测试服务。

## 6. 常见问题

### 页面无法读取任务

1. 打开 `http://localhost:8000/health`；
2. 确认前端 API 地址与后端端口一致；
3. 检查浏览器 Network 和后端终端中的第一条错误；
4. 不要混用已停止的旧后端进程。

### 实时进度中断

刷新任务页面。前端会先恢复已保存事件，再从最后序号继续 SSE。连接中断与研究任务失败是两个不同状态。

### LLM 调用失败

- `LLM_CONNECTION_ERROR`：检查 Base URL 和网络；
- HTTP 401：检查 API Key 及其所属项目；
- HTTP 404：检查 Base URL、路径和模型名；
- `LLM_INVALID_RESPONSE`：确认服务支持严格 JSON Schema；
- `LLM_TIMEOUT`：确认服务状态，必要时提高超时；
- 重复 `/chat/completions/chat/completions`：Base URL 填成了完整端点，应改回根地址。

### Embedding 调用失败

- `EMBEDDING_NOT_CONFIGURED`：填写 Provider、模型和密钥后重新处理文档；
- HTTP 401/403：检查密钥和模型权限；
- `EMBEDDING_REPROCESS_REQUIRED`：当前向量与模型、维度或检索指令策略不匹配；
- `EMBEDDING_DIMENSION_MISMATCH`：确认查询与文档使用相同配置并重新处理；
- 模型不支持指定维度：删除或修改 `RESEARCHFLOW_EMBEDDING_DIMENSIONS`。

### SQLite 锁定

确认只启动了一个后端实例。停止所有后端、备份 `var/`，再启动单个实例。只有确认数据可舍弃时才重置。

## 7. 安全与当前边界

- 密钥只保存在服务端 `.env` 或部署平台 Secret；
- 文档片段会发送给 Embedding Provider，检索命中还会发送给 LLM；
- 不上传不允许交给这些供应商处理的私人或受限资料；
- 错误响应不会返回密钥、供应商原始正文或堆栈；
- 当前 SQLite 和进程内任务适合单实例、低流量演示，不适合直接横向扩展；
- API 日志只记录请求 ID、路径、状态和耗时，不记录请求正文、密钥或文档内容；
- 本地可不设置访问码；设置 `RESEARCHFLOW_DEMO_ACCESS_CODE` 后，Dashboard 会先要求解锁，Cookie 只保存后端签发的会话值；
- `production` 环境强制使用 `langgraph`、公开 CORS Origin 和至少 12 字符的访问码；
- 线上限流、费用上限、持久磁盘和备份要求见[部署指南](online-demo-deployment.md)。

演示前只需确认：前后端健康、真实服务密钥有效、知识文档为 `ready`、任务能够完成、来源链接可打开且页面未暴露敏感信息。
