# ResearchFlow 仓库结构

> 状态：当前实现
>
> 更新日期：2026-08-28

本文说明每个目录的职责和主要依赖方向。完整运行链路见[系统架构与完整研究工作流](llm-integration.md)，使用与配置见[运行手册](../guides/development-and-operations.md)，业务实体见[核心数据模型](domain-model.md)。

## 1. 顶层目录

```text
ResearchFlow/
├── .github/workflows/       GitHub Actions 自动化检查
├── apps/
│   ├── api/                 FastAPI 后端
│   └── web/                 Next.js 前端
├── docs/                    当前产品、架构、指南、课程和评测
├── examples/                可公开使用的演示输入、结果和知识资料
├── scripts/                 备份、E2E 与真实服务评测脚本
├── var/                     本地数据库和上传文件，不提交
├── .env.example             无密钥的核心配置示例
├── compose.yaml             可选容器拓扑
├── CONTEXT.md               前后端共享的领域词汇
├── pyproject.toml           Python workspace 与版本范围
├── uv.lock                  Python 依赖锁文件
└── README.md                产品介绍和最短启动路径
```

前后端保留独立构建边界；根目录只放整个 workspace 共用的配置和入口。

## 2. 前端 `apps/web`

```text
apps/web/
├── e2e/
│   └── research-flow.spec.ts       浏览器黄金流程
├── src/
│   ├── app/
│   │   ├── page.tsx                Dashboard 与知识文档管理
│   │   ├── demo-access-gate.tsx    可选访问码入口
│   │   ├── research/[runId]/
│   │   │   ├── page.tsx            Research Workspace 与 SSE
│   │   │   └── research-*.tsx      计划、材料、报告、度量和错误组件
│   │   ├── globals.css             全局样式
│   │   └── layout.tsx              页面根布局
│   └── lib/
│       ├── api.ts                  REST 类型与统一客户端
│       ├── event-stream.ts         SSE 事件合并和终态判断
│       └── format.ts               时间与数字格式化
├── Dockerfile                      可选生产镜像
├── package.json                    前端依赖与命令
└── playwright.config.ts            E2E 配置
```

页面组件不直接接触 SQLite、供应商密钥或 LangGraph State。所有后端访问集中在 `lib/api.ts`，研究页只消费 ResearchFlow 的 API 与领域事件。

## 3. 后端 `apps/api`

```text
apps/api/
├── src/researchflow/
│   ├── api/             HTTP/SSE 路由、请求响应模型和错误契约
│   ├── application/     研究运行与知识库用例编排
│   ├── core/            配置、访问保护和结构化日志
│   ├── domain/          领域对象、来源分类和引用不变量
│   ├── ingestion/       PDF/文本解析、分块和本地向量检索
│   ├── integrations/
│   │   ├── embedding/   Gemini、OpenAI-compatible 与 Fake
│   │   ├── llm/         OpenAI-compatible LLM 与 Fake
│   │   └── web/         Exa、结果读取与 Fake
│   ├── persistence/     SQLAlchemy 表、schema 版本和两个仓储
│   ├── workflows/       模拟与真实联合研究
│   ├── app_factory.py   依赖装配和 FastAPI 生命周期
│   └── main.py          服务器入口
├── tests/               后端单元与集成测试
├── Dockerfile           可选生产镜像
└── pyproject.toml       后端依赖与工具配置
```

依赖方向是 `api → application → domain`。外部 HTTP 与数据库细节分别留在 `integrations` 和 `persistence`；`app_factory.py` 负责选择真实或 Fake 实现并注入应用层。

### 研究工作流边界

```text
FastAPI Route
  → ResearchRunApplication
    → ResearchWorkflow
      ├─ SimulatedResearchWorkflow
      └─ LangGraphResearchWorkflow
           ├─ LLMClient
           ├─ SearchProvider
           ├─ WebPageReader
           └─ KnowledgeRetriever
                └─ EmbeddingClient
```

LangGraph 只存在于 `workflows/langgraph_research.py`。它的 Graph、Node 和 State 不进入 FastAPI、领域模型、数据库接口或前端契约；SQLite 中的 Research Run 才是产品状态的权威来源。这样可以保留图编排能力，同时让模拟模式、测试替身和未来替换框架不影响其余模块。

## 4. 文档 `docs`

```text
docs/
├── architecture/        当前实现的结构、数据模型、工作流和 SSE 契约
├── evaluation/          可由仓库脚本复现的搜索与检索结果
├── guides/              安装、使用、测试、运维和可选在线部署
├── learning/
│   ├── assets/          课程共享样式
│   ├── lessons/         按顺序阅读的项目课程网页
│   ├── reference/       全栈地图与通信速查页
│   ├── index.html       网页课程入口、分组与推荐路线
│   ├── README.md        从仓库进入网页课程的简短说明
│   ├── resources.html   课程使用的规范、官方文档和论文
│   └── RESOURCES.md     从仓库进入网页资料页的简短说明
├── product/             当前产品定位与作品集展示材料
└── README.md            文档总索引
```

- `architecture/` 回答“代码现在怎样组织、契约是什么”；
- `guides/` 回答“用户或开发者怎样运行和维护”；
- `learning/` 回答“这些技术为什么这样工作”；
- `evaluation/` 保存仍可重复执行的质量证据，不保存一次性选型过程；
- `product/` 只保留当前定位、范围和展示方式。

阶段路线图、ADR、开发复盘和一次性 Provider 比较已经在项目完成后移除；仍有效的结论直接写入对应的当前文档。

## 5. 示例与脚本

```text
examples/
├── ai-code-generation-evaluation.md          黄金研究输入
├── ai-code-generation-evaluation-result.md   可公开示例报告
└── knowledge-base/                            本地检索评测资料

scripts/
├── backup_data.ps1              备份 SQLite 与 uploads
├── restore_data.ps1             恢复到空数据目录
├── run_e2e.ps1                  启动隔离服务并运行浏览器测试
├── evaluate_exa_coverage.py     真实网页搜索覆盖度评测
└── evaluate_local_retrieval.py  真实 Embedding 检索评测
```

评测脚本会读取本地 `.env` 并调用真实服务；常规自动化测试只使用 Fake 或 HTTP Mock。

## 6. 运行数据与提交边界

```text
var/
├── researchflow.db
└── uploads/
```

数据库与上传目录是同一个数据集，备份和恢复时必须一起处理。`.env`、`var/`、备份、虚拟环境、`node_modules` 和构建产物不提交；锁文件、`.env.example`、公开样例、测试和 CI 配置应提交。

项目暂不引入额外 monorepo 工具、微服务、Redis、消息队列、Kubernetes、独立向量数据库，也不按 LangGraph 节点或数据库表机械拆分文件。这些边界让个人作品集保持可读，同时保留更换外部 Provider 和工作流实现的接口。
