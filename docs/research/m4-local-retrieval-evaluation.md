# M4 本地检索方案评测

> 日期：2026-08-26  
> 状态：原轻量方案与 Gemini Embedding 真实评测均已完成

## 评测方法

首版评测脚本曾将 `examples/knowledge-base/` 中三份可公开样例导入临时 SQLite，并通过生产使用的 `KnowledgeRetriever` 接口分别运行三种轻量模式：

- `lexical`：英文词、中文单字与双字组合的确定性匹配；
- `vector`：字符 n-gram 稀疏向量余弦相似度，不是语义 Embedding；
- `hybrid`：归一化后的词法分数与字符稀疏向量分数加权合并。

三条固定查询分别对应代码正确性、安全性和开发效率文档。指标为 Top-1 Accuracy 与 MRR@3。

## 结果

| 模式 | Top-1 Accuracy | MRR@3 |
| --- | ---: | ---: |
| lexical | 1.000 | 1.000 |
| vector | 1.000 | 1.000 |
| hybrid | 1.000 | 1.000 |

## 当时的决策

三种方案在当时的小规模黄金样例上没有质量差异，因此 M4 首版选择词法检索。这份结果解释了历史取舍，但不能证明词法检索在同义改写、跨语言或更复杂资料上足够。

## 后续设计调整

为了提高语义召回并让作品集展示真正的向量 RAG，当前实现已经移除词法、字符稀疏向量和混合模式，改为：

- 文档处理时调用 Gemini 原生 `batchEmbedContents`，使用 `RETRIEVAL_DOCUMENT`；
- 查询时使用同一模型和维度，使用 `RETRIEVAL_QUERY`；
- 向量连同模型标识保存在 SQLite，以余弦相似度排序；
- 仍不引入独立向量数据库或本地 GPU；
- `KnowledgeRetriever` 与 `EmbeddingClient` 保留未来更换模型和存储实现的 seam。

## Gemini Embedding 2 真实结果

2026-08-26 使用 `gemini-embedding-2`、768 维向量运行同一组 3 条中文查询，结果如下：

| 指标 | 结果 |
| --- | ---: |
| Top-1 Accuracy | 1.000 |
| MRR@3 | 1.000 |

三个预期文档都排在第一位，说明当前 API 配置、文档/查询任务类型、SQLite 向量持久化和余弦排序能够共同跑通。样例规模很小，这个结果属于连通性与回归基线，不代表对真实大型知识库的通用质量结论。复现脚本会调用真实服务并消耗少量 Embedding 额度。

当前复现命令：

```powershell
.\.venv\Scripts\python.exe scripts\evaluate_local_retrieval.py
```
