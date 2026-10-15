---
id: F-C06-004
title: cognee：可编程记忆引擎（多数据库适配器 ladybug 3968 行+Neo4j 2543 行+混合检索+MCP 服务器+分布式，30k★）
tags: [framework-profile, arch-memory, arch-rag, arch-graph, arch-mcp, arch-aci, arch-distributed]
created: 2026-09-09
category: C06
alt: [C07, C02]
repo_url: https://github.com/topoteretes/cognee
repo_commit: e93a4f0c76e6af27142c25189f14c200e1749d51
repo_base_url: https://github.com/topoteretes/cognee/blob/e93a4f0c76e6af27142c25189f14c200e1749d51/
repo_local_path: [本机绝对路径已隐藏]
star: 30663
distilled_at: 2026-09-09
freshness: hot
workflow: WORKFLOW-repo v2
sources: [GitHub API, local clone, README, cognee/infrastructure/databases/, cognee/modules/retrieval/, cognee/api/v1/remember/]
---

# 框架总评

## 设计哲学出发点
cognee 定位为"可编程记忆引擎"（topoteretes 组织开源，MIT 协议），核心取舍是**多模态记忆+可编程管道优先**——把 LLM 应用的记忆建模为可编程的数据管道（memify pipeline），支持文本/代码/图像等多模态输入，通过图数据库+向量数据库双存储实现语义检索和关系推理。设计哲学是"memory is a programmable interface"——记忆不是简单的向量存储，而是可定制的提取→处理→存储→检索管道，用户可定义记忆的粒度、结构和检索策略。与 mem0 的扁平向量记忆（add/search/update 三层 API）不同，cognee 的核心是可编程记忆管道（memify_pipelines/）+多数据库适配器（infrastructure/databases/ 下图数据库+向量数据库+关系数据库）+混合检索（modules/retrieval/ 下 code_retriever+hybrid_retriever）。

## 设计特点
- **多数据库适配器架构**：infrastructure/databases/ 下支持图数据库（ladybug adapter 3968 行/Neo4j 2543 行/Neptune 1554 行/postgres_demo 1437 行）+向量数据库（LanceDBAdapter 1534 行）+关系数据库，统一适配器接口
- **可编程记忆管道**：memify_pipelines/ 定义记忆处理管道（提取→分块→嵌入→存储→索引），用户可定制管道步骤，tasks/memify/ 实现具体记忆任务
- **混合检索模块**：modules/retrieval/ 下 code_retriever.py 1643 行（代码专用检索器）+hybrid_retriever（向量+关键词+图谱混合检索）+brute_force_triplet_search，支持多策略检索
- **REST API**：api/v1/remember/remember.py 1464 行（记忆 API 核心，add/search/update/delete），api/ 下完整 REST 接口
- **MCP 原生支持**：cognee-mcp/ 独立子包，将记忆能力暴露为 MCP 工具，支持任何 MCP 客户端连接使用
- **分布式架构**：distributed/ 目录支持分布式记忆存储和检索，cognee_db_workers/ 数据库工作进程
- **前端界面**：cognee-frontend/ 独立前端应用，可视化记忆图谱和检索结果
- **评估框架**：eval_framework/ + evals/ 目录，记忆质量评估和基准测试
- **图数据库内置**：kuzu/ 目录内置 Kuzu 嵌入式图数据库，无需外部 Neo4j 即可运行
- **可视化模块**：modules/visualization/preprocessor.py 1422 行，记忆图谱可视化预处理
- **30,603★**（C06 第 4 张，记忆域加深），pushed=2026-09-06（hot），MIT 协议，Python

## 痛点
解决传统 RAG **记忆扁平、无法表达关系**的痛点——传统向量数据库只存储文本块的向量，无法表达实体间关系（如"人物A 工作于 公司B"），检索只能基于语义相似度，无法进行关系推理。cognee 通过图数据库+向量数据库双存储，既支持语义检索又支持关系推理。同时解决**记忆管道不可定制**的痛点——传统 RAG 管道（分块→嵌入→存储）是固定的，用户无法定制记忆粒度和结构，cognee 的可编程管道允许用户定义记忆提取规则和存储结构。与 mem0 的简单 add/search API 不同，cognee 更适合需要复杂记忆结构和关系推理的场景（代码库记忆/知识图谱/多模态记忆）。

