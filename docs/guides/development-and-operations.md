# ResearchFlow 使用、开发与运维手册

> 适用阶段：M1 真实 LLM 最小接入
> 主要平台：Windows 10 / 11 + PowerShell
> 最后更新：2026-08-24

本文是 ResearchFlow 的统一运行手册，回答以下问题：

- 普通用户如何使用和演示产品；
- 开发者第一次拿到代码后如何初始化；
- 日常开发时如何启动、检查、停止和重启服务；
- 数据放在哪里，如何备份与重置；
- 常见故障如何定位；
- 如何在默认模拟模式和真实 LLM 规划模式之间切换；
- 未来接入搜索、RAG 等服务后，运行方式会如何扩展。

项目已完成 M1：真实 LLM 可以生成结构化研究计划；检索、证据与引用仍未实现。文中标注为“未来”的操作是维护预案，不代表对应能力已经实现。

## 1. 当前产品由什么组成

| 组件 | 当前实现 | 默认地址或位置 | 是否必须运行 |
| --- | --- | --- | --- |
| Web 前端 | Next.js | http://127.0.0.1:3000 | 是 |
| API 后端 | FastAPI | http://127.0.0.1:8000 | 是 |
| 本地数据库 | SQLite | `var/researchflow.db` | 由后端自动使用 |
| 研究工作流 | 模拟或 LLM 规划工作流 | 后端进程内 | 由后端自动运行 |
| LLM | OpenAI-compatible HTTP 适配器 | 远程或本地兼容服务 | 仅 `llm` 模式需要 |
| 网页/论文搜索 | 尚未接入 | 无 | 否 |
| 向量数据库 / RAG | 尚未接入 | 无 | 否 |

前端负责展示页面和接收操作，后端负责保存任务、运行工作流并通过 SSE 推送进度。关闭前端不会删除数据；关闭后端会让页面暂时无法读取或创建任务。

## 2. 普通用户如何使用当前产品

1. 确认前端和后端已经启动。
2. 打开 http://localhost:3000。
3. 在“你想研究什么？”文本框输入至少 10 个字符的研究目标。
4. 点击“开始研究”。
5. 在 Research Workspace 查看阶段、进度、实时日志和最终报告。
6. 返回 Dashboard，可从“研究记录”查看完成/更新时间并重新打开已保存任务；重新进入后会恢复完整工作日志。

推荐演示输入：

```text
调研学术界和工业界对 AI 代码生成工具的评测方法，并设计一份覆盖代码质量、安全性和开发效率的评测方案。
```

默认 `simulation` 模式输出模拟报告，不访问互联网、论文数据库或真实模型。`llm` 模式会真实生成并展示研究计划，但后续检索、分析和报告仍是演示逻辑。演示时应主动说明这一边界。

## 3. 第一次初始化开发环境

### 3.1 环境要求

- Git
- Python 3.12
- uv
- Node.js 20.9 或更高版本
- npm

当前阶段不需要 Docker、Redis、PostgreSQL、GPU 或本地大模型。

### 3.2 安装项目依赖

在仓库根目录 `E:\VScodeProjects\ResearchFlow` 打开 PowerShell：

```powershell
uv sync --package researchflow-api
Copy-Item .env.example .env
npm install --prefix apps/web
```

执行完成后将出现：

- `.venv/`：项目隔离的 Python 环境；
- `apps/web/node_modules/`：前端依赖；
- `.env`：本机配置，不提交到 Git；
- `.uv-cache/`：本机当前采用的项目内 uv 缓存；其他环境可能使用 uv 的默认缓存位置。它不是运行必需文件，可删除后重新生成。

`uv.lock` 和 `apps/web/package-lock.json` 应提交到 Git；`.venv`、`node_modules` 和 `.env` 不应提交。

## 4. 日常启动

每次开发需要两个 PowerShell 终端，两个终端都从仓库根目录开始。

### 4.1 启动后端

```powershell
.\.venv\Scripts\python.exe -m uvicorn researchflow.main:app `
  --app-dir apps/api/src `
  --host 127.0.0.1 `
  --port 8000 `
  --reload
```

`--reload` 表示 Python 文件变化时自动重启后端，只适合本地开发。

检查后端：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

预期返回中包含：

```text
status workflow_mode
------ -------------
ok     simulation
```

切换为真实规划后，`workflow_mode` 显示 `llm`。

也可以打开 http://localhost:8000/docs 查看 FastAPI 自动生成的接口文档。

### 4.2 启动前端

在第二个终端执行：

```powershell
Set-Location apps/web
npm run dev -- --hostname 127.0.0.1
```

