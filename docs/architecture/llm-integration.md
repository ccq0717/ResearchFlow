# LLM 与联合研究工作流接入架构

> 状态：当前实现
> 更新日期：2026-08-26

## 1. 三种工作流模式

| 模式 | 外部调用 | 用途 |
| --- | --- | --- |
| `simulation` | 无 | 默认离线演示 |
| `llm` | LLM | 只真实生成研究计划 |
| `langgraph` | LLM + Exa Search + Gemini Embedding + 所选本地文档 | 网页与本地资料联合研究闭环 |

`langgraph` 模式依次执行 planning、searching、reading、extracting、writing、checking。LangGraph 只存在于 `workflows/langgraph_research.py` 内部。

## 2. 深接口

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

## 3. 结构化输出

远程适配器使用 Chat Completions 的 JSON Schema 输出。Pydantic 严格校验计划、证据、Claim 文本和报告；未知字段和缺失字段会失败。适配器与工作流会过滤不存在的 `source_id`、不存在的 `question_id`，以及不能在对应正文中找到的原文片段，避免模型凭空创建关联或伪造引文。

模型生成的 `search_query` 使用英文，是通用 Web 检索的执行输入；界面仍展示原始研究问题。查询通过自然语言表达研究主题和来源偏好，不把论文、博客或文档限制成供应商类别。

## 4. 数据流

1. 模型生成 `ResearchPlan`；
2. Search Provider 为每个问题产生网页结果；Knowledge Retriever 只在用户所选文档范围内检索；
3. Exa 返回的网页 highlights 经 Page Reader 做长度限制；本地命中保留文件名与页码或行号。两者统一转换成运行内 Source，并分别按 URL 或片段标识去重；
4. 模型提取 Evidence 和它直接支持的 Claim，工作流持久化显式关系；
5. 模型写报告，工作流确定性追加“可追溯主张与证据”章节；
6. 确定性检查确认结构化 Claim—Evidence—Source 关联、原文可定位性、主张覆盖率和相邻来源链接；
7. Application 保存每次更新并通过领域事件通知前端。

## 5. 错误与重试

LLM 保持 `LLM_TIMEOUT`、`LLM_CONNECTION_ERROR`、`LLM_HTTP_ERROR`、`LLM_INVALID_RESPONSE` 等安全错误。网页层使用 `SEARCH_*`、`WEB_*` 错误；Exa 适配器只对超时、连接错误、429 和 5xx 做有限重试，不无限阻塞，并单独映射鉴权失败与额度限制。原始响应正文和密钥不会进入用户事件。

## 6. 当前边界

- 当前网页 Provider 覆盖通用公开 Web，但结果质量和数量受 Exa 免费额度影响；
- 本地文档片段和查询默认使用同一个 Gemini Embedding 2 模型，分别标记为文档与查询用途；也保留 OpenAI-compatible 适配器。向量保存在 SQLite 并用余弦相似度排序，不要求本地 GPU 或独立向量数据库；
- 更换 Embedding 模型、维度或检索指令策略后必须重新处理已有文档，系统不会混算不兼容的向量；
- PDF 只提取已有文本层，不执行 OCR；扫描件会进入明确的失败状态；
- 已保存 Exa 可用的作者与发布时间并分类来源，但没有 DOI、卷期、被引量等专业学术元数据；
- LangGraph 尚未配置持久 checkpoint；进程中断遗留的运行会标记为 `RUN_INTERRUPTED`，用户可在界面创建一次保留原记录的新运行；
- Citation Coverage 只衡量结构化 Claim，不自动证明报告正文的每句话都获得语义充分的支持；
- 自动化测试使用 Fake/Mock，真实网络兼容性由单独冒烟测试验证。
