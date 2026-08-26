# ResearchFlow 仓库结构

> 状态：当前实现
>
> 更新日期：2026-08-26

## 1. 顶层目录

```text
ResearchFlow/
├── .github/workflows/       CI
├── apps/web/                Next.js 前端
├── apps/api/                FastAPI 后端
├── docs/                    产品、架构、决策、调研与学习资料
├── examples/                可公开演示输入
├── scripts/                 评测与辅助脚本
├── var/                     本地数据库和上传文件，不提交
├── .env.example             无密钥配置示例
├── pyproject.toml           Python workspace
├── uv.lock                  Python 锁文件
└── README.md
```

前后端使用各自的 `src`，避免 TypeScript 和 Python 构建边界混在根目录。空目录和假想基础设施不提前创建。

## 2. 后端模块

```text
apps/api/src/researchflow/
├── api/             HTTP、SSE 路由和请求响应模型
├── application/     研究任务与知识库用例
├── core/            配置
├── domain/          领域对象和不变量
├── ingestion/       文件解析、分块与本地检索
├── integrations/    LLM、搜索、网页读取和 Embedding 适配器
├── persistence/     SQLAlchemy 表和仓储
└── workflows/       模拟、规划与 LangGraph 工作流
```

FastAPI 路由只负责协议转换。Application 编排用例，领域模块保存业务语义，外部协议和数据库细节分别留在 integrations 与 persistence。

## 3. 工作流 seam

```text
FastAPI Route
  → ResearchRunApplication
    → ResearchWorkflow
      → LangGraphResearchWorkflow
        ├─ LLMClient
        ├─ SearchProvider
        ├─ WebPageReader
        └─ KnowledgeRetriever
             └─ EmbeddingClient
```

LangGraph 的 Graph、Node 和 State 不进入 FastAPI、领域模型或前端事件。`ResearchWorkflow` 对调用方只暴露 ResearchFlow 自己的输入和更新类型。

真实外部能力都有测试替身：

- `LLMClient`：OpenAI-compatible / Fake；
- `SearchProvider`：Exa / Fake；
- `WebPageReader`：搜索结果正文读取器 / Fake；
- `EmbeddingClient`：Gemini、OpenAI-compatible / Fake；
- `KnowledgeRetriever`：封装查询向量、模型匹配和余弦排序。

额外学术搜索、OCR、独立向量数据库或新仓储只在出现实际需求和第二种实现时增加，不预设空接口。

## 4. 运行数据

```text
var/
├── researchflow.db
└── uploads/
```

数据库与上传目录必须一起备份。`.env`、`var/`、虚拟环境、前端依赖和构建产物不提交；锁文件、`.env.example`、公开样例和 CI 配置应提交。

## 5. 暂不引入

- Nx、Turborepo 等额外 monorepo 编排；
- 微服务、Redis、消息队列和 Kubernetes；
- 按 LangGraph 节点机械拆分文件；
- 为只有一个实现的简单类建立形式化接口。

这些选择让仓库保持适合个人作品集的规模，同时保留更换真实 Provider 和工作流实现所需的 seam。
