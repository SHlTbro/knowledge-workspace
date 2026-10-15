---
id: M-001
title: C06 记忆框架域×框架横评：mem0 vs graphiti vs letta
tags: [arch-memory, arch-context, arch-rag, arch-session, matrix]
created: 2026-09-08
category: C06
domains: [arch-memory, arch-context, arch-rag, arch-session, arch-orchestration, arch-evals, arch-llm-abstraction]
columns: 3
sources: [F-C06-001, F-C06-002, F-C06-003]
---

# 矩阵定位
对比三种 agent 记忆范式：扁平向量检索（mem0）、时序知识图谱（graphiti）、文件系统+Git 版本化（letta），解决面试高频问题"agent 记忆怎么选"。中立性声明：格内结论全部回溯到三张 F 卡的代码级溯源（repo:file:line），厂商自证数字仅作参考标注 [UNVERIFIED]，不入正文论断。

# 矩阵本体

| 维度/子维度       | mem0（F-C06-001）                                                                                                                                  | graphiti（F-C06-002）                                                                                                                                                     | letta（F-C06-003）                                                                                                                                |
| ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| **存储范式**     | [EXTRACTED] 扁平向量记忆（文本片段+嵌入向量，存向量数据库）[F-C06-001 §arch-memory]                                                                                     | [EXTRACTED] 时序知识图谱（四层节点 Entity/Episodic/Community/Saga+多层边，存图数据库）[F-C06-002 §arch-memory]                                                                               | [EXTRACTED] 文件系统+Git 版本化（Markdown/MDX 文件存 `~/.letta/agents/<id>/memory/`，Git 自动 commit）[F-C06-003 §arch-memory]                                 |
| **写入管道**     | [EXTRACTED] V3 分阶段批量管道 5 阶段：context→retrieval→LLM extraction→batch embed→hash dedup；**单次 LLM 调用**完成提取+ADD/UPDATE/DELETE [F-C06-001 §arch-memory] | [EXTRACTED] 多阶段抽取管道 6 阶段：extract_nodes→extract_edges→dedupe→embed→edge invalidation→build_communities；**多次 LLM 调用**（抽取+去重分离），官方建议后台顺序运行 [F-C06-002 §arch-orchestration] | [EXTRACTED] 工具调用写入：agent 通过 write_file/edit_file 操作 MemFS，Git 钩子自动 commit；无独立记忆提取管道 [F-C06-003 §arch-orchestration]                             |
| **检索方式**     | [EXTRACTED] 向量搜索为主+BM25 为辅：vector_store.search(top_k=10)+lemmatize_for_bm25；支持 threshold/rerank/explain [F-C06-001 §arch-rag]                    | [EXTRACTED] 混合搜索（向量+图谱结构）3 配方：RRF 倒数排名融合/NodeDistance 中心节点距离/CrossEncoder 交叉编码器；支持 BFS 广度优先 [F-C06-002 §arch-rag]                                                       | [EXTRACTED] 文件系统遍历（非向量语义搜索）：agent 通过 read_file/list_directory/search_file_content 主动遍历目录树；检索质量依赖 agent 工具调用策略 [F-C06-003 §arch-rag]             |
| **去重机制**     | [EXTRACTED] MD5 hash 精确去重：现有记忆+批次内双重去重，精确低成本但无法识别同义实体 [F-C06-001 §arch-memory]                                                                   | [EXTRACTED] LLM 语义去重：dedupe_nodes/dedupe_edges 用 LLM 判断实体/关系是否重复，能识别同义但成本高且可能不一致 [F-C06-002 §arch-orchestration]                                                        | [EXTRACTED] 无显式去重：Git 版本化保留所有历史变更，重复记忆由 agent 自行判断处理 [F-C06-003 §arch-memory]                                                                   |
| **遗忘/时效**    | [EXTRACTED] expiration_date 字段：过期记忆从 search/get_all 隐藏（show_expired=True 才显示），非物理删除 [F-C06-001 §arch-memory]                                     | [EXTRACTED] 边失效（edge invalidation）：新关系与旧关系矛盾时旧边标记 expired_at，非物理删除，保留记忆演化历史 [F-C06-002 §arch-memory]                                                                    | [EXTRACTED] 目录限制：MEMORY_TREE_MAX_LINES/CHARS/CHILDREN_PER_DIR 防止记忆树过大；无显式过期机制，Git 历史永久保留 [F-C06-003 §arch-memory]                               |
| **版本化能力**    | [EXTRACTED] 无显式版本化：记忆更新覆盖旧值，ADD/UPDATE/DELETE 事件记录但无版本回滚 [F-C06-001 §arch-memory]                                                                | [EXTRACTED] 时序属性版本化：EntityEdge 带 valid_at/expired_at，保留历史边但无完整版本树/回滚 [F-C06-002 §arch-memory]                                                                           | [EXTRACTED] Git 完整版本化：memory-git.ts（61KB）提供 commit/branch/merge/diff/log/status，支持任意历史版本回滚；Worktree 隔离支持并行记忆分支实验 [F-C06-003 §arch-memory]       |
| **会话隔离**     | [EXTRACTED] 三级隔离：user_id/agent_id/run_id；search/get_all 拒绝顶层 entity params 必须用 filters，防止跨会话泄露 [F-C06-001 §arch-session]                         | [EXTRACTED] group_id 图分区：NodeNamespace/EdgeNamespace 物理隔离；search 支持 group_ids 跨多分区检索 [F-C06-002 §arch-session]                                                          | [EXTRACTED] agentId+Git worktree：每个 agent 独立记忆目录；同 agent 不同会话/任务通过 Git worktree 隔离，合并时 Git merge 解决冲突 [F-C06-003 §arch-session]                 |
| **LLM 调用成本** | [EXTRACTED] 单次 LLM 调用/写入：ADDITIVE_EXTRACTION_PROMPT+response_format=json_object，成本低延迟低 [F-C06-001 §arch-orchestration]                           | [EXTRACTED] 多次 LLM 调用/写入：extract_nodes+extract_edges+dedupe_nodes+dedupe_edges，成本高延迟高，官方建议后台任务队列 [F-C06-002 §arch-orchestration]                                        | [EXTRACTED] 无独立记忆提取 LLM 调用：记忆读写通过 agent 主循环工具调用，LLM 调用成本已含在 agent 主循环中 [F-C06-003 §arch-orchestration]                                          |
| **形态定位**     | [EXTRACTED] 纯记忆库/平台：无 agent 主循环，核心 API add/search/get_all/update/delete/history，库+平台双形态 [F-C06-001 §arch-orchestration]                          | [EXTRACTED] 纯记忆库：无 agent 主循环，核心 API add_episode/search/search_；REST API（FastAPI）+MCP server 双服务附加层 [F-C06-002 §arch-orchestration]                                      | [EXTRACTED] 完整 agent 框架：有主循环+channels（Slack/Discord）+cron+queue+sandbox+skills+lsp，28 子目录；记忆是框架内置能力而非独立库 [F-C06-003 §arch-orchestration]        |
| **提供商生态**    | [EXTRACTED] 28 向量数据库+21 LLM 提供商+15 嵌入模型，提供商无关三层抽象 [F-C06-001 §arch-llm-abstraction]                                                              | [EXTRACTED] 4 图数据库后端（Neo4j/FalkorDB/Kuzu/Neptune）+8+ LLM 提供商+GLiNER2 轻量 NER [F-C06-002 §arch-llm-abstraction]                                                           | [EXTRACTED] 多 LLM BYOK（byok-providers.ts 24KB）+Node.js 生态+Gemini 专用记忆检索工具适配 [F-C06-003 §arch-llm-abstraction]                                   |
| **评估框架**     | [EXTRACTED] OSS 版较薄：evaluation/ 目录基本为空，评估主要在平台版；可通过 threshold/top_k 调优但无标准化基准 [F-C06-001 §arch-evals]                                            | [EXTRACTED] OSS 版有基础组件：prompts/eval.py+token_tracker+telemetry 事件捕获；无标准化召回率/准确率基准 [F-C06-002 §arch-evals]                                                               | [EXTRACTED] OSS 版有集成测试：memory-filesystem.sync.integration.test+send-message-stream 测试；Git log/diff/blame 可审计记忆变更（独特评估维度）[F-C06-003 §arch-evals] |

