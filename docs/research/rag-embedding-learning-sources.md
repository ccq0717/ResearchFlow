# RAG、Embedding 与检索评测课程资料

> 核对日期：2026-08-26  
> 用途：为 ResearchFlow 学习课程提供一手来源与事实边界  
> 范围：RAG、文本 Embedding、余弦相似度、基础检索评测

## 结论摘要

- RAG 的核心是让生成模型同时利用参数化记忆和可检索的外部非参数化记忆；原始论文中的实现由稠密检索器、向量索引和生成器组成。
- Embedding 把内容转换成数值向量。检索系统把查询和资料映射到可比较的向量空间，再按相似度取 Top-K 结果。
- 余弦相似度比较两个向量的方向，计算式为归一化点积；向量长度归一化后，余弦相似度与点积给出相同排序。
- 检索质量不能靠几个看起来合理的结果判断。评测至少需要资料集、查询集和相关性标注，再根据目标选择 Recall@K、Precision@K、MRR 等指标。
- Embedding 相似不等于事实正确，也不等于资料足以支持结论。ResearchFlow 仍需分别处理 Evidence、Claim 与 Citation。
- Gemini Embedding 的模型版本差异会直接影响实现：`gemini-embedding-001` 支持 `task_type`，`gemini-embedding-2` 改用文本任务指令；二者向量空间不兼容。

## 1. RAG 的原始含义

### 来源直接陈述

Lewis 等人在 2020 年提出的 RAG 将生成模型的参数化记忆与非参数化记忆结合。论文实例中，参数化记忆是预训练 seq2seq 模型，非参数化记忆是 Wikipedia 文本段落组成的稠密向量索引。给定输入后，检索器先返回 Top-K 段落，生成器再结合输入与检索内容生成结果。

论文提出这一方向的动机包括：只保存在模型参数中的知识不容易扩充或修改，预测依据不容易检查，并可能产生幻觉；外部检索记忆则可以更新，并让被访问的知识可供检查。论文在特定实验中观察到 RAG 比参数模型基线生成得更具体、丰富且更符合事实，但这不是“使用 RAG 就不会产生幻觉”的保证。

原始实验把 Wikipedia 文章切成互不重叠的 100 词片段，建立约 2,100 万条记录的向量索引，并通过开发集选择测试时的 K。这说明分块方式和 Top-K 是需要实验验证的设计参数，不是由 RAG 概念给出的固定答案。

来源：

