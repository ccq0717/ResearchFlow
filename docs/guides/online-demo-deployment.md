# ResearchFlow 可选在线 Demo 部署指南

> 默认展示方式：本地运行并在面试中共享屏幕
>
> 可选在线方案：Railway Hobby，Singapore，Next.js 与 FastAPI 各一个服务

本地安装与排错见[使用、开发与运维手册](development-and-operations.md)，平台选型依据见[部署平台比较](../research/deployment-platform-comparison.md)。项目无需 Docker 或在线服务即可完成作品集演示；只有确实需要长期公开链接时才执行本文。

## 是否需要部署

- **本地共享屏幕**：零平台费用、数据留在本机，是当前默认方案。
- **临时公网演示**：可按需使用隧道服务，但必须实际验证 SSE、访问码和公开风险。
- **长期在线链接**：使用下述 Railway 方案，接受平台与外部 Provider 费用。

Railway Free 每月只有 1 美元资源额度，且资源和 Volume 上限较低，可以实验但不作为稳定链接承诺；Render Free 会休眠并丢失本地 SQLite 与上传文件。需要完全零成本时，应保留本地演示，并在 GitHub 展示架构、示例报告和演示视频。

## 部署边界

这是使用共享访问码保护的低流量作品集 Demo，不是多租户 SaaS。FastAPI 在进程内执行任务，SQLite 与上传文件位于单块持久卷，因此 API 必须保持单实例。进程重启时未完成任务会标记为中断，用户可以重新运行，但不会从节点中间续跑。

```text
浏览器 ──HTTPS──> Next.js
  └──── REST / SSE ────> FastAPI（单实例）
                            ├─ LLM / Exa / Embedding
                            └─ /data
                               ├─ researchflow.db
                               └─ uploads/
```

## Railway 配置

Railway 会直接从仓库 Dockerfile 构建镜像，因此本机不必安装 Docker Compose。在同一个 Railway 项目中创建 `web` 和 `api` 两个服务，不设置子目录 Root Directory；两个 Dockerfile 都需要仓库根目录作为构建上下文。

### API 服务

- Dockerfile Path：`/apps/api/Dockerfile`
- Region：`Singapore`
- Replicas：`1`
- Serverless：关闭
- Public Networking：开启
- Healthcheck Path：`/health`
- Volume：1 GB，挂载到 `/data`

设置以下变量；密钥和访问码使用平台 Secret，不复制仓库 `.env`：

```dotenv
RAILWAY_DOCKERFILE_PATH=/apps/api/Dockerfile
RESEARCHFLOW_ENVIRONMENT=production
RESEARCHFLOW_WORKFLOW_MODE=langgraph
RESEARCHFLOW_DATABASE_URL=sqlite+aiosqlite:////data/researchflow.db
RESEARCHFLOW_KNOWLEDGE_UPLOAD_DIRECTORY=/data/uploads
RESEARCHFLOW_CORS_ORIGINS=["https://<web-domain>"]
RESEARCHFLOW_DEMO_ACCESS_CODE=<至少12字符的随机访问码>
RESEARCHFLOW_MAX_CONCURRENT_RUNS=1
RESEARCHFLOW_MAX_RUNS_PER_DAY=10
```

再按本地已验证配置加入 LLM、Exa 和 Embedding 变量。可选填写两项每百万 Token 单价，让运行页显示模型费用估算；真正的月度硬预算仍应在各 Provider 控制台设置。

### Web 服务

- Dockerfile Path：`/apps/web/Dockerfile`
- Region：`Singapore`
- Public Networking：开启
- Healthcheck Path：`/`

```dotenv
RAILWAY_DOCKERFILE_PATH=/apps/web/Dockerfile
NEXT_PUBLIC_API_BASE_URL=https://<api-domain>
```

`NEXT_PUBLIC_API_BASE_URL` 会写入浏览器包，修改后必须重新构建；它只能包含公开 API 地址，不能包含密钥。取得 Web 域名后，再把 API 的 `RESEARCHFLOW_CORS_ORIGINS` 改为该完整 Origin 并重新部署。

## 安全、预算与数据

- 生产配置会拒绝模拟工作流、本地域名、通配 CORS 或短访问码；访问成功后后端只写入 8 小时有效的 HttpOnly、Secure、SameSite=None Cookie，使分域 Web 与 API 能携带会话，同时不把访问码放进前端包。
- API 已限制全站并发数和每日创建数；搜索结果数、上传体积与数量也有上限。平台和 Provider 仍需分别设置费用提醒或硬上限。
- 日志只记录请求 ID、方法、路径、状态和耗时，不记录请求正文、密钥或文档内容。
- 演示只上传公开资料。文档片段会发送给 Embedding Provider，检索命中还会发送给 LLM。
- Railway Volume 启用每日或每周备份。定期把 SQLite 与 uploads 导出到平台外；平台内备份不能作为唯一副本。

## 发布与恢复

首次发布按 `API → Web → API CORS` 的顺序进行。后续更新先备份 `/data`，再部署一个已通过 CI 的提交；不要横向扩展 API。

回滚分两类：

- 代码问题：在 Railway 回滚到上一成功部署；
- 数据或 schema 问题：停止 API 写入，恢复同一时间点的 SQLite 与 uploads，再部署与该 schema 兼容的代码。

仓库中的 `scripts/backup_data.ps1` 和 `scripts/restore_data.ps1` 用于本地与导出副本的恢复演练；平台备份和平台外副本都应至少验证一次。

## 上线验收

- [ ] 两个镜像在干净环境构建成功，API 健康检查通过；
- [ ] HTTPS 页面显示访问码入口，未授权请求不能读取历史或创建任务；
- [ ] 黄金输入完成规划、网页与本地检索、证据、报告和度量；
- [ ] SSE 中断或刷新后能恢复已保存进度；取消、失败和一次重试状态明确；
- [ ] 重启 API 后历史、SQLite 和上传文件仍在；
- [ ] 外部服务失败或超时时，页面不泄露密钥、原始响应或堆栈；
- [ ] Railway 与 Provider 的预算提醒已开启；
- [ ] 备份恢复、代码回滚和数据回滚各验证一次；
- [ ] README 只在上述检查完成后加入真实在线链接和截图。

Dockerfile 与 Compose 是可选交付物，当前尚未在本机实际构建。若未来执行在线部署，必须完成上述验收并回填真实链接、平台规格和恢复结果，不能把“已配置”写成“已验证”。
