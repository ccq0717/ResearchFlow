# ResearchFlow Domain

ResearchFlow 把开放式研究目标转化为可追踪的研究过程和有证据支持的报告。本词汇表规定产品与代码共享的核心语言。

## Language

**Research Goal（研究目标）**:
用户希望系统调查、回答或产出方案的原始意图。
_Avoid_: Prompt、问题描述

**Research Run（研究运行）**:
从一个研究目标开始，到完成、失败或取消为止的一次独立执行。
_Avoid_: Session、Job、对话

**Research Outcome（研究结果）**:
Research Run 到达终态时形成的不可再变化结果，成功时包含报告，失败时包含可安全展示的原因。
_Avoid_: Terminal Status、最终事件

**Research Plan（研究计划）**:
研究运行在检索前形成的结构化中间产物，包含计划摘要、研究问题和预期交付物。
_Avoid_: Agent 思维过程、Prompt

**Research Question（研究问题）**:
研究计划中可通过检索和证据验证的具体问题。
_Avoid_: Task、搜索词

**Research Event（研究事件）**:
描述研究运行中已发生状态变化的不可变记录。
_Avoid_: Log、消息

**Research Report（研究报告）**:
研究运行交付给用户的最终结构化成果。
_Avoid_: 回复、Completion
