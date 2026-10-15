---
id: M-002
title: C10 协议与生态域×框架横评：superpowers vs mcp-servers vs openclaw
tags: [arch-plugins, arch-skill-philosophy, arch-distribution, arch-aci, matrix]
created: 2026-09-08
category: C10
domains: [arch-plugins, arch-skill-philosophy, arch-distribution, arch-aci, arch-orchestration]
columns: 3
sources: [F-C10-001, F-C10-002, F-C10-003]
---

# 矩阵定位
对比 C10 协议/插件/生态枢纽的三种分发形态：静态文档技能集（superpowers）、运行时工具服务器参考实现（mcp-servers）、完整 AI 助手运行时（openclaw），解决面试高频问题"agent 生态/插件/技能怎么选"。中立性声明：格内结论全部回溯到三张 F 卡的代码级溯源，厂商自证数字仅 [UNVERIFIED] 不入正文。

# 矩阵本体

| 维度/子维度                         | superpowers（F-C10-001）                                                                                                                                                                                                                       | mcp-servers（F-C10-002）                                                                                                                                                                    | openclaw（F-C10-003）                                                                                                                                                                |
| ------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **分发形态（核心谱系）**                 | [EXTRACTED] **静态文档技能集**：14 个标准化开发工作流技能，以 SKILL.md（YAML frontmatter+Markdown）静态文档形式分发，agent 读取后执行 [F-C10-001 claim 台账]                                                                                                                        | [EXTRACTED] **运行时工具服务器**：7 个 MCP 参考服务器（everything/filesystem/git/memory/fetch/sequentialthinking/time），以 npm 包形式分发，agent 通过 MCP 协议 stdio/SSE 连接调用 [F-C10-002 claim 台账]                    | [EXTRACTED] **完整 AI 助手运行时**：多通道 AI 网关+5 平台原生应用+Gateway 本地控制平面+插件系统+16+ 技能+60+ CLI 命令，以 TypeScript monorepo+原生应用形式分发 [F-C10-003 claim 台账]                                           |
| **arch-plugins 插件架构**          | [EXTRACTED] 10 个平台插件目录（.claude-plugin/.codex-plugin/.cursor-plugin/.devin-plugin/.hermes-plugin/.kimi-plugin/.opencode/.pi/.agents/.github），为每个 agent 平台提供适配层，技能本身平台无关 [F-C10-001 claim 台账]                                                  | [EXTRACTED] MCP 协议原生插件架构：三大原语（Tools/Resources/Prompts），服务器通过协议暴露工具/资源/提示词，客户端（agent）通过协议调用，无需平台特定适配 [F-C10-002 claim 台账]                                                                  | [EXTRACTED] 插件系统（plugin-sdk + plugin-package-contract）：21 个核心包，插件通过 SDK 开发，通过 contract 契约加载，运行时插件化架构 [F-C10-003 claim 台账]                                                          |
| **arch-skill-philosophy 技能哲学** | [EXTRACTED] 标准化工作流技能：systematic-debugging Iron Law（先找根因再修）、writing-skills 元技能（26KB SKILL.md+46KB anthropic-best-practices）、多 agent 协作技能（subagent-driven-development+dispatching-parallel-agents）；技能创建留痕 CREATION-LOG.md [F-C10-001 claim 台账] | [EXTRACTED] 无独立技能哲学：mcp-servers 是工具服务器参考实现，技能/能力以工具（Tools）形式暴露，sequentialthinking 服务器提供思维链工具，memory 服务器提供知识图谱记忆工具 [F-C10-002 claim 台账]                                                    | [EXTRACTED] 16+ 技能（skills/ 目录）：技能作为运行时内置能力，与 Gateway 控制平面集成，可通过 CLI 命令（60+）调用，技能与插件系统协同 [F-C10-003 claim 台账]                                                                       |
| **arch-distribution 分发机制**     | [EXTRACTED] npm 分发 superpowers v6.3.0 + GitHub 仓库；技能以静态 Markdown 文件随包分发，agent 可直接读取 SKILL.md；10 平台插件目录确保跨平台兼容 [F-C10-001 claim 台账]                                                                                                           | [EXTRACTED] npm 分发 @modelcontextprotocol/server-*（everything@2.0.0/filesystem@0.6.3/memory@0.6.3/sequential-thinking@0.6.2 等）；服务器以独立 npm 包分发，agent 通过 npx/stdio 启动连接 [F-C10-002 claim 台账] | [EXTRACTED] TypeScript monorepo（openclaw@2026.9.2）+5 平台原生应用（macOS/iOS/Android/Windows/Linux）+CLI（v2026.7.1-2）；通过 npm+原生应用商店+GitHub 多渠道分发 [F-C10-003 claim 台账]                      |
| **arch-aci 工具接口**              | [EXTRACTED] 标准文件接口：技能为 SKILL.md 静态文档，agent 通过文件系统读取，无运行时 API/协议；平台插件目录提供各 agent 的适配配置文件 [F-C10-001 §arch-aci]                                                                                                                                | [EXTRACTED] MCP 协议标准接口：Tools（工具调用）/Resources（资源读取）/Prompts（提示词模板）三大原语；多传输方式 stdio/SSE/HTTP/Streamable HTTP；多语言 SDK（10+ 语言） [F-C10-002 claim 台账]                                           | [EXTRACTED] Gateway 本地控制平面 API：sessions/tools/events/channel connections；60+ CLI 命令；插件 SDK API；多通道消息接口（20+ 渠道：Discord/iMessage/Slack/Teams/Telegram/WhatsApp） [F-C10-003 claim 台账] |
| **arch-orchestration 编排定位**    | [EXTRACTED] 无独立编排：superpowers 是技能/知识层，由调用方 agent 编排；技能提供工作流方法论（如 systematic-debugging），不提供运行时编排引擎 [F-C10-001 §arch-orchestration]                                                                                                            | [EXTRACTED] 无独立编排：mcp-servers 是工具层，由调用方 agent 通过 MCP 协议编排；sequentialthinking 提供思维链工具辅助编排，但无独立编排引擎 [F-C10-002 §arch-orchestration]                                                         | [EXTRACTED] 完整编排运行时：Gateway 本地控制平面（sessions/tools/events），多通道消息路由，插件系统运行时加载，技能与 CLI 集成，是完整的 agent 编排运行时而非纯工具/技能层 [F-C10-003 §arch-orchestration]                                   |
| **star/生态规模**                  | [EXTRACTED] 282,954★（GitHub API 实测，2026-09-08）；14 技能+10 平台插件，生态规模最大 [F-C10-001 claim 台账]                                                                                                                                                     | [EXTRACTED] star 数见 F-C10-002 frontmatter；7 参考服务器+MCP 协议生态（10+ 语言 SDK），协议级生态 [F-C10-002 claim 台账]                                                                                         | [EXTRACTED] star 数见 F-C10-003 frontmatter；20+ 渠道+5 平台+21 包+16+ 技能+60+ CLI，运行时生态 [F-C10-003 claim 台账]                                                                               |

