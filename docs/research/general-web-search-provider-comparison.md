# 通用网页搜索 Provider 比较

> 核对日期：2026-08-25
> 状态：已决定首版采用 Exa，并保留可替换 Provider 接口

## 1. 调研目标

ResearchFlow 面向科研与技术预研，需要检索论文页面、企业工程博客、官方文档、技术报告和社区材料。首个正式搜索 Provider 应满足：

- 搜索开放 Web，而不是限定在单一站点；
- 有持续免费额度，且无需为试用绑定付费方案；
- 能以服务端 API 方式集成到在线作品集 Demo；
- 免费额度耗尽时安全停止，不产生意外费用；
- 通过 ResearchFlow 自有接口接入，将来可以替换为更好的付费服务；
- 最好同时返回正文或相关片段，减少通用网页抓取的不稳定性。

## 2. 结论摘要

首版已决定采用 **Exa**，Tavily 保留为未来备选。选择依据是 Exa 的持续免费额度、通用 Web 覆盖以及随搜索返回网页/PDF highlights 的能力；接入后仍需用公开研究问题完成真实冒烟测试。

- Exa 更适合未来公开 Demo：免费 Starter 每月提供 10 美元 credits，无需支付方式；搜索覆盖通用 Web，并能在搜索响应中返回网页或 PDF 的清洗文本、重点片段、作者和发布日期等信息。
- Tavily 更适合快速原型：每月 1,000 credits，无需信用卡；Basic Search 每次 1 credit，也可以返回清洗正文。但官方说明 Production key 需要付费计划或启用 PAYGO，免费 Development key 是否适合长期公开 Demo 需要进一步确认。
- SearXNG 没有 API 费用，但自托管会增加部署、内存、维护和上游封禁成本；公共实例常关闭 JSON 输出，也可能因滥用被验证码或封禁，不适合作为作品集 Demo 的默认依赖。
- Brave Search API 的免费月度 credits 需要信用卡和署名，不符合“完全不绑定支付方式”的优先条件。
- Serper 的 2,500 次免费查询是注册试用额度而非每月持续额度；SerpApi 的持续免费层只有 250 次/月。二者可用于对照，不是首选。
- Google Custom Search JSON API 已关闭新客户并计划于 2027-01-01 停止；Bing Search APIs 已于 2025-08-11 退役。
- DuckDuckGo 没有面向开发者的官方通用 Web SERP API；Instant Answer 或抓取 Lite/HTML 页面不能当作稳定生产接口。

## 3. 候选比较

| 候选 | 通用 Web | 免费条件 | 正文能力 | 在线 Demo 适配 | 结论 |
| --- | --- | --- | --- | --- | --- |
| Exa | 是，另有可选内容类别 | 注册赠送 20 美元，此后每月 10 美元；无需支付方式 | 搜索可返回全文或 highlights，支持网页、PDF 和复杂布局 | 免费 Starter 未显示 Development/Production 分层；5 QPS | 第一候选 |
| Tavily | 是，`topic=general` | 每月 1,000 credits；无需信用卡 | Search 可返回相关内容或清洗正文 | 免费 key 为 Development；Production key 需要付费/PAYGO | 第二候选 |
| SearXNG | 是，聚合多个搜索引擎 | 软件免费；运行实例仍消耗服务器资源 | 主要返回结果链接；正文需另行读取 | 公共实例不稳定，自托管增加运维 | 本地备用，不作默认 |
| Brave Search API | 是，自有 Web 索引 | 每月 5 美元 credits，约 1,000 Search 请求；必须绑卡并署名 | 返回结果和 snippets；内容读取需另做 | API 稳定，但不满足无支付方式偏好 | 暂不选 |
| Serper | 是，Google SERP | 注册赠送 2,500 次；不是持续月度免费层 | 搜索正文需单独 Scrape API 和额外 credits | 可快速验证，但免费额度用完即结束 | 只作对照 |
| SerpApi | 是，可选 Google 等引擎 | 每月 250 次免费搜索 | 主要返回 SERP 结构 | 额度较少，付费起步较高 | 不优先 |
| Google Custom Search | 曾支持 | 只对既有客户保留 | 结果链接和 snippet | 新客户不可用，且即将停止 | 排除 |
| Bing Search APIs | 曾支持 | 已退役 | 不适用 | 已不可用 | 排除 |
| DuckDuckGo 非官方抓取 | 搜索页面本身是通用的 | 无 API Key | 依赖抓取 HTML | 没有官方完整 SERP API，易受页面变化和封禁影响 | 排除 |

