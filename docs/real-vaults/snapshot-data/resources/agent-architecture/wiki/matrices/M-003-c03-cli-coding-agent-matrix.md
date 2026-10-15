---
id: M-003
title: C03 CLI/编码 Agent 域×框架横评：claude-code vs codex vs DeepSeek Harness
tags: [arch-code-intel, arch-session, arch-security, arch-orchestration, matrix]
created: 2026-09-08
category: C03
domains: [arch-code-intel, arch-session, arch-security, arch-orchestration, arch-aci, arch-context]
columns: 3
sources: [F-C03-001, F-C03-002, F-C03-003]
---

# 矩阵定位
对比三种 CLI/编码 Agent 运行时：查询引擎驱动（claude-code）、Rust 分布式架构（codex）、Everything-is-a-Plugin+Cordis（DeepSeek Harness），解决面试高频问题"编码 agent 运行时怎么选"。中立性声明：claude-code 为 source-leak 通道（非官方 repo，数据来源等级低于官方 repo），格内已标注；DeepSeek Harness 走 CB-11 Update 增补路径，结论已同步；格内结论全部回溯到 F 卡代码级溯源。

# 矩阵本体

| 维度/子维度                      | claude-code（F-C03-001，source-leak）                                                                                                                                                                         | codex（F-C03-002）                                                                                                                                                 | DeepSeek Harness（F-C03-003，CB-11 Update）                                                                                                           |
| --------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| **数据来源等级**                  | [EXTRACTED] **source-leak 通道**：非官方 repo，基于社区泄露的 claude-code-main 源码蒸馏，无官方文档/DeepWiki 覆盖（Tier3）；核心设计与社区公开功能描述一致 [F-C03-001 §对照验证]                                                                           | [EXTRACTED] **官方 repo**：openai/codex，AGENTS.md 官方开发文档+代码级溯源，DeepWiki Tier2 覆盖 [F-C03-002 §对照验证]                                                                  | [EXTRACTED] **官方 repo**：deepseek-ai/deepseek-harness，README 官方文档+代码级溯源，DeepWiki Tier2 覆盖；CB-11 Update 增补路径结论已同步 [F-C03-003 §对照验证]                  |
| **arch-code-intel 代码智能**    | [EXTRACTED] LSPTool 语言服务器协议代码智能；60+ 工具生态含文件/LSP/Shell/MCP/任务/技能/计划/Web/团队；文件历史快照（fileHistory+FileStateCache）[F-C03-001 claim 台账]                                                                           | [EXTRACTED] 工具系统动态+MCP 优先（dynamic_tool/mcp_tool）；Responses API 原生支持（tools/responses_api.rs）；Rust 100+ crate 强类型代码智能 [F-C03-002 claim 台账]                         | [EXTRACTED] Everything-is-a-Plugin 架构，代码智能通过插件扩展；56 个 packages 含 lsp/code-runtime 等；4 个应用（cli/desktop/desktop-host/web）多端代码智能 [F-C03-003 claim 台账] |
| **arch-session 会话管理**       | [EXTRACTED] memdir 文件记忆（loadMemoryPrompt 注入系统提示）；子 agent 协作（AgentTool+AgentDefinition）；Worktree 隔离（EnterWorktree/ExitWorktree）；计划-执行分离（EnterPlanMode/ExitPlanMode/VerifyPlanExecution）[F-C03-001 claim 台账] | [EXTRACTED] 模型上下文六规则（增量构建/有界/≤10K/>1K标P0/ContextualUserFragment trait）；分布式架构（app-server JSON-RPC v2+exec-server 跨 OS）支持跨机会话 [F-C03-002 claim 台账]                 | [EXTRACTED] session 包（packages/session/）管理会话状态；Cordis 时空可组合编程范式支持会话状态时空组合；desktop/desktop-host 应用支持多会话 [F-C03-003 claim 台账]                        |
| **arch-security 安全/沙箱**     | [EXTRACTED] 权限系统（PermissionMode+CanUseToolFn）；Worktree 隔离提供文件系统级隔离；无独立沙箱后端（依赖宿主权限）[F-C03-001 claim 台账]                                                                                                     | [EXTRACTED] **跨平台沙箱（Seatbelt/macOS、linux、windows、mxc、bwrap）**：codex-rs/sandboxing/+linux-sandbox/+windows-sandbox-rs/+bwrap，5 种沙箱后端，安全设计最完善 [F-C03-002 claim 台账] | [EXTRACTED] 沙箱通过插件扩展（packages/sandbox/）；runtime-diagnostics 包提供运行时诊断；developer preview 阶段安全机制持续演进 [F-C03-003 claim 台账]                             |
| **arch-orchestration 编排架构** | [EXTRACTED] **查询引擎驱动 agent 循环**：QueryEngine 48KB+query 69KB，以查询为中心的编排模式；计划-执行分离（EnterPlanMode/ExitPlanMode/VerifyPlanExecution）[F-C03-001 claim 台账]                                                        | [EXTRACTED] **Rust 分布式架构**：app-server JSON-RPC v2+exec-server 跨 OS，100+ crate 模块化；codex-core 487 .rs files，AGENTS.md 抵制继续膨胀 [F-C03-002 claim 台账]                 | [EXTRACTED] **Everything-is-a-Plugin+Cordis 时空可组合**：56 个 packages，Cordis 依赖注入+时空可组合编程范式（arXiv:2608.25512），极致插件化 [F-C03-003 claim 台账]               |
| **arch-aci 工具接口**           | [EXTRACTED] 60+ 工具生态（文件/LSP/Shell/MCP/任务/技能/计划/Web/团队）；MCP 支持；AgentTool 子 agent 工具 [F-C03-001 claim 台账]                                                                                                    | [EXTRACTED] MCP 原生支持（codex-mcp+mcp_connection_manager+rmcp-client）；工具系统动态+MCP 优先（dynamic_tool/mcp_tool）；Responses API 原生支持 [F-C03-002 claim 台账]                  | [EXTRACTED] 插件 SDK API；MCP 支持（packages/mcp/）；Python 绑定（python/sdk+sdk-runtime）；npm 包 @deepseek-ai/dsh [F-C03-003 claim 台账]                         |
| **arch-context 上下文管理**      | [EXTRACTED] memdir 文件记忆注入系统提示；查询引擎上下文管理；文件历史快照 [F-C03-001 claim 台账]                                                                                                                                        | [EXTRACTED] 模型上下文六规则（增量构建/有界/≤10K/>1K标P0/ContextualUserFragment trait），上下文管理最严格 [F-C03-002 claim 台账]                                                             | [EXTRACTED] context 包管理上下文；Cordis 时空可组合支持上下文状态管理；compaction 包支持上下文压缩 [F-C03-003 claim 台账]                                                          |
| **技术栈/语言**                  | [EXTRACTED] TypeScript（claude-code-main/src/），Node.js 运行时 [F-C03-001 claim 台账]                                                                                                                             | [EXTRACTED] Rust workspace 100+ crate，codex-core 487 .rs files [F-C03-002 claim 台账]                                                                              | [EXTRACTED] TypeScript monorepo（56 packages）+Python 绑定（sdk/sdk-runtime），多语言 [F-C03-003 claim 台账]                                                   |
| **star/成熟度**                | [EXTRACTED] star 数见 F-C03-001 frontmatter；source-leak 通道，成熟度基于社区功能描述推断 [F-C03-001 claim 台账]                                                                                                                | [EXTRACTED] star 数见 F-C03-002 frontmatter；OpenAI 官方，Rust 生产级架构，AGENTS.md 官方开发文档 [F-C03-002 claim 台账]                                                             | [EXTRACTED] 215,765★（GitHub API 实测）；developer preview（会有破坏性变更），pushed=2026-09-07 hot [F-C03-003 claim 台账]                                          |