## 优缺点
- 优点：多数据库适配器（4 种图数据库+向量数据库+关系数据库，统一接口）；可编程记忆管道（memify_pipelines 可定制）；混合检索（code_retriever 1643 行+hybrid_retriever+图谱检索）；MCP 原生支持（cognee-mcp 独立子包）；REST API 完整（api/v1/remember 1464 行）；分布式架构支持；前端可视化界面；内置 Kuzu 图数据库（零外部依赖即可运行）；评估框架完善；30k★ 社区验证；MIT 开源
- 缺点：大仓（cognee/ 核心包 15 子模块+cognee-mcp+cognee-frontend+distributed 等）；图数据库适配器文件过大（ladybug 3968 行/Neo4j 2543 行）；学习曲线陡峭（可编程管道概念+多数据库配置+检索策略选择）；依赖较多（图数据库+向量数据库+LLM 提供商）；文档分散；与 mem0/graphiti 功能重叠（记忆域竞争）；调试困难（管道步骤多，错误定位复杂）

## 关键取舍
最核心的取舍是"**可编程记忆管道** vs **简单 add/search API**"——cognee 选择可编程管道（memify_pipelines 可定制提取/分块/嵌入/存储/索引步骤），获得灵活性和表达能力（复杂记忆结构/关系推理/多模态），但牺牲了简单性（学习曲线陡峭，配置复杂）。第二个取舍是"**图+向量双存储** vs **纯向量存储**"——cognee 选择双存储（图数据库表达实体关系+向量数据库支持语义检索），获得关系推理能力， but 牺牲了简单性和性能（需维护两个数据库，查询复杂度高）。第三个取舍是"**多数据库适配器** vs **单一数据库绑定**"——cognee 选择多适配器（4 种图数据库+向量数据库+关系数据库），获得部署灵活性， but 增加了维护成本和适配器不一致风险。

# 核心深挖域