# 数据口径
- EXTRACTED = 代码/官方文档级溯源（repo:file:line 或 F 卡分节引用），格内 [EXTRACTED] 角标+F 卡 ID 回溯
- 实验数字 = 复现脚本随卡入库（本矩阵无独立实验，全部数字来自 F 卡已验证溯源）
- 厂商数字 = UNVERIFIED 引用并注明口径偏见（禁直接搬入正文论断）

# 一页口径（30 秒版结论，面试直接背）
mem0=扁平向量记忆，单次 LLM 调用低成本，适合通用 agent 记忆层；graphiti=时序知识图谱，多阶段 LLM 抽取高成本高推理力，适合需要实体关系推理和时序追溯的场景；letta=文件系统+Git 版本化，记忆可回滚可审计，适合已用 letta 完整 agent 框架且需要记忆版本控制的场景。三者非替代关系而是记忆范式选择：向量检索快/图谱可推理/Git 可回滚。

# 溯源
- F-C06-001 mem0（扁平向量记忆，V3 分阶段批量管道，28 向量库+21 LLM+15 embeddings）
- F-C06-002 graphiti（时序知识图谱，四层节点+多层边，多阶段抽取管道，4 图数据库后端）
- F-C06-003 letta（文件系统+Git 版本化记忆，MemFS+memory-git.ts 61KB，完整 agent 框架 28 子目录）
- 格内结论全部回溯到上述三卡 §arch-memory/§arch-rag/§arch-orchestration/§arch-session/§arch-llm-abstraction/§arch-evals 分节

# 待补
- [ ] graphiti/letta 的精确 star 数对比（需从 F 卡 frontmatter 提取补全）
- [ ] 三者延迟/成本的量化对比（需独立基准测试，当前为管道设计推断）
- [ ] letta 记忆检索效率的量化评估（文件系统遍历 vs 向量搜索的召回率/延迟对比）
- [ ] graphiti GLiNER2 轻量 NER 与 LLM 抽取的成本/准确率对比（需独立实验）
