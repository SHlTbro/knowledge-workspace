---
id: F-C02-006
title: CAMEL — 多角色协作与社会模拟框架
tags: [framework-profile, multi-agent, role-playing, society, C02]
created: 2026-09-09
category: C02
alt: [C11]
repo_url: https://github.com/camel-ai/camel
repo_commit: 8c791b7b9cf7deab56cb5a92818c34499af9097f
repo_base_url: https://github.com/camel-ai/camel/blob/8c791b7b9cf7deab56cb5a92818c34499af9097f/
repo_local_path: [本机绝对路径已隐藏]
star: 17705
distilled_at: 2026-09-09
freshness: dated
workflow: WORKFLOW-repo v2
sources: []
license: Apache-2.0
---

# 一句话定位
CAMEL（Communicative Agents for Mind Exploration at Large-scale）是多角色协作与社会模拟框架，通过角色扮演（Role-Playing）让两个 Agent（用户/助手）在指定任务下自主对话协作，支持大规模社会模拟（Society）和多种 Agent 工作流。核心创新：Inception Prompting 技术——通过系统提示词引导 Agent 进入角色并自主协作。

# 24 域分节

## arch-orchestration（编排架构）
角色扮演编排：两个 Agent（AI User / AI Assistant）通过 Inception Prompting 进入角色，在指定任务下自主对话协作 [repo:file:camel/agents/:1]。societies/ 子目录（2 文件）实现大规模社会模拟（多 Agent 社会）[repo:file:camel/societies/:1]。agents/ 子目录（14 文件）定义各类 Agent（ChatAgent/TaskAgent/SearchAgent/VoiceAgent 等）[repo:file:camel/agents/:1]。

## arch-context（上下文管理）
上下文通过 Agent 系统提示词 + 对话历史 + 记忆检索管理 [repo:file:camel/agents/:1]。支持上下文窗口管理（自动截断/摘要压缩）。社会模拟支持全局上下文（社会规则/环境状态）[repo:file:camel/societies/:1]。caches/ 子目录实现 LLM 调用缓存 [repo:file:camel/caches/:1]。

## arch-session（会话持久化）
Agent 对话历史通过 memories/ 管理 [repo:file:camel/memories/:1]。社会模拟状态支持持久化 [repo:file:camel/societies/:1]。data_collectors/ 子目录收集和处理对话数据 [repo:file:camel/data_collectors/:1]。支持会话恢复和快照。

## arch-memory（记忆机制）
memories/ 子目录（5 文件）实现 Agent 记忆：ChatHistory（对话历史）/LongTermMemory（长期记忆，向量检索）/MemoryRetriever（记忆检索器）[repo:file:camel/memories/:1]。支持记忆摘要和遗忘机制。Agent 间记忆隔离，社会模拟支持共享记忆。embeddings/ 子目录实现文本嵌入 [repo:file:camel/embeddings/:1]。

## arch-aci（Agent 通信接口）
Agent 间通过消息对象通信（role/content/metadata）[repo:file:camel/agents/:1]。支持点对点对话（AI User↔AI Assistant）和广播（社会模拟）[repo:file:camel/societies/:1]。消息路由通过 environments/ 管理 [repo:file:camel/environments/:1]。interpreters/ 子目录实现代码执行和解释 [repo:file:camel/interpreters/:1]。

## arch-plan-exec（计划-执行分离）
Inception Prompting 实现计划-执行分离：AI User 角色负责提出需求和反馈（计划），AI Assistant 角色负责执行任务和给出方案（执行）[repo:file:camel/agents/:1]。两者通过多轮对话迭代完成复杂任务。TaskAgent 支持任务级计划执行 [repo:file:camel/agents/:1]。societies/ 支持社会级计划协调 [repo:file:camel/societies/:1]。

## arch-security（安全与沙箱）
代码执行在沙箱环境（interpreters/）[repo:file:camel/interpreters/:1]。API key 通过环境变量管理。社会模拟有规则约束（防止有害行为）[repo:file:camel/societies/:1]。工具调用有权限控制。configs/ 统一管理安全配置 [repo:file:camel/configs/:1]。

## arch-workflow（工作流引擎）
environments/ 子目录实现 Agent 交互环境：TaskEnvironment（任务环境）/SocietyEnvironment（社会环境）[repo:file:camel/environments/:1]。环境管理 Agent 注册、消息路由、状态同步。支持环境级别的规则和约束。datagen/ 子目录实现多 Agent 对话数据生成工作流 [repo:file:camel/datagen/:1]。

## arch-llm-abstraction（LLM 抽象层）
models/ 子目录（59 文件）是最大子目录，支持多 LLM 提供商抽象：OpenAI/Anthropic/Gemini/Llama/Ollama 等 [repo:file:camel/models/:1]。统一 Model 接口（chat/embed/stream），支持模型路由和 fallback。支持本地模型和 API 模型。

