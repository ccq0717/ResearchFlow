# 本地 Embedding 检索评测

> 最近验证：2026-08-26

## 目的与方法

`scripts/evaluate_local_retrieval.py` 将 `examples/knowledge-base/` 的三份公开样例导入临时 SQLite，使用真实 Embedding 生成文档与查询向量，再通过生产使用的余弦排序检索。三条固定中文查询分别对应正确性、安全性和开发效率文档。

```powershell
uv run --package researchflow-api python scripts/evaluate_local_retrieval.py
```

脚本读取本地 `.env` 并消耗少量 Embedding 额度。

## 最近结果

使用 `gemini-embedding-2` 和 768 维向量：

| 指标 | 结果 |
| --- | ---: |
| Top-1 Accuracy | 1.000 |
| MRR@3 | 1.000 |

三个预期文档均排在第一位，验证了任务指令、API 配置、SQLite 向量持久化与余弦排序可以协同工作。样例规模很小，因此结果只作为连通性和回归基线，不代表大型知识库上的通用质量。
