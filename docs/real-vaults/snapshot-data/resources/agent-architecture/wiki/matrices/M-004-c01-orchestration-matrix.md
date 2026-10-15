---
id: M-004
title: C01 通用编排框架域×框架横评：langchain vs langgraph vs eino
tags: [arch-orchestration, arch-workflow, arch-context, arch-llm-abstraction, matrix]
created: 2026-09-09
category: C01
domains: [arch-orchestration, arch-workflow, arch-plan-exec, arch-llm-abstraction, arch-context, arch-aci, arch-fault-tolerance]
columns: 3
sources: [F-C01-001, F-C01-002, F-C01-003]
---

# 矩阵定位
对比 C01 通用编排框架三种范式：LCEL 管道+Agent middleware（langchain）、Pregel 状态图执行引擎（langgraph）、Go 生态三层架构 Components+ADK+Composition（eino），解决面试高频问题"通用编排框架怎么选"。中立性声明：格内结论全部回溯到三张 F 卡的代码级溯源，厂商自证数字仅 [UNVERIFIED] 不入正文；eino 卡 frontmatter 为 name 风格，矩阵引用以 F 卡 ID 为准。

# 矩阵本体

| 维度/子维度         | langchain（F-C01-001）                                                                                                                                                    | langgraph（F-C01-002）                                                                                                                                                     | eino（F-C01-003）                                                                                                                                                                                                |
| -------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **设计哲学**       | [EXTRACTED] LCEL Runnable 协议为核心，链式组合+管道抽象；v1 引入 Agent middleware 架构（factory.py 84KB+10+ 中间件），从经典 AgentExecutor 向 middleware 迁移 [F-C01-001 claim 台账]                     | [EXTRACTED] Pregel 执行引擎为核心，状态图+消息传递范式；StateGraph 显式状态管理，Pregel 算法（_algo.py 1351 行）驱动超步执行 [F-C01-002 claim 台账]                                                            | [EXTRACTED] 三层架构 Components+ADK+Composition，借鉴 LangChain+Google ADK；Go 惯例适配（接口组合+context.Context+goroutine），主仓接口+eino-ext 实现分离 [F-C01-003 claim 台账]                                                            |
| **图编排形态**      | [EXTRACTED] LCEL 管道（RunnableSequence/RunnableParallel）+ classic AgentExecutor ReAct 循环（1569 行）；v1 middleware 架构支持中间件链编排，非显式状态图 [F-C01-001 claim 台账]                     | [EXTRACTED] StateGraph 状态图（state.py 1692 行）+ MessageGraph（message.py 369 行）；条件边（_branch.py 210 行）支持分支路由；图可视化（_draw.py 278 行+ui.py 173 行） [F-C01-002 claim 台账]            | [EXTRACTED] Composition 多模式编排：chain.go（线性链）/branch.go（分支）/chain_parallel.go（并行）/dag.go（DAG 有向无环图）/checkpoint.go（检查点）/agentic_tools_node.go（agent 工具节点）/component_to_graph_node.go（组件转图节点） [F-C01-003 claim 台账] |
| **状态管理**       | [EXTRACTED] Runnable 无显式状态，状态通过 RunnableWithMessageHistory 等包装器传递；classic AgentExecutor 内部状态隐式管理；v1 middleware 架构通过中间件传递上下文状态 [F-C01-001 §arch-orchestration]           | [EXTRACTED] 10 种状态通道（channels/ 10 文件：LastValue/Binop/Topic/EphemeralValue 等），显式状态定义+通道语义；StateGraph 状态通过 TypedDict/Pydantic 定义，Pregel 超步间状态传递 [F-C01-002 claim 台账]       | [EXTRACTED] context.Context 贯穿全链路（Go 惯例）；ADK callback 机制管理执行状态；Composition checkpoint.go 支持状态持久化恢复；Runner 事件流（iter.Next()）流式传递状态 [F-C01-003 claim 台账]                                                          |
| **上下文策略**      | [EXTRACTED] Runnable 上下文通过 invoke(input) 传递；BaseChatMessageHistory 管理对话历史；v1 middleware 架构支持上下文注入中间件 [F-C01-001 §arch-context]                                          | [EXTRACTED] 状态通道管理上下文（Messages 通道内置消息历史）；Checkpoint 持久化上下文（checkpoint-sqlite/checkpoint-postgres）；远程执行（remote.py 1187 行）支持跨进程上下文传递 [F-C01-002 claim 台账]                  | [EXTRACTED] context.Context 标准上下文传递；ADK call_option 支持上下文选项；Components prompt 组件管理提示词上下文；interrupt/resume 支持 human-in-the-loop 上下文中断恢复 [F-C01-003 claim 台账]                                                    |
| **多 Agent 支持** | [EXTRACTED] classic AgentExecutor 单 agent 循环；v1 middleware 架构支持多 agent 中间件组合；MultiAgent 相关示例在 examples/ 中 [F-C01-001 §arch-orchestration]                               | [EXTRACTED] StateGraph 原生支持多 agent 图编排（agent 节点+条件边路由）；Supervisor/Hierarchical 模式通过图结构实现；Pregel 超步执行支持多节点并行 [F-C01-002 §arch-orchestration]                              | [EXTRACTED] ADK Multi-Agent Host 模式（flow/agent/multiagent/host/）；agent_tool 支持 agent 间工具调用；Composition DAG 支持多 agent 节点编排；interrupt/resume 支持多 agent 协作中断 [F-C01-003 claim 台账]                                 |
| **语言生态定位**     | [EXTRACTED] **Python 生态双雄之一**，Python 原生实现，15+ 提供商集成（partners/ openai/anthropic/deepseek/groq/mistralai/ollama/xai 等），PyPI 分发，Python 数据科学生态深度集成 [F-C01-001 claim 台账]     | [EXTRACTED] **Python 生态双雄之二**，Python 原生实现，与 langchain 同家族（langchain-ai 组织），Checkpoint 独立包（sqlite/postgres/conformance），远程执行支持 LangGraph Platform 部署 [F-C01-002 claim 台账] | [EXTRACTED] **Go 生态唯一**，Go 原生实现（go.mod go 1.18），字节 CloudWeGo 生态，eino-ext 扩展仓提供 OpenAI/Ollama 等实现，Go 微服务生态深度集成，goroutine 原生并发 [F-C01-003 claim 台账]                                                              |
| **LLM 抽象层**    | [EXTRACTED] BaseChatModel/BaseLLM 抽象（libs/core/），15+ 提供商集成（partners/），工具抽象 BaseTool/StructuredTool（tools/base.py 1640 行），MCP 支持（v1 langchain/mcp/） [F-C01-001 claim 台账] | [EXTRACTED] 复用 langchain 的 LLM 抽象层（BaseChatModel），无独立 LLM 抽象；专注图编排和状态管理，LLM 调用通过 langchain 模型节点接入 [F-C01-002 §arch-llm-abstraction]                                      | [EXTRACTED] Components model 组件定义 LLM 接口（主仓空目录，实现在 eino-ext），7 大组件含 model/prompt/embedding，ADK 统一 LLM 调用接口，Go interface 组合实现多提供商适配 [F-C01-003 claim 台账]                                                        |
| **容错机制**       | [EXTRACTED] RunnableRetry 324 行（重试）+ with_fallbacks 597 行（降级），Runnable 协议原生支持容错装饰器；v1 middleware 架构支持容错中间件 [F-C01-001 claim 台账]                                         | [EXTRACTED] Pregel 执行引擎内置重试（retry 配置）；Checkpoint 持久化支持故障恢复（从 checkpoint 恢复执行）；远程执行（remote.py）支持网络容错 [F-C01-002 §arch-fault-tolerance]                                    | [EXTRACTED] ADK cancel 机制（cancel.go + 4 种取消测试：edge/multicall/recursive/stream_race）；Composition checkpoint.go 支持故障恢复；Go context 取消/超时原生支持 [F-C01-003 claim 台账]                                                 |
| **评估维度**       | [EXTRACTED] v1 迁移中（langchain_classic 旧版+langchain_v1 新版并存），评估框架在 libs/langchain_v1/ 中；145,914★（GitHub API 实测）[F-C01-001 claim 台账]                                       | [EXTRACTED] Checkpoint conformance 测试（checkpoint-conformance 包）确保后端一致性；图可视化支持调试；41,238★（F-C01-002 frontmatter）[F-C01-002 claim 台账]                                       | [EXTRACTED] 完善取消机制测试（4 种取消场景测试）；checkpoint_migrate_test/checkpoint_test 验证持久化；12,987★（F-C01-003 frontmatter），pushed=2026-09-08 hot [F-C01-003 claim 台账]                                                        |

