# ResearchFlow 文档索引

文档按用途组织。第一次接触项目不需要从头阅读全部文件。

## 使用与部署

- [使用、开发与运维手册](guides/development-and-operations.md)：安装、启动、配置、数据、测试和排错；
- [可选在线 Demo 部署指南](guides/online-demo-deployment.md)：需要公开链接时的 Railway 配置与验收清单。

## 产品与架构

- [产品定位与设计取舍](product/project-discussion.md)：稳定的产品范围与非目标；
- [项目路线图](product/roadmap.md)：实施阶段、状态和后续计划；
- [作品集展示材料](product/portfolio-presentation.md)：演示顺序、简历描述和技术取舍；
- [领域词汇表](../CONTEXT.md)：核心术语；
- [核心数据模型](architecture/domain-model.md)：实体、关系和数据库表；
- [LLM 与联合研究工作流](architecture/llm-integration.md)：工作流、外部接口和数据流；
- [SSE 事件契约](architecture/sse-events.md)：实时事件格式；
- [仓库结构](architecture/repository-structure.md)：代码模块与 seam；
- [LangGraph 架构决策](decisions/0001-use-langgraph-behind-workflow-interface.md)：为何以及如何隔离 LangGraph。

## 调研与评测

- [通用网页搜索 Provider 比较](research/general-web-search-provider-comparison.md)；
- [Exa 来源覆盖度评测](research/exa-m3-source-coverage.md)；
- [本地检索方案评测](research/m4-local-retrieval-evaluation.md)；
- [在线 Demo 部署平台比较](research/deployment-platform-comparison.md)；
- [Hello-Agents 参考分析](research/hello-agents-analysis.md)。

这些文件保留选型依据和可复现结果，不是运行产品的必读前置。

## 学习与实施历史

- [学习课程入口](learning/README.md)：面向从零理解前后端与 AI 工程的读者；
- [进入 M5 前审查](product/retrospectives/pre-m5-review.md)：当前实现、文档、设计与简洁性门禁；
- [M5 阶段复盘](product/retrospectives/m5-deployment-readiness.md)：可靠性、测试、部署准备与作品集交付结论；
- `product/retrospectives/`：阶段复盘与历史问题；
- [早期 MVP 技术规格](product/mvp-spec.md)：最初纵向闭环的验收基线。

学习材料和复盘允许保留历史上下文；面向当前用户的行为以 README、运行手册和当前架构文档为准。
