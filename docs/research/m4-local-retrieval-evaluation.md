# M4 本地检索方案评测

> 日期：2026-08-26  
> 结论：默认采用词法检索，不引入 Embedding API、GPU 或独立向量数据库

## 评测方法

`scripts/evaluate_local_retrieval.py` 将 `examples/knowledge-base/` 中三份可公开样例导入临时 SQLite，并通过生产使用的 `KnowledgeRetriever` 接口分别运行三种模式：

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

复现命令：

```powershell
.\.venv\Scripts\python.exe scripts\evaluate_local_retrieval.py
```

## 决策

三种方案在当前小规模黄金样例上没有质量差异。词法方案实现和运行成本最低、行为最容易解释，也不需要下载模型或调用付费服务，因此成为默认配置。`KnowledgeRetriever` 与配置项继续保留另外两种模式，方便未来用更大、更难的语料重新评测；只有真实数据证明语义检索有稳定收益时，才考虑引入 Embedding Provider 或向量索引。

此结果只说明当前作品集规模和样例下“效果足够”，不代表词法检索普遍优于语义 Embedding。