# 数据口径
- EXTRACTED = 代码/官方文档级溯源（repo:file:line 或 F 卡分节引用），格内 [EXTRACTED] 角标+F 卡 ID 回溯
- 实验数字 = 复现脚本随卡入库（本矩阵无独立实验，全部数字来自 F 卡已验证溯源）
- 厂商数字 = UNVERIFIED 引用并注明口径偏见，禁直接搬入正文论断
- eino 卡 frontmatter 为 name 风格（非 title 风格），矩阵引用以 F 卡 ID（F-C01-003）为准

# 一页口径（30 秒版结论，面试直接背）
langchain=LCEL 管道+Agent middleware，Python 生态双雄之一，15+ 提供商集成，适合快速原型和通用 LLM 应用开发；langgraph=Pregel 状态图执行引擎，Python 生态双雄之二，显式状态管理+Checkpoint 持久化+多 agent 图编排，适合复杂状态机和多 agent 工作流；eino=Go 生态唯一，三层架构 Components+ADK+Composition，Go 惯例适配+goroutine 并发+字节 CloudWeGo 生态，适合 Go 微服务架构下的 LLM 应用。三者语言生态决定选型：Python 选 langchain（快速）/langgraph（复杂状态），Go 选 eino（唯一选择）。

# 溯源
- F-C01-001 langchain（LCEL Runnable 协议，runnables/base.py 5718 行，v1 Agent middleware factory.py 84KB，classic AgentExecutor 1569 行，15+ 提供商，145,914★）
- F-C01-002 langgraph（StateGraph state.py 1692 行，Pregel main.py 3972 行，10 种状态通道，Checkpoint 4 包，远程执行 remote.py 1187 行，41,238★）
- F-C01-003 eino（Go 生态，三层架构 Components+ADK+Composition，7 大组件，主仓+eino-ext 分离，ReAct+Multi-Agent Host，Runner 事件流，12,987★）

# 待补
- [ ] langgraph 精确 star 数对比（当前 41,238★ 来自 F 卡 frontmatter，需 GitHub API 复测）
- [ ] 三者性能/延迟对比（LCEL 管道 vs Pregel 状态图 vs Go Composition，需独立基准测试）
- [ ] eino eino-ext 扩展仓的完整提供商列表（当前仅确认 OpenAI/Ollama，需完整列表）
- [ ] langchain v1 迁移进度（langchain_classic 旧版+langchain_v1 新版并存，需跟踪 v1 GA 时间）
- [ ] 多 agent 编排的具体模式对比（langgraph Supervisor vs eino Multi-Agent Host vs langchain middleware，需精读示例）
