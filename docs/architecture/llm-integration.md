# LLM 与 M2 研究工作流接入架构

> 状态：M2 实现基线
> 更新日期：2026-08-25

## 1. 三种工作流模式

| 模式 | 外部调用 | 用途 |
| --- | --- | --- |
| `simulation` | 无 | 默认离线演示 |
| `llm` | LLM | 兼容 M1，只真实生成研究计划 |
| `langgraph` | LLM + Exa Search | 通用网页研究闭环 |

`langgraph` 模式依次执行 planning、searching、reading、extracting、writing、checking。LangGraph 只存在于 `workflows/langgraph_research.py` 内部。

## 2. 深接口

```text
ResearchRunApplication
  └─ ResearchWorkflow
       └─ LangGraphResearchWorkflow
            ├─ LLMClient
            ├─ SearchProvider
            └─ WebPageReader
```

`LLMClient` 提供三个领域操作：

- `create_research_plan`：生成问题、原因、英文检索词和交付物；
- `extract_evidence`：只从传入网页正文提取证据；
- `write_research_report`：只用传入证据和来源撰写 Markdown 报告。

调用方不处理提示词、HTTP、鉴权、JSON Schema 或供应商响应。Fake 和真实适配器返回相同 DTO。

## 3. 结构化输出

远程适配器使用 Chat Completions 的 JSON Schema 输出。Pydantic 严格校验计划、证据和报告；未知字段、缺失字段和非法关联都会失败。证据阶段还会过滤不存在的 `source_id` 与 `question_id`，避免模型凭空创建来源。

模型生成的 `search_query` 使用英文，是通用 Web 检索的执行输入；界面仍展示原始研究问题。查询通过自然语言表达研究主题和来源偏好，不把论文、博客或文档限制成供应商类别。

## 4. 数据流

1. 模型生成 `ResearchPlan`；
2. Search Provider 为每个问题产生结果；
3. Exa 随搜索结果返回 highlights，Page Reader 将其转换为受长度限制的供应商无关文档，并按 URL 去重；
4. 模型提取 Evidence；
5. 模型写报告；
6. 确定性检查确认 Evidence—Source 关联和报告来源链接；
7. Application 保存每次更新并通过领域事件通知前端。

## 5. 错误与重试

LLM 保持 `LLM_TIMEOUT`、`LLM_CONNECTION_ERROR`、`LLM_HTTP_ERROR`、`LLM_INVALID_RESPONSE` 等安全错误。网页层使用 `SEARCH_*`、`WEB_*` 错误；Exa 适配器只对超时、连接错误、429 和 5xx 做有限重试，不无限阻塞，并单独映射鉴权失败与额度限制。原始响应正文和密钥不会进入用户事件。

## 6. 当前边界

- 当前网页 Provider 覆盖通用公开 Web，但结果质量和数量受 Exa 免费额度影响；
- 没有专业学术元数据归一化和 Claim 级引用验证；
- LangGraph 尚未配置持久 checkpoint；进程中断的运行会被标记为 `RUN_INTERRUPTED`；
- 自动化测试使用 Fake/Mock，真实网络兼容性由单独冒烟测试验证。
