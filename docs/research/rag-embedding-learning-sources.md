# RAG、Embedding 与检索评测资料依据

> 核对日期：2026-08-26  
> 用途：记录课程采用的一手来源和 ResearchFlow 的解释边界

## 项目采用的结论

- RAG 的核心是先检索外部资料，再让生成模型结合资料作答；它不会自动消除幻觉。
- Embedding 把文本转换为可比较的数值向量，本身不生成报告，也不判断事实真假。
- ResearchFlow 使用分块、文档向量、查询向量、余弦排序和 Top-K 构成小规模本地检索，再把命中转换为 Source。
- 检索相似度不等于证据强度。Source、Evidence、Claim 和 Citation 必须继续分层处理。
- 更换 Embedding Provider、模型、维度或检索指令策略后必须重新生成已有向量。
- 三条固定查询只能作为连通性与回归基线，不能证明大型知识库上的通用质量。

## RAG 与当前实现的边界

Lewis 等人的原始 RAG 工作将生成模型的参数化记忆与可检索的非参数化记忆结合，实例由稠密检索器、向量索引和生成器组成。ResearchFlow 沿用“检索后生成”的核心思路，但采用工程流水线，不声称复现原论文的联合训练架构。

```text
资料解析 → 分块 → 文档向量化 → SQLite
                                 ↓
研究问题 → 查询向量化 → 余弦 Top-K → Source → Evidence → Claim → 报告
```

分块大小和 Top-K 是需要通过固定查询集验证的工程参数，不应直接照搬论文实验值。

来源：

- [Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks（NeurIPS 2020）](https://proceedings.neurips.cc/paper/2020/hash/6b493230205f780e1bc26945df7481e5-Abstract.html)
- [论文 PDF](https://proceedings.neurips.cc/paper/2020/file/6b493230205f780e1bc26945df7481e5-Paper.pdf)

## Gemini 模型版本差异

Google 将 Embedding 描述为内容的数值表示，可用于语义搜索、分类和聚类。与 ResearchFlow 直接相关的版本差异是：

| 模型 | 检索用途表达 | 迁移要求 |
| --- | --- | --- |
| `gemini-embedding-001` | `RETRIEVAL_DOCUMENT` / `RETRIEVAL_QUERY` 等 `task_type` | 与 Gemini 2 向量不兼容 |
| `gemini-embedding-2` | 把任务说明写入文本；不支持 `task_type` | 升级后重建全部向量 |

Gemini 2 的文本检索格式包括：

```text
文档：title: {title} | text: {content}
查询：task: search result | query: {content}
```

ResearchFlow 暂无独立标题字段传给 Embedding，因此文档使用 `title: none`。项目采用 768 维以降低作品集规模下的 SQLite 存储量；Google 当前推荐 768、1536 或 3072 维，并说明 Gemini 2 会自动归一化截断后的向量。

来源：

- [Gemini API Embeddings](https://ai.google.dev/gemini-api/docs/embeddings)
- [Gemini EmbedContent API](https://ai.google.dev/api/embeddings)

## 相似度与评测边界

余弦相似度是归一化点积：

```text
cosine(x, y) = (x · y) / (||x|| × ||y||)
```

它只用于排列向量方向的接近程度。高分不证明资料真实、权威或足以支持结论。

可复现检索评测至少需要语料、查询和相关性标注（qrels）。ResearchFlow 当前最需要的指标是：

- `Recall@K`：需要的片段有多少进入候选；
- `MRR@K`：第一个相关片段是否足够靠前；
- `Precision@K`：Top-K 中的噪声比例；
- `nDCG@K`：仅在有可靠分级相关性标注时使用。

检索评测与报告评测应分开：前者检查片段召回，后者还要检查 Evidence 是否支持 Claim、Citation 是否正确绑定，以及报告是否忠实使用证据。

来源：

- [Google：Measuring similarity from embeddings](https://developers.google.com/machine-learning/clustering/dnn-clustering/supervised-similarity)
- [Stanford IR Book：Evaluation in information retrieval](https://nlp.stanford.edu/IR-book/html/htmledition/evaluation-in-information-retrieval-1.html)
- [NIST TREC：Relevance Judgements](https://trec.nist.gov/data/reljudge_eng.html)
- [TREC-8 Question Answering Track（MRR）](https://trec.nist.gov/pubs/trec8/papers/qa_report.pdf)
- [Cumulated gain-based evaluation of IR techniques（nDCG）](https://doi.org/10.1145/582415.582418)