## 4. 两个首选方案

### 4.1 Exa

官方定价页当前列出免费 Starter：注册赠送 20 美元 credits，之后每月 10 美元，无需支付方式；Search 基础价格为每千次 7 美元。按只使用基础 Search 粗略计算，月度免费额度约能覆盖 1,400 次调用，实际数量取决于内容提取和所选模式。

Exa `/search` 是通用 Web 搜索，不要求限定学术站点；`category` 只是可选过滤。搜索响应可以同时包含 URL、标题、作者、发布日期、全文或相关 highlights。Contents 文档说明它能处理 JavaScript 页面、PDF 和复杂布局，并建议 Web Search 场景直接在 `/search` 中请求 contents。

适合 ResearchFlow 的原因：

- 一次调用可同时完成发现和初步正文读取；
- 对论文 PDF、技术报告和普通网页采用相同结果结构；
- 可以只使用 `auto` 搜索和限制后的文本，不使用它的 Deep Search 或答案生成，保持 ResearchFlow 自己的 LangGraph 和 LLM 价值；
- 免费层与将来的付费层使用同一 API，升级额度不需要改 adapter。

风险：Exa 隐私政策明确说明 Query Data 可能用于改进、训练和微调服务，因此只能提交公开、非敏感研究目标。

官方资料：

