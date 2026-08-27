# 在线 Demo 部署平台比较

> 调研日期：2026-08-27  
> 范围：只比较 Railway、Render、Fly.io 的官方资料；价格和平台限制在部署前仍需复核。

## 结论

项目默认本地演示。若未来需要长期在线链接，首选 **Railway Hobby**：保持现有 Next.js 与 FastAPI 两个服务，只给单实例 API 挂载 1 GB Volume。建议区域为 **Singapore**，平台最低消费 5 美元/月，按实际 RAM、CPU、流量和磁盘计费；项目预算先设为 **5–15 美元/月**，另计 LLM、Exa 与 Embedding 费用。

原因是它不要求把当前动态研究路由改成静态导出。Render 固定费用更容易预测，但当前结构需要两个 Starter Web Service 和磁盘，基线约 14.25 美元/月；若未来前端成功静态化，Render 的约 7.25 美元方案可重新成为首选。

## 推荐拓扑

```text
Railway Next.js Service
  └─ HTTPS → Railway FastAPI Service（单实例，关闭 Serverless）
                  └─ /data：1 GB Volume
                       ├─ researchflow.db
                       └─ uploads/
```

- 区域：两个服务与 Volume 都使用 Singapore。
- 实例：API 只运行一个实例并关闭 Serverless，避免面试访问遇到冷启动或首次 502。
- Secret：LLM、Exa、Embedding 和演示访问码使用 Railway Sealed Variables，不写入仓库或 `NEXT_PUBLIC_*`。
- HTTPS：先使用平台域名，作品集定稿时再绑定自定义域名。
- 预算：平台预留 **5–15 美元/月**并设置用量提醒；外部 Provider 使用独立额度。
- 备份：平台磁盘快照不能代替独立备份，仍需定期导出 SQLite 与 uploads，并做一次恢复演练。

Railway 的公共 HTTP 流最长 15 分钟、静默 5 分钟；当前 SSE 每约 3 秒发送心跳，任务通常远短于 15 分钟，断线后也会从持久事件恢复。上线验收仍需实际验证该边界。

## 平台比较

| 平台 | 适配度 | 最低可用成本 | 主要优点 | 关键限制 |
| --- | --- | --- | --- | --- |
| Render | 备选 | 当前结构约 $14.25/月；前端静态化后约 $7.25/月 | 付费 API 不休眠；最长 100 分钟 HTTP 响应；固定价格 | 静态低价方案需要改动态路由；带盘服务不能多实例且部署有短暂停机 |
| Railway | 推荐 | Hobby 最低 $5/月，按实际资源用量结算 | 无需改当前前后端结构；支持卷、Secret 和 HTTPS；monorepo 部署方便 | Free 每月仅 $1 额度；HTTP 流最长 15 分钟；费用随用量波动 |
| Fly.io | 暂不选 | 无长期免费层；两台小 Machine、1 GB 盘通常为数美元起 | 资源价格低、区域多、网络和运行参数可细调 | CLI 和 Machine/Volume 配置更多；本地卷不复制；没有可靠的免费层和硬费用上限 |

## Railway

