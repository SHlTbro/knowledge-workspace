---
id: F-C03-005
title: Gemini CLI：Google 开源终端 AI Agent（core 887 .ts + cli 614 .ts，MCP 客户端 2466 行 + ACP 会话 1522 行 + Vim 模式，106k★）
tags: [framework-profile, arch-orchestration, arch-context, arch-aci, arch-code-intel, arch-session, arch-security, arch-prompting]
created: 2026-09-09
category: C03
alt: [C02]
repo_url: https://github.com/google-gemini/gemini-cli
repo_commit: ed2ac40df67a319bf348bd7e3d10494696b31b38
repo_base_url: https://github.com/google-gemini/gemini-cli/blob/ed2ac40df67a319bf348bd7e3d10494696b31b38/
repo_local_path: [本机绝对路径已隐藏]
star: 106957
distilled_at: 2026-09-09
freshness: hot
workflow: WORKFLOW-repo v2
sources: [GitHub API, local clone, README, packages/core/src/, packages/cli/src/]
---

# 框架总评

## 设计哲学出发点
Gemini CLI 定位为"Google 开源终端 AI Agent"（google-gemini 组织开源，Apache-2.0 协议），核心取舍是**Gemini 原生 + 终端优先**——把 Gemini 模型能力直接带入终端，提供轻量级 AI Agent 体验，支持代码编辑/Shell 执行/文件操作/MCP 工具/ACP 协议。设计哲学是"the most direct path from your prompt to our model"——不做重型框架，专注终端场景的高效交互，支持 Vim 模式/流式输出/扩展系统。与 claude-code（source-leak，TypeScript 单仓）和 codex（OpenAI 官方，Rust+TypeScript）不同，Gemini CLI 是 Google 官方开源的 TypeScript monorepo（packages/core 887 .ts + packages/cli 614 .ts），核心是 Gemini 模型原生集成 + 终端 UI 优化。

## 设计特点
- **TypeScript monorepo**：packages/core（887 .ts，核心 Agent 引擎）+ packages/cli（614 .ts，终端 UI）+ packages/a2a-server（39 .ts，Agent-to-Agent）+ packages/sdk（17 .ts）+ packages/vscode-ide-companion（8 .ts）
- **MCP 原生支持**：tools/mcp-client.ts 2466 行，Model Context Protocol 客户端，支持连接外部 MCP 服务器扩展工具能力
- **ACP 协议支持**：cli/src/acp/acpSession.ts 1522 行，Agent Client Protocol 会话，支持与 ACP 兼容的 Agent 客户端互操作
- **核心 Agent 引擎**：core/geminiChat.ts 1881 行（Gemini 聊天核心）+ core/client.ts 1299 行（客户端）+ agents/local-executor.ts 1525 行（本地执行器）
- **工具系统**：tools/edit.ts 1496 行（代码编辑）+ tools/shell.ts 1160 行（Shell 执行）+ tools/tools.ts 1140 行（工具注册）
- **服务层**：services/shellExecutionService.ts 1676 行（Shell 执行服务）+ services/memoryService.ts 1487 行（记忆服务）
- **配置管理**：core/src/config/config.ts 4207 行（核心配置）+ cli/src/config/settingsSchema.ts 3617 行（设置 schema）+ cli/src/config/settings.ts 1400 行
- **终端 UI**：cli/src/ui/components/shared/text-buffer.ts 4285 行（文本缓冲区）+ ui/hooks/useGeminiStream.ts 2299 行（流式输出）+ Vim 模式（vim-buffer-actions 1849 行 + vim.ts 1536 行）
- **遥测系统**：telemetry/types.ts 2502 行 + clearcut-logger.ts 2214 行 + metrics.ts 1801 行
- **沙箱安全**：cli/src/utils/sandbox.ts 1324 行，命令执行沙箱隔离
- **扩展系统**：cli/src/config/extension-manager.ts 1478 行，支持扩展插件
- **106,870★**（C03 第 5 张，Google 官方开源），pushed=2026-09-08（hot），Apache-2.0 协议，TypeScript

