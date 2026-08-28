# ResearchFlow 系统架构与完整研究工作流

> 状态：当前实现
> 更新日期：2026-08-28

本文是项目架构和端到端工作流程的主入口。目录职责见[仓库结构](repository-structure.md)，实体关系见[核心数据模型](domain-model.md)，实时协议见[SSE 事件契约](sse-events.md)。

## 1. 系统架构

```text
Next.js Dashboard / Research Workspace
  ├─ REST：创建、读取和管理任务与知识文档
  └─ SSE：接收研究进度事件
        ↓
FastAPI Route
  → ResearchRunApplication / KnowledgeLibrary
    ├─ ResearchWorkflow → LLM、Exa、网页读取、Embedding 检索
    └─ Repository → SQLite + uploads
```

浏览器不接触供应商密钥、SQLite 或 LangGraph State。Application 负责用例、事务和后台运行；工作流负责研究步骤；领域对象保持供应商无关；Repository 和 integrations 分别隔离持久化与外部 HTTP。

## 2. 两种工作流模式

| 模式 | 外部调用 | 用途 |
| --- | --- | --- |
| `simulation` | 无 | 默认离线演示 |
| `research` | LLM + Exa Search；选择本地文档时还会使用 Embedding | 网页与本地资料联合研究闭环 |

`research` 模式内部依次执行 planning、searching、reading、extracting、writing、checking。LangGraph 只存在于 `workflows/langgraph_research.py` 的实现中，不暴露为用户配置名称。

## 3. 深接口

```text
ResearchRunApplication
  └─ ResearchWorkflow
       └─ LangGraphResearchWorkflow
            ├─ LLMClient
            ├─ SearchProvider
            ├─ WebPageReader
            └─ KnowledgeRetriever
                 └─ EmbeddingClient
```

`LLMClient` 提供三个领域操作：

- `create_research_plan`：生成问题、原因、英文检索词和交付物；
- `extract_evidence`：只从传入的网页或本地片段正文提取证据及其直接支持的 Claim；
- `write_research_report`：只用传入证据和来源撰写 Markdown 报告。

调用方不处理提示词、HTTP、鉴权、JSON Schema 或供应商响应。Fake 和真实适配器返回相同 DTO。

## 4. 结构化输出

远程适配器使用 Chat Completions 的 JSON Schema 输出。Pydantic 严格校验计划、证据、Claim 文本和报告；计划必须包含 3～8 个研究问题和 1～8 项预期交付物，未知字段和缺失字段会失败。适配器与工作流会过滤不存在的 `source_id`、不存在的 `question_id`，以及不能在对应正文中找到的原文片段，避免模型凭空创建关联或伪造引文。

模型生成的 `search_query` 使用英文，是通用 Web 检索的执行输入；界面仍展示原始研究问题。查询通过自然语言表达研究主题和来源偏好，不把论文、博客或文档限制成供应商类别。

## 5. 端到端数据流

1. Dashboard 读取历史与知识库；用户可上传资料，并选择本次研究使用的文档。
2. 前端通过 REST 创建 Research Run。Application 保存目标和文档选择，启动后台工作流；Research Workspace 通过 SSE 订阅进度。
3. 模型生成包含研究问题、英文检索词和交付物的 `ResearchPlan`。
4. 每个问题同时使用 Exa 检索公开网页，并在所选文档中执行 Embedding 相似度检索。网页 highlights 与本地片段统一转换为 Source、限制长度并去重。
5. 模型只从 Source 正文提取 Evidence 及其直接支持的 Claim；工作流过滤无效 ID 和无法定位的原文。
6. 模型根据证据撰写 Markdown 报告，工作流确定性追加可追溯章节，并检查 Claim—Evidence—Source 链路、引用覆盖率与来源定位。
7. Application 逐步把计划、材料、事件和终态写入 SQLite。前端收到 SSE 后重新读取相应 REST 资源，完成时渲染报告和运行度量。
8. 页面刷新后以 SQLite 为权威状态恢复；取消进入终态，失败可创建一次保留原记录的新运行。进程中断的运行会明确标记失败，不伪装成节点级续跑。

## 6. 错误与重试

LLM 保持 `LLM_TIMEOUT`、`LLM_CONNECTION_ERROR`、`LLM_HTTP_ERROR`、`LLM_INVALID_RESPONSE` 等安全错误。网页层使用 `SEARCH_*`、`WEB_*` 错误；Exa 适配器只对超时、连接错误、429 和 5xx 做有限重试，不无限阻塞，并单独映射鉴权失败与额度限制。原始响应正文和密钥不会进入用户事件。

## 7. 当前边界

- 当前网页 Provider 覆盖通用公开 Web，但结果质量和数量受 Exa 免费额度影响；
- 本地文档片段和查询默认使用同一个 Gemini Embedding 2 模型，分别标记为文档与查询用途；也保留 OpenAI-compatible 适配器。向量保存在 SQLite 并用余弦相似度排序，不要求本地 GPU 或独立向量数据库；
- 更换 Embedding 模型、维度或检索指令策略后必须重新处理已有文档，系统不会混算不兼容的向量；
- PDF 只提取已有文本层，不执行 OCR；扫描件会进入明确的失败状态；
- 已保存 Exa 可用的作者与发布时间并分类来源，但没有 DOI、卷期、被引量等专业学术元数据；
- LangGraph 尚未配置持久 checkpoint；进程中断遗留的运行会标记为 `RUN_INTERRUPTED`，用户可在界面创建一次保留原记录的新运行；
- Citation Coverage 只衡量结构化 Claim，不自动证明报告正文的每句话都获得语义充分的支持；
- 自动化测试使用 Fake/Mock，真实网络兼容性由单独冒烟测试验证。
