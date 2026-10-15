---
id: F-C06-003
title: letta：有状态 agent 框架（MemFS 文件系统记忆 + Git 版本化，原 MemGPT）
tags: [framework-profile, arch-memory, arch-context, arch-rag, arch-session, arch-orchestration, arch-evals, arch-llm-abstraction]
created: 2026-09-08
category: C06
alt: []
repo_url: https://github.com/letta-ai/letta-code
repo_commit: 2f0fb7c12c6973be7d52d9c7d3bf0bf4d9120cb8
repo_base_url: https://github.com/letta-ai/letta-code/blob/2f0fb7c12c6973be7d52d9c7d3bf0bf4d9120cb8/
repo_local_path: [本机绝对路径已隐藏]
star: 24699
distilled_at: 2026-09-08
freshness: dated
workflow: WORKFLOW-repo v2
sources: []
---

# 框架总评
## 设计哲学出发点
letta（f.k.a. MemGPT）定位为"有状态 agent 框架"（stateful agents with memory that can learn and improve over time），核心取舍是把 agent 记忆建模为**可版本化的文件系统**而非向量条目或知识图谱。设计哲学源于操作系统隐喻——main context = RAM（有限上下文窗口），external memory = disk（无限文件系统），agent 通过工具调用在两者间移动数据。letta-code v0.31.13 已将记忆系统升级为 **MemFS（Memory File System）+ Git 版本化**：记忆以 Markdown 文件存储在 `~/.letta/agents/<agentId>/memory/`，整个记忆目录是 Git 仓库，支持版本历史、分支、worktree 隔离、钩子和签名。

## 设计特点
- MemFS 文件系统记忆：记忆以 Markdown/MDX 文件存储在文件系统中，agent 通过读写文件管理记忆
- Git 版本化：记忆目录是 Git 仓库，memory-git.ts（61KB）提供完整 Git 操作（commit/branch/merge/diff/log）
- Worktree 隔离：不同会话/任务用 Git worktree 隔离（memory-worktree.ts 18KB），支持并行记忆分支
- Git 钩子 + GPG 签名：记忆变更触发 pre/post 钩子，支持提交签名验证（memory-git-hooks.ts, memory-git-signing.ts）
- 基于块的记忆：标准 agent 使用 persona/human 记忆块（memory.ts），从 .mdx 模板加载
- 完整 agent 平台：28 子目录（channels/cron/mods/permissions/queue/reminders/sandbox/skills/web/websocket）
- TypeScript 实现（@letta-ai/letta-code v0.31.13），代码已从 letta-ai/letta 迁移到 letta-ai/letta-code
- 多 LLM 提供商（byok-providers.ts 24KB，支持 OpenAI/Anthropic/Gemini/Codex 等）

## 痛点
解决 agent 无状态和记忆不可追溯的痛点——LLM 上下文窗口有限，跨会话记忆需要持久化；传统向量记忆（mem0）和图谱记忆（graphiti）虽然可检索，但记忆变更不可追溯、无法回滚、无法分支实验。letta 的 MemFS + Git 设计让记忆像代码一样可版本化、可审查、可回滚、可分支，适合需要记忆可追溯性和合规性的场景。

## 优缺点
- 优点：记忆可版本化（Git 历史/回滚/分支）；文件系统记忆人类可读可编辑；worktree 隔离支持并行实验；Git 钩子支持记忆变更审计；完整 agent 平台（channels/cron/queue/sandbox/skills）；TypeScript 类型安全
- 缺点：记忆检索依赖文件系统遍历（非向量语义搜索，大规模记忆检索效率低）；Git 操作 overhead（每次记忆变更需 commit）；MemFS 目录限制（MEMORY_TREE_MAX_LINES/CHARS/CHILDREN 防止记忆树过大）；代码仓库迁移（letta-ai/letta 现为 landing page，代码在 letta-code，易混淆）；2158 files 大仓库，架构复杂