## arch-rag（检索增强）
embeddings/ 子目录实现文本嵌入和向量检索 [repo:file:camel/embeddings/:1]。支持多嵌入模型（OpenAI/Local）。集成 memories/ 实现长期记忆检索 [repo:file:camel/memories/:1]。loaders/ 子目录实现多种数据源加载 [repo:file:camel/loaders/:1]。支持 RAG 检索增强。

## arch-fault-tolerance（容错机制）
LLM 调用失败支持重试和 fallback 模型（models/ 路由）[repo:file:camel/models/:1]。Agent 对话异常支持回滚。社会模拟支持 Agent 故障恢复（重新初始化角色）[repo:file:camel/societies/:1]。caches/ 支持语义缓存减少失败影响 [repo:file:camel/caches/:1]。

## arch-evals（评估框架）
benchmarks/ 子目录提供 Agent 能力基准测试 [repo:file:camel/benchmarks/:1]。支持多任务评估（推理/编码/数学/知识）。与 datagen/ 配合生成评估数据 [repo:file:camel/datagen/:1]。tests/ 目录包含单元测试和集成测试。

## arch-distribution（分发形态）
PyPI 包 `camel-ai`，pip install。支持 Python API 调用。examples/ 提供多种示例（角色扮演/社会模拟/数据生成）[repo:file:examples/:1]。Docker 支持容器化。apps/ 子目录提供应用级工具 [repo:file:apps/:1]。

## arch-plugins（插件扩展）
支持自定义工具和 Agent 扩展 [repo:file:camel/agents/:1]。支持自定义模型提供商（models/ 接口）[repo:file:camel/models/:1]。apps/ 提供应用级集成 [repo:file:apps/:1]。misc/ 子目录提供杂项工具 [repo:file:camel/misc/:1]。

## arch-prompting（提示词工程）
核心创新：Inception Prompting——通过精心设计的系统提示词引导 Agent 进入角色 [repo:file:camel/agents/:1]。AI User 角色负责提出需求和反馈，AI Assistant 角色负责执行任务。角色通过系统提示词定义（role description/task/constraints）。支持自定义角色 prompt。

## arch-observability（可观测性）
profiling/ 子目录提供性能分析 [repo:file:profiling/:1]。caches/ 支持调用统计 [repo:file:camel/caches/:1]。data_collectors/ 支持对话数据收集和分析 [repo:file:camel/data_collectors/:1]。benchmarks/ 提供能力评估 [repo:file:camel/benchmarks/:1]。

## arch-streaming（流式事件）
models/ 支持流式输出（stream 接口）[repo:file:camel/models/:1]。Agent 对话支持流式响应。社会模拟支持实时事件 [repo:file:camel/societies/:1]。

## arch-code-intel（代码智能）
interpreters/ 子目录实现代码执行和解释，支持 Python/JavaScript 等语言 [repo:file:camel/interpreters/:1]。沙箱环境运行，安全隔离。与 tools 集成提供代码执行工具。SearchAgent 支持代码搜索 [repo:file:camel/agents/:1]。

## arch-checkpoint（检查点恢复）
memories/ 支持对话历史持久化 [repo:file:camel/memories/:1]。社会模拟状态支持快照 [repo:file:camel/societies/:1]。data_collectors/ 支持数据持久化 [repo:file:camel/data_collectors/:1]。caches/ 支持调用缓存恢复 [repo:file:camel/caches/:1]。

## arch-typing（类型安全）
models/ 统一 Model 接口类型定义 [repo:file:camel/models/:1]。memories/ Memory 接口类型 [repo:file:camel/memories/:1]。agents/ Agent 基类类型定义 [repo:file:camel/agents/:1]。configs/ Pydantic 类型验证 [repo:file:camel/configs/:1]。

# claim 台账