看到 Next.js 显示 Ready 后，打开 http://localhost:3000。

开发模式左下角的 `N` 是 Next.js 16 自带的开发指示器（Dev Indicator），用于查看当前 Route、Bundler 等开发信息，不属于 ResearchFlow 产品界面，也不会出现在生产模式页面。可以在 `next.config.ts` 中通过 `devIndicators` 调整位置或关闭；当前保留默认设置，方便开发诊断。

### 4.3 推荐启动顺序

1. 后端；
2. 后端健康检查；
3. 前端；
4. 浏览器演示。

先启动后端可以避免前端首次加载研究历史时出现连接错误。

## 5. 停止、重启与端口管理

### 5.1 正常停止

在运行前端和后端的两个终端中分别按：

```text
Ctrl + C
```

这是首选方式，因为进程有机会正常结束并释放资源。关闭终端窗口通常也会结束进程，但不如 `Ctrl + C` 明确。

### 5.2 找不到原终端时

先查看是谁占用了端口：

```powershell
Get-NetTCPConnection -State Listen |
  Where-Object LocalPort -in 3000, 8000 |
  Select-Object LocalAddress, LocalPort, OwningProcess
```

再检查进程名称：

```powershell
Get-Process -Id <进程ID>
```

只有确认 3000 对应项目的 Node.js、8000 对应项目的 Python 后，再执行：

```powershell
Stop-Process -Id <进程ID>
```

不要保存并重复使用旧 PID；进程 ID 每次启动都可能变化，也可能被其他程序重新使用。

### 5.3 确认已经关闭

```powershell
Get-NetTCPConnection -State Listen |
  Where-Object LocalPort -in 3000, 8000
```

没有输出表示当前没有程序监听这两个端口。

### 5.4 是否可以一直开着

可以，但没有必要。按本文命令启动时，前后端都显式绑定 `127.0.0.1`，不会主动暴露给局域网；它们仍会占用内存、端口和文件监听资源。若使用不带 `--hostname` 的其他前端命令，应根据终端输出确认实际监听地址。短时间连续开发可以保持运行，长时间不用、准备休眠或需要释放资源时建议关闭。

### 5.5 重启

先在对应终端按 `Ctrl + C`，确认进程退出，再重新执行启动命令。只修改普通 Python 文件时，后端的 `--reload` 通常会自动重启；修改依赖、环境变量或遇到异常状态时，应手动完整重启。

后端正常关闭时会请求取消正在执行的工作流并等待数据库清理完成；若任务尚未到达终态，则保存为 `failed` 并使用稳定错误码 `RUN_INTERRUPTED`。若进程被强制结束而来不及清理，下次启动会恢复检查，并把遗留的 `queued` 或 `running` 任务标记为同类中断失败，避免任务永远卡住。

## 6. 配置文件与环境变量

### 6.1 后端当前实际读取的变量

后端从仓库根目录 `.env` 读取带 `RESEARCHFLOW_` 前缀的配置：

| 变量 | 当前作用 | 默认值 |
| --- | --- | --- |
| `RESEARCHFLOW_ENVIRONMENT` | 环境名称 | `development` |
| `RESEARCHFLOW_DATABASE_URL` | 数据库连接地址 | SQLite 文件 |
| `RESEARCHFLOW_CORS_ORIGINS` | 允许访问 API 的前端来源 | `http://localhost:3000` |
| `RESEARCHFLOW_SIMULATION_STEP_DELAY` | 演示阶段之间的等待秒数 | `0.7` |
| `RESEARCHFLOW_WORKFLOW_MODE` | `simulation` 或 `llm` | `simulation` |
| `RESEARCHFLOW_LLM_PROVIDER` | 接口协议/来源标签；当前不用于动态选择适配器 | `openai-compatible` |
| `RESEARCHFLOW_LLM_MODEL` | 模型服务识别的模型名 | 空 |
| `RESEARCHFLOW_LLM_API_KEY` | 模型鉴权密钥；本地服务可留空 | 空 |
| `RESEARCHFLOW_LLM_BASE_URL` | 兼容 API 根地址；客户端追加 `/chat/completions` | `https://api.openai.com/v1` |
| `RESEARCHFLOW_LLM_TIMEOUT_SECONDS` | 单次模型请求超时秒数 | `60` |

修改 `.env` 后应重启后端。`llm` 模式必须配置非空模型名；API Key 使用 `SecretStr` 读取，不会出现在正常配置打印中。`RESEARCHFLOW_LLM_PROVIDER` 保持 `openai-compatible` 即可，它目前只用于记录协议/来源，不会切换适配器。Base URL 应填 API 根地址，不要包含末尾的 `/chat/completions`。

