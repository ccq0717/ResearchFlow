# ResearchFlow 仓库结构设计

> 状态：M2 实现基线
> 更新日期：2026-08-25

## 1. 设计目标

当前工作空间 `E:\VScodeProjects\ResearchFlow` 将直接作为 GitHub 仓库根目录，不在其中再嵌套一层同名项目目录。

目录结构需要同时满足：

- 前后端职责清楚；
- 适合个人学习和面试讲解；
- 不引入不必要的 monorepo 工具；
- 能在 Windows 上分别或统一启动；
- 文档、测试、部署配置和源码都有稳定位置；
- 密钥、本地数据库、上传文件和生成报告不会进入 Git。

## 2. 推荐目录结构

```text
ResearchFlow/
├── .github/
│   └── workflows/                 # CI：检查、测试与构建
├── apps/
│   ├── web/                       # Next.js 前端应用
│   │   ├── public/
│   │   ├── src/
│   │   │   ├── app/              # 路由和页面
│   │   │   ├── components/       # 通用 UI
│   │   │   ├── features/         # 按业务功能组织的前端模块
│   │   │   ├── lib/              # HTTP、SSE、配置等基础代码
│   │   │   └── types/            # 前端共享类型
│   │   ├── tests/
│   │   ├── package.json
│   │   └── tsconfig.json
│   └── api/                       # FastAPI 后端应用
│       ├── src/
│       │   └── researchflow/
│       │       ├── api/           # HTTP/SSE 路由和请求模型
│       │       ├── domain/        # 研究任务、证据、来源等领域模型
│       │       ├── application/   # 用例编排，不依赖 Web 框架
│       │       ├── workflows/     # ResearchWorkflow 与 LangGraph 实现
│       │       ├── integrations/  # LLM 与 Web 外部适配器
│       │       ├── ingestion/     # 后续文件解析、切分与索引
│       │       ├── persistence/   # SQLAlchemy 仓储和数据库模型
│       │       └── core/          # 配置、日志和通用错误
│       ├── tests/
│       │   ├── unit/
│       │   └── integration/
│       └── pyproject.toml
├── docs/
│   ├── product/                   # 定位、范围、用户旅程和 MVP
│   ├── architecture/              # 架构、数据模型和接口设计
│   ├── decisions/                 # 重要架构决策记录（ADR）
│   └── research/                  # 对外部项目和技术的调研
├── examples/                      # 可公开的演示输入和样例资料
├── infra/
│   └── docker/                    # 可选的容器和部署配置
├── scripts/                       # Windows/跨平台开发辅助脚本
├── .editorconfig
├── .env.example                   # 可提交的配置模板，不含真实密钥
├── .gitignore
├── LICENSE
├── README.md
└── CONTRIBUTING.md                # 可在需要时添加
```

空目录不应只为追求结构完整而提前创建。实现某个模块时再创建相应目录和文件，让仓库结构反映真实代码。

## 3. 为什么不使用根目录 `src/`

本项目同时包含 TypeScript 前端和 Python 后端。若只建立一个根目录 `src/`，两套语言、构建工具和依赖会混在一起，降低可读性。

因此采用：

- `apps/web/src`：前端源码；
- `apps/api/src/researchflow`：后端 Python 包源码。

这种布局仍然遵循“源码放在 src 下”的习惯，同时明确两个可独立运行的应用。

## 4. LangGraph 的位置与接口

LangGraph 放在后端 `workflows/` 模块内部。FastAPI 路由不直接导入 Graph、Node 或 LangGraph State，也不把 LangGraph 的事件结构直接返回给前端。

```text
FastAPI Route
    ↓
Research Application Use Case
    ↓
ResearchWorkflow interface
    ↓
LangGraphResearchWorkflow implementation
    ├─ LLMClient
    ├─ SearchProvider
    └─ WebPageReader
```

`ResearchWorkflow` 是框架隔离的 seam。它对调用方暴露少量 ResearchFlow 自己的输入、事件和结果类型，并在内部处理：

- 节点顺序与条件分支；
- 搜索、阅读、证据提取、写作与检查节点；
- 外部请求的有限重试与超时；
- LangGraph 状态到领域事件的转换。

这一模块应保持较深：调用方只学习一个小接口，就能获得完整研究流程，而不需要理解 LangGraph 的实现细节。

## 5. 外部依赖的 seam

只有确实需要生产实现和测试替身的外部能力才建立接口，例如：

- `LLMClient`：OpenAI-compatible 适配器 / Fake；
- `SearchProvider`：Exa 通用 Web 适配器 / Fake；
- `WebPageReader`：Provider 内容读取 / Fake，未来可替换为独立网页读取器；
- `PaperProvider`：学术资料适配器 / 固定论文假实现；
- `KnowledgeRetriever`：本地向量检索 / 内存测试实现；
- `SqliteResearchRepository` 当前只有一个真实 adapter，因此暂不提取假想的 Repository Protocol；测试使用临时 SQLite。出现第二种存储后再建立 seam。

这些接口由工作流和应用用例接收，而不是在模块内部临时创建真实客户端。测试通过相同 seam 运行完整流程。

## 6. GitHub 仓库要求

正式初始化仓库时至少加入：

- `README.md`：项目价值、截图、架构、启动与演示；
- `LICENSE`：明确开源许可；
- `.gitignore`：忽略密钥、依赖、缓存、数据库和用户文件；
- `.env.example`：列出配置项，不保存真实 API Key；
- GitHub Actions：运行前端检查、后端检查和测试；
- `examples/`：提供不受版权限制的演示输入；
- 清晰、分阶段的提交记录。

本地运行数据建议统一放到被 Git 忽略的 `var/` 中，例如：

```text
var/
├── researchflow.db
├── uploads/
├── indexes/
└── reports/
```

`var/` 不作为源码结构的一部分提交，只在 README 中说明它会在运行时自动生成。

## 7. 暂不引入的复杂度

初始仓库不需要：

- Nx、Turborepo 等 monorepo 编排工具；
- 独立共享包目录；
- 微服务拆分；
- Redis、消息队列和 Kubernetes 配置；
- 为每个简单类建立独立接口；
- 按 LangGraph 节点机械地一文件一目录。

只有出现真实的第二个调用方、第二个实现或明确部署需求时，才增加新的 seam 和基础设施。
