# 网页搜索覆盖度评测

> 最近验证：2026-08-26

## 目的与方法

`scripts/evaluate_exa_coverage.py` 使用三条固定查询检查 Exa 能否从通用 Web 同时发现学术、官方和工业来源。每条查询取前五项，不使用网站白名单或 Exa 类别限制；至少一项被归为预期类型即通过。

```powershell
uv run --package researchflow-api python scripts/evaluate_exa_coverage.py
```

脚本读取本地 `.env`，执行三次真实搜索并消耗少量额度，只输出公开元数据。

## 最近结果

| 查询方向 | 预期类型命中 | 代表性来源 | 结果 |
| --- | ---: | --- | --- |
| 同行评议论文与公开基准 | 5 / 5 | ICLR、NeurIPS、ACL Anthology、arXiv | 通过 |
| 官方文档与公开标准 | 2 / 5 | 政府开发者文档、ETSI | 通过 |
| 工程博客与工业研究 | 3 / 5 | Faros AI、Opsera、DX | 通过 |

这组小样只证明当前黄金场景可以通过一个通用 Provider 跑通，不代表长期质量保证。需要 DOI、卷期、被引量或同行评议状态时，再增加专业元数据服务。