### 6.2 前端 API 地址

前端读取 `NEXT_PUBLIC_API_BASE_URL`，未配置时默认使用 `http://localhost:8000`。

Next.js 开发服务器从 `apps/web` 运行，因此需要覆盖默认值时，推荐创建：

```text
apps/web/.env.local
```

内容示例：

```dotenv
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

修改后应重启前端。`.env.local` 已被仓库的忽略规则覆盖，不应提交。

### 6.3 启用真实 LLM 规划

先确认服务支持 Chat Completions 的 `/chat/completions` 路径和 `response_format.type=json_schema`。把仓库根目录 `.env` 中相关配置改为：

```dotenv
RESEARCHFLOW_WORKFLOW_MODE=llm
RESEARCHFLOW_LLM_PROVIDER=openai-compatible
RESEARCHFLOW_LLM_MODEL=供应商提供的模型名
RESEARCHFLOW_LLM_API_KEY=本机真实密钥
RESEARCHFLOW_LLM_BASE_URL=https://供应商地址/v1
RESEARCHFLOW_LLM_TIMEOUT_SECONDS=60
```

OpenCode Zen 的 MiMo-V2.5 Free 示例：

```dotenv
RESEARCHFLOW_LLM_PROVIDER=openai-compatible
RESEARCHFLOW_LLM_MODEL=mimo-v2.5-free
RESEARCHFLOW_LLM_BASE_URL=https://opencode.ai/zen/v1
```

直接 API 不使用 `opencode/` 模型前缀；该前缀仅属于 OpenCode 自身的模型配置。根据 OpenCode 官方说明，免费 MiMo 模型的数据可能被用于改进模型，因此不要提交密钥、个人信息、未公开论文或企业敏感资料。详细核对见 [OpenCode Zen API 配置调研](../research/opencode-zen-api.md)。

重启后端并访问 `/health`，确认 `workflow_mode` 为 `llm`。创建任务后，规划阶段会访问模型服务；成功时工作区出现结构化计划，失败时任务进入 `failed` 并显示安全错误。

要回到完全离线、无费用的模式，只需设置：

```dotenv
RESEARCHFLOW_WORKFLOW_MODE=simulation
```

然后重启后端。不要把真实密钥复制回 `.env.example`、README、聊天截图或 Git Commit。

### 6.4 当前仍未生效的搜索配置

`SEARCH_PROVIDER` 和 `TAVILY_API_KEY` 只是未来占位符，当前代码不会读取，也不会执行真实网页或论文搜索。

## 7. 本地数据、备份与重置

### 7.1 数据位置

当前研究任务、结构化计划、事件和报告保存在：

```text
var/researchflow.db
```

`var/` 被 Git 忽略，不会上传到 GitHub。

### 7.2 当前数据库技术分层与只读检查

当前不需要安装或启动独立的 SQLite 服务，也没有安装 `sqlite3.exe` 命令行工具。项目使用以下几层协作：

| 层 | 当前来源 | 作用 |
| --- | --- | --- |
| SQLite 引擎与 `sqlite3` 接口 | 本机已有的 Python 3.12 | 直接打开和读写数据库文件 |
| aiosqlite | 项目 `.venv` | 为 SQLite 提供适合 `async/await` 的桥接接口 |
| SQLAlchemy | 项目 `.venv` | 管理表映射、查询、Session 和事务 |
| `SqliteResearchRepository` | ResearchFlow 源代码 | 保存任务、结构化计划、状态和事件 |
| 数据库文件 | `var/researchflow.db` | 持久保存任务、结构化计划、事件和报告 |

后端启动时会自动创建数据库目录、文件和当前所需的表。SQLite 没有独立端口；关闭后端后也就没有 ResearchFlow 进程在使用它，但数据库文件仍然存在。

需要确认数据库包含哪些表时，可以先停止后端，再从仓库根目录执行只读查询：

```powershell
.\.venv\Scripts\python.exe -c 'import sqlite3; db=sqlite3.connect("file:var/researchflow.db?mode=ro", uri=True); print(db.execute("SELECT name FROM sqlite_master WHERE type=? ORDER BY name", ("table",)).fetchall()); db.close()'
```

查看当前研究任务数量：

```powershell
.\.venv\Scripts\python.exe -c 'import sqlite3; db=sqlite3.connect("file:var/researchflow.db?mode=ro", uri=True); print(db.execute("SELECT COUNT(*) FROM research_runs").fetchone()[0]); db.close()'
```

两个命令都使用 Python 自带的 `sqlite3` 接口和只读模式，不会修改数据库。当前业务表包括 `research_runs`、`research_plans` 和 `research_events`。概念解释见 [SQLite 与数据持久化课程](../learning/lessons/0003-understand-sqlite-persistence.html)。

### 7.3 备份

先停止后端，再执行：

```powershell
New-Item -ItemType Directory -Force backups | Out-Null
Copy-Item .\var\researchflow.db .\backups\researchflow.db
```

如需保留多份备份，可以在文件名中加入日期。`backups/` 当前没有被默认忽略；若实际使用该目录，应先将它加入 `.gitignore`，避免提交包含个人研究内容的数据库。

### 7.4 重置本地数据

先停止后端。为了可恢复，优先移动而不是直接删除：

```powershell
Move-Item .\var\researchflow.db .\var\researchflow.db.bak
```

下次启动后端时会自动创建新的空数据库。确认旧数据不再需要后，再手动处理 `.bak` 文件。

## 8. 代码检查与测试

后端测试：

```powershell
.\.venv\Scripts\python.exe -m pytest apps/api/tests
```

后端静态检查：

```powershell
.\.venv\Scripts\ruff.exe check apps/api
```

前端代码检查：

```powershell
npm run lint --prefix apps/web
```

前端生产构建检查：

```powershell
npm run build --prefix apps/web
```

一个完整功能改动在提交前至少应运行与该改动相关的检查；跨越前后端的改动建议运行全部四项。

自动化测试通过 `_env_file=None` 明确禁止读取仓库根目录 `.env`，并使用 Fake 或 Mock，因而不会使用本机真实 API Key、访问外部模型或产生费用。真实供应商检查是单独执行、需要明确授权的冒烟测试，不能混入常规测试套件。

## 9. 常见问题排查

### 9.1 提示端口已被占用

症状通常包含 `address already in use` 或 `EADDRINUSE`。

1. 使用第 5.2 节命令查找端口对应进程；
2. 判断它是旧 ResearchFlow 进程还是其他软件；
3. 若是旧进程，正常停止或确认后结束；
4. 若是其他软件，不要强行关闭，可临时换端口并同步修改前端 API 地址和 CORS 配置。

### 9.2 页面提示无法读取研究历史

依次检查：

1. 后端终端是否仍在运行；
2. http://localhost:8000/health 是否返回 `ok`；
3. 前端使用的 API 地址是否正确；
4. 浏览器开发者工具 Network 面板中请求的状态码；
5. 后端终端是否出现异常堆栈。

### 9.3 页面能打开，但实时进度中断

1. 检查 `/api/research-runs/{id}/events` 请求是否仍处于连接状态；
2. 检查后端是否仍在运行；
3. 刷新或重新进入任务页面；前端会先读取 `/events/history` 恢复已保存日志，再从最后事件序号继续 SSE；
4. 区分“SSE 连接中断”和“研究任务失败”，两者不是同一件事。

详细协议见 [SSE 事件契约](../architecture/sse-events.md)，入门解释见 [SSE 第一课](../learning/lessons/0001-understand-sse.html)。SQLite 取回的时间可能没有时区信息，Repository 会将其恢复为 UTC；API 输出 `Z`/`+00:00`，前端再按浏览器本地时区展示。

### 9.4 修改代码后没有生效

- Python 普通代码：观察后端是否完成自动重载；
- `.env` 或依赖：手动重启后端；
- React / CSS：观察 Next.js 是否重新编译，必要时刷新浏览器；
- `apps/web/.env.local` 或前端依赖：手动重启前端；
- 仍异常时，先阅读终端中的第一条错误，而不是只看最后一行。

### 9.5 数据库异常或锁定

1. 确认是否启动了多个后端实例；
2. 停止全部后端；
3. 备份 `var/`；
4. 再启动单个后端验证；
5. 只有确认数据可舍弃时才按第 7.4 节重置。

### 9.6 LLM 模式启动或运行失败

1. `/health` 仍显示 `simulation`：确认修改的是仓库根目录 `.env`，然后完整重启后端；
2. 启动时报模型名缺失：设置 `RESEARCHFLOW_LLM_MODEL`；
3. `LLM_CONNECTION_ERROR`：检查 Base URL、网络或本地模型服务是否启动；
4. `LLM_HTTP_ERROR`：检查状态码、模型名、权限和余额，但不要把完整 Key 发到聊天或日志；
5. `LLM_INVALID_RESPONSE`：服务可能不支持严格 JSON Schema，或所选模型没有按 Schema 返回；
6. `LLM_TIMEOUT`：确认服务状态，必要时谨慎提高超时；
7. 若请求路径出现重复的 `/chat/completions/chat/completions`，说明 Base URL 填成了完整端点，应改回 API 根地址。

模型错误事件不会包含密钥或原始响应正文。真实服务兼容性、隐私规则与费用需要使用者根据供应商文档自行确认。OpenCode Zen 的当前核对记录见 [OpenCode Zen API 配置调研](../research/opencode-zen-api.md)。

## 10. Git 与敏感信息

提交前检查：

```powershell
git status
git diff --check
git diff --cached
```

完成一个可说明、可验证的改动单元后再提交。提交信息采用类型前缀加中文描述，例如：

```text
feat: 实现真实检索工作流
fix: 修复 SSE 断线重连
docs: 补充开发与运维手册
```

推送前确认没有 `.env`、API Key、访问令牌、个人数据库或私有论文资料。普通开发流程为：

```powershell
git add <本次改动文件>
git commit -m "类型: 中文说明"
git push
```

## 11. 本地生产模式预览

前端可以用接近生产的方式运行：

```powershell
npm run build --prefix apps/web
npm run start --prefix apps/web -- --hostname 127.0.0.1
```

后端去掉开发专用的 `--reload`：

```powershell
.\.venv\Scripts\python.exe -m uvicorn researchflow.main:app `
  --app-dir apps/api/src `
  --host 127.0.0.1 `
  --port 8000
```