# 数据口径
- EXTRACTED = 代码/官方文档级溯源（repo:file:line 或 F 卡分节引用），格内 [EXTRACTED] 角标+F 卡 ID 回溯
- claude-code 为 source-leak 通道（Tier3），数据来源等级低于官方 repo，格内已标注
- DeepSeek Harness 走 CB-11 Update 增补路径，结论已同步进矩阵
- 厂商数字 = UNVERIFIED 引用并注明口径偏见，禁直接搬入正文论断

# 一页口径（30 秒版结论，面试直接背）
claude-code=查询引擎驱动+60+ 工具生态+计划-执行分离，TypeScript 实现，source-leak 通道适合研究其设计模式；codex=Rust 分布式架构+跨平台沙箱（Seatbelt 5 后端）+MCP 原生+上下文六规则，OpenAI 官方生产级，适合需要强安全和分布式部署的编码 agent；DeepSeek Harness=Everything-is-a-Plugin+Cordis 时空可组合+56 packages+4 应用+Python 绑定，极致插件化多端，developer preview 阶段适合需要高度可定制插件架构的场景。三者编排范式不同：查询引擎 vs 分布式 Rust vs 插件化 Cordis，非替代而是架构哲学选择。

# 溯源
- F-C03-001 claude-code（查询引擎驱动，60+ 工具，LSPTool，权限系统，memdir，计划-执行分离，Worktree 隔离；source-leak 通道 Tier3）
- F-C03-002 codex（Rust 100+ crate，codex-core 487 files，跨平台沙箱 Seatbelt 5 后端，MCP 原生，分布式 app-server+exec-server，上下文六规则；OpenAI 官方）
- F-C03-003 deepseek-harness（Everything-is-a-Plugin+Cordis，56 packages，4 应用，Python 绑定，215,765★，developer preview；CB-11 Update 增补路径；DeepSeek 官方）

# 待补
- [ ] claude-code/codex 的精确 star 数对比（需从 F 卡 frontmatter 提取补全）
- [ ] 三者性能/延迟对比（查询引擎 vs Rust 分布式 vs 插件化，需独立基准测试）
- [ ] claude-code source-leak 与官方版本的差异（官方 claude-code 发布后需对比验证）
- [ ] DeepSeek Harness Cordis 时空可组合的具体机制（需精读 packages/core/ 和 arXiv 论文）
- [ ] codex 分布式架构（app-server+exec-server）的部署模式（需精读 AGENTS.md 260-304 行）