## 关键取舍
最核心的取舍是"文件系统 + Git 版本化记忆" vs "向量检索记忆" vs "知识图谱记忆"——letta 选择文件系统记忆，牺牲了语义检索效率（mem0 的向量搜索）和结构化推理（graphiti 的图谱），但获得了记忆可版本化、可追溯、可回滚、人类可读的优势。另一个取舍是"完整 agent 平台" vs "纯记忆层"——letta 不只是记忆层，而是完整的 agent 框架（有主循环、channels、cron、queue、sandbox、skills），mem0/graphiti 是纯记忆库。第三个取舍是 OSS 核心保持轻量，高级功能（Web UI、channels、cron）作为附加模块，避免核心过度膨胀。

# 核心深挖域

## arch-memory：记忆分层/检索/遗忘/巩固
letta 的记忆核心是 **MemFS（Memory File System）+ Git 版本化**，记忆以 Markdown/MDX 文件存储在 `~/.letta/agents/<agentId>/memory/` 目录（MEMORY_FS_ROOT=".letta", MEMORY_FS_AGENTS_DIR="agents", MEMORY_FS_MEMORY_DIR="memory"）。整个记忆目录是 Git 仓库，memory-git.ts（61KB）提供完整 Git 操作（commit/branch/merge/diff/log/status），记忆变更自动 commit，支持版本历史回溯和回滚。Worktree 隔离（memory-worktree.ts 18KB）允许不同会话/任务在独立 Git worktree 中操作记忆，支持并行记忆分支实验。Git 钩子（memory-git-hooks.ts 13KB）在记忆变更前后触发 pre/post 钩子，支持记忆变更审计和自动化验证；GPG 签名（memory-git-signing.ts）支持记忆提交签名验证。标准 agent（non-MemFS）使用基于块的记忆（memory.ts）：MEMORY_BLOCK_LABELS=["persona","human"]，从 .mdx 模板加载，READ_ONLY_BLOCK_LABELS 标记只读块（agent 不能修改）。遗忘机制通过目录限制实现（MEMORY_TREE_MAX_LINES/CHARS/CHILDREN_PER_DIR），防止记忆树过大。溯源：[repo:file:src/agent/memory-filesystem.ts:26](https://github.com/letta-ai/letta-code/blob/2f0fb7c12c6973be7d52d9c7d3bf0bf4d9120cb8/src/agent/memory-filesystem.ts#L26) (MEMORY_FS_ROOT), [repo:file:src/agent/memory-git.ts:1](https://github.com/letta-ai/letta-code/blob/2f0fb7c12c6973be7d52d9c7d3bf0bf4d9120cb8/src/agent/memory-git.ts#L1) (Git 版本化记忆 61KB), [repo:file:src/agent/memory-worktree.ts:1](https://github.com/letta-ai/letta-code/blob/2f0fb7c12c6973be7d52d9c7d3bf0bf4d9120cb8/src/agent/memory-worktree.ts#L1) (worktree 隔离), [repo:file:src/agent/memory.ts:16](https://github.com/letta-ai/letta-code/blob/2f0fb7c12c6973be7d52d9c7d3bf0bf4d9120cb8/src/agent/memory.ts#L16) (MEMORY_BLOCK_LABELS)

## arch-context：上下文窗口管理与记忆的边界
上下文管理通过 context.ts（5KB）和 max-context.ts（12KB）实现——context.ts 提供 getCurrentAgentId 等上下文辅助函数，max-context.ts 管理最大上下文窗口限制（modify-context-window-explicit.test.ts 测试显式上下文窗口修改）。上下文与记忆的边界遵循操作系统隐喻：main context（LLM 上下文窗口）= RAM（有限），external memory（MemFS 文件系统）= disk（无限），agent 通过工具调用在两者间移动数据。runtime-context.ts（4KB）管理运行时上下文。记忆块（persona/human）在 agent 创建时加载到系统提示中（作为上下文的一部分），MemFS 文件系统记忆在需要时通过工具调用读取（不常驻上下文）。backend/local/local-context-estimate.ts（6KB）提供本地后端上下文估算。溯源：[repo:file:src/agent/context.ts:1](https://github.com/letta-ai/letta-code/blob/2f0fb7c12c6973be7d52d9c7d3bf0bf4d9120cb8/src/agent/context.ts#L1) (上下文管理), [repo:file:src/agent/max-context.ts:1](https://github.com/letta-ai/letta-code/blob/2f0fb7c12c6973be7d52d9c7d3bf0bf4d9120cb8/src/agent/max-context.ts#L1) (最大上下文窗口), [repo:file:src/runtime-context.ts:1](https://github.com/letta-ai/letta-code/blob/2f0fb7c12c6973be7d52d9c7d3bf0bf4d9120cb8/src/runtime-context.ts#L1) (运行时上下文), [repo:file:src/agent/memory.ts:101](https://github.com/letta-ai/letta-code/blob/2f0fb7c12c6973be7d52d9c7d3bf0bf4d9120cb8/src/agent/memory.ts#L101) (getDefaultMemoryBlocks 加载到上下文)

## arch-rag：记忆检索与 RAG 的关系
letta 的记忆检索是**文件系统遍历**而非向量语义搜索——agent 通过记忆工具（read_file/list_directory/search_file_content 等）遍历 MemFS 目录树，读取 Markdown 文件内容。memory-markdown.ts（5KB）提供 Markdown 记忆格式解析，memory-scanner.ts（3KB）扫描记忆文件。目录限制（MEMORY_TREE_MAX_LINES=DIRECTORY_LIMIT_DEFAULTS.memfsTreeMaxLines, MEMORY_TREE_MAX_CHARS, MEMORY_TREE_MAX_CHILDREN_PER_DIR）防止记忆树过大导致检索效率下降。tools/impl/ 中有 search-file-content-gemini.ts（Gemini 专用文件内容搜索）和 read-many-files-gemini.ts（批量读文件），说明 LLM 提供商特定的记忆检索优化。与 mem0（向量 top_k 搜索）和 graphiti（混合搜索+图谱遍历）不同，letta 的检索是"agent 主动遍历文件系统"模式，检索质量依赖 agent 的工具调用策略而非底层搜索引擎。溯源：[repo:file:src/agent/memory-filesystem.ts:30](https://github.com/letta-ai/letta-code/blob/2f0fb7c12c6973be7d52d9c7d3bf0bf4d9120cb8/src/agent/memory-filesystem.ts#L30) (MEMORY_TREE_MAX_LINES/CHARS), [repo:file:src/agent/memory-markdown.ts:1](https://github.com/letta-ai/letta-code/blob/2f0fb7c12c6973be7d52d9c7d3bf0bf4d9120cb8/src/agent/memory-markdown.ts#L1) (Markdown 记忆格式), [repo:file:src/agent/memory-scanner.ts:1](https://github.com/letta-ai/letta-code/blob/2f0fb7c12c6973be7d52d9c7d3bf0bf4d9120cb8/src/agent/memory-scanner.ts#L1) (记忆文件扫描), [repo:file:src/tools/impl/search-file-content-gemini.ts:1](https://github.com/letta-ai/letta-code/blob/2f0fb7c12c6973be7d52d9c7d3bf0bf4d9120cb8/src/tools/impl/search-file-content-gemini.ts#L1) (文件内容搜索)

## arch-session：会话级与跨会话记忆
会话隔离通过 **agentId + Git worktree** 实现——每个 agent 有独立的记忆目录 `~/.letta/agents/<agentId>/memory/`（getMemoryFilesystemRoot(agentId)），agentId 是记忆隔离的主键。同一 agent 的不同会话/任务可通过 Git worktree 隔离（memory-worktree.ts），在独立分支中操作记忆，合并时通过 Git merge 解决冲突。跨会话记忆通过 Git 仓库持久化——agent 重启后记忆目录（Git 仓库）保留所有历史，agent 可通过 git log/diff 查看记忆变更历史，通过 git checkout 回滚到任意历史版本。channels/ 目录支持多渠道（Slack/Discord 等）接入，thread-context.ts（7KB）管理 Slack 线程上下文。reminders/ 和 cron/ 支持定时提醒和定时任务，跨会话持久化。溯源：[repo:file:src/agent/memory-filesystem.ts:43](https://github.com/letta-ai/letta-code/blob/2f0fb7c12c6973be7d52d9c7d3bf0bf4d9120cb8/src/agent/memory-filesystem.ts#L43) (getMemoryFilesystemRoot agentId 隔离), [repo:file:src/agent/memory-worktree.ts:1](https://github.com/letta-ai/letta-code/blob/2f0fb7c12c6973be7d52d9c7d3bf0bf4d9120cb8/src/agent/memory-worktree.ts#L1) (worktree 会话隔离), [repo:file:src/agent/memory-git.ts:1](https://github.com/letta-ai/letta-code/blob/2f0fb7c12c6973be7d52d9c7d3bf0bf4d9120cb8/src/agent/memory-git.ts#L1) (Git 跨会话持久化), [repo:file:src/channels/slack/thread-context.ts:1](https://github.com/letta-ai/letta-code/blob/2f0fb7c12c6973be7d52d9c7d3bf0bf4d9120cb8/src/channels/slack/thread-context.ts#L1) (多渠道会话上下文)

## arch-orchestration：记忆驱动的决策 loop
letta 是完整的 agent 框架，有主循环（agent loop）——agent 接收消息 → LLM 生成工具调用 → 执行工具（包括记忆读写工具）→ 观察结果 → 循环直到完成。记忆驱动决策体现在：agent 通过记忆工具读取 MemFS 文件系统中的历史记忆，基于记忆内容决定下一步行动；通过记忆工具写入/修改记忆文件，Git 自动 commit 版本化。subagents/ 目录支持子 agent（context-budget.ts 管理子 agent 上下文预算）。mods/ 目录支持模组扩展。sandbox/ 提供代码执行沙箱。queue/ 提供任务队列。cron/ 和 reminders/ 提供定时任务和提醒。skills/ 提供技能系统（shared-memory-skills.ts 5KB 管理共享记忆技能）。letta 的编排是"工具调用循环"模式，与 mem0/graphiti 的"纯记忆库无主循环"不同。溯源：[repo:file:src/agent/](https://github.com/letta-ai/letta-code/tree/2f0fb7c12c6973be7d52d9c7d3bf0bf4d9120cb8/src/agent/) (agent 主循环目录), [repo:file:src/agent/subagents/context-budget.ts:1](https://github.com/letta-ai/letta-code/blob/2f0fb7c12c6973be7d52d9c7d3bf0bf4d9120cb8/src/agent/subagents/context-budget.ts#L1) (子 agent 上下文预算), [repo:file:src/skills/](https://github.com/letta-ai/letta-code/tree/2f0fb7c12c6973be7d52d9c7d3bf0bf4d9120cb8/src/skills/) (技能系统), [repo:file:src/sandbox/](https://github.com/letta-ai/letta-code/tree/2f0fb7c12c6973be7d52d9c7d3bf0bf4d9120cb8/src/sandbox/) (沙箱执行), [repo:file:src/agent/shared-memory-skills.ts:1](https://github.com/letta-ai/letta-code/blob/2f0fb7c12c6973be7d52d9c7d3bf0bf4d9120cb8/src/agent/shared-memory-skills.ts#L1) (共享记忆技能)

## arch-evals：记忆效果评估
OSS 版评估框架较薄——integration-tests/ 目录包含集成测试（memory-filesystem.sync.integration.test.ts 测试记忆文件系统同步），send-message-stream-*.test.ts 测试消息流和记忆交互，modify-context-window-explicit.test.ts 测试上下文窗口修改。telemetry/ 提供事件捕获和可观测性。评估主要通过集成测试间接衡量记忆系统的正确性（文件读写、Git commit、worktree 隔离），无标准化记忆召回率/准确率基准。记忆可追溯性是 letta 的独特评估维度——Git log/diff/blame 可审计每次记忆变更，这是 mem0/graphiti 不具备的。chatgpt-usage-service.ts（30KB）追踪 LLM token 使用和成本。[待补] OSS 版是否有独立的记忆质量评估脚本（tests/ 目录待确认）。溯源：[repo:file:src/agent/memory-filesystem.sync.integration.test.ts:1](https://github.com/letta-ai/letta-code/blob/2f0fb7c12c6973be7d52d9c7d3bf0bf4d9120cb8/src/agent/memory-filesystem.sync.integration.test.ts#L1) (记忆文件系统集成测试), [repo:file:src/telemetry/](https://github.com/letta-ai/letta-code/tree/2f0fb7c12c6973be7d52d9c7d3bf0bf4d9120cb8/src/telemetry/) (可观测性), [repo:file:src/providers/chatgpt-usage-service.ts:1](https://github.com/letta-ai/letta-code/blob/2f0fb7c12c6973be7d52d9c7d3bf0bf4d9120cb8/src/providers/chatgpt-usage-service.ts#L1) (token 使用追踪), [repo:file:src/agent/memory-git.ts:1](https://github.com/letta-ai/letta-code/blob/2f0fb7c12c6973be7d52d9c7d3bf0bf4d9120cb8/src/agent/memory-git.ts#L1) (Git 可追溯性评估维度)

## arch-llm-abstraction：记忆与 LLM 的接口
多 LLM 提供商抽象——providers/ 目录支持 BYOK（Bring Your Own Key）多提供商：byok-providers.ts（24KB，提供商配置管理）、openai-codex-provider.ts（OpenAI Codex 提供商）、connect-provider-service.ts（11KB，提供商连接服务）、chatgpt-usage-service.ts（30KB，ChatGPT 使用追踪）。LLM 调用通过统一的 provider 接口，支持 OpenAI/Anthropic/Gemini/Codex 等。记忆与 LLM 的接口体现在：记忆块（persona/human）在 agent 创建时加载到系统提示中（getDefaultMemoryBlocks → CreateBlock[]），作为 LLM 上下文的一部分；MemFS 文件系统记忆通过工具调用读取，LLM 决定何时读取/写入记忆文件。prompt-assets/（MEMORY_PROMPTS）集中管理记忆相关提示词模板。tools/impl/ 中有 Gemini 专用的记忆检索工具（search-file-content-gemini.ts, read-many-files-gemini.ts, run-shell-command-gemini.ts），说明 LLM 提供商特定的工具适配。溯源：[repo:file:src/providers/byok-providers.ts:1](https://github.com/letta-ai/letta-code/blob/2f0fb7c12c6973be7d52d9c7d3bf0bf4d9120cb8/src/providers/byok-providers.ts#L1) (多提供商抽象 24KB), [repo:file:src/providers/openai-codex-provider.ts:1](https://github.com/letta-ai/letta-code/blob/2f0fb7c12c6973be7d52d9c7d3bf0bf4d9120cb8/src/providers/openai-codex-provider.ts#L1) (Codex 提供商), [repo:file:src/agent/memory.ts:101](https://github.com/letta-ai/letta-code/blob/2f0fb7c12c6973be7d52d9c7d3bf0bf4d9120cb8/src/agent/memory.ts#L101) (getDefaultMemoryBlocks 加载到 LLM 上下文), [repo:file:src/tools/impl/search-file-content-gemini.ts:1](https://github.com/letta-ai/letta-code/blob/2f0fb7c12c6973be7d52d9c7d3bf0bf4d9120cb8/src/tools/impl/search-file-content-gemini.ts#L1) (Gemini 专用记忆检索)

# 其他架构域简评
- arch-patterns：操作系统隐喻模式（RAM/disk 分页）+ 工具调用循环模式，非典型编排模式
- arch-aci：工具接口为标准工具调用（function calling），记忆读写通过工具实现；MCP 支持（mcp 相关目录）
- arch-security：Git GPG 签名验证记忆提交真实性；sandbox/ 隔离代码执行；permissions/ 权限管理；记忆目录文件系统权限
- arch-prompting：系统提示词集中在 agent/prompts/（.mdx 模板），记忆块从模板加载，支持自定义 persona/human
- arch-observability：telemetry/ 事件捕获 + chatgpt-usage-service token 追踪 + Git log 记忆变更审计，可观测性较完善
- arch-plan-exec：无显式计划-执行分离，agent 循环是"LLM 决策→工具执行→观察"的单循环
- arch-streaming：send-message-stream-* 支持流式消息输出（streaming），websocket/ 支持实时通信
- arch-code-intel：lsp/ 目录支持语言服务器协议（代码智能），是 letta 作为编码 agent 的特色
- arch-skill-philosophy：skills/ 目录提供技能系统，shared-memory-skills.ts 管理共享记忆技能，技能通过系统提醒注入（LET-7353 移除了 per-project skills 块）
- arch-workflow：无 DAG/状态机引擎，cron/ + queue/ + reminders/ 提供定时和异步任务编排
- arch-typing：TypeScript 强类型贯穿（@letta-ai/letta-client 类型定义），Pydantic 等价为 Zod/TS 接口
- arch-distribution：npm 发布（@letta-ai/letta-code），支持 npm install -g 全局安装，无插件市场
- arch-exec-backend：Node.js 运行时，backend/ 支持 local/dev/api 三种后端，sandbox/ 隔离代码执行
- arch-frontend：web/ 目录提供 Web UI，cli/ 提供命令行界面（交互式终端 UI），channels/ 支持多渠道接入
- arch-checkpoint：Git 仓库即 checkpoint，每次记忆变更自动 commit，支持任意历史版本回滚
- arch-plugins：mods/ 目录支持模组扩展，hooks/ 支持钩子系统，无运行时插件市场
- arch-fault-tolerance：Git 版本化支持记忆回滚（误操作可恢复）；sandbox/ 隔离代码执行故障；queue/ 支持任务重试；无自动熔断机制

# claim 台账

| claim | 溯源锚点（repo:file:line） | 置信度 |
|---|---|---|
| MemFS 文件系统记忆（~/.letta/agents/<id>/memory/） | [repo:file:src/agent/memory-filesystem.ts:26-53](https://github.com/letta-ai/letta-code/blob/2f0fb7c12c6973be7d52d9c7d3bf0bf4d9120cb8/src/agent/memory-filesystem.ts#L26-L53) | EXTRACTED |
| Git 版本化记忆（memory-git.ts 61KB，commit/branch/merge/diff） | [repo:file:src/agent/memory-git.ts:1](https://github.com/letta-ai/letta-code/blob/2f0fb7c12c6973be7d52d9c7d3bf0bf4d9120cb8/src/agent/memory-git.ts#L1) | EXTRACTED |
| Worktree 隔离（memory-worktree.ts 18KB） | [repo:file:src/agent/memory-worktree.ts:1](https://github.com/letta-ai/letta-code/blob/2f0fb7c12c6973be7d52d9c7d3bf0bf4d9120cb8/src/agent/memory-worktree.ts#L1) | EXTRACTED |
| Git 钩子 + GPG 签名 | [repo:file:src/agent/memory-git-hooks.ts:1](https://github.com/letta-ai/letta-code/blob/2f0fb7c12c6973be7d52d9c7d3bf0bf4d9120cb8/src/agent/memory-git-hooks.ts#L1), [repo:file:src/agent/memory-git-signing.ts:1](https://github.com/letta-ai/letta-code/blob/2f0fb7c12c6973be7d52d9c7d3bf0bf4d9120cb8/src/agent/memory-git-signing.ts#L1) | EXTRACTED |
| 基于块的记忆（persona/human 块，.mdx 模板） | [repo:file:src/agent/memory.ts:16](https://github.com/letta-ai/letta-code/blob/2f0fb7c12c6973be7d52d9c7d3bf0bf4d9120cb8/src/agent/memory.ts#L16), :101 | EXTRACTED |
| 代码已从 letta-ai/letta 迁移到 letta-ai/letta-code | repo:README.md (letta-ai/letta landing page), repo:package.json (@letta-ai/letta-code 0.31.13) | EXTRACTED |
| 完整 agent 平台（28 子目录） | repo:src/ (28 子目录) | EXTRACTED |
| 多 LLM 提供商 BYOK（byok-providers.ts 24KB） | [repo:file:src/providers/byok-providers.ts:1](https://github.com/letta-ai/letta-code/blob/2f0fb7c12c6973be7d52d9c7d3bf0bf4d9120cb8/src/providers/byok-providers.ts#L1) | EXTRACTED |
| 记忆检索是文件系统遍历（非向量搜索） | [repo:file:src/agent/memory-filesystem.ts:30](https://github.com/letta-ai/letta-code/blob/2f0fb7c12c6973be7d52d9c7d3bf0bf4d9120cb8/src/agent/memory-filesystem.ts#L30) (目录限制), [repo:file:src/tools/impl/search-file-content-gemini.ts:1](https://github.com/letta-ai/letta-code/blob/2f0fb7c12c6973be7d52d9c7d3bf0bf4d9120cb8/src/tools/impl/search-file-content-gemini.ts#L1) | INFERRED（基于目录结构和工具命名推断，非显式文档声明） |
| 操作系统隐喻（RAM/disk 分页） | README/设计文档描述 | UNVERIFIED（MemGPT 时代设计哲学，letta-code v0.31 可能已演进） |

# 矛盾记录（Disputed）
无（与 F-C06-001 mem0（向量记忆）、F-C06-002 graphiti（图谱记忆）形成三种记忆范式对比：文件系统+Git vs 向量检索 vs 知识图谱，非矛盾而是不同设计取舍）。

# 对照验证
- 对照源：https://deepwiki.com/letta-ai/letta-code（Tier2：DeepWiki 自动生成的代码文档）
- 访问日期：2026-09-08
- 不一致裁决：deepwiki 页面 HTTP 200 可访问，页面标题 "letta-ai/letta-code | DeepWiki"；核心设计与本地蒸馏结论一致（MemFS 文件系统记忆 + Git 版本化 + worktree 隔离 + 基于块的记忆 persona/human + 完整 agent 平台 28 子目录），未发现不一致。代码仓库迁移（letta-ai/letta → letta-ai/letta-code）与 README 声明一致。

# 溯源
- repo:src/agent/memory-git.ts（61KB，Git 版本化记忆核心）
- repo:src/agent/memory-filesystem.ts（21KB，MemFS 文件系统记忆）
- repo:src/agent/memory-worktree.ts（18KB，worktree 隔离）
- repo:src/agent/memory.ts（3KB，基于块的记忆 persona/human）
- repo:src/agent/memory-git-hooks.ts（13KB，Git 钩子）
- repo:src/agent/context.ts（5KB，上下文管理）
- repo:src/agent/max-context.ts（12KB，最大上下文窗口）
- repo:src/providers/byok-providers.ts（24KB，多 LLM 提供商）
- repo:src/（28 子目录，完整 agent 平台）
- repo:package.json（@letta-ai/letta-code 0.31.13）
- letta-ai/letta README.md（代码迁移声明：代码在 letta-ai/letta-code）
- corpus/repos/letta/repomix-output.md（全量 Repomix 产物，留档）
- corpus/repos/letta/codemap-map.md（codemap 地图）

# 待补
- [ ] arch-evals 域：OSS 版是否有独立记忆质量评估脚本
- [ ] agent 主循环具体实现（send-message-stream 核心逻辑待精读）
- [ ] MemFS 记忆工具的完整列表（read_file/write_file/list_directory 等）
- [ ] memory-git.ts（61KB）核心 Git 操作细节待精读

## 更新记录

- 2026-09-11 | LB-R2-a 30天复扫 | star=24699（24647→24699） | HEAD=aa3e294d006b448e36a0be44afed440f47923aa8（pinned=2f0fb7c12c6973be7d52d9c7d3bf0bf4d9120cb8，commit 漂移 2f0fb7c12c→aa3e294d00）| L1 微漂移标注（CB-11：仅标注，未重蒸馏；3 天窗口 star 漂移<2%，无 L2/L3 信号）| pushed_at= archived=false | 锚点 repo_base_url/repo_local_path 不动