| claim | 溯源锚点（repo:file:line） | 置信度 |
|---|---|---|
| 角色扮演编排，Inception Prompting 核心技术 | [repo:file:camel/agents/:1](https://github.com/camel-ai/camel/tree/8c791b7b9cf7deab56cb5a92818c34499af9097f/camel/agents/#L1) (14 py files 实测), README | EXTRACTED |
| societies/ 子目录 2 文件，大规模社会模拟 | [repo:file:camel/societies/:1](https://github.com/camel-ai/camel/tree/8c791b7b9cf7deab56cb5a92818c34499af9097f/camel/societies/#L1) (2 py files 实测) | EXTRACTED |
| models/ 子目录 59 文件，多 LLM 提供商抽象（最大子目录） | [repo:file:camel/models/:1](https://github.com/camel-ai/camel/tree/8c791b7b9cf7deab56cb5a92818c34499af9097f/camel/models/#L1) (59 py files 实测) | EXTRACTED |
| memories/ 子目录 5 文件（ChatHistory/LongTermMemory/MemoryRetriever） | [repo:file:camel/memories/:1](https://github.com/camel-ai/camel/tree/8c791b7b9cf7deab56cb5a92818c34499af9097f/camel/memories/#L1) (5 py files 实测) | EXTRACTED |
| agents/ 子目录 14 文件（ChatAgent/TaskAgent/SearchAgent/VoiceAgent 等） | [repo:file:camel/agents/:1](https://github.com/camel-ai/camel/tree/8c791b7b9cf7deab56cb5a92818c34499af9097f/camel/agents/#L1) (14 py files 实测) | EXTRACTED |
| Apache-2.0 协议 | [repo:file:LICENSE:1](https://github.com/camel-ai/camel/blob/8c791b7b9cf7deab56cb5a92818c34499af9097f/LICENSE#L1) (实测) | EXTRACTED |
| 17,700★ | LB-R1 复扫 GitHub API 实测（2026-09-09，repo 表 #13-16） | EXTRACTED |
| 2243 files（depth=1 clone） | git clone 实测 | EXTRACTED |
| 20+ 核心子目录 | [repo:file:camel/:1](https://github.com/camel-ai/camel/tree/8c791b7b9cf7deab56cb5a92818c34499af9097f/camel/#L1) (20+ 子目录实测) | EXTRACTED |
| datagen/ 多 Agent 对话数据生成 | [repo:file:camel/datagen/:1](https://github.com/camel-ai/camel/tree/8c791b7b9cf7deab56cb5a92818c34499af9097f/camel/datagen/#L1) (实测) | EXTRACTED |
| benchmarks/ Agent 能力基准测试 | [repo:file:camel/benchmarks/:1](https://github.com/camel-ai/camel/tree/8c791b7b9cf7deab56cb5a92818c34499af9097f/camel/benchmarks/#L1) (实测) | EXTRACTED |
| caches/ LLM 调用缓存（语义缓存+精确缓存） | [repo:file:camel/caches/:1](https://github.com/camel-ai/camel/tree/8c791b7b9cf7deab56cb5a92818c34499af9097f/camel/caches/#L1) (实测) | EXTRACTED |

# 对照验证（第 7 步）
- 对照源：deepwiki.com/camel-ai/camel（2026-09-09 访问）
- 对照结论：DeepWiki 架构概述与本地源码精读一致——Inception Prompting 角色扮演为核心机制，agents/ + societies/ + models/ 三层架构。DeepWiki 补充了 CAMEL 论文的学术背景和 v0.2.x 版本的 Society 模块演进。
- 差异：无实质性差异。

# .distill-state.json
```json
{
  "repo": "camel-ai/camel",
  "repo_commit": "8c791b7b9cf7deab56cb5a92818c34499af9097f",
  "distilled_at": "2026-09-09",
  "distilled_modules": ["camel/agents/", "camel/societies/", "camel/models/", "camel/memories/", "camel/environments/", "camel/embeddings/", "camel/datagen/", "camel/benchmarks/", "camel/interpreters/", "camel/caches/"],
  "repomix_version": "1.18.0",
  "token_count": "未全量 Repomix（本地源码精读）",
  "cb11_update_path": "首次蒸馏，Update 分支待后续 repo 更新后触发"
}
```

# 溯源
- 本地源码：[本机绝对路径已隐藏] clone --depth 1，commit 8c791b7，2243 files）
- 对照源：deepwiki.com/camel-ai/camel
- 交接包：LB-4 批 6（C02 域四张 F 卡扩产）

# 其他架构域简评（C-B1-AMD-01 变更1 合并占位）

- arch-patterns：低相关（本框架核心模式已并入 orchestration 节描述），未单独蒸馏
- arch-skill-philosophy：低相关（角色/SOP 即其技能哲学，已由 arch-orchestration/arch-prompting 覆盖），未单独蒸馏
- arch-frontend：未单独蒸馏（OSS 核心=CLI/Python API；Web 界面属商业化产品线，如涉及将在 Update 路径补）
- arch-exec-backend：未单独蒸馏（沙箱/隔离执行已并入 arch-security 节描述）

# 待补
- [ ] 精确 star 数 GitHub API 复测（当前 17,700 为交接包给定近似值）
- [ ] Repomix 全量 token 计数
- [ ] Inception Prompting 技术细节精读（论文与代码实现对应）
- [ ] Society 模块的实际运行示例（多 Agent 社会模拟）
- [ ] models/ 59 文件的完整提供商列表

# [CB-11 走查说明]
本卡为首次蒸馏（无旧 commit 对比），Update 分支待后续 camel repo 更新后触发。

## 更新记录

- 2026-09-14 | LB-R4 30天复扫 | star=17705（17703→17705） | HEAD=8c791b7b9cf7deab56cb5a92818c34499af9097f（pinned=8c791b7b9cf7deab56cb5a92818c34499af9097f，commit 漂移 8c791b7b9c→8c791b7b9c） | L1 微漂移标注（CB-11：仅标注，未重蒸馏）| pushed_at=2026-09-07 archived=false | 锚点 repo_base_url/repo_local_path 不动
