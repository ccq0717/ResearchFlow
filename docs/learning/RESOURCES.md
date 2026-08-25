# ResearchFlow 全栈学习资料

## Knowledge

- [HTML Living Standard：Server-sent events — WHATWG](https://html.spec.whatwg.org/dev/server-sent-events.html)
  SSE 的规范来源。用于确认 EventSource、text/event-stream、事件格式和 Last-Event-ID 的标准行为。
- [Using server-sent events — MDN](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events)
  面向 Web 开发者的 SSE 实用指南。用于浏览器端连接、监听、关闭、重连和消息格式示例。
- [Server-Sent Events — FastAPI](https://fastapi.tiangolo.com/reference/sse/)
  FastAPI 的 SSE 官方参考。用于理解 Python 后端如何持续 yield 事件并返回 text/event-stream。
- [HTTP Overview — MDN](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Overview)
  HTTP 请求、响应和基于 HTTP 的 API 概览。
- [React Learn — React](https://react.dev/learn)
  React 官方入门课程。用于组件、状态、事件处理和副作用等前端基础。
- [FastAPI Tutorial](https://fastapi.tiangolo.com/tutorial/)
  FastAPI 官方教程。用于路由、请求模型、依赖注入、错误处理和异步接口。
- [SQLite Is Serverless — SQLite](https://www.sqlite.org/serverless.html)
  SQLite 官方对无独立服务器进程和零配置模式的解释。用于区分嵌入式数据库与数据库服务器。
- [sqlite3 — Python 3.12](https://docs.python.org/3.12/library/sqlite3.html)
  Python 标准库的 SQLite 接口文档。用于理解 Python 如何直接打开和查询本地数据库文件。
- [Asynchronous I/O — SQLAlchemy 2.0](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
  SQLAlchemy 官方异步 Engine、Connection 和 Session 文档。用于理解项目的数据访问基础。
- [aiosqlite — OmniLib](https://github.com/omnilib/aiosqlite)
  aiosqlite 官方项目说明。用于理解它如何把标准 sqlite3 操作桥接到 asyncio，而不是提供独立数据库服务。

## Wisdom (Communities)

- [FastAPI Discussions](https://github.com/fastapi/fastapi/discussions)
  遇到框架边界问题时，查看真实项目中的 FastAPI 设计与排错讨论。
- [Next.js Discussions](https://github.com/vercel/next.js/discussions)
  遇到版本相关问题时，查看使用者和维护者对 Next.js 行为的讨论。

## Gaps

- LangGraph 的基础资料已随现有课程补充；后续讲解 RAG 和 Agent 评估前，还需要加入对应的官方文档与高质量论文。
- 学习者暂未选择是否参与开发者社区，当前以阅读高质量讨论为主。
