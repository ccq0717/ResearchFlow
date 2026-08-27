# ResearchFlow 作品集在线 Demo 部署指南

> 当前方案：Railway Hobby，Singapore，Next.js 与 FastAPI 各一个服务
>
> 当前状态：代码与配置已准备；平台部署、容器验证和线上验收尚未执行

本地安装与排错见[使用、开发与运维手册](development-and-operations.md)，平台选型依据见[部署平台比较](../research/deployment-platform-comparison.md)。本文只保留首次上线所需配置和验收步骤。

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

在同一个 Railway 项目中从本仓库创建 `web` 和 `api` 两个服务，不设置子目录 Root Directory；两个 Dockerfile 都需要仓库根目录作为构建上下文。

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

- 生产配置会拒绝模拟工作流、本地域名、通配 CORS 或短访问码；访问成功后后端只写入 8 小时有效的 HttpOnly、Secure Cookie，不把访问码放进前端包。
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

Docker 当前未安装在本开发设备，因此 Dockerfile 与 Compose 尚未实际构建；线上链接、真实平台规格和恢复步骤也必须在首次部署后回填，不能把“已配置”写成“已验证”。