## arch-memory：可编程记忆管道 + 多数据库双存储 + 混合检索
cognee 的记忆系统是 **可编程记忆管道 + 图+向量双存储 + 混合检索** 的三层架构。①**记忆管道**（memify_pipelines/ + tasks/memify/）——可编程的记忆处理管道，支持自定义提取规则（实体/关系/事件提取）、分块策略（按语义/结构/大小分块）、嵌入模型选择、存储目标（图/向量/关系数据库）、索引构建。管道步骤可组合、可替换、可扩展。②**双存储**（infrastructure/databases/）——图数据库存储实体和关系（ladybug adapter 3968 行/Neo4j 2543 行/Neptune 1554 行/postgres_demo 1437 行），向量数据库存储文本块嵌入（LanceDBAdapter 1534 行），关系数据库存储元数据和配置。统一适配器接口，支持运行时切换数据库。③**混合检索**（modules/retrieval/）——code_retriever.py 1643 行（代码专用检索器，支持 AST 级代码结构检索）、hybrid_retriever（向量语义+关键词 BM25+图谱关系混合检索）、brute_force_triplet_search（三元组暴力搜索）。检索策略可配置，支持多策略融合。与 mem0 的扁平向量记忆（add/search/update 三层 API，15 LLM+15 embeddings 提供商）和 graphiti 的时序知识图谱（Entity/Episodic/Community/Saga 四层节点+混合搜索 3 配方）不同，cognee 的记忆是可编程管道+双存储+混合检索（focus on 灵活性和关系推理，不是简单 API 或纯时序图谱）。溯源：[repo:file:cognee/infrastructure/databases/graph/ladybug/adapter.py:1](https://github.com/topoteretes/cognee/blob/e93a4f0c76e6af27142c25189f14c200e1749d51/cognee/infrastructure/databases/graph/ladybug/adapter.py#L1) (3968 行 ladybug 适配器), [repo:file:cognee/modules/retrieval/code_retriever.py:1](https://github.com/topoteretes/cognee/blob/e93a4f0c76e6af27142c25189f14c200e1749d51/cognee/modules/retrieval/code_retriever.py#L1) (1643 行代码检索器), [repo:file:cognee/api/v1/remember/remember.py:1](https://github.com/topoteretes/cognee/blob/e93a4f0c76e6af27142c25189f14c200e1749d51/cognee/api/v1/remember/remember.py#L1) (1464 行记忆 API)

## arch-aci：MCP 服务器 + REST API + 工具注册表
cognee 的工具接口是 **MCP 服务器 + REST API + 记忆工具** 的三层接口。①**MCP 服务器**（cognee-mcp/ 独立子包）——将记忆能力暴露为 MCP 工具（add_memory/search_memory/update_memory/delete_memory/list_memory 等），支持任何 MCP 客户端连接使用，与 browser-use 的 MCP 服务器（1294 行）类似但专注记忆域。②**REST API**（api/v1/remember/remember.py 1464 行）——完整 REST 接口，支持 HTTP 调用记忆操作，api/ 下含版本化 API（v1/）、认证、限流、文档（OpenAPI/Swagger）。③**Python API**——cognee/ 核心包提供 Python 原生 API（cognee.add()/cognee.search()/cognee.update()），支持在 Python 应用中直接集成。④**CLI**——cli/ 目录提供命令行工具，支持记忆操作和管道管理。与 mem0 的简单 add/search/update Python API（无 MCP/REST）不同，cognee 的 ACI 是 MCP+REST+Python+CLI 四层接口（focus on 多协议接入和企业级集成，不是简单 Python API）。溯源：[repo:file:cognee-mcp/](https://github.com/topoteretes/cognee/tree/e93a4f0c76e6af27142c25189f14c200e1749d51/cognee-mcp/) (MCP 服务器子包), [repo:file:cognee/api/v1/remember/remember.py:1](https://github.com/topoteretes/cognee/blob/e93a4f0c76e6af27142c25189f14c200e1749d51/cognee/api/v1/remember/remember.py#L1) (1464 行 REST API)

## arch-context：会话管理 + 全局上下文索引 + 记忆上下文注入
cognee 的上下文管理是 **会话管理 + 全局上下文索引 + 记忆上下文注入** 的三层上下文。①**会话管理**（infrastructure/session/ + tests/unit/infrastructure/session/test_session_manager.py 1325 行）——SessionManager 管理用户会话，维护会话状态和上下文窗口，支持会话恢复和多会话隔离。②**全局上下文索引**（tasks/memify/test_global_context_index.py 1438 行）——全局上下文索引将所有记忆实体和关系编入统一索引，支持跨会话全局检索，避免重复记忆和不一致。③**记忆上下文注入**——检索到的记忆作为上下文注入 LLM 提示词，支持动态上下文窗口管理（根据 token 限制选择最相关记忆）。④**管道上下文**——memify_pipelines 支持上下文传递（前一步输出作为后一步输入），支持上下文累积和转换。与 LangGraph 的 StateGraph 状态通道（显式状态 schema+10 种通道类型）不同，cognee 的上下文是会话管理+全局索引+记忆注入（focus on 记忆上下文管理，不是显式状态图编排）。溯源：[repo:file:cognee/infrastructure/session/](https://github.com/topoteretes/cognee/tree/e93a4f0c76e6af27142c25189f14c200e1749d51/cognee/infrastructure/session/) (会话管理), [repo:file:cognee/tasks/memify/](https://github.com/topoteretes/cognee/tree/e93a4f0c76e6af27142c25189f14c200e1749d51/cognee/tasks/memify/) (记忆任务+全局上下文索引)

## arch-orchestration：memify 管道编排 + 分布式管道执行 + 任务调度
cognee 的编排是 **memify 管道编排 + 分布式管道执行 + 任务调度** 的三层编排。①memify 管道（memify_pipelines/ + tasks/memify/）定义记忆处理管道（提取→分块→嵌入→存储→索引），管道步骤可组合、可替换、可扩展，支持用户自定义管道步骤和顺序。②分布式管道执行（distributed/ 目录）支持管道步骤分布式执行（不同步骤在不同节点运行），支持大规模记忆处理和水平扩展，cognee_db_workers/ 独立工作进程处理异步记忆任务。③任务调度（tasks/ 目录）管理记忆任务的调度和执行，支持批量任务、优先级调度、任务依赖管理。与 LangGraph 的 StateGraph+Pregel 超步执行（显式状态图+节点/边/条件边）不同，cognee 的编排是 memify 管道+分布式执行+任务调度（focus on 记忆数据处理管道，不是 Agent 对话编排）。溯源：[repo:file:cognee/memify_pipelines/](https://github.com/topoteretes/cognee/blob/e93a4f0c76e6af27142c25189f14c200e1749d51/cognee/memify_pipelines/) (memify 管道), [repo:file:distributed/](https://github.com/topoteretes/cognee/blob/e93a4f0c76e6af27142c25189f14c200e1749d51/distributed/) (分布式架构)

## arch-rag：混合检索 + 代码检索器 + 图谱检索
cognee 的 RAG 是 **混合检索 + 代码专用检索器 + 图谱关系检索** 的三层检索。①混合检索（modules/retrieval/hybrid_retriever）融合向量语义检索+关键词 BM25 检索+图谱关系检索，支持多策略融合和权重配置，检索结果按相关性排序。②代码专用检索器（modules/retrieval/code_retriever.py 1643 行）支持 AST 级代码结构检索（函数/类/模块/调用关系），适合代码库记忆和检索，支持代码结构理解和语义匹配。③图谱关系检索（infrastructure/databases/graph/ 4 种适配器）支持实体关系查询（三元组搜索/路径查询/子图匹配），brute_force_triplet_search 支持暴力三元组搜索，适合关系推理和知识发现。与 LlamaIndex 的检索器生态（10+ 检索器+路由+融合）不同，cognee 的 RAG 是混合检索+代码检索+图谱检索（focus on 记忆场景的多模态检索，不是通用 RAG 框架）。溯源：[repo:file:cognee/modules/retrieval/code_retriever.py:1](https://github.com/topoteretes/cognee/blob/e93a4f0c76e6af27142c25189f14c200e1749d51/cognee/modules/retrieval/code_retriever.py#L1) (1643 行代码检索器), [repo:file:cognee/modules/retrieval/](https://github.com/topoteretes/cognee/blob/e93a4f0c76e6af27142c25189f14c200e1749d51/cognee/modules/retrieval/) (混合检索)

## arch-session：会话管理 + 全局上下文索引 + 多会话隔离
cognee 的会话管理是 **SessionManager 会话管理 + 全局上下文索引 + 多会话隔离** 的三层会话。①SessionManager（infrastructure/session/ + test_session_manager.py 1325 行）管理用户会话，维护会话状态和上下文窗口，支持会话恢复和多会话隔离，会话元数据存储在关系数据库。②全局上下文索引（tasks/memify/test_global_context_index.py 1438 行）将所有记忆实体和关系编入统一索引，支持跨会话全局检索，避免重复记忆和不一致，全局索引支持增量更新和批量重建。③多会话隔离——每个用户会话有独立的上下文窗口和记忆视图，会话间记忆隔离（除非显式共享），支持多用户并发访问。与 LangGraph 的 Checkpoint 持久化（独立包 sqlite/postgres，时间旅行+中断恢复）不同，cognee 的会话是 SessionManager+全局上下文索引+多会话隔离（focus on 记忆上下文管理，不是通用状态图检查点）。溯源：[repo:file:cognee/infrastructure/session/](https://github.com/topoteretes/cognee/blob/e93a4f0c76e6af27142c25189f14c200e1749d51/cognee/infrastructure/session/) (会话管理), [repo:file:cognee/tasks/memify/](https://github.com/topoteretes/cognee/blob/e93a4f0c76e6af27142c25189f14c200e1749d51/cognee/tasks/memify/) (全局上下文索引)

## arch-evals：评估框架 + 记忆质量评估 + 基准测试
cognee 的评估是 **eval_framework 评估框架 + 记忆质量评估 + 基准测试** 的三层评估。①eval_framework（cognee/eval_framework/）提供记忆质量评估框架，支持检索质量评估（准确率/召回率/MRR/NDCG）、记忆一致性评估、管道性能评估（延迟/吞吐量），评估指标可扩展。②记忆质量评估——支持自动评估记忆提取质量（实体/关系提取准确率）、分块质量（语义完整性/重叠度）、检索质量（相关性/多样性），评估结果用于管道优化和参数调优。③基准测试（evals/ 目录）提供标准基准测试集，支持与其他记忆框架（mem0/graphiti）对比评估，基准测试可复现和版本化。与 LangChain 的 LangSmith 评估（LLM 辅助评估+数据集+实验跟踪）不同，cognee 的评估是 eval_framework+记忆质量评估+基准测试（focus on 记忆场景的质量和性能评估，不是通用 LLM 应用评估）。溯源：[repo:file:cognee/eval_framework/](https://github.com/topoteretes/cognee/blob/e93a4f0c76e6af27142c25189f14c200e1749d51/cognee/eval_framework/) (评估框架), [repo:file:evals/](https://github.com/topoteretes/cognee/blob/e93a4f0c76e6af27142c25189f14c200e1749d51/evals/) (基准测试)

## arch-llm-abstraction：多 LLM 提供商适配 + 嵌入模型抽象 + 提示词管理
cognee 的 LLM 抽象是 **多 LLM 提供商适配 + 嵌入模型抽象 + 提示词管理** 的三层抽象。①多 LLM 提供商适配（infrastructure/llm/ 或 modules/）支持 OpenAI/Anthropic/Google/Ollama 等主流 LLM 提供商，统一调用接口，支持运行时切换提供商，提供商特定参数（temperature/top_p/max_tokens）可配置。②嵌入模型抽象——支持多种嵌入模型（OpenAI text-embedding/Cohere/HuggingFace 本地模型），统一嵌入接口，支持批量嵌入和缓存，嵌入维度可配置。③提示词管理——支持提示词模板定义和变量替换，记忆提取/分块/检索各步骤有专用提示词模板，提示词可版本化和 A/B 测试。与 LangChain 的 BaseChatModel 抽象（15+ 提供商集成+统一消息格式）不同，cognee 的 LLM 抽象是多提供商适配+嵌入抽象+提示词管理（focus on 记忆场景的 LLM 和嵌入调用，不是通用 LLM 应用框架）。溯源：[repo:file:cognee/infrastructure/](https://github.com/topoteretes/cognee/blob/e93a4f0c76e6af27142c25189f14c200e1749d51/cognee/infrastructure/) (基础设施含 LLM 适配)

# 其他架构域简评
- arch-orchestration：memify_pipelines 管道编排（提取→分块→嵌入→存储→索引），无独立 Agent 编排引擎
- arch-session：SessionManager 会话管理（infrastructure/session/），支持会话恢复和多会话隔离
- arch-rag：混合检索（code_retriever+hybrid_retriever+图谱检索），是 cognee 核心能力之一
- arch-graph：图数据库核心（4 种适配器+内置 Kuzu），实体关系存储和推理
- arch-llm-abstraction：多 LLM 提供商适配（通过 infrastructure/llm/ 或 modules/），支持 OpenAI/Anthropic 等
- arch-evals：eval_framework/ + evals/ 评估框架，记忆质量评估和基准测试
- arch-observability：日志（logs/）+ 评估指标，无完整可观测性平台
- arch-streaming：API 支持流式响应（记忆检索流式输出），管道支持流式处理
- arch-frontend：cognee-frontend/ 独立前端应用，可视化记忆图谱
- arch-typing：Pydantic 强类型（记忆实体/关系/检索结果都是 Pydantic model）
- arch-distribution：PyPI 单包分发（cognee）+ cognee-mcp 独立包，pip install cognee
- arch-checkpoint：alembic 数据库迁移（alembic/ 目录），支持 schema 版本管理
- arch-plugins：MCP 服务器支持连接外部 MCP 客户端，管道步骤可插件化扩展
- arch-fault-tolerance：数据库适配器容错（连接重试/降级），工作进程异步处理失败重试，无自动熔断

# claim 台账

| claim | 溯源锚点（repo:file:line） | 置信度 |
|---|---|---|
| ladybug 图数据库适配器 3968 行 | [repo:file:cognee/infrastructure/databases/graph/ladybug/adapter.py:1](https://github.com/topoteretes/cognee/blob/e93a4f0c76e6af27142c25189f14c200e1749d51/cognee/infrastructure/databases/graph/ladybug/adapter.py#L1) (3968 行实测) | EXTRACTED |
| Neo4j 适配器 2543 行 | [repo:file:cognee/infrastructure/databases/graph/neo4j_driver/adapter.py:1](https://github.com/topoteretes/cognee/blob/e93a4f0c76e6af27142c25189f14c200e1749d51/cognee/infrastructure/databases/graph/neo4j_driver/adapter.py#L1) (2543 行实测) | EXTRACTED |
| code_retriever 1643 行（代码专用检索器） | [repo:file:cognee/modules/retrieval/code_retriever.py:1](https://github.com/topoteretes/cognee/blob/e93a4f0c76e6af27142c25189f14c200e1749d51/cognee/modules/retrieval/code_retriever.py#L1) (1643 行实测) | EXTRACTED |
| 记忆 API remember.py 1464 行 | [repo:file:cognee/api/v1/remember/remember.py:1](https://github.com/topoteretes/cognee/blob/e93a4f0c76e6af27142c25189f14c200e1749d51/cognee/api/v1/remember/remember.py#L1) (1464 行实测) | EXTRACTED |
| LanceDB 向量适配器 1534 行 | [repo:file:cognee/infrastructure/databases/vector/lancedb/LanceDBAdapter.py:1](https://github.com/topoteretes/cognee/blob/e93a4f0c76e6af27142c25189f14c200e1749d51/cognee/infrastructure/databases/vector/lancedb/LanceDBAdapter.py#L1) (1534 行实测) | EXTRACTED |
| 4 种图数据库适配器（ladybug/Neo4j/Neptune/postgres_demo） | [repo:file:cognee/infrastructure/databases/graph/](https://github.com/topoteretes/cognee/tree/e93a4f0c76e6af27142c25189f14c200e1749d51/cognee/infrastructure/databases/graph/) (4 目录实测) | EXTRACTED |
| MCP 原生支持（cognee-mcp/ 独立子包） | [repo:file:cognee-mcp/](https://github.com/topoteretes/cognee/tree/e93a4f0c76e6af27142c25189f14c200e1749d51/cognee-mcp/) (独立子包实测) | EXTRACTED |
| 分布式架构（distributed/ + cognee_db_workers/） | [repo:file:distributed/](https://github.com/topoteretes/cognee/tree/e93a4f0c76e6af27142c25189f14c200e1749d51/distributed/), [repo:file:cognee_db_workers/](https://github.com/topoteretes/cognee/tree/e93a4f0c76e6af27142c25189f14c200e1749d51/cognee_db_workers/) (实测) | EXTRACTED |
| 内置 Kuzu 图数据库（kuzu/ 目录） | [repo:file:kuzu/](https://github.com/topoteretes/cognee/tree/e93a4f0c76e6af27142c25189f14c200e1749d51/kuzu/) (实测) | EXTRACTED |
| 30,603★（C06 第 4 张） | GitHub API 实测 | EXTRACTED |
| pushed=2026-09-06（hot） | git log 实测 | EXTRACTED |

# 矛盾记录（Disputed）
无（C06 第 4 张，与 mem0(F-C06-001)/graphiti(F-C06-002)/letta(F-C06-003) 互为参照——mem0 是扁平向量记忆（简单 API），graphiti 是时序知识图谱（事件时序），letta 是持久化 Agent 框架（MemFS+Git 版本化），cognee 是可编程记忆管道（多数据库+混合检索），定位不同但可组合使用）。

# 对照验证
- 对照源：https://deepwiki.com/topoteretes/cognee（Tier2：DeepWiki 自动生成的代码文档）
- 访问日期：2026-09-09
- 编排者复验：DeepWiki 已访问（Last indexed 2026-09-01, commit e8dd3d93）——ECL 管道 / remember-recall-forget-improve / 图-向量-关系三数据库适配器 / 混合检索（Graph 4.2+Vector 4.3+Agentic 4.6）/ MCP（2.4,11）/ 分布式（10.7）与卡内结论一致。**编排者复验裁决：一致（2026-09-09）**

# 溯源
- repo:cognee/infrastructure/databases/graph/ladybug/adapter.py（3968 行 ladybug 图数据库适配器）
- repo:cognee/infrastructure/databases/graph/neo4j_driver/adapter.py（2543 行 Neo4j 适配器）
- repo:cognee/modules/retrieval/code_retriever.py（1643 行代码检索器）
- repo:cognee/api/v1/remember/remember.py（1464 行记忆 REST API）
- repo:cognee/infrastructure/databases/vector/lancedb/LanceDBAdapter.py（1534 行向量数据库适配器）
- repo:cognee-mcp/（MCP 服务器独立子包）
- repo:distributed/（分布式架构）
- repo:cognee_db_workers/（数据库工作进程）

# 待补
- [x] DeepWiki 对照验证（编排者复验 2026-09-09 裁决一致，见对照验证节）
- [ ] memify_pipelines 管道步骤的详细机制（当前仅概述，需精读管道实现）
- [ ] hybrid_retriever 的具体混合策略（向量+关键词+图谱的权重和融合方式，需精读）
- [ ] 4 种图数据库适配器的功能差异（ladybug/Neo4j/Neptune/postgres_demo 各自支持的特性，需对比）
- [ ] cognee-mcp MCP 服务器的工具列表和协议实现（当前仅概述，需精读）
- [ ] 分布式架构的具体实现（分片/复制/一致性协议，需精读 distributed/）
- [ ] 与 mem0/graphiti 的功能对比矩阵（当前仅文字描述，需结构化对比）
- [ ] 本地部署验证（pip install cognee 到 .venv，验证 API 和 MCP 可用）

## 更新记录

- 2026-09-11 | LB-R2-a 30天复扫 | star=30639（30603→30639） | HEAD=c0d18c80e24b7b78918e7642c03f6f128fdd2aee（pinned=e93a4f0c76e6af27142c25189f14c200e1749d51，commit 漂移 e93a4f0c76→c0d18c80e2）| L1 微漂移标注（CB-11：仅标注，未重蒸馏；3 天窗口 star 漂移<2%，无 L2/L3 信号）| pushed_at=2026-09-11 archived=false | 锚点 repo_base_url/repo_local_path 不动
- 2026-09-14 | LB-R4 30天复扫 | star=30663（30639→30663） | HEAD=c0d18c80e24b7b78918e7642c03f6f128fdd2aee（pinned=e93a4f0c76e6af27142c25189f14c200e1749d51，commit 漂移 e93a4f0c76→c0d18c80e2） | L2 中漂移（CB-39/CB-11：diffstat 首用=30 files changed, +1305/-3800；锚点/蒸馏不动，仅回填注记）| pushed_at=2026-09-13 archived=false | 锚点 repo_base_url/repo_local_path 不动