- [Exa API 定价](https://exa.ai/pricing?tab=api)
- [Exa Search API](https://exa.ai/docs/reference/search)
- [Exa Contents API](https://exa.ai/docs/reference/contents-api-guide)
- [Exa 隐私政策](https://exa.ai/privacy-policy)

### 4.2 Tavily

Tavily 免费 Researcher 计划每月提供 1,000 credits，无需信用卡；Basic、Fast 和 Ultra-fast Search 每次 1 credit，Advanced 每次 2 credits。免费额度耗尽后请求停止，除非主动升级或启用 PAYGO。

`topic=general` 是通用网页搜索；结果包含标题、URL、相关内容和分数。`include_raw_content` 可以随搜索返回清洗后的 Markdown 或纯文本，也支持 include/exclude domain 和时间过滤。

适合 ResearchFlow 的原因：

- 接口简单，免费额度明确且不会自动产生费用；
- Search 和正文提取可以一次完成；
- 未来升级付费计划仍复用相同 adapter。

风险：官方 Rate Limits 文档注明 Production key 需要付费计划或启用 PAYGO。免费 Development key 的 100 RPM 对本地和受控演示足够，但在正式公开在线 Demo 前应向 Tavily 确认使用边界。隐私政策还说明查询可能被用于改进服务，并在少数情况下提交给第三方搜索索引。

官方资料：

- [Tavily 免费额度与定价](https://docs.tavily.com/documentation/api-credits)
- [Tavily Search API](https://docs.tavily.com/documentation/api-reference/endpoint/search)
- [Tavily Rate Limits](https://docs.tavily.com/documentation/rate-limits)
- [Tavily 隐私政策](https://www.tavily.com/privacy)

## 5. 其他方案为何不优先

### SearXNG

SearXNG 是自由的元搜索软件，支持 JSON Search API，并能聚合大量通用与专业搜索引擎。但官方文档提醒：许多公共实例关闭 JSON 格式；公共实例还可能记录查询、遭受滥用、触发验证码或被上游封禁。自托管可以控制这些风险，却会把“免费 API”转化为额外容器、服务器资源和维护工作。

- [SearXNG 项目说明](https://docs.searxng.org/)
- [SearXNG Search API](https://docs.searxng.org/dev/search_api.html)
- [公共实例与私有实例的取舍](https://docs.searxng.org/own-instance.html)

### Brave Search API

Brave 提供独立的通用 Web 索引和正式 API。Search 当前为每千次 5 美元，并每月赠送 5 美元 credits；但官方 Quickstart 要求信用卡，免费 credits 还要求在项目中署名。官方也说明存储完整搜索结果需要具有存储权的计划。

- [Brave Search API 与定价](https://brave.com/search/api/)
- [Brave API Quickstart](https://api-dashboard.search.brave.com/documentation/quickstart)

### Serper 与 SerpApi

Serper 返回实时 Google SERP，注册可获得 2,500 次免费查询且无需信用卡，但这是试用 credits，不是持续的每月免费额度。SerpApi 有每月 250 次免费层，但额度较小。两者核心能力是把第三方搜索结果页转换成 JSON；正文读取仍需另做。

- [Serper 官方主页与定价](https://serper.dev/)
- [SerpApi 官方定价](https://serpapi.com/pricing)

### Google、Bing 与 DuckDuckGo

- Google Custom Search JSON API 已关闭新客户，既有客户也必须在 2027-01-01 前迁移：[Google 官方公告与文档](https://developers.google.com/custom-search/v1/overview)。
- Microsoft 已于 2025-08-11 退役 Bing Search APIs：[Microsoft 生命周期公告](https://learn.microsoft.com/en-us/lifecycle/announcements/bing-search-api-retirement)。
- DuckDuckGo 的官方帮助页说明其面向用户的搜索结果来自自身和合作索引，但没有提供正式的完整 Web SERP API。依赖 Instant Answer、Lite HTML 或第三方库抓取不符合本项目对稳定可替换 Provider 的要求：[DuckDuckGo 搜索结果来源](https://duckduckgo.com/duckduckgo-help-pages/results/sources)。

## 6. 推荐的 ResearchFlow 接口演进

不把 Exa 或 Tavily 类型暴露给 LangGraph。保留现有 `SearchProvider.search(query, limit)`，把不同供应商响应归一化为 ResearchFlow DTO：

```text
SearchResult
├── title
├── url
├── snippet
├── content?       # Provider 已提取的正文或相关片段
├── published_at?  # 可选元数据
└── author?        # 可选元数据
```

读取节点优先使用 `content`；若未来某个 Provider 只返回 URL，再调用通用 `WebPageReader`。这样：

- 当前可以利用 Exa/Tavily 的正文提取，避免依赖脆弱的通用 HTML 抓取；
- 未来切换 Brave、Serper 或付费搜索服务时，只新增 adapter；
- LangGraph、Application、Source/Evidence 和前端不需要认识具体供应商；
- Fake Search Provider 继续保证自动化测试不联网。

配置建议：

```dotenv
RESEARCHFLOW_WEB_SEARCH_PROVIDER=exa
RESEARCHFLOW_WEB_SEARCH_BASE_URL=https://api.exa.ai
RESEARCHFLOW_WEB_SEARCH_API_KEY=
RESEARCHFLOW_WEB_SEARCH_RESULT_LIMIT=3
```

Provider 选择由应用工厂集中完成。API Key 只保存在服务端 Secret；额度耗尽、429、超时和供应商错误统一转换成 ResearchFlow 的安全错误代码。

## 7. 实施与验证状态

1. 第一版已选择 Exa，Stack Exchange 实现已移除。
2. 搜索查询只允许包含公开、非敏感信息。
3. 已在本地配置免费 API Key，并使用公开输入完成两次真实冒烟搜索：
   - 代码生成评测查询返回 arXiv 与 Springer 论文/出版物页面；
   - 生产 RAG 向量数据库选型查询返回 MongoDB、Google Cloud 与独立技术博客；
   - 两组结果均包含 3 个来源，每个结果都带有可供下游证据提取的 highlights。
4. 后续质量评估仍应继续记录：
   - AI 代码生成工具评测方法；
   - 一项普通科研综述问题；
   - 一项企业技术选型问题。
5. 验证结果至少记录来源类型覆盖、重复率、正文可读率、中文输入效果、延迟和单次 credits。

当前验证确认了 Exa 的通用 Web 来源覆盖和 highlights 响应可用，但样本仍很小，也尚未系统评测中文查询质量、重复率和长期稳定性。
