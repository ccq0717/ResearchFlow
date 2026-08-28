# ResearchFlow 文档索引

文档按用途组织。第一次接触项目不需要从头阅读全部文件。

## 使用与部署

- [使用、开发与运维手册](guides/development-and-operations.md)：安装、启动、配置、数据、测试和排错；
- [可选在线 Demo 部署指南](guides/online-demo-deployment.md)：需要公开链接时的 Railway 配置与验收清单。

## 产品与架构

- [产品定位与设计取舍](product/project-discussion.md)：稳定的产品范围与非目标；
- [作品集展示材料](product/portfolio-presentation.md)：演示顺序、简历描述和技术取舍；
- [领域词汇表](../CONTEXT.md)：核心术语；
- [核心数据模型](architecture/domain-model.md)：实体、关系和数据库表；
- [系统架构与完整研究工作流](architecture/llm-integration.md)：从浏览器创建任务到持久化报告的端到端主入口；
- [SSE 事件契约](architecture/sse-events.md)：实时事件格式；
- [仓库结构](architecture/repository-structure.md)：目录职责、代码模块与 seam。

## 评测

- [网页搜索覆盖度评测](evaluation/web-search.md)；
- [本地 Embedding 检索评测](evaluation/local-retrieval.md)。

这两项评测对应仓库中的可执行脚本，不是运行产品的必读前置。

## 学习

- [学习课程入口](learning/README.md)：面向从零理解前后端与 AI 工程的读者；
- [学习资料](learning/RESOURCES.md)：课程使用的规范、官方文档和论文。

本目录只保留当前产品说明、架构、使用指南、学习课程和可复现评测，不保存阶段计划或开发复盘。