这只是本地生产模式预览，不等于已经可以安全公开部署。当前项目尚未加入用户鉴权、HTTPS、限流、正式数据库迁移、生产日志与备份策略。

## 12. 当前 LLM 接入与未来搜索、RAG

### 12.1 两种已支持的 LLM 连接方式

**远程模型 API：**模型运行在提供商服务器上，本机不需要启动 LLM 服务。后端通过 HTTPS 调用模型；通常需要模型名、Base URL 和 API Key。

**本地兼容服务：**模型运行在本机独立进程中，并向 ResearchFlow 提供 OpenAI-compatible HTTP API。本项目不自动安装或启动模型运行器；内存、显存、磁盘和启动命令取决于你选择的运行器。若服务不要求鉴权，可将 API Key 留空。

两种方式都经过 `OpenAICompatibleLLMClient`，工作流不直接依赖某一家 SDK。当前要求服务支持 Chat Completions 和 JSON Schema 结构化输出。

### 12.2 未来推荐启动顺序

当相关组件真正实现后，推荐顺序为：

1. PostgreSQL / 向量数据库（如果启用）；
2. Redis / 后台任务执行器（如果启用）；
3. 本地 LLM 服务（仅本地模型方案需要）；
4. 搜索或文档解析服务（如果是本地服务）；
5. ResearchFlow 后端；
6. 后端健康检查和依赖检查；
7. ResearchFlow 前端。

