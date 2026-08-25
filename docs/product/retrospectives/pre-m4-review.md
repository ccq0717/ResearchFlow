# 进入 M4 前审查：M0～M3 基线

> 日期：2026-08-26
> 结论：修复数据完整性问题并补清 M4 边界后，可以进入 M4

## 实现质量

审查发现 Evidence 的防御性校验只在真实 LLM adapter 中过滤问题关联，工作流本身没有维护 `question_id` 与原文片段约束；替换 LLMClient 后可能保存悬空问题或伪造引文。现已在工作流边界统一验证 `source_id`、`question_id`，并对归一化后的 excerpt 与来源正文做包含检查。

Citation Coverage 原先只检查 Evidence ID，未确认 Evidence 指向的 Source 仍存在。计算逻辑现已移入领域模块，并验证完整 Claim—Evidence—Source 链路，为 M4 的本地文档删除语义建立一致基础。

三个工作流重复构造 `run.started`，两个真实工作流重复构造失败终态。公共构造逻辑已收敛到工作流接口模块；模式特有的阶段事件和报告仍由各实现负责，不建立强制继承层级。

SQLite Repository 已经同时承担九张表的持久化和映射，继续直接加入文档、分块和索引会使模块过深。M4 实现存储模型时应保留单一公开 adapter，同时把数据库 rows、映射和知识文档操作拆成内部模块。

## 实现—文档一致性

- 修正 SSE 教学页把业务类型误当成线路事件名的问题；
- 明确 `stage.started/completed` 是 simulation/llm 兼容事件，LangGraph 使用 `research.*.completed`；
- 明确 Citation Coverage 衡量结构化 Claim 的引用链路，不声称自动验证报告每句话的语义真实性；
- 将 M3 的语义支持验收改为“结构自动检查 + 黄金样例人工抽查”，与阶段复盘中的已知限制保持一致；
- Source 的定义调整为已读取并保留用于溯源的材料，不再错误声称每个已读取来源都一定形成 Evidence。

## M4 设计调整

M4 不应让 Evidence 直接维护“网页 source_id 或本地 chunk_id”的两套互斥关联。`KnowledgeDocument` 和 `DocumentChunk` 负责可复用文件及其定位信息；一次研究命中的本地片段先转换成运行内 Source，再复用现有 Evidence、Claim 和 Citation Coverage。

上传边界必须从第一步包含类型、体积、数量、路径和安全文件名限制。检索实现不预设必须使用独立向量数据库；先以固定小样比较全文、向量或混合检索，再选择在 Windows 和在线 Demo 预算内效果足够的方案。

M4 按五个内部步骤推进，不新增 M4.5：领域与存储、上传解析、检索评测、联合工作流与引用、删除清理与验收。