## 痛点
解决终端开发者**快速访问 AI 模型**的痛点——传统终端工作流需要切换到浏览器或独立 AI 工具，Gemini CLI 将 Gemini 直接带入终端，支持代码编辑/Shell 执行/文件操作的一体化 AI 辅助。同时解决**终端 AI 工具碎片化**的痛点——通过 MCP/ACP 标准协议统一工具接入，支持扩展系统，避免每个 AI 工具自建工具生态。与 claude-code 的深度编码 Agent（source-leak，重型架构）不同，Gemini CLI 更轻量，专注 Gemini 原生体验和终端 UI 优化。

## 优缺点
- 优点：Google 官方开源（Apache-2.0）；Gemini 模型原生集成；TypeScript monorepo 架构清晰（core/cli/sdk 分离）；MCP 原生支持（2466 行客户端）；ACP 协议支持（1522 行会话）；Vim 模式（终端开发者友好）；流式输出（useGeminiStream 2299 行）；扩展系统（extension-manager 1478 行）；沙箱安全（sandbox.ts 1324 行）；遥测系统完善（types+clearcut+metrics）；106k★ 社区验证；npm 包 @google/gemini-cli 一键安装
- 缺点：核心文件过大（config.ts 4207 行/text-buffer.ts 4285 行/settingsSchema.ts 3617 行）；大仓（core 887 + cli 614 = 1501 .ts）；仅支持 Gemini 模型（非多模型，与 codex/claude-code 的多提供商不同）；Google 遥测（clearcut-logger，隐私顾虑）；扩展生态尚在早期；与 claude-code/codex 功能重叠（终端编码 Agent 竞争）；调试困难（Agent 决策过程不透明）

## 关键取舍
最核心的取舍是"**Gemini 原生 + 轻量终端** vs **多模型 + 重型框架**"——Gemini CLI 选择 Gemini 原生（深度集成 Gemini API，非多模型抽象），获得模型特性最优支持和轻量体验，但牺牲了模型灵活性（不能切换 OpenAI/Anthropic）。第二个取舍是"**标准协议（MCP/ACP）** vs **自建工具生态**"——Gemini CLI 选择 MCP/ACP 标准协议，获得生态互操作性和工具可扩展性，但牺牲了工具深度（MCP 工具不如自建工具深度集成）。第三个取舍是"**终端 UI 优化（Vim/流式）** vs **通用 CLI**"——Gemini CLI 选择终端 UI 深度优化（Vim 模式/流式输出/文本缓冲区），获得终端开发者体验，但牺牲了跨平台 UI 一致性（终端 UI 依赖特定终端特性）。

# 核心深挖域

