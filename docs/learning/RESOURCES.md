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
- [react-markdown — remarkjs](https://github.com/remarkjs/react-markdown)
  ResearchFlow 把 Markdown 语法树转换成 React 元素所使用的渲染组件。
- [remark-math 与 rehype-katex — remarkjs](https://github.com/remarkjs/remark-math)
  用于理解 Markdown 数学语法如何经过语法树转换并交给 KaTeX 渲染。
- [KaTeX Browser API](https://katex.org/docs/browser)
  KaTeX 的浏览器端渲染与样式说明。
- [GitHub Actions documentation](https://docs.github.com/actions)
  GitHub 官方的工作流、Runner、事件触发、Secret 和部署自动化文档。
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
- [Retrieval-Augmented Generation — NeurIPS 2020](https://papers.nips.cc/paper/2020/hash/6b493230205f780e1bc26945df7481e5-Abstract.html)
  RAG 原始论文。用于区分参数化记忆、外部非参数记忆、检索器和生成器。
- [Gemini Embeddings — Google AI for Developers](https://ai.google.dev/gemini-api/docs/embeddings)
  Gemini Embedding 的当前官方指南。用于确认模型版本、检索任务指令和输出维度。
- [Gemini EmbedContent API — Google AI for Developers](https://ai.google.dev/api/embeddings)
  Gemini Embedding 的请求、批处理与响应字段参考。
- [Introduction to Information Retrieval — Stanford](https://nlp.stanford.edu/IR-book/)
  信息检索教材。用于理解余弦相似度、相关性判断和常见检索指标。
- [Evaluation in information retrieval — Stanford](https://nlp.stanford.edu/IR-book/html/htmledition/evaluation-in-information-retrieval-1.html)
  用于理解查询集、相关性标注和 MRR 等检索评测边界。
- [Text REtrieval Conference — NIST](https://trec.nist.gov/)
  TREC 官方入口。用于理解查询集、语料、qrels 和可复现检索评测。

## Wisdom (Communities)

- [FastAPI Discussions](https://github.com/fastapi/fastapi/discussions)
  遇到框架边界问题时，查看真实项目中的 FastAPI 设计与排错讨论。
- [Next.js Discussions](https://github.com/vercel/next.js/discussions)
  遇到版本相关问题时，查看使用者和维护者对 Next.js 行为的讨论。

后台任务可靠性和部署课程以当前代码、运行手册与自动化测试为准；平台价格和限制可能变化，实际部署前应重新核对官方信息。
