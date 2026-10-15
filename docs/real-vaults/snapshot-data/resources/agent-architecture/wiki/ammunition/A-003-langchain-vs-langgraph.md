---
id: A-003
title: LangChain 和 LangGraph 到底什么关系、怎么选？
tags: [arch-orchestration, arch-workflow, ammunition]
created: 2026-09-09
domain: arch-orchestration
frequency: 高
sources: [F-C01-001, F-C01-002, M-004]
---

# 一句话结论
LangChain 和 LangGraph 是同一家族（langchain-ai 组织）的两代产品：LangChain 是通用 LLM 应用开发框架（LCEL 管道+工具抽象+15+ 提供商），LangGraph 是基于状态图的 agent 编排引擎（Pregel 执行+显式状态+Checkpoint 持久化）。关系是互补而非替代：LangChain 提供 LLM/工具/提供商抽象，LangGraph 提供复杂 agent 工作流编排；LangGraph 底层复用 LangChain 的 LLM 抽象。选型：简单 LLM 管道/快速原型选 LangChain，复杂多 agent/状态机/需要持久化和中断恢复选 LangGraph。

# 对比表

| 维度      | LangChain                                                                                                             | LangGraph                                                                                      |
| ------- | --------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| 定位      | 通用 LLM 应用开发框架                                                                                                         | 基于状态图的 agent 编排引擎                                                                              |
| 核心抽象    | LCEL Runnable 协议（runnables/base.py 5718 行）                                                                            | StateGraph 状态图（state.py 1692 行）+ Pregel 执行引擎（main.py 3972 行）                                   |
| 编排形态    | LCEL 管道（RunnableSequence/RunnableParallel）+ classic AgentExecutor ReAct 循环（1569 行）+ v1 middleware 架构（factory.py 84KB） | StateGraph/MessageGraph + 条件边（_branch.py 210 行）+ Pregel 超步执行                                   |
| 状态管理    | 无显式状态，通过 RunnableWithMessageHistory 等包装器传递                                                                            | 10 种状态通道（LastValue/Binop/Topic/EphemeralValue 等），显式 TypedDict/Pydantic 状态定义                    |
| 持久化     | 无内置持久化，BaseChatMessageHistory 管理对话历史                                                                                  | Checkpoint 独立包（checkpoint/checkpoint-sqlite/checkpoint-postgres/checkpoint-conformance），支持故障恢复 |
| 多 agent | classic 单 agent 循环，v1 middleware 支持多 agent 组合                                                                         | 原生支持多 agent 图编排（Supervisor/Hierarchical 模式），Pregel 超步支持多节点并行                                   |
| LLM 抽象  | BaseChatModel/BaseLLM + 15+ 提供商集成（partners/）+ BaseTool/StructuredTool（1640 行）                                         | 复用 LangChain 的 LLM 抽象，无独立 LLM 层，专注图编排                                                          |
| 容错      | RunnableRetry（324 行）+ with_fallbacks（597 行）                                                                           | Pregel 内置重试 + Checkpoint 故障恢复 + 远程执行（remote.py 1187 行）                                         |
| 中断恢复    | 无内置支持                                                                                                                 | 原生支持（Checkpoint + interrupt/resume）                                                            |
| 可视化     | 无内置图可视化                                                                                                               | 图可视化（_draw.py 278 行 + ui.py 173 行）                                                             |
| 适用场景    | 快速原型、简单 LLM 管道、工具调用、通用 LLM 应用                                                                                         | 复杂多 agent 工作流、状态机、需要持久化和中断恢复的生产级 agent                                                         |
| star    | 145,914★（GitHub API 实测）                                                                                               | 41,238★（F-C01-002 frontmatter）                                                                 |

# 取舍论述
**选 LangChain**：当需要快速构建 LLM 应用原型，或应用主要是简单的 LLM 管道（提示词→LLM→输出解析）和工具调用时。LangChain 的 LCEL Runnable 协议提供了简洁的链式组合语法，15+ 提供商集成降低了接入成本，BaseTool/StructuredTool 抽象简化了工具定义。**何时反转**：当 agent 工作流变得复杂（多 agent 协作、条件分支、循环、需要持久化状态），LangChain 的 classic AgentExecutor ReAct 循环和 v1 middleware 架构无法提供显式状态管理和 Checkpoint 持久化，应选 LangGraph。

**选 LangGraph**：当需要构建复杂的多 agent 工作流、显式状态机、或生产级 agent 需要持久化和中断恢复时。LangGraph 的 StateGraph 提供了显式的状态定义和 10 种状态通道，Pregel 执行引擎支持超步并行和条件边路由，Checkpoint 独立包支持 sqlite/postgres 持久化和故障恢复，图可视化支持调试。**何时反转**：当应用只是简单的 LLM 管道或单 agent 工具调用，LangGraph 的状态图抽象增加了不必要的复杂度，应选 LangChain。