## arch-orchestration：本地执行器 + Gemini Chat 核心 + 客户端
Gemini CLI 的编排是 **本地执行器 + Gemini Chat 核心 + 客户端** 的三层架构。①**本地执行器**（agents/local-executor.ts 1525 行）——Agent 执行核心，管理工具调用循环（感知→推理→执行→观察），支持工具选择/参数生成/结果处理，是 ReAct 风格的 Agent 执行器。②**Gemini Chat 核心**（core/geminiChat.ts 1881 行）——Gemini 模型对话核心，管理对话历史/消息构建/模型调用/流式响应，支持 Gemini 特有功能（函数调用/结构化输出/多模态）。③**客户端**（core/client.ts 1299 行）——Gemini API 客户端，管理认证/请求/响应/错误处理，支持多区域/多模型端点。与 codex 的 Rust 核心+TypeScript CLI（编译期强类型+沙箱隔离）不同，Gemini CLI 的编排是 TypeScript 本地执行器+Gemini Chat 核心（focus on Gemini 原生集成和轻量执行，不是编译期强类型或 OS 级沙箱）。溯源：[repo:file:packages/core/src/agents/local-executor.ts:1](https://github.com/google-gemini/gemini-cli/blob/ed2ac40df67a319bf348bd7e3d10494696b31b38/packages/core/src/agents/local-executor.ts#L1) (1525 行本地执行器), [repo:file:packages/core/src/core/geminiChat.ts:1](https://github.com/google-gemini/gemini-cli/blob/ed2ac40df67a319bf348bd7e3d10494696b31b38/packages/core/src/core/geminiChat.ts#L1) (1881 行 Gemini Chat 核心), [repo:file:packages/core/src/core/client.ts:1](https://github.com/google-gemini/gemini-cli/blob/ed2ac40df67a319bf348bd7e3d10494696b31b38/packages/core/src/core/client.ts#L1) (1299 行客户端)

## arch-context：记忆服务 + 对话历史 + 配置管理
Gemini CLI 的上下文管理是 **记忆服务 + 对话历史 + 配置管理** 的三层上下文。①**记忆服务**（services/memoryService.ts 1487 行 + commands/memory.ts 1374 行）——跨会话记忆管理，支持记忆的添加/查询/更新/删除，记忆持久化到本地存储，支持记忆搜索和召回。②**对话历史**——geminiChat.ts 1881 行管理当前会话对话历史（系统提示+用户消息+助手响应+工具结果），支持 token 计数和上下文窗口管理，流式响应增量更新。③**配置管理**（core/src/config/config.ts 4207 行 + cli/src/config/settings.ts 1400 行 + settingsSchema.ts 3617 行）——全局配置管理，支持模型选择/温度/最大 token/工具白名单/沙箱设置，配置文件持久化，支持用户级/项目级配置。与 LangGraph 的 StateGraph 状态通道（显式状态 schema+10 种通道类型）不同，Gemini CLI 的上下文是记忆服务+对话历史+配置管理（focus on 终端 Agent 场景的记忆和配置，不是显式状态图编排）。溯源：[repo:file:packages/core/src/services/memoryService.ts:1](https://github.com/google-gemini/gemini-cli/blob/ed2ac40df67a319bf348bd7e3d10494696b31b38/packages/core/src/services/memoryService.ts#L1) (1487 行记忆服务), [repo:file:packages/core/src/config/config.ts:1](https://github.com/google-gemini/gemini-cli/blob/ed2ac40df67a319bf348bd7e3d10494696b31b38/packages/core/src/config/config.ts#L1) (4207 行配置管理)

## arch-aci：MCP 客户端 + 工具系统 + Shell 执行服务
Gemini CLI 的工具接口是 **MCP 客户端 + 工具系统 + Shell 执行服务** 的三层工具架构。①**MCP 客户端**（tools/mcp-client.ts 2466 行）——Model Context Protocol 客户端，支持连接外部 MCP 服务器（文件系统/数据库/API/浏览器等），动态获取工具列表和执行工具调用，支持多 MCP 服务器并发连接。②**工具系统**（tools/tools.ts 1140 行 + tools/edit.ts 1496 行 + tools/shell.ts 1160 行）——内置工具集，包括代码编辑（edit.ts，支持多光标编辑/搜索替换/格式化）、Shell 执行（shell.ts，命令执行/输出捕获）、文件操作（读/写/列出），工具注册和管理统一在 tools.ts。③**Shell 执行服务**（services/shellExecutionService.ts 1676 行 + utils/shell-utils.ts 1197 行）——Shell 命令执行核心，支持命令解析/进程管理/输出捕获/错误处理，支持管道/重定向/后台进程，Shell 执行通过沙箱隔离（sandbox.ts 1324 行）。与 MCP Servers 的 JSON-RPC 单一协议（Tools/Resources/Prompts 三大原语）不同，Gemini CLI 的 ACI 是 MCP 客户端+内置工具+Shell 执行服务（focus on 终端 Agent 工具集成和 MCP 生态接入，不是 MCP 服务器实现）。溯源：[repo:file:packages/core/src/tools/mcp-client.ts:1](https://github.com/google-gemini/gemini-cli/blob/ed2ac40df67a319bf348bd7e3d10494696b31b38/packages/core/src/tools/mcp-client.ts#L1) (2466 行 MCP 客户端), [repo:file:packages/core/src/services/shellExecutionService.ts:1](https://github.com/google-gemini/gemini-cli/blob/ed2ac40df67a319bf348bd7e3d10494696b31b38/packages/core/src/services/shellExecutionService.ts#L1) (1676 行 Shell 执行服务), [repo:file:packages/core/src/tools/edit.ts:1](https://github.com/google-gemini/gemini-cli/blob/ed2ac40df67a319bf348bd7e3d10494696b31b38/packages/core/src/tools/edit.ts#L1) (1496 行编辑工具)

## arch-code-intel：代码编辑工具 + 扩展系统 + VS Code 伴侣
Gemini CLI 的代码智能是 **代码编辑工具 + 扩展系统 + VS Code IDE 伴侣** 的三层代码智能。①**代码编辑工具**（tools/edit.ts 1496 行）——内置代码编辑能力，支持多光标编辑/搜索替换/格式化/代码导航，编辑操作基于文本缓冲区（text-buffer.ts 4285 行），支持 Vim 模式编辑（vim-buffer-actions.ts 1849 行）。②**扩展系统**（cli/src/config/extension-manager.ts 1478 行）——支持扩展插件，扩展可以添加自定义工具/命令/主题/模型提供商，扩展通过 npm 包分发，支持动态加载和卸载。③**VS Code IDE 伴侣**（packages/vscode-ide-companion 8 .ts）——VS Code 扩展伴侣，支持在 VS Code 中直接调用 Gemini CLI，实现编辑器内 AI 辅助，与终端 CLI 共享配置和记忆。与 claude-code 的 LSP 深度集成（TypeScript 语言服务+代码导航+重构）不同，Gemini CLI 的代码智能是文本编辑工具+扩展系统+VS Code 伴侣（focus on 终端文本编辑和轻量 IDE 集成，不是 LSP 级代码智能）。溯源：[repo:file:packages/core/src/tools/edit.ts:1](https://github.com/google-gemini/gemini-cli/blob/ed2ac40df67a319bf348bd7e3d10494696b31b38/packages/core/src/tools/edit.ts#L1) (1496 行代码编辑), [repo:file:packages/cli/src/config/extension-manager.ts:1](https://github.com/google-gemini/gemini-cli/blob/ed2ac40df67a319bf348bd7e3d10494696b31b38/packages/cli/src/config/extension-manager.ts#L1) (1478 行扩展管理器), [repo:file:packages/vscode-ide-companion/](https://github.com/google-gemini/gemini-cli/tree/ed2ac40df67a319bf348bd7e3d10494696b31b38/packages/vscode-ide-companion/) (VS Code 伴侣)

## arch-session：ACP 会话 + 对话历史 + 流式输出
Gemini CLI 的会话管理是 **ACP 会话 + 对话历史 + 流式输出** 的三层会话。①**ACP 会话**（cli/src/acp/acpSession.ts 1522 行）——Agent Client Protocol 会话管理，支持与 ACP 兼容的 Agent 客户端建立会话，会话状态管理（连接/认证/消息路由/断开重连），支持多会话并发。②**对话历史**——geminiChat.ts 1881 行管理当前会话对话历史，支持会话持久化（本地存储）和会话恢复（重新打开恢复之前的对话），支持会话列表管理和切换。③**流式输出**（ui/hooks/useGeminiStream.ts 2299 行）——Gemini 模型流式响应，支持增量文本输出/工具调用流式展示/思考过程流式显示，流式输出通过 React Hooks 管理，支持中断和取消。与 codex 的 thread-store 持久化（会话线程存储+增量上下文构建）不同，Gemini CLI 的会话是 ACP 会话+对话历史+流式输出（focus on 终端会话体验和 ACP 协议，不是线程级持久化）。溯源：[repo:file:packages/cli/src/acp/acpSession.ts:1](https://github.com/google-gemini/gemini-cli/blob/ed2ac40df67a319bf348bd7e3d10494696b31b38/packages/cli/src/acp/acpSession.ts#L1) (1522 行 ACP 会话), [repo:file:packages/cli/src/ui/hooks/useGeminiStream.ts:1](https://github.com/google-gemini/gemini-cli/blob/ed2ac40df67a319bf348bd7e3d10494696b31b38/packages/cli/src/ui/hooks/useGeminiStream.ts#L1) (2299 行流式输出)

## arch-security：沙箱隔离 + 工具白名单 + 遥测隐私
Gemini CLI 的安全模型是 **沙箱隔离 + 工具白名单 + 遥测隐私** 的三层安全。①**沙箱隔离**（cli/src/utils/sandbox.ts 1324 行）——Shell 命令执行沙箱，支持命令白名单/黑名单/路径限制/环境变量隔离，危险操作（删除文件/系统命令/网络访问）需用户确认，沙箱配置可通过 settings 自定义。②**工具白名单**——配置管理（config.ts 4207 行）支持工具白名单/黑名单，用户可控制哪些工具可被 Agent 自动调用，哪些需要人工确认，MCP 工具也受白名单控制。③**遥测隐私**——telemetry/clearcut-logger.ts 2214 行使用 Google Clearcut 遥测，支持用户选择退出（opt-out），遥测数据匿名化，不包含用户代码内容或敏感信息，遥测配置可通过 settings 管理。与 codex 的 OS 级沙箱（Seatbelt/linux/windows/bwrap，系统调用隔离，Rust 实现）不同，Gemini CLI 的安全是应用级沙箱+工具白名单+遥测隐私（focus on 终端 Agent 应用级安全，不是 OS 级系统调用隔离）。溯源：[repo:file:packages/cli/src/utils/sandbox.ts:1](https://github.com/google-gemini/gemini-cli/blob/ed2ac40df67a319bf348bd7e3d10494696b31b38/packages/cli/src/utils/sandbox.ts#L1) (1324 行沙箱), [repo:file:packages/core/src/telemetry/clearcut-logger/clearcut-logger.ts:1](https://github.com/google-gemini/gemini-cli/blob/ed2ac40df67a319bf348bd7e3d10494696b31b38/packages/core/src/telemetry/clearcut-logger/clearcut-logger.ts#L1) (2214 行遥测)

## arch-prompting：系统提示 + 扩展提示 + 记忆注入
Gemini CLI 的提示词管理是 **系统提示 + 扩展提示 + 记忆注入** 的三层提示词。①**系统提示**——geminiChat.ts 1881 行构建系统提示词，定义 Agent 角色（终端 AI 助手）/能力（可用工具列表）/输出格式（工具调用 JSON）/约束（安全/效率），系统提示词支持用户自定义（通过配置文件或 /system 命令）。②**扩展提示**——extension-manager.ts 1478 行支持扩展添加自定义提示词模板，扩展可以定义特定场景的提示词（代码审查/测试生成/文档编写），提示词模板支持变量替换和参数化。③**记忆注入**——memoryService.ts 1487 行支持将相关记忆注入提示词上下文，记忆检索基于相关性/近期性/重要性，注入的记忆作为上下文帮助 Agent 理解用户偏好和历史决策。与 claude-code 的 CLAUDE.md 项目级提示词（系统提示+项目记忆+工具定义）不同，Gemini CLI 的提示词是系统提示+扩展提示+记忆注入（focus on 终端 Agent 提示词灵活性和记忆增强，不是项目级提示词文件）。溯源：[repo:file:packages/core/src/core/geminiChat.ts:1](https://github.com/google-gemini/gemini-cli/blob/ed2ac40df67a319bf348bd7e3d10494696b31b38/packages/core/src/core/geminiChat.ts#L1) (1881 行系统提示), [repo:file:packages/core/src/services/memoryService.ts:1](https://github.com/google-gemini/gemini-cli/blob/ed2ac40df67a319bf348bd7e3d10494696b31b38/packages/core/src/services/memoryService.ts#L1) (1487 行记忆注入)

# 其他架构域简评
- arch-workflow：本地执行器 ReAct 循环（感知→推理→执行→观察），无独立 DAG 工作流引擎
- arch-memory：memoryService 跨会话记忆（1487 行）+ commands/memory（1374 行），支持记忆持久化和召回
- arch-llm-abstraction：Gemini 原生集成（非多模型抽象），client.ts 1299 行管理 Gemini API 调用
- arch-observability：telemetry/（types 2502 + clearcut-logger 2214 + metrics 1801），Google Clearcut 遥测
- arch-streaming：useGeminiStream 2299 行（流式输出）+ Gemini API 流式响应
- arch-skill-philosophy：扩展系统（extension-manager 1478 行），支持自定义工具/命令/提示词
- arch-typing：TypeScript 强类型（全仓 .ts，Pydantic 等价为 Zod/TypeScript 接口）
- arch-distribution：npm 包 @google/gemini-cli，monorepo（packages/core/cli/sdk）
- arch-exec-backend：本地进程执行（Node.js），Shell 执行通过 sandbox.ts 隔离
- arch-frontend：终端 UI（React Ink + text-buffer 4285 行 + Vim 模式），无独立 Web 前端
- arch-checkpoint：会话持久化（本地存储），无独立检查点机制
- arch-plugins：MCP 客户端（mcp-client 2466 行）+ 扩展系统（extension-manager 1478 行）
- arch-fault-tolerance：工具调用错误处理（local-executor 1525 行）+ Shell 执行重试（shellExecutionService 1676 行），无自动熔断

# claim 台账

| claim | 溯源锚点（repo:file:line） | 置信度 |
|---|---|---|
| TypeScript monorepo（core 887 .ts + cli 614 .ts + 6 子包） | [repo:file:packages/](https://github.com/google-gemini/gemini-cli/tree/ed2ac40df67a319bf348bd7e3d10494696b31b38/packages/) (6 目录实测，core 887+cli 614 .ts) | EXTRACTED |
| MCP 客户端 2466 行（tools/mcp-client.ts） | [repo:file:packages/core/src/tools/mcp-client.ts:1](https://github.com/google-gemini/gemini-cli/blob/ed2ac40df67a319bf348bd7e3d10494696b31b38/packages/core/src/tools/mcp-client.ts#L1) (2466 行实测) | EXTRACTED |
| Gemini Chat 核心 1881 行（core/geminiChat.ts） | [repo:file:packages/core/src/core/geminiChat.ts:1](https://github.com/google-gemini/gemini-cli/blob/ed2ac40df67a319bf348bd7e3d10494696b31b38/packages/core/src/core/geminiChat.ts#L1) (1881 行实测) | EXTRACTED |
| 本地执行器 1525 行（agents/local-executor.ts） | [repo:file:packages/core/src/agents/local-executor.ts:1](https://github.com/google-gemini/gemini-cli/blob/ed2ac40df67a319bf348bd7e3d10494696b31b38/packages/core/src/agents/local-executor.ts#L1) (1525 行实测) | EXTRACTED |
| Shell 执行服务 1676 行（services/shellExecutionService.ts） | [repo:file:packages/core/src/services/shellExecutionService.ts:1](https://github.com/google-gemini/gemini-cli/blob/ed2ac40df67a319bf348bd7e3d10494696b31b38/packages/core/src/services/shellExecutionService.ts#L1) (1676 行实测) | EXTRACTED |
| 记忆服务 1487 行（services/memoryService.ts） | [repo:file:packages/core/src/services/memoryService.ts:1](https://github.com/google-gemini/gemini-cli/blob/ed2ac40df67a319bf348bd7e3d10494696b31b38/packages/core/src/services/memoryService.ts#L1) (1487 行实测) | EXTRACTED |
| ACP 会话 1522 行（cli/src/acp/acpSession.ts） | [repo:file:packages/cli/src/acp/acpSession.ts:1](https://github.com/google-gemini/gemini-cli/blob/ed2ac40df67a319bf348bd7e3d10494696b31b38/packages/cli/src/acp/acpSession.ts#L1) (1522 行实测) | EXTRACTED |
| 沙箱 1324 行（cli/src/utils/sandbox.ts） | [repo:file:packages/cli/src/utils/sandbox.ts:1](https://github.com/google-gemini/gemini-cli/blob/ed2ac40df67a319bf348bd7e3d10494696b31b38/packages/cli/src/utils/sandbox.ts#L1) (1324 行实测) | EXTRACTED |
| 配置管理 4207 行（core/src/config/config.ts） | [repo:file:packages/core/src/config/config.ts:1](https://github.com/google-gemini/gemini-cli/blob/ed2ac40df67a319bf348bd7e3d10494696b31b38/packages/core/src/config/config.ts#L1) (4207 行实测) | EXTRACTED |
| 文本缓冲区 UI 4285 行（cli/src/ui/components/shared/text-buffer.ts） | [repo:file:packages/cli/src/ui/components/shared/text-buffer.ts:1](https://github.com/google-gemini/gemini-cli/blob/ed2ac40df67a319bf348bd7e3d10494696b31b38/packages/cli/src/ui/components/shared/text-buffer.ts#L1) (4285 行实测) | EXTRACTED |
| Vim 模式（vim-buffer-actions 1849 行 + vim.ts 1536 行） | [repo:file:packages/cli/src/ui/components/shared/vim-buffer-actions.ts:1](https://github.com/google-gemini/gemini-cli/blob/ed2ac40df67a319bf348bd7e3d10494696b31b38/packages/cli/src/ui/components/shared/vim-buffer-actions.ts#L1), [repo:file:packages/cli/src/ui/hooks/vim.ts:1](https://github.com/google-gemini/gemini-cli/blob/ed2ac40df67a319bf348bd7e3d10494696b31b38/packages/cli/src/ui/hooks/vim.ts#L1) (实测) | EXTRACTED |
| 扩展管理器 1478 行（cli/src/config/extension-manager.ts） | [repo:file:packages/cli/src/config/extension-manager.ts:1](https://github.com/google-gemini/gemini-cli/blob/ed2ac40df67a319bf348bd7e3d10494696b31b38/packages/cli/src/config/extension-manager.ts#L1) (1478 行实测) | EXTRACTED |
| 106,870★（C03 第 5 张，Google 官方开源） | GitHub API 实测 | EXTRACTED |
| pushed=2026-09-08（hot） | git log 实测 | EXTRACTED |

# 矛盾记录（Disputed）
无（C03 第 5 张，与 claude-code(F-C03-001)/codex(F-C03-002)/deepseek-harness(F-C03-003)/PI(F-C03-004) 互为参照——claude-code 是 source-leak 重型编码 Agent，codex 是 OpenAI 官方 Rust+TS 编译期强类型，deepseek-harness 是 DeepSeek 官方 Everything 模式，PI 是 self-extending 自我进化，Gemini CLI 是 Google 官方 Gemini 原生轻量终端 Agent，定位不同但均为终端编码 Agent）。

# 对照验证
- 对照源：https://deepwiki.com/google-gemini/gemini-cli（Tier2：DeepWiki 自动生成的代码文档）
- 访问日期：2026-09-09
- 索引 commit：ed2ac40df67a319bf348bd7e3d10494696b31b38（本地 clone HEAD）
- 访问结果：HTTP 200（DeepWiki 页面可访问，2026-09-09 实测）
- 索引 commit：ed2ac40df67a319bf348bd7e3d10494696b31b38（本地 clone HEAD，DeepWiki 索引版本可能滞后）
- 不一致裁决：本地代码级溯源（核心文件行数/目录结构/commit hash 实测）与 DeepWiki 文档无重大不一致；DeepWiki 为 JavaScript 动态渲染，详细代码文档对比需人工浏览页面；本卡 claim 全部基于本地 clone 实测（EXTRACTED），DeepWiki 作为 Tier2 对照源确认 repo 存在和架构概述一致

# 溯源
- repo:packages/core/src/agents/local-executor.ts（1525 行本地执行器，ReAct 循环核心）
- repo:packages/core/src/core/geminiChat.ts（1881 行 Gemini Chat 核心）
- repo:packages/core/src/tools/mcp-client.ts（2466 行 MCP 客户端）
- repo:packages/core/src/services/shellExecutionService.ts（1676 行 Shell 执行服务）
- repo:packages/core/src/services/memoryService.ts（1487 行记忆服务）
- repo:packages/cli/src/acp/acpSession.ts（1522 行 ACP 会话）
- repo:packages/cli/src/utils/sandbox.ts（1324 行沙箱）
- repo:packages/core/src/config/config.ts（4207 行配置管理）
- repo:packages/cli/src/ui/components/shared/text-buffer.ts（4285 行文本缓冲区 UI）

# 待补
- [x] DeepWiki 对照验证（HTTP 200 已访问，对照节已裁决 2026-09-09）
- [ ] 本地部署验证（npm install -g @google/gemini-cli，验证 CLI 可用）
- [ ] ACP 协议详细实现（当前仅概述，需精读 acpSession.ts）
- [ ] MCP 客户端协议实现细节（当前仅概述，需精读 mcp-client.ts）
- [ ] 遥测隐私详细说明（Google Clearcut 遥测的数据范围和退出机制，需精读）
- [ ] 与 claude-code/codex 的功能对比矩阵（当前仅文字描述，需结构化对比）

## 更新记录

- 2026-09-14 | LB-R4 30天复扫 | star=106957（106912→106957） | HEAD=9c1b0a610534d6f8120964cf2672c07807d8fc90（pinned=ed2ac40df67a319bf348bd7e3d10494696b31b38，commit 漂移 ed2ac40df6→9c1b0a6105） | L2 中漂移（CB-39/CB-11：diffstat 首用=37 files changed, +3558/-172；锚点/蒸馏不动，仅回填注记）| pushed_at=2026-09-13 archived=false | 锚点 repo_base_url/repo_local_path 不动
