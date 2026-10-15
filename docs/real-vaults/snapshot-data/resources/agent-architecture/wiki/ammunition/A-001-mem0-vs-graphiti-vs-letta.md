---
id: A-001
title: mem0 vs graphiti vs letta 怎么选？
tags: [arch-memory, arch-rag, ammunition]
created: 2026-09-08
domain: arch-memory
frequency: 高
sources: [F-C06-001, F-C06-002, F-C06-003, M-001]
---

# 一句话结论
mem0 适合通用 agent 记忆层（单次 LLM 调用低成本，向量检索快）；graphiti 适合需要实体关系推理和时序追溯的场景（知识图谱高推理力但高成本）；letta 适合已用 letta 完整 agent 框架且需要记忆版本控制和可审计的场景（Git 版本化可回滚）。三者非替代而是记忆范式选择：向量检索快/图谱可推理/Git 可回滚。

# 对比表

| 维度 | mem0 | graphiti | letta |
|---|---|---|---|
| 存储范式 | 扁平向量记忆 | 时序知识图谱 | 文件系统+Git 版本化 |
| 写入成本 | 单次 LLM 调用（低） | 多次 LLM 调用（高） | 无独立记忆提取 LLM（含在主循环） |
| 检索方式 | 向量搜索+BM25（快） | 混合搜索+图谱遍历（可推理） | 文件系统遍历（依赖 agent 策略） |
| 版本化 | 无 | 时序属性（valid_at/expired_at） | Git 完整版本化（可回滚） |
| 去重 | MD5 hash 精确 | LLM 语义去重 | 无显式去重 |
| 形态 | 纯记忆库/平台 | 纯记忆库+REST+MCP | 完整 agent 框架 |
| 适用场景 | 通用 agent 记忆层 | 实体关系推理/时序追溯 | 记忆版本控制/可审计 |

# 取舍论述
**选 mem0**：当需要低成本、低延迟的通用 agent 记忆层，且已有向量数据库基础设施时。mem0 的 V3 分阶段批量管道单次 LLM 调用完成记忆提取，28 向量库+21 LLM+15 embeddings 的提供商无关抽象使其易于集成。**何时反转**：当需要实体关系推理（如"用户 A 和组织 B 的关系随时间如何变化"）或语义去重（识别同义实体）时，mem0 的 MD5 hash 去重和扁平向量检索无法满足，应选 graphiti。

**选 graphiti**：当记忆需要结构化推理（实体-关系-时序）和可追溯的演化历史时。graphiti 的四层节点体系（Entity/Episodic/Community/Saga）+多层边体系支持复杂关系推理，LLM 语义去重能识别同义实体，边失效机制保留记忆演化历史。**何时反转**：当延迟和成本敏感（如实时对话 agent），或不需要图谱推理（只需事实检索）时，graphiti 的多次 LLM 调用和高延迟成为负担，应选 mem0。

**选 letta**：当已使用 letta 完整 agent 框架，且需要记忆的版本控制、可审计性和可回滚时。letta 的 MemFS+Git 版本化（memory-git.ts 61KB）支持任意历史版本回滚，Git log/diff/blame 可审计每次记忆变更，Worktree 隔离支持并行记忆分支实验。**何时反转**：当 letta 不是 agent 框架（如使用 langchain/autogen），或需要向量语义检索（letta 的文件系统遍历检索效率低于向量搜索）时，应选 mem0 或 graphiti 作为独立记忆层。

# 量化证据
- mem0：64,868★（GitHub API 实测，2026-09-08）[EXTRACTED，F-C06-001 frontmatter]；V3 管道 5 阶段单次 LLM 调用 [EXTRACTED，F-C06-001 §arch-memory]；28 向量库+21 LLM+15 embeddings [EXTRACTED，F-C06-001 §arch-llm-abstraction]
- graphiti：4 图数据库后端（Neo4j/FalkorDB/Kuzu/Neptune）[EXTRACTED，F-C06-002 claim 台账]；四层节点+多层边体系 [EXTRACTED，F-C06-002 §arch-memory]；多阶段抽取管道 6 阶段多次 LLM 调用 [EXTRACTED，F-C06-002 §arch-orchestration]
- letta：memory-git.ts 61KB Git 版本化 [EXTRACTED，F-C06-003 §arch-memory]；完整 agent 框架 28 子目录 [EXTRACTED，F-C06-003 claim 台账]；Worktree 隔离支持并行分支实验 [EXTRACTED，F-C06-003 §arch-memory]
- 三者对比矩阵：M-001 C06 记忆框架域×框架横评 [EXTRACTED，M-001]

# 面试 follow-up

#flashcards

三者可以组合使用吗？::可以。典型组合：mem0 作为通用事实记忆层（低成本向量检索）+ graphiti 作为实体关系推理层（高成本图谱推理，仅在需要时触发）+ letta 的 Git 版本化思想用于关键记忆的审计和回滚。但需注意避免记忆冗余和一致性问题，建议通过 agent 编排层统一管理记忆写入路由。
<!--SR:!2026-10-06,1,210-->

如何评估记忆系统的效果？::三个维度：①召回率（相关记忆是否被检索到）——mem0 可通过 threshold/top_k 调优，graphiti 可通过搜索配方调优，letta 依赖 agent 遍历策略；②准确率（检索到的记忆是否相关/正确）——mem0 的向量相似度分数可参考，graphiti 的图谱结构可验证，letta 的 Git 历史可审计；③成本（LLM 调用次数+延迟）——mem0 单次 LLM 最低，graphiti 多次 LLM 最高，letta 含在主循环中。
<!--SR:!2026-10-06,1,210-->

# 溯源
- F-C06-001 mem0（扁平向量记忆，V3 管道，28 向量库+21 LLM+15 embeddings，64,868★）
- F-C06-002 graphiti（时序知识图谱，四层节点+多层边，多阶段管道，4 图数据库后端）
- F-C06-003 letta（文件系统+Git 版本化，MemFS+memory-git.ts 61KB，完整 agent 框架 28 子目录）
- M-001 C06 记忆框架域×框架横评矩阵（12 维度对比）

# 待补
- [ ] 三者延迟/成本的量化基准测试（当前为管道设计推断，需独立实验）
- [ ] 组合使用的最佳实践（mem0+graphiti+letta 的记忆路由策略，需实际案例验证）
- [ ] letta 记忆检索效率的量化评估（文件系统遍历 vs 向量搜索的召回率/延迟对比）
