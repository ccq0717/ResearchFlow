# ResearchFlow Domain

ResearchFlow 把开放式研究目标转化为可追踪的研究过程和有证据支持的报告。本词汇表规定产品与代码共享的核心语言。

## Language

**Research Goal（研究目标）**:
用户希望系统调查、回答或产出方案的原始意图。
_Avoid_: Prompt、问题描述

**Research Run（研究运行）**:
从一个研究目标开始，到完成、失败或取消为止的一次独立执行。
_Avoid_: Session、Job、对话

**Research Outcome（研究结果）**:
Research Run 到达终态时形成的不可再变化结果，成功时包含报告，失败时包含可安全展示的原因。
_Avoid_: Terminal Status、最终事件

**Research Plan（研究计划）**:
研究运行在检索前形成的结构化中间产物，包含计划摘要、研究问题和预期交付物。
_Avoid_: Agent 思维过程、Prompt

**Research Question（研究问题）**:
研究计划中可通过检索和证据验证的具体问题。
_Avoid_: Task、搜索词

**Research Task（研究任务）**:
为回答一个 Research Question 而执行的具体检索活动，记录查询内容和完成状态。
_Avoid_: Research Run、搜索结果

**Knowledge Document（知识文档）**:
用户上传并可跨 Research Run 复用的原始 PDF、Markdown 或纯文本资料，具有独立的处理状态和安全存储名。
_Avoid_: Source、附件

**Document Chunk（文档片段）**:
Knowledge Document 解析后形成的可检索文本单元，保留页码或行号等原文定位信息。
_Avoid_: Evidence、模型摘要

**Chunk Embedding（片段向量）**:
Embedding 模型为 Document Chunk 生成的语义向量，必须记录模型与维度，并且只能与同一配置生成的查询向量比较。
_Avoid_: Document Chunk、Evidence、模型结论

**Source（研究来源）**:
某次研究过程中实际读取并保留用于溯源的资料，可以来自公开网页，也可以是所选 Knowledge Document 的命中片段；它可以形成 Evidence，也可以作为已检查但未采用的材料保留。
_Avoid_: 搜索结果、链接

**Evidence（研究证据）**:
从 Source 中提取、能够支持一个 Research Question 的原文片段及其研究解释。
_Avoid_: 摘要、模型结论

**Claim（研究主张）**:
报告中需要证据支持、可以独立检查的关键陈述；一条 Claim 可以由一条或多条 Evidence 支持。
_Avoid_: Evidence、摘要、整份报告的结论

**Citation Coverage（引用覆盖）**:
一组 Claim 中已经关联有效 Evidence 的比例，用于识别缺少依据的关键陈述。
_Avoid_: 来源数量、链接数量

**Research Event（研究事件）**:
描述研究运行中已发生状态变化的不可变记录。
_Avoid_: Log、消息

**Research Report（研究报告）**:
研究运行交付给用户的最终结构化成果。
_Avoid_: 回复、Completion