停止时采用大致相反的顺序：先停止前端和后端，再停止后台任务与基础设施。不要在仍有任务写入时直接停止数据库。

### 12.3 未来健康检查应覆盖

- API 进程是否存活；
- 数据库是否可读写；
- LLM Provider 是否可连接、模型是否存在；
- 搜索 Provider 是否可用；
- 向量库是否可查询；
- 后台任务执行器是否在线。

当前 `/health` 表示 FastAPI 进程能够响应，并返回所选工作流模式；它不会主动请求 LLM，也不代表外部依赖健康。

### 12.4 未来配置原则

- 密钥只进入本地环境变量或部署平台的 Secret 管理，不写入代码；
- `.env.example` 只保留变量名和无敏感信息的示例；
- 启动时校验必要配置，缺失时给出明确错误；
- 日志不能打印完整 Key、用户隐私、受版权保护的全文或模型的敏感上下文；
- 本地低资源模式应允许只启动必要服务，并优先使用远程模型 API。

## 13. 演示前检查清单

1. `git status` 确认没有意外文件；
2. 运行后端测试、Ruff、前端 ESLint 和生产构建；
3. 备份需要保留的本地数据库；
4. 确认 `.env` 使用预期演示模式，启动后端并检查 `/health`；
5. 启动前端并刷新 Dashboard；
6. 创建一次演示任务并确认 SSE 进度、报告和历史记录；
7. 确认屏幕和日志中没有 API Key、个人路径或敏感数据；
8. 演示结束后按 `Ctrl + C` 停止两个服务。

## 14. 手册维护规则

以下变化发生时，应在同一个功能改动中同步更新本文：

- 新增或删除运行服务；
- 更改端口、启动命令或环境变量；
- 更换数据库、模型或搜索 Provider；
- 新增数据迁移、备份或恢复步骤；
- 新增部署方式；
- 常见故障出现新的稳定解决方法。

README 只保留最短的快速开始；完整的生命周期、维护和排错说明统一以本文为准。