Railway 对当前代码的改动最少：同一项目建立 Next.js 与 FastAPI 两个服务，只给 API 挂卷。Hobby 为每月 5 美元最低消费并包含等额资源用量；RAM、CPU、出站和卷按量计费，卷为 0.15 美元/GB/月。[定价与计划](https://docs.railway.com/pricing/plans)、[卷](https://docs.railway.com/volumes)

Free 计划只有每月 1 美元资源额度，服务最多 0.5 GB RAM，卷最多 0.5 GB，不适合作为稳定在线 Demo。Hobby 允许 5 GB 卷，足以从 1 GB 开始验证。[计划资源上限](https://docs.railway.com/pricing/plans)

Serverless 可在连续 10 分钟无出站流量后休眠，从而减少费用；但首次唤醒有冷启动，甚至可能返回一次 502。面试展示期间应关闭它，或在前端实现明确的预热与重试体验。[Serverless 行为](https://docs.railway.com/deployments/serverless)

公共 HTTP 流在持续传输时最多保持 15 分钟，5 分钟无数据会被关闭。当前研究任务在后台执行，SSE 断开后可以重连恢复，因此并非架构阻塞项，但必须发送心跳并验证自动重连。[公共网络限制](https://docs.railway.com/networking/public-networking/specs-and-limits)

Railway 提供 Singapore 区域、平台域名、自动 TLS、运行时变量和不可再次读取的 Sealed Variables。[区域](https://docs.railway.com/deployments/regions)、[域名与 HTTPS](https://docs.railway.com/networking/domains/working-with-domains)、[变量与 Secret](https://docs.railway.com/variables)

适用情形：希望保持当前 Next.js 运行方式、先快速上线，并接受约 **5–15 美元/月**的波动预算。应设置资源限制、用量提醒和可用的硬上限。[费用控制](https://docs.railway.com/pricing/cost-control)

## Render

Render 的免费 Web Service 会在 15 分钟无流量后休眠，唤醒约需一分钟；重启、部署或休眠都会清空本地文件，而且免费实例不能挂持久磁盘。因此 FastAPI + SQLite + uploads 必须使用付费实例。[免费实例限制](https://render.com/docs/free)

Starter Web Service 为 0.5 CPU、512 MB RAM，价格 7 美元/月；持久磁盘为 0.25 美元/GB/月。磁盘只保留挂载路径，只能供一个服务实例使用，并会让部署产生短暂停机。[计算规格](https://render.com/docs/compute-plans)、[Starter 价格](https://render.com/articles/best-railway-alternatives)、[持久磁盘](https://render.com/docs/disks)、[磁盘价格](https://render.com/articles/how-much-does-cloud-application-hosting-cost-for-small-businesses)

静态站可免费部署到全球 CDN；Next.js 可根据应用能力选择 Web Service 或静态导出。FastAPI 使用付费 Web Service 后不会因空闲休眠，Render 官方给出的 HTTP 响应上限为 100 分钟，足够当前 SSE 研究过程。[Next.js 部署](https://render.com/docs/deploy-nextjs-app)、[长请求说明](https://render.com/docs/render-vs-vercel-comparison)

Render 支持 Singapore 区域、自动 HTTPS、自定义域名、环境变量和 Secret 文件。已有服务不能原地切换区域，首次创建时应选对位置。[区域](https://render.com/docs/regions)、[Web Service](https://render.com/docs/web-services)、[环境变量与 Secret](https://render.com/docs/configure-environment-variables)

## Fly.io

Fly.io 技术上能够运行两个容器化应用，并为 FastAPI Machine 挂载本地 Volume。Singapore 可用，默认 `*.fly.dev` 地址支持 HTTPS，Secret 通过加密 vault 在启动时注入。[区域](https://fly.io/docs/reference/regions/)、[公共网络](https://fly.io/docs/networking/services/)、[Secret](https://fly.io/docs/apps/secrets/)

它没有长期免费层，所有普通组织需要绑定信用卡。计算按 Machine 规格和区域计费，Volume 为 0.15 美元/GB/月；自动停止可节省计算费用，但会引入冷启动。[费用说明](https://fly.io/docs/about/cost-management/)、[资源价格](https://fly.io/docs/about/pricing/)、[自动启停](https://fly.io/docs/reference/fly-proxy-autostop-autostart/)

Volume 位于单台主机和单一区域，只能挂载到一台 Machine，不会自动复制。平台每天创建快照，但官方明确说明快照不应作为主要备份。[Volume 限制](https://fly.io/docs/volumes/overview/)

Fly Proxy 的 HTTP idle timeout 可以配置，因此 SSE 可通过心跳保持连接；部署或 Machine 替换仍会中断连接，客户端必须重连。[应用网络配置](https://fly.io/docs/reference/configuration/)

Fly.io 的原始资源成本可能最低，但需要维护 Dockerfile、`fly.toml`、Machine、Volume、自动启停和恢复流程。对这个低流量单实例作品集而言，这些额外操作没有带来相应价值，因此不作为首次上线平台。

## 部署前必须保留的边界

- SQLite 与 uploads 必须位于同一持久磁盘，FastAPI 只运行一个实例。
- 部署、休眠或平台维护会终止进程；未完成任务只能被标记为中断后重试，不能宣称原地续跑。
- SSE 需要心跳和自动重连，页面重连后从持久化事件恢复进度。
- 持久磁盘和平台快照都不是完整备份方案，必须验证独立导出与恢复。
- 平台费用不包含 LLM、Exa 和 Embedding 调用；公开 Demo 必须另设访问保护、并发限制和 Provider 预算。
