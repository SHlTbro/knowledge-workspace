---
id: F-C06-002
title: graphiti：时序知识图谱记忆层（实体-关系-社区-Saga 四层，混合搜索）
tags: [framework-profile, arch-memory, arch-context, arch-rag, arch-session, arch-orchestration, arch-evals, arch-llm-abstraction]
created: 2026-09-08
category: C06
alt: []
repo_url: https://github.com/getzep/graphiti
repo_commit: b943c9e8486cdc7fe6cb2f4cfe151ae53f0a884d
repo_base_url: https://github.com/getzep/graphiti/blob/b943c9e8486cdc7fe6cb2f4cfe151ae53f0a884d/
repo_local_path: [本机绝对路径已隐藏]
star: 30851
distilled_at: 2026-09-08
freshness: dated
workflow: WORKFLOW-repo v2
sources: []
---

# 框架总评
## 设计哲学出发点
graphiti 定位为"时序知识图谱记忆层"（temporal knowledge graph memory layer），核心取舍是把 agent 记忆建模为**带时间属性的知识图谱**而非扁平向量条目。设计哲学是"结构化记忆"——通过 LLM 从对话片段中抽取实体（EntityNode）和关系（EntityEdge），构建可推理、可溯源、有时序的记忆网络，支持社区检测（CommunityNode）和长篇事件链摘要（SagaNode）。

## 设计特点
- 四层节点体系：EntityNode（实体）+ EpisodicNode（片段/事件）+ CommunityNode（社区）+ SagaNode（长篇故事/事件链）
- 多层边体系：EntityEdge（实体关系）+ EpisodicEdge（片段关系）+ HasEpisodeEdge + NextEpisodeEdge + CommunityEdge
- 多阶段抽取管道：extract nodes → extract edges → dedupe（LLM 语义去重）→ summarize → build communities
- 混合搜索 3 配方：RRF（倒数排名融合）/ NodeDistance（中心节点距离重排序）/ CrossEncoder（交叉编码器重排序）
- 4 图数据库后端：Neo4j / FalkorDB / Kuzu / Neptune
- 多 LLM 提供商含 GLiNER2 轻量 NER 模型（无需大模型即可做实体识别）
- REST API + MCP server 双服务形态
- LLM 缓存 + token 追踪 + telemetry 可观测性

## 痛点
解决扁平向量记忆无法表达实体间关系和时序演化的痛点——mem0 类向量记忆只能检索"相关条目"，无法回答"A 和 B 是什么关系""这个关系是什么时候建立的"这类结构化推理问题。graphiti 通过知识图谱建模，支持关系推理、时序衰减、社区发现和事件链追踪。

## 优缺点
- 优点：结构化记忆支持关系推理；时序知识图谱天然支持记忆演化和衰减；社区检测自动发现实体聚类；Saga 摘要支持长篇事件链；混合搜索兼顾向量语义和图谱结构；GLiNER2 轻量 NER 降低成本
- 缺点：add_episode 是重量级多阶段 LLM 调用（建议后台顺序运行，延迟高）；依赖图数据库（Neo4j 等）运维成本；LLM 语义去重（非 hash）成本高且可能不一致；graphiti.py 单文件 73KB 过大；实体-关系抽取质量依赖 LLM 能力

## 关键取舍
最核心的取舍是"结构化知识图谱记忆" vs "扁平向量记忆"——graphiti 用多阶段 LLM 抽取构建图谱，记忆质量高、可推理，但延迟和成本远高于 mem0 的单次 LLM 调用。另一个取舍是"LLM 语义去重" vs "hash 精确去重"——graphiti 用 LLM 判断实体/关系是否重复（语义去重），能识别同义实体，但成本高且可能不一致；mem0 用 MD5 hash 去重，精确低成本但无法识别同义。第三个取舍是 OSS 库保持核心图谱能力，REST/MCP 服务和高级可观测性作为附加层，避免核心库过度膨胀。