**两者关系的本质**：LangGraph 不是 LangChain 的替代品，而是 LangChain 生态的扩展。LangGraph 底层复用 LangChain 的 LLM 抽象（BaseChatModel）和工具抽象，专注于图编排和状态管理。实际项目中常组合使用：用 LangChain 定义 LLM/工具/提示词，用 LangGraph 编排 agent 工作流。

# 量化证据
- LangChain：LCEL Runnable base.py 5718 行（最大文件）[EXTRACTED，F-C01-001 claim 台账]；v1 Agent middleware factory.py 84KB+10+ 中间件 [EXTRACTED，F-C01-001 claim 台账]；classic AgentExecutor 1569 行 ReAct 循环 [EXTRACTED，F-C01-001 claim 台账]；15+ 提供商集成（partners/）[EXTRACTED，F-C01-001 claim 台账]；RunnableRetry 324 行+with_fallbacks 597 行 [EXTRACTED，F-C01-001 claim 台账]；145,914★（GitHub API 实测）[EXTRACTED，F-C01-001 claim 台账]
- LangGraph：StateGraph state.py 1692 行 [EXTRACTED，F-C01-002 claim 台账]；Pregel main.py 3972 行（最大文件）[EXTRACTED，F-C01-002 claim 台账]；Pregel _algo.py 1351 行 [EXTRACTED，F-C01-002 claim 台账]；10 种状态通道（channels/ 10 文件）[EXTRACTED，F-C01-002 claim 台账]；Checkpoint 4 个独立包 [EXTRACTED，F-C01-002 claim 台账]；远程执行 remote.py 1187 行 [EXTRACTED，F-C01-002 claim 台账]；条件边 _branch.py 210 行 [EXTRACTED，F-C01-002 claim 台账]；图可视化 _draw.py 278 行+ui.py 173 行 [EXTRACTED，F-C01-002 claim 台账]；41,238★（F-C01-002 frontmatter）[EXTRACTED]
- 对比矩阵：M-004 C01 通用编排框架横评（10 维度）[EXTRACTED，M-004]

# 面试 follow-up

#flashcards

LangGraph 的 Pregel 执行引擎和传统的 DAG 执行有什么区别？::Pregel 是基于超步（superstep）的批量同步并行计算模型，源自 Google Pregel 图计算论文。与 DAG 执行的区别：①DAG 是有向无环图，节点按拓扑顺序执行一次；Pregel 是状态图，节点可以在多个超步中反复执行（直到所有节点 vote to halt）；②Pregel 支持节点间消息传递（MessageGraph），DAG 只支持数据沿边流动；③Pregel 的超步并行允许多个节点同时执行，适合多 agent 协作；④Pregel 的 Checkpoint 在每个超步后持久化，支持从任意超步恢复。LangGraph 的 Pregel 实现（main.py 3972 行+_algo.py 1351 行）是对 Google Pregel 模型的 agent 编排适配。
<!--SR:!2026-10-09,4,270-->

LangChain v1 的 middleware 架构和 LangGraph 的状态图有什么区别？会取代 LangGraph 吗？::LangChain v1 的 middleware 架构（factory.py 84KB+10+ 中间件）是在 classic AgentExecutor 基础上引入的中间件链模式，支持在 agent 执行前后插入中间件（如日志、鉴权、限流）。与 LangGraph 状态图的区别：①middleware 是线性链（before→agent→after），状态图是有向图（支持分支、循环、并行）；②middleware 无显式状态定义，状态通过中间件上下文传递；状态图有 10 种状态通道和显式 TypedDict 状态；③middleware 无 Checkpoint 持久化，状态图有独立 Checkpoint 包。两者不会互相取代：LangChain v1 middleware 适合简单的 agent 执行链增强，LangGraph 适合复杂的多 agent 工作流编排。实际项目中可组合使用。
<!--SR:!2026-10-09,4,270-->

# 溯源
- F-C01-001 langchain（LCEL Runnable 协议，v1 Agent middleware，classic AgentExecutor，15+ 提供商，145,914★）
- F-C01-002 langgraph（StateGraph，Pregel 执行引擎，10 种状态通道，Checkpoint 4 包，远程执行，41,238★）
- M-004 C01 通用编排框架域×框架横评矩阵（10 维度对比，含设计哲学/图编排形态/状态管理/语言生态定位等）

# 待补
- [ ] LangChain v1 GA 时间和 middleware 架构的完整文档（当前 v1 迁移中，需跟踪官方发布）
- [ ] LangGraph Pregel 执行引擎的性能基准（超步并行 vs DAG 执行的延迟对比，需独立实验）
- [ ] LangChain + LangGraph 组合使用的最佳实践（LLM/工具用 LC，编排用 LG，需实际案例验证）
- [ ] LangGraph Platform（托管服务）与开源版的功能差异（需官方文档确认）