# 数据口径
- EXTRACTED = 代码/官方文档级溯源（repo:file:line 或 F 卡分节引用），格内 [EXTRACTED] 角标+F 卡 ID 回溯
- INFERRED = 基于目录结构/协议规范推断，已在 F 卡 claim 台账标注
- 厂商数字 = UNVERIFIED 引用并注明口径偏见，禁直接搬入正文论断

# 一页口径（30 秒版结论，面试直接背）
superpowers=静态文档技能集，14 个标准化工作流技能+10 平台插件，适合需要跨 agent 平台复用开发方法论的场景；mcp-servers=MCP 协议运行时工具服务器参考实现，7 个服务器+三大原语+多传输，适合需要标准化工具协议接入的 agent；openclaw=完整 AI 助手运行时，多通道网关+5 平台原生应用+插件系统+16+ 技能，适合需要开箱即用的多通道 AI 助手。三者形成 C10 谱系：静态技能→协议工具→完整运行时，非替代而是生态层级选择。

# 溯源
- F-C10-001 superpowers（静态文档技能集，14 技能+10 平台插件，npm superpowers v6.3.0，282,954★）
- F-C10-002 mcp-servers（MCP 协议参考服务器，7 服务器+三大原语+多传输，npm @modelcontextprotocol/server-*）
- F-C10-003 openclaw（完整 AI 助手运行时，多通道网关+5 平台+插件系统+16+ 技能+60+ CLI，TypeScript monorepo）

# 待补
- [ ] mcp-servers/openclaw 的精确 star 数对比（需从 F 卡 frontmatter 提取补全）
- [ ] 三者性能/延迟对比（MCP 协议开销 vs 静态文件读取 vs 运行时插件加载，需独立基准）
- [ ] openclaw 插件系统与 MCP 协议的兼容性（openclaw 是否支持 MCP 服务器接入，需确认）
- [ ] superpowers 技能与 openclaw 技能的格式差异（SKILL.md vs 运行时内置技能，需对比）