# 核心深挖域

## arch-memory：记忆分层/检索/遗忘/巩固
graphiti 的记忆核心是**时序知识图谱**，采用四层节点体系：EntityNode（实体，如人物/组织/地点）、EpisodicNode（片段/事件，每次 add_episode 创建一个）、CommunityNode（社区，实体聚类自动发现）、SagaNode（长篇故事/事件链，连续片段通过 NEXT_EPISODE 边链接）。多层边体系：EntityEdge（实体间关系，带 valid_at/expired_at 时序属性）、EpisodicEdge（片段间关系）、HasEpisodeEdge（Saga→Episode）、NextEpisodeEdge（片段顺序链）、CommunityEdge（社区-实体归属）。遗忘机制通过**边失效**（edge invalidation）实现——当新关系与旧关系矛盾时，旧边标记 expired_at（非物理删除），保留记忆演化历史。巩固机制通过社区检测（build_communities）和 Saga 摘要（summarize_sagas）实现——实体自动聚类为社区，长篇事件链自动摘要为 Saga。溯源：[repo:file:graphiti_core/nodes.py:1](https://github.com/getzep/graphiti/blob/b943c9e8486cdc7fe6cb2f4cfe151ae53f0a884d/graphiti_core/nodes.py#L1) (EntityNode/EpisodicNode/CommunityNode/SagaNode), [repo:file:graphiti_core/edges.py:1](https://github.com/getzep/graphiti/blob/b943c9e8486cdc7fe6cb2f4cfe151ae53f0a884d/graphiti_core/edges.py#L1) (EntityEdge/EpisodicEdge/CommunityEdge), [repo:file:graphiti_core/graphiti.py:1490](https://github.com/getzep/graphiti/blob/b943c9e8486cdc7fe6cb2f4cfe151ae53f0a884d/graphiti_core/graphiti.py#L1490) (build_communities)

## arch-context：上下文窗口管理与记忆的边界
上下文管理通过 EpisodicNode（片段节点）实现——每次 add_episode 创建一个 EpisodicNode，包含 name/episode_body/source_description/reference_time/source 等字段，作为原始上下文的持久化快照。片段间通过 NextEpisodeEdge 链接形成时间线，通过 previous_episode_uuids 参数可指定前序片段（默认按 created_at 取最近片段）。上下文与记忆的边界：EpisodicNode 是"原始上下文"（不经过 LLM 抽取，原样存储），EntityNode/EntityEdge 是"结构化记忆"（经过 LLM 抽取）。EPISODE_WINDOW_LEN 常量控制抽取时参考的历史片段窗口长度。Saga 机制将多个相关片段组织为长篇故事链，通过 HAS_EPISODE 边关联，支持跨片段上下文聚合。溯源：[repo:file:graphiti_core/graphiti.py:980](https://github.com/getzep/graphiti/blob/b943c9e8486cdc7fe6cb2f4cfe151ae53f0a884d/graphiti_core/graphiti.py#L980) (add_episode 参数 name/episode_body/reference_time), [repo:file:graphiti_core/utils/maintenance/graph_data_operations.py:1](https://github.com/getzep/graphiti/blob/b943c9e8486cdc7fe6cb2f4cfe151ae53f0a884d/graphiti_core/utils/maintenance/graph_data_operations.py#L1) (EPISODE_WINDOW_LEN, retrieve_episodes), [repo:file:graphiti_core/nodes.py:1](https://github.com/getzep/graphiti/blob/b943c9e8486cdc7fe6cb2f4cfe151ae53f0a884d/graphiti_core/nodes.py#L1) (EpisodicNode 定义)

## arch-rag：记忆检索与 RAG 的关系
检索采用**混合搜索**（hybrid search），结合向量语义搜索和图谱结构搜索，提供 3 种预配置搜索配方：EDGE_HYBRID_SEARCH_RRF（倒数排名融合 Reciprocal Rank Fusion，无中心节点时默认）、EDGE_HYBRID_SEARCH_NODE_DISTANCE（基于中心节点距离重排序，有 center_node_uuid 时）、COMBINED_HYBRID_SEARCH_CROSS_ENCODER（组合混合搜索+交叉编码器重排序，高级 search_() 方法默认）。search() 基础方法返回 list[EntityEdge]，默认 num_results=10（DEFAULT_SEARCH_LIMIT），使用当前日期时间作为时序相关性参考点。search_() 高级方法支持 bfs_origin_node_uuids（BFS 广度优先搜索原点）、自定义 SearchConfig、SearchFilters（按实体类型/时间范围/社区等过滤）。交叉编码器重排序使用 OpenAIRerankerClient，对初筛结果做语义精排。溯源：[repo:file:graphiti_core/graphiti.py:1527](https://github.com/getzep/graphiti/blob/b943c9e8486cdc7fe6cb2f4cfe151ae53f0a884d/graphiti_core/graphiti.py#L1527) (search 方法), [repo:file:graphiti_core/search/search_config_recipes.py:1](https://github.com/getzep/graphiti/blob/b943c9e8486cdc7fe6cb2f4cfe151ae53f0a884d/graphiti_core/search/search_config_recipes.py#L1) (3 种搜索配方定义), [repo:file:graphiti_core/search/search.py:1](https://github.com/getzep/graphiti/blob/b943c9e8486cdc7fe6cb2f4cfe151ae53f0a884d/graphiti_core/search/search.py#L1) (search 核心逻辑), [repo:file:graphiti_core/cross_encoder/openai_reranker_client.py:1](https://github.com/getzep/graphiti/blob/b943c9e8486cdc7fe6cb2f4cfe151ae53f0a884d/graphiti_core/cross_encoder/openai_reranker_client.py#L1) (交叉编码器重排序)

## arch-session：会话级与跨会话记忆
多租户隔离通过 **group_id**（图分区）实现——每个 add_episode/search 调用可指定 group_id，图数据库中不同 group_id 的节点/边物理隔离（通过命名空间 NodeNamespace/EdgeNamespace 实现）。search() 接受 group_ids: list[str]，可跨多个分区检索（@handle_multiple_group_ids 装饰器处理多 group_id 并发查询）。EpisodicNode 的 source 字段（EpisodeType）支持 message/file/api 等多种来源类型，reference_time 支持自定义时间（可用于历史数据回填）。跨会话记忆通过 group_id 持久化——同一 group_id 下的所有片段和实体关系跨会话保留，支持长期记忆。Saga 机制支持跨会话事件链追踪——saga 参数可指定 SagaNode 或 saga 名称，新片段自动加入已有 Saga。溯源：[repo:file:graphiti_core/graphiti.py:987](https://github.com/getzep/graphiti/blob/b943c9e8486cdc7fe6cb2f4cfe151ae53f0a884d/graphiti_core/graphiti.py#L987) (add_episode group_id 参数), [repo:file:graphiti_core/graphiti.py:1531](https://github.com/getzep/graphiti/blob/b943c9e8486cdc7fe6cb2f4cfe151ae53f0a884d/graphiti_core/graphiti.py#L1531) (search group_ids 参数), [repo:file:graphiti_core/namespaces/nodes.py:1](https://github.com/getzep/graphiti/blob/b943c9e8486cdc7fe6cb2f4cfe151ae53f0a884d/graphiti_core/namespaces/nodes.py#L1) (NodeNamespace), [repo:file:graphiti_core/namespaces/edges.py:1](https://github.com/getzep/graphiti/blob/b943c9e8486cdc7fe6cb2f4cfe151ae53f0a884d/graphiti_core/namespaces/edges.py#L1) (EdgeNamespace)

## arch-orchestration：记忆驱动的决策 loop
graphiti 是库形态，无 agent 主循环，核心 API 是 add_episode（写入）和 search/search_（读取），由调用方 agent 在其主循环中调用。add_episode 内部是**多阶段抽取管道**：①extract_nodes（LLM 从片段中抽取实体，支持自定义 entity_types/excluded_entity_types）→ ②extract_edges（LLM 抽取实体间关系，支持自定义 edge_types/edge_type_map）→ ③dedupe_nodes/dedupe_edges（LLM 语义去重，识别同义实体/矛盾关系）→ ④create_entity_node_embeddings/create_entity_edge_embeddings（批量嵌入）→ ⑤edge invalidation（旧关系失效标记 expired_at）→ ⑥build_communities（可选，社区检测更新）。官方文档明确建议"run this method as a background process"且"each episode is added sequentially and awaited"——多阶段 LLM 调用延迟高，必须顺序执行避免图谱状态不一致。溯源：[repo:file:graphiti_core/graphiti.py:980](https://github.com/getzep/graphiti/blob/b943c9e8486cdc7fe6cb2f4cfe151ae53f0a884d/graphiti_core/graphiti.py#L980) (add_episode), [repo:file:graphiti_core/utils/maintenance/node_operations.py:1](https://github.com/getzep/graphiti/blob/b943c9e8486cdc7fe6cb2f4cfe151ae53f0a884d/graphiti_core/utils/maintenance/node_operations.py#L1) (extract_nodes), [repo:file:graphiti_core/utils/maintenance/edge_operations.py:1](https://github.com/getzep/graphiti/blob/b943c9e8486cdc7fe6cb2f4cfe151ae53f0a884d/graphiti_core/utils/maintenance/edge_operations.py#L1) (extract_edges), [repo:file:graphiti_core/prompts/dedupe_nodes.py:1](https://github.com/getzep/graphiti/blob/b943c9e8486cdc7fe6cb2f4cfe151ae53f0a884d/graphiti_core/prompts/dedupe_nodes.py#L1) (LLM 语义去重)

## arch-evals：记忆效果评估
OSS 版评估框架较薄但有基础组件——prompts/eval.py 提供评估提示词模板，token_tracker.py 追踪 LLM 调用的 token 消耗（输入/输出/成本），telemetry/ 提供事件捕获（capture_event）用于可观测性。评估主要通过搜索结果质量（SearchResults）和 token 消耗间接衡量，无标准化记忆召回率/准确率基准。实体-关系抽取质量可通过自定义 entity_types Pydantic 模型约束（强类型抽取减少幻觉），excluded_entity_types 可排除不需要的实体类型。GLiNER2 轻量 NER 模型可作为 LLM 抽取的低成本替代/预筛选，降低评估时的 LLM 调用成本。[待补] OSS 版是否有独立的抽取准确率/搜索召回率评估脚本（tests/ 目录可能含评估测试）。溯源：[repo:file:graphiti_core/prompts/eval.py:1](https://github.com/getzep/graphiti/blob/b943c9e8486cdc7fe6cb2f4cfe151ae53f0a884d/graphiti_core/prompts/eval.py#L1) (评估提示词), [repo:file:graphiti_core/llm_client/token_tracker.py:1](https://github.com/getzep/graphiti/blob/b943c9e8486cdc7fe6cb2f4cfe151ae53f0a884d/graphiti_core/llm_client/token_tracker.py#L1) (token 追踪), [repo:file:graphiti_core/telemetry/](https://github.com/getzep/graphiti/tree/b943c9e8486cdc7fe6cb2f4cfe151ae53f0a884d/graphiti_core/telemetry/) (事件捕获), [repo:file:graphiti_core/llm_client/gliner2_client.py:1](https://github.com/getzep/graphiti/blob/b943c9e8486cdc7fe6cb2f4cfe151ae53f0a884d/graphiti_core/llm_client/gliner2_client.py#L1) (GLiNER2 轻量 NER)

## arch-llm-abstraction：记忆与 LLM 的接口
提供商无关的 LLM 抽象层——llm_client/ 目录支持 8+ LLM 提供商：OpenAI（openai_client/openai_base_client/openai_generic_client）、Anthropic（anthropic_client，18KB）、Gemini（gemini_client，20KB 最大）、Azure OpenAI、Groq、GLiNER2（gliner2_client，轻量 NER 模型，无需大模型即可实体识别）。统一接口 LLMClient.generate_response()，支持结构化输出（Pydantic 模型解析）。LLM 缓存（cache.py）对重复抽取请求做缓存，token_tracker.py 追踪每次调用的 token 消耗和成本。嵌入模型抽象（embedder/）支持 OpenAIEmbedder 等，统一接口 embed/embed_batch。交叉编码器抽象（cross_encoder/）支持 OpenAIRerankerClient 用于搜索重排序。提示词模板库（prompts/lib.py prompt_library）集中管理所有 LLM 提示词，支持 custom_extraction_instructions 自定义抽取指令。溯源：[repo:file:graphiti_core/llm_client/client.py:1](https://github.com/getzep/graphiti/blob/b943c9e8486cdc7fe6cb2f4cfe151ae53f0a884d/graphiti_core/llm_client/client.py#L1) (LLMClient 基类), [repo:file:graphiti_core/llm_client/gliner2_client.py:1](https://github.com/getzep/graphiti/blob/b943c9e8486cdc7fe6cb2f4cfe151ae53f0a884d/graphiti_core/llm_client/gliner2_client.py#L1) (GLiNER2 轻量 NER), [repo:file:graphiti_core/llm_client/cache.py:1](https://github.com/getzep/graphiti/blob/b943c9e8486cdc7fe6cb2f4cfe151ae53f0a884d/graphiti_core/llm_client/cache.py#L1) (LLM 缓存), [repo:file:graphiti_core/llm_client/token_tracker.py:1](https://github.com/getzep/graphiti/blob/b943c9e8486cdc7fe6cb2f4cfe151ae53f0a884d/graphiti_core/llm_client/token_tracker.py#L1) (token 追踪), [repo:file:graphiti_core/prompts/lib.py:1](https://github.com/getzep/graphiti/blob/b943c9e8486cdc7fe6cb2f4cfe151ae53f0a884d/graphiti_core/prompts/lib.py#L1) (prompt_library)

# 其他架构域简评
- arch-patterns：知识图谱模式（实体-关系-时序），非典型 agent 编排模式，由调用方决定集成模式
- arch-aci：工具接口为标准 Python async API + REST API（server/）+ MCP server（mcp_server/），MCP 是原生支持
- arch-security：多租户隔离通过 group_id 图分区强制，数据安全依赖底层图数据库（Neo4j 等）的认证授权
- arch-prompting：系统提示词集中在 prompts/ 目录（13 个提示词模块），支持 custom_extraction_instructions 自定义
- arch-observability：telemetry/ 事件捕获 + tracer.py 分布式追踪 + token_tracker token 消耗追踪，可观测性较完善
- arch-plan-exec：无计划-执行分离，add_episode 是线性多阶段管道（extract→dedupe→embed→invalidate）
- arch-streaming：add_episode 为异步阻塞调用（async def），无流式事件输出；search 也是异步一次性返回
- arch-code-intel：非代码框架，无代码智能模块
- arch-skill-philosophy：无 skill 分发机制，记忆层与 skill 系统解耦
- arch-workflow：无 DAG/状态机引擎，add_episode 管道是线性阶段流程（非 DAG）
- arch-typing：强类型贯穿——entity_types/edge_types 接受 Pydantic 模型定义，LLM 输出强制结构化解析
- arch-distribution：通过 PyPI 发布（graphiti-core 包），REST/MCP 服务为附加层，无插件市场
- arch-exec-backend：asyncio 异步架构，所有核心方法 async def，建议后台任务队列（Celery/FastAPI BackgroundTasks）
- arch-frontend：无独立前端，REST API 提供 Swagger 文档（/docs），MCP server 供 agent 调用
- arch-checkpoint：图数据库持久化即 checkpoint，EpisodicNode 保留原始上下文快照，支持时间点回溯
- arch-plugins：无运行时插件加载，图数据库后端通过 driver/ 目录添加新文件实现（编译时扩展）
- arch-fault-tolerance：LLM 调用失败抛出 LLMError（调用方处理 retry/fallback），图数据库操作失败抛出驱动层错误，无自动重试/熔断；FalkorDB 异步驱动在并发查询时会丢连接（官方建议本地开发用 Neo4j）

# claim 台账

| claim | 溯源锚点（repo:file:line） | 置信度 |
|---|---|---|
| 四层节点体系（Entity/Episodic/Community/Saga）+ 多层边体系 | [repo:file:graphiti_core/nodes.py:1](https://github.com/getzep/graphiti/blob/b943c9e8486cdc7fe6cb2f4cfe151ae53f0a884d/graphiti_core/nodes.py#L1), [repo:file:graphiti_core/edges.py:1](https://github.com/getzep/graphiti/blob/b943c9e8486cdc7fe6cb2f4cfe151ae53f0a884d/graphiti_core/edges.py#L1) | EXTRACTED |
| 多阶段抽取管道（extract nodes→edges→dedupe→embed→invalidate→communities） | [repo:file:graphiti_core/graphiti.py:980-1060](https://github.com/getzep/graphiti/blob/b943c9e8486cdc7fe6cb2f4cfe151ae53f0a884d/graphiti_core/graphiti.py#L980-L1060), [repo:file:graphiti_core/utils/maintenance/](https://github.com/getzep/graphiti/tree/b943c9e8486cdc7fe6cb2f4cfe151ae53f0a884d/graphiti_core/utils/maintenance/) | EXTRACTED |
| 混合搜索 3 配方（RRF/NodeDistance/CrossEncoder） | [repo:file:graphiti_core/search/search_config_recipes.py:1](https://github.com/getzep/graphiti/blob/b943c9e8486cdc7fe6cb2f4cfe151ae53f0a884d/graphiti_core/search/search_config_recipes.py#L1), [repo:file:graphiti_core/graphiti.py:1569-1571](https://github.com/getzep/graphiti/blob/b943c9e8486cdc7fe6cb2f4cfe151ae53f0a884d/graphiti_core/graphiti.py#L1569-L1571) | EXTRACTED |
| 4 图数据库后端（Neo4j/FalkorDB/Kuzu/Neptune） | [repo:file:graphiti_core/driver/](https://github.com/getzep/graphiti/tree/b943c9e8486cdc7fe6cb2f4cfe151ae53f0a884d/graphiti_core/driver/) (4 个驱动文件) | EXTRACTED |
| GLiNER2 轻量 NER 模型支持 | [repo:file:graphiti_core/llm_client/gliner2_client.py:1](https://github.com/getzep/graphiti/blob/b943c9e8486cdc7fe6cb2f4cfe151ae53f0a884d/graphiti_core/llm_client/gliner2_client.py#L1) | EXTRACTED |
| LLM 语义去重（非 hash） | [repo:file:graphiti_core/prompts/dedupe_nodes.py:1](https://github.com/getzep/graphiti/blob/b943c9e8486cdc7fe6cb2f4cfe151ae53f0a884d/graphiti_core/prompts/dedupe_nodes.py#L1), [repo:file:graphiti_core/prompts/dedupe_edges.py:1](https://github.com/getzep/graphiti/blob/b943c9e8486cdc7fe6cb2f4cfe151ae53f0a884d/graphiti_core/prompts/dedupe_edges.py#L1) | EXTRACTED |
| 边失效时序衰减（expired_at 非物理删除） | [repo:file:graphiti_core/edges.py:1](https://github.com/getzep/graphiti/blob/b943c9e8486cdc7fe6cb2f4cfe151ae53f0a884d/graphiti_core/edges.py#L1) (EntityEdge valid_at/expired_at) | EXTRACTED |
| add_episode 建议后台顺序运行 | [repo:file:graphiti_core/graphiti.py:1056-1058](https://github.com/getzep/graphiti/blob/b943c9e8486cdc7fe6cb2f4cfe151ae53f0a884d/graphiti_core/graphiti.py#L1056-L1058) (docstring) | EXTRACTED |
| REST API + MCP server 双服务 | repo:server/, repo:mcp_server/ | EXTRACTED |
| FalkorDB 并发查询丢连接（官方建议 Neo4j） | repo:README/Repomix 末尾 "Backend gotcha" | INFERRED（基于 Repomix 打包的文档内容推断） |

# 矛盾记录（Disputed）
无（与 F-C06-001 mem0 形成互补：mem0 扁平向量记忆 vs graphiti 结构化图谱记忆，非矛盾而是不同设计取舍）。

# 对照验证
- 对照源：https://deepwiki.com/getzep/graphiti（Tier2：DeepWiki 自动生成的代码文档）
- 访问日期：2026-09-08
- 不一致裁决：deepwiki 页面 HTTP 200 可访问，页面标题 "getzep/graphiti | DeepWiki"；核心设计与本地蒸馏结论一致（四层节点体系/多阶段抽取管道/混合搜索 3 配方/4 图数据库后端/GLiNER2 轻量 NER），未发现不一致。

# 溯源
- repo:graphiti_core/graphiti.py（核心类 73KB，Graphiti，add_episode/search/search_）
- repo:graphiti_core/nodes.py（39KB，四层节点定义）
- repo:graphiti_core/edges.py（34KB，多层边定义）
- repo:graphiti_core/search/（搜索模块，search_utils.py 75KB 最大）
- repo:graphiti_core/driver/（4 图数据库驱动）
- repo:graphiti_core/llm_client/（8+ LLM 提供商 + GLiNER2 + 缓存 + token 追踪）
- repo:graphiti_core/prompts/（13 个提示词模块，extract_nodes.py 30KB 最大）
- repo:graphiti_core/namespaces/（多租户命名空间）
- repo:server/（REST API，FastAPI）
- repo:mcp_server/（MCP server）
- corpus/repos/graphiti/repomix-output.md（全量 Repomix 产物，留档）
- corpus/repos/graphiti/codemap-map.md（codemap 地图 24KB）

# 待补
- [ ] arch-evals 域：OSS 版是否有独立评估脚本（tests/ 目录待确认）
- [ ] search_utils.py（75KB）核心搜索算法细节待精读
- [ ] 社区检测算法（build_communities）具体实现待精读
- [ ] Saga 摘要机制（summarize_sagas）具体实现待精读

## 更新记录

- 2026-09-11 | LB-R2-a 30天复扫 | star=30796（30682→30796） | HEAD=c64e45c111fd43ca7f5536a7f84a73f6acafd5b1（pinned=b943c9e8486cdc7fe6cb2f4cfe151ae53f0a884d，commit 漂移 b943c9e848→c64e45c111）| L1 微漂移标注（CB-11：仅标注，未重蒸馏；3 天窗口 star 漂移<2%，无 L2/L3 信号）| pushed_at=2026-09-10 archived=false | 锚点 repo_base_url/repo_local_path 不动
- 2026-09-14 | LB-R4 30天复扫 | star=30851（30796→30851） | HEAD=c035afb7990b6077331a81e98b04efcfd9bf8184（pinned=b943c9e8486cdc7fe6cb2f4cfe151ae53f0a884d，commit 漂移 b943c9e848→c035afb799） | L2 中漂移（CB-39/CB-11：diffstat 首用=26 files changed, +2181/-1145；锚点/蒸馏不动，仅回填注记）| pushed_at=2026-09-11 archived=false | 锚点 repo_base_url/repo_local_path 不动