- [Lewis et al., Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks（NeurIPS 2020）](https://proceedings.neurips.cc/paper/2020/hash/6b493230205f780e1bc26945df7481e5-Abstract.html)
- [论文 PDF](https://proceedings.neurips.cc/paper/2020/file/6b493230205f780e1bc26945df7481e5-Paper.pdf)

### 对 ResearchFlow 课程的推论

原始论文描述的是一种可联合训练检索器与生成器的特定模型架构。ResearchFlow 沿用“先检索外部资料，再让模型基于资料生成”的核心思想，但采用工程化流水线，不应把两者的实现细节说成完全相同。

课程可以把当前流程概括为：

```text
资料解析 → 分块 → 文档向量化 → SQLite 持久化
                                      ↓
研究问题 → 查询向量化 → 余弦排序 → Top-K → Evidence → Claim → Citation → 报告
```

分块是一种工程策略：较小的块通常更聚焦，但可能丢失上下文；较大的块保留更多上下文，也可能带入无关内容。具体块大小、重叠量与 K 值应通过固定查询集比较，不能从原始论文的“100 词”直接照搬。

## 2. Embedding 与语义检索

### 来源直接陈述

Google 将 Embedding 描述为内容的数值表示，可用于语义搜索、分类和聚类。与只比较关键词不同，稠密向量可用于查找语义接近的内容，即使查询与资料没有使用完全相同的词。

Embedding 模型只负责把输入转换成数值表示，并不生成报告。RAG 系统仍需保存资料向量、生成查询向量、计算相似度、选择上下文，再调用生成模型。

来源：

- [Gemini API Embeddings 官方指南](https://ai.google.dev/gemini-api/docs/embeddings)
- [Gemini EmbedContent API 定义](https://ai.google.dev/api/embeddings)
- [Google Cloud：Get text embeddings](https://cloud.google.com/vertex-ai/generative-ai/docs/embeddings/get-text-embeddings)

### 查询与文档的非对称任务

对 `gemini-embedding-001`，Google 官方文档规定：

- 建立检索语料索引时使用 `RETRIEVAL_DOCUMENT`；
- 普通搜索查询使用 `RETRIEVAL_QUERY`；
- 问答查询可使用 `QUESTION_ANSWERING`，待检索资料仍使用 `RETRIEVAL_DOCUMENT`；
- 待核验陈述可使用 `FACT_VERIFICATION`，资料仍使用 `RETRIEVAL_DOCUMENT`。

选择与场景匹配的任务类型，是为了让模型针对需要表达的关系优化向量。

对 `gemini-embedding-2`，当前官方指南改为：

- 不支持 `task_type` 字段；
- 纯文本检索应按官方格式，把任务说明放入输入文本；
- 查询和文档使用非对称格式，例如搜索查询使用 `task: search result | query: ...`，文档使用 `title: ... | text: ...`。

来源：

- [Gemini Embeddings：Specify task type to improve performance](https://ai.google.dev/gemini-api/docs/embeddings#specify-task-type-to-improve-performance)
- [Gemini Embeddings API：TaskType 枚举](https://ai.google.dev/api/embeddings#TaskType)

### 模型、维度与索引兼容性

当前 Gemini 官方指南列出的文本 Embedding 输出维度范围为 128–3072，并推荐 768、1536 或 3072。维度影响向量存储与相似度计算成本，但官方给出的基准结果也说明，维度增加并不保证效果严格单调提升。

Google 明确说明：

- `gemini-embedding-001` 与 `gemini-embedding-2` 的向量空间不兼容；升级模型必须重新生成全部已有向量；
- `gemini-embedding-001` 使用非 3072 维输出时需要手动归一化；
- `gemini-embedding-2` 会自动归一化默认维度和截断后的维度。

来源：

- [Gemini Embeddings：模型信息与迁移说明](https://ai.google.dev/gemini-api/docs/embeddings#model-versions)
- [Gemini Embeddings：Ensuring quality for smaller dimensions](https://ai.google.dev/gemini-api/docs/embeddings#ensuring-quality-for-smaller-dimensions)

对课程而言，“更换模型或维度后重新处理文档”不能只解释成数据库字段不匹配。根本原因是新旧向量必须处于同一个可比较的空间，且相似度计算要求维数一致。

## 3. 余弦相似度

Google 给出的余弦相似度公式为：

\[
\operatorname{cos}(x,y)=\frac{x^\mathsf{T}y}{\lVert x\rVert\lVert y\rVert}
\]

它比较向量夹角，忽略向量长度本身；值越高，两个向量的方向越接近。点积则同时受方向和长度影响。两个向量都归一化为单位长度后，余弦相似度等于点积，欧氏距离也会与它形成单调对应关系，因此三者会产生相同的相似度排序。

来源：

- [Google Machine Learning：Measuring similarity from embeddings](https://developers.google.com/machine-learning/clustering/dnn-clustering/supervised-similarity)

对 ResearchFlow 的解释应止于“余弦分数用于排序语义接近程度”。高分不证明资料真实、权威或足以支持某条结论，也不能直接当作引用置信度。

## 4. 检索评测基础

### 4.1 先建立可评测的数据

标准信息检索评测需要三个组成部分：

1. 文档或片段集合；
2. 一组表达信息需求的测试查询；
3. 每个查询与候选资料之间的相关性判断，即 ground truth 或 qrels。

相关性针对用户的信息需求判断，而不是只看文档有没有包含查询中的字词。查询数量过少时，结果容易受个别样例影响，不能据此声称系统具有普遍质量。

来源：

- [Manning, Raghavan, Schütze：Information retrieval system evaluation](https://nlp.stanford.edu/IR-book/html/htmledition/information-retrieval-system-evaluation-1.html)
- [NIST TREC：Relevance Judgements](https://trec.nist.gov/data/reljudge_eng.html)

### 4.2 基础指标

对单个查询，在前 K 个结果上：

\[
\operatorname{Precision@K}=\frac{\text{Top-K 中的相关结果数}}{K}
\]

\[
\operatorname{Recall@K}=\frac{\text{Top-K 中的相关结果数}}{\text{该查询的全部相关结果数}}
\]

Precision@K 关注前 K 项中有多少噪声；Recall@K 关注需要的资料有多少被找回。两者会随 K 发生不同变化，因此评测记录必须写明 K。

Reciprocal Rank 只看第一个相关结果的位置：若第一个相关结果位于第 r 名，得分为 `1/r`；若规定的结果范围内没有相关项，则为 0。MRR 是多个查询 Reciprocal Rank 的平均值。它适合衡量“第一个可用结果是否足够靠前”，但不会奖励第一个结果之后找回的其他相关资料。

来源：

- [Introduction to Information Retrieval：Evaluation of unranked retrieval sets](https://nlp.stanford.edu/IR-book/html/htmledition/evaluation-of-unranked-retrieval-sets-1.html)
- [Introduction to Information Retrieval：Evaluation of ranked retrieval results](https://nlp.stanford.edu/IR-book/html/htmledition/evaluation-of-ranked-retrieval-results-1.html)
- [Voorhees：The TREC-8 Question Answering Track Report](https://trec.nist.gov/pubs/trec8/papers/qa_report.pdf)

如果相关性不是简单的“相关 / 不相关”，而是“高度相关 / 部分相关 / 不相关”，可以使用 nDCG@K。它累加各排名位置的相关性收益，对靠后的结果打折，再除以理想排序的收益。该指标适合分级相关性，不应在没有稳定分级标注时为了指标数量而加入。

来源：

- [Järvelin & Kekäläinen：Cumulated gain-based evaluation of IR techniques](https://doi.org/10.1145/582415.582418)

### 4.3 适合 ResearchFlow 的最小评测组合

以下是基于上述定义对本项目的课程建议，不是来源原句：

- 使用 `Recall@K` 检查回答问题所需片段是否进入上下文候选；
- 使用 `MRR@K` 检查第一个相关片段是否足够靠前；
- 需要衡量 Top-K 噪声时加入 `Precision@K`；
- 存在可靠的多级相关性标注时再加入 `nDCG@K`；
- 同时记录延迟、Embedding 调用成本和索引规模，因为离线相关性指标不反映运行成本。

当前三条固定查询得到的 Top-1 Accuracy 和 MRR@3 可以作为连通性与回归基线，但样本量不足以证明真实大型知识库上的通用质量。后续评测应扩大查询类型，并为每条查询标注相关片段，而不只是相关文档。

## 5. 课程必须保留的概念边界

以下均为基于一手定义与 ResearchFlow 实现得到的教学结论：

- **检索结果不等于 Evidence**：相似度只负责找候选内容，还要判断该内容是否与问题相关、是否足以支撑后续陈述。
- **Evidence 不等于 Claim**：Evidence 是来源中的支持材料，Claim 是系统准备写入报告的陈述。
- **Claim 不等于 Citation**：Citation 是 Claim 与具体来源位置的可追溯关系，不能只因为来源出现在 Top-K 就自动成立。
- **RAG 不保证事实正确**：检索可能漏掉资料、召回错误片段，生成模型也可能忽略或误读上下文。
- **Embedding 维度不代表可解释的概念数量**：每一维通常没有可供业务直接命名的独立含义，应把整个向量视为模型学习到的表示。
- **Top-K 不是越大越好**：增加 K 可能提高召回，也会增加噪声、上下文长度、延迟和生成成本，应通过固定评测集选择。
- **检索与最终报告应分层评测**：至少分别检查片段召回、Evidence 对 Claim 的支持、Claim 与 Citation 的绑定，以及报告是否忠实使用证据。

## 来源清单

1. [Lewis et al., Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks](https://proceedings.neurips.cc/paper/2020/hash/6b493230205f780e1bc26945df7481e5-Abstract.html)
2. [Google Gemini API：Embeddings](https://ai.google.dev/gemini-api/docs/embeddings)
3. [Google Gemini API：Embeddings API reference](https://ai.google.dev/api/embeddings)
4. [Google Machine Learning：Measuring similarity from embeddings](https://developers.google.com/machine-learning/clustering/dnn-clustering/supervised-similarity)
5. [Manning, Raghavan, Schütze：Introduction to Information Retrieval, Chapter 8](https://nlp.stanford.edu/IR-book/html/htmledition/evaluation-in-information-retrieval-1.html)
6. [Voorhees：The TREC-8 Question Answering Track Report](https://trec.nist.gov/pubs/trec8/papers/qa_report.pdf)
7. [Järvelin & Kekäläinen：Cumulated gain-based evaluation of IR techniques](https://doi.org/10.1145/582415.582418)
8. [NIST TREC：Relevance Judgements](https://trec.nist.gov/data/reljudge_eng.html)
