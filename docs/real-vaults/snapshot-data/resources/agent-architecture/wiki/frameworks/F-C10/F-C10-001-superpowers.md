---
id: F-C10-001
title: Superpowers：多平台 Agent 技能生态枢纽（14 标准化开发工作流技能 + 9 平台适配目录，282k★）
tags: [framework-profile, arch-plugins, arch-skill-philosophy, arch-distribution, arch-aci, arch-typing, arch-security, arch-orchestration]
created: 2026-09-08
category: C10
alt: [C03]
repo_url: https://github.com/obra/superpowers
repo_commit: b36e0829c6d0140e93cfef2ca599b1b07d4a7797
repo_base_url: https://github.com/obra/superpowers/blob/b36e0829c6d0140e93cfef2ca599b1b07d4a7797/
repo_local_path: [本机绝对路径已隐藏]
star: 286101
distilled_at: 2026-09-08
freshness: dated
workflow: WORKFLOW-repo v2
sources: []
---

# 框架总评
## 设计哲学出发点
Superpowers 定位为"多平台 Agent 技能生态枢纽"（superpowers skills and runtime bootstrap for coding agents），核心取舍是**技能标准化 + 多平台分发**——把编码 agent 的开发工作流提炼为 14 个标准化技能（brainstorming→writing-plans→executing-plans→TDD→systematic-debugging→code-review→finishing-branch→git-worktrees→subagent-development→parallel-agents→verification→writing-skills→using-superpowers），每个技能以 SKILL.md（YAML frontmatter + Markdown）定义，通过 9 个平台适配目录（.claude-plugin/.codex-plugin/.cursor-plugin/.devin-plugin/.hermes-plugin/.kimi-plugin/.opencode/.pi/.agents；.github 为 GitHub 社区配置非适配器——2026-09-10 实测更正）分发到主流 agent 平台。设计哲学是"技能即文档"——技能本身是人类可读的 Markdown 文档，agent 通过 description 字段判断何时触发，执行权限由宿主 agent 控制。

## 设计特点
- 14 个标准化开发工作流技能，覆盖编码全流程（从头脑风暴到完成分支）
- 技能格式：SKILL.md（YAML frontmatter: name/description + Markdown 内容），可含辅助文件（.md/.sh/.ts/.dot/.js）
- 9 个平台适配目录（2026-09-10 实测更正，原记 10 误含 .github）：Claude/Codex/Cursor/Devin/Kimi 5 目录含 plugin.json；.agents 含 plugins/marketplace.json；.hermes-plugin 用 plugin.yaml（含 provides_hooks: pre_llm_call）；.opencode/.pi 为运行时代码适配（superpowers.js / superpowers.ts）；marketplace.json 仅 .claude-plugin 与 .agents 有
- npm 分发：superpowers v6.3.0，"Superpowers skills and runtime bootstrap for coding agents"
- 纪律性技能设计：systematic-debugging 的"Iron Law: NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST"
- 元技能自举：writing-skills 技能（26KB SKILL.md + 46KB anthropic-best-practices.md）教 agent 如何写技能
- 多 agent 协作：subagent-driven-development + dispatching-parallel-agents 技能
- 技能创建留痕：仅 systematic-debugging 含 CREATION-LOG.md（全仓实测 1 个，2026-09-10 更正"每个技能含"）
- 282,954★（GitHub 星标，agent 技能生态第一大仓）

## 痛点
解决 agent 技能碎片化和平台锁定的痛点——每个 agent 平台都有自己的技能格式和分发机制，技能无法跨平台复用。Superpowers 通过标准化 SKILL.md 格式 + 多平台插件目录，实现"一次编写，多平台分发"。同时解决 agent 开发工作流不规范的痛点——14 个标准化技能强制纪律性开发流程（如先找根因再修 bug、先写计划再执行、完成前验证），提升 agent 编码质量。

## 优缺点
- 优点：技能标准化（SKILL.md 格式简单通用）；多平台分发（9 个适配目录覆盖主流 agent）；282k★ 社区验证；纪律性设计提升编码质量；元技能自举（writing-skills 教写技能）；技能即文档（人类可读可审计）；npm 一键安装
- 缺点：技能本身是 Markdown 文档（无独立代码执行能力，执行依赖宿主 agent）；适配机制不统一（5 目录静态 plugin.json、2 目录运行时代码、2 目录其他格式——9 目录需同步维护）；技能触发依赖 description 匹配（可能误触发/漏触发）；无技能版本管理机制（技能更新需手动同步）；无技能市场/发现机制（靠 GitHub/npm 分发）

## 关键取舍
最核心的取舍是"技能即文档（Markdown）" vs "技能即可执行代码"——Superpowers 选择 Markdown 文档，获得跨平台通用性和人类可审计性，但牺牲了技能的执行能力（必须依赖宿主 agent 解释执行）。另一个取舍是"多平台适配目录" vs "统一技能协议"——Superpowers 选择为每个平台维护独立适配目录，获得最大平台兼容性，但增加了维护成本（9 个目录需同步更新）。第三个取舍是"纪律性强制" vs "灵活性"——Superpowers 选择纪律性（如 systematic-debugging 的 Iron Law），提升编码质量但可能降低 agent 灵活性。

# 核心深挖域

## arch-plugins：插件系统与多平台适配
Superpowers 的适配机制是**多平台目录适配**模式（2026-09-10 一级事实源实测更正，反馈源=codex 交叉审查）——仓库根目录含 **9 个平台适配目录**，呈**三种适配模式**：①**plugin.json 静态配置型（5/9）**：.claude-plugin（Claude Code，含 plugin.json+marketplace.json）、.codex-plugin（OpenAI Codex）、.cursor-plugin（Cursor）、.devin-plugin（Devin）、.kimi-plugin（Kimi）；②**运行时代码适配型（2/9）**：.opencode（OpenCode，plugins/superpowers.js——"Injects superpowers bootstrap context via message transform. Auto-registers skills directory via config hook"）+ .pi（PI，extensions/superpowers.ts——ExtensionAPI 扩展）；③**其他格式配置型（2/9）**：.agents（通用，plugins/marketplace.json）、.hermes-plugin（Hermes，plugin.yaml v6.3.0，声明 provides_hooks: pre_llm_call）。**.github 是 GitHub 社区配置（ISSUE_TEMPLATE/FUNDING.yml/PR 模板），不是平台适配器**。并非所有目录都有 plugin.json（仅 5/9），marketplace.json 仅 .claude-plugin 与 .agents 有——原卡"每个平台目录含 plugin.json 和/或 marketplace.json"有误。技能本体仍为 SKILL.md 文档，适配器负责加载方式（其中 OpenCode/PI/Hermes 三家引入了运行时 hook/扩展层，"纯静态无运行时"表述已被实测推翻）。与 MCP 协议（运行时工具调用）不同，技能与平台之间仍无标准协议通信。溯源：[repo:file:.claude-plugin/plugin.json:1](https://github.com/obra/superpowers/blob/b36e0829c6d0140e93cfef2ca599b1b07d4a7797/.claude-plugin/plugin.json#L1), [repo:file:.opencode/plugins/superpowers.js:1-5](https://github.com/obra/superpowers/blob/b36e0829c6d0140e93cfef2ca599b1b07d4a7797/.opencode/plugins/superpowers.js#L1-L5) (运行时 bootstrap), [repo:file:.pi/extensions/superpowers.ts:1](https://github.com/obra/superpowers/blob/b36e0829c6d0140e93cfef2ca599b1b07d4a7797/.pi/extensions/superpowers.ts#L1) (ExtensionAPI), [repo:file:.hermes-plugin/plugin.yaml:1-7](https://github.com/obra/superpowers/blob/b36e0829c6d0140e93cfef2ca599b1b07d4a7797/.hermes-plugin/plugin.yaml#L1-L7) (provides_hooks), [repo:file:.agents/plugins/marketplace.json:1](https://github.com/obra/superpowers/blob/b36e0829c6d0140e93cfef2ca599b1b07d4a7797/.agents/plugins/marketplace.json#L1), [repo:file:package.json:1](https://github.com/obra/superpowers/blob/b36e0829c6d0140e93cfef2ca599b1b07d4a7797/package.json#L1) (superpowers v6.3.0)

## arch-skill-philosophy：技能设计哲学与方法论
Superpowers 的技能哲学是**纪律性标准化开发工作流**——14 个技能覆盖编码全流程，每个技能强制特定的工作纪律：①systematic-debugging（9KB SKILL.md + 11 files）："Iron Law: NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST"，分阶段根因追踪（root-cause-tracing.md + defense-in-depth.md + condition-based-waiting.md），含测试压力样例（test-pressure-1/2/3.md）；②test-driven-development：强制先写测试再写实现；③writing-plans + executing-plans：强制先计划后执行；④requesting-code-review + receiving-code-review：强制代码审查流程；⑤verification-before-completion：完成前强制验证；⑥finishing-a-development-branch：分支完成规范；⑦using-git-worktrees：Git worktree 隔离工作流；⑧subagent-driven-development + dispatching-parallel-agents：多 agent 协作；⑨brainstorming：头脑风暴方法论；⑩writing-skills（26KB SKILL.md + 46KB anthropic-best-practices.md + 12KB testing-skills-with-subagents.md）：元技能，教 agent 如何写高质量技能，含 graphviz 约定（graphviz-conventions.dot）和渲染脚本（render-graphs.js）；⑪using-superpowers：自举技能，教 agent 如何使用 Superpowers 技能集。技能创建留痕 **CREATION-LOG.md 全仓仅 systematic-debugging 一例**（4KB 创建日志；2026-09-10 实测更正，原卡"每个技能含"有误——Get-ChildItem -Recurse -Filter CREATION-LOG.md = 1）。溯源：[repo:file:skills/systematic-debugging/SKILL.md:1](https://github.com/obra/superpowers/blob/b36e0829c6d0140e93cfef2ca599b1b07d4a7797/skills/systematic-debugging/SKILL.md#L1) (Iron Law), [repo:file:skills/writing-skills/SKILL.md:1](https://github.com/obra/superpowers/blob/b36e0829c6d0140e93cfef2ca599b1b07d4a7797/skills/writing-skills/SKILL.md#L1) (元技能 26KB), [repo:file:skills/writing-skills/anthropic-best-practices.md:1](https://github.com/obra/superpowers/blob/b36e0829c6d0140e93cfef2ca599b1b07d4a7797/skills/writing-skills/anthropic-best-practices.md#L1) (46KB), [repo:file:skills/systematic-debugging/CREATION-LOG.md:1](https://github.com/obra/superpowers/blob/b36e0829c6d0140e93cfef2ca599b1b07d4a7797/skills/systematic-debugging/CREATION-LOG.md#L1) (创建留痕，全仓唯一)

## arch-distribution：分发机制与生态建设
Superpowers 的分发机制是**多渠道分发**：①npm 包（superpowers v6.3.0，"Superpowers skills and runtime bootstrap for coding agents"），支持 `npm install -g superpowers` 或项目级安装；②GitHub 仓库（282,954★，直接 clone 或 fork）；③多平台适配目录（9 个，各平台 agent 可直接读取，其中 OpenCode/PI 为运行时代码适配）；④技能市场（.claude-plugin/marketplace.json 与 .agents/plugins/marketplace.json）。分发的核心是 skills/ 目录——14 个技能目录，每个含 SKILL.md + 辅助文件。**runtime bootstrap 已实证落地在适配器层**（2026-09-10 实测更正，原"npm 包可能包含"为推测）：.opencode/plugins/superpowers.js 经 message transform 注入 bootstrap 上下文并自动注册技能目录；.pi/extensions/superpowers.ts 为 PI 扩展；.hermes-plugin/plugin.yaml 声明 pre_llm_call hook。生态建设通过 282k★ 社区驱动，技能贡献者通过 PR 添加新技能或改进现有技能。与 MCP 生态（运行时工具服务器）不同，Superpowers 的技能本体是静态文档（适配器层存在 JS/TS 运行时引导，但技能与平台间无标准协议）。溯源：[repo:file:package.json:1](https://github.com/obra/superpowers/blob/b36e0829c6d0140e93cfef2ca599b1b07d4a7797/package.json#L1) (superpowers v6.3.0), [repo:file:skills/](https://github.com/obra/superpowers/tree/b36e0829c6d0140e93cfef2ca599b1b07d4a7797/skills/) (14 技能目录), [repo:file:.opencode/plugins/superpowers.js:1-5](https://github.com/obra/superpowers/blob/b36e0829c6d0140e93cfef2ca599b1b07d4a7797/.opencode/plugins/superpowers.js#L1-L5) (运行时 bootstrap 实锚), [repo:file:.claude-plugin/marketplace.json:1](https://github.com/obra/superpowers/blob/b36e0829c6d0140e93cfef2ca599b1b07d4a7797/.claude-plugin/marketplace.json#L1) (Claude 市场配置), repo:README.md:1

## arch-aci：工具接口与技能调用机制
Superpowers 的工具接口是**技能触发式**——技能本身不是可执行工具，而是通过 SKILL.md 的 YAML frontmatter `description` 字段定义触发条件，宿主 agent（如 Claude Code/Codex）在处理用户请求时，根据 description 匹配决定是否加载该技能的内容到上下文，然后由 agent 解释执行技能中的指令。例如 systematic-debugging 的 description: "Use when encountering any bug, test failure, or unexpected behavior, before proposing fixes"——agent 遇到 bug 时自动加载该技能。技能执行依赖宿主 agent 的原生工具（文件编辑/Shell/Git 等），Superpowers 不提供额外工具接口。技能可含辅助脚本（.sh/.ts/.js），但执行权限由宿主 agent 控制。与 MCP 工具（JSON-RPC 运行时调用）不同，Superpowers 的"工具接口"是文档级触发，无协议通信。溯源：[repo:file:skills/systematic-debugging/SKILL.md:1-5](https://github.com/obra/superpowers/blob/b36e0829c6d0140e93cfef2ca599b1b07d4a7797/skills/systematic-debugging/SKILL.md#L1-L5) (YAML frontmatter name/description), [repo:file:skills/writing-skills/SKILL.md:1](https://github.com/obra/superpowers/blob/b36e0829c6d0140e93cfef2ca599b1b07d4a7797/skills/writing-skills/SKILL.md#L1), [repo:file:skills/systematic-debugging/find-polluter.sh:1](https://github.com/obra/superpowers/blob/b36e0829c6d0140e93cfef2ca599b1b07d4a7797/skills/systematic-debugging/find-polluter.sh#L1) (辅助脚本)

## arch-typing：类型系统与技能 Schema
Superpowers 的类型系统是**轻量 YAML frontmatter schema**——每个 SKILL.md 必须包含 YAML frontmatter，定义两个必填字段：`name`（技能名，kebab-case）和 `description`（触发描述，用于 agent 匹配）。无强制 JSON Schema 或 TypeScript 类型定义，类型约束由约定而非编译器保证。辅助文件无类型约束（.md/.sh/.ts/.dot/.js 自由格式）。plugin.json 仅 5/9 适配目录有（schema 由各平台定义，格式各异：JSON 的 plugin.json / YAML 的 plugin.yaml / JS·TS 代码内联配置），marketplace.json 仅 .claude-plugin 与 .agents 有。writing-skills 技能含 anthropic-best-practices.md（46KB），定义了技能编写的最佳实践（隐含类型规范），但非强制 schema。与强类型技能系统（如 TypeScript DSL 定义技能）不同，Superpowers 选择轻量 YAML + Markdown，获得跨平台通用性但牺牲了类型安全。溯源：[repo:file:skills/systematic-debugging/SKILL.md:1-5](https://github.com/obra/superpowers/blob/b36e0829c6d0140e93cfef2ca599b1b07d4a7797/skills/systematic-debugging/SKILL.md#L1-L5) (YAML frontmatter), [repo:file:skills/writing-skills/anthropic-best-practices.md:1](https://github.com/obra/superpowers/blob/b36e0829c6d0140e93cfef2ca599b1b07d4a7797/skills/writing-skills/anthropic-best-practices.md#L1) (46KB 最佳实践), [repo:file:.codex-plugin/plugin.json:1](https://github.com/obra/superpowers/blob/b36e0829c6d0140e93cfef2ca599b1b07d4a7797/.codex-plugin/plugin.json#L1) (平台特定 schema)

## arch-security：安全模型与权限边界
Superpowers 的安全模型是**宿主代理**——技能本身是 Markdown 文档（无执行能力），所有执行权限由宿主 agent 控制。技能可含辅助脚本（.sh/.ts/.js），但是否执行、如何执行由宿主 agent 的权限系统决定（如 Claude Code 的 PermissionMode、Codex 的沙箱）。技能内容无沙箱隔离——加载到上下文后，agent 可按技能指令执行任何操作（依赖宿主 agent 的安全机制）。技能创建留痕（CREATION-LOG.md，仅 systematic-debugging 一例）提供审计能力，但非运行时安全机制。无技能签名/验证机制——技能来源可信性由分发渠道（npm/GitHub/平台市场）保证。与 MCP 的权限隔离（每个 MCP 服务器独立进程/权限）不同，Superpowers 的技能无独立安全边界，完全依赖宿主。溯源：[repo:file:skills/systematic-debugging/find-polluter.sh:1](https://github.com/obra/superpowers/blob/b36e0829c6d0140e93cfef2ca599b1b07d4a7797/skills/systematic-debugging/find-polluter.sh#L1) (辅助脚本，执行权限由宿主控制), [repo:file:skills/systematic-debugging/CREATION-LOG.md:1](https://github.com/obra/superpowers/blob/b36e0829c6d0140e93cfef2ca599b1b07d4a7797/skills/systematic-debugging/CREATION-LOG.md#L1) (创建留痕审计), repo:README.md:1 (安全说明)

## arch-orchestration：技能编排与工作流组合
Superpowers 的编排是**技能链隐式编排**——14 个技能按开发工作流顺序组织（brainstorming→writing-plans→executing-plans→test-driven-development→systematic-debugging→requesting-code-review→receiving-code-review→verification-before-completion→finishing-a-development-branch），agent 在开发过程中按阶段触发对应技能，形成隐式工作流。显式编排技能：①subagent-driven-development（4 files）——教 agent 如何使用子 agent 分解复杂任务，定义子 agent 创建/任务分配/结果回收流程；②dispatching-parallel-agents（1 file）——教 agent 如何并行调度多个 agent 处理独立子任务；③using-superpowers（1 file）——元编排技能，教 agent 如何在整个 Superpowers 技能集中导航和选择合适技能。无 DAG/状态机引擎，编排完全由 agent 的 LLM 决策驱动（技能内容提供编排指导，但执行顺序由 agent 决定）。与 LangGraph 的显式 DAG 编排不同，Superpowers 是隐式技能链编排，灵活性高但可预测性低。溯源：[repo:file:skills/subagent-driven-development/](https://github.com/obra/superpowers/tree/b36e0829c6d0140e93cfef2ca599b1b07d4a7797/skills/subagent-driven-development/) (子 agent 编排), [repo:file:skills/dispatching-parallel-agents/](https://github.com/obra/superpowers/tree/b36e0829c6d0140e93cfef2ca599b1b07d4a7797/skills/dispatching-parallel-agents/) (并行 agent 调度), [repo:file:skills/using-superpowers/](https://github.com/obra/superpowers/tree/b36e0829c6d0140e93cfef2ca599b1b07d4a7797/skills/using-superpowers/) (技能集导航), [repo:file:skills/](https://github.com/obra/superpowers/tree/b36e0829c6d0140e93cfef2ca599b1b07d4a7797/skills/) (14 技能按工作流组织)

# 其他架构域简评
- arch-patterns：技能链模式 + 纪律性工作流模式，非典型 agent 编排模式
- arch-memory：无独立记忆系统，技能内容是静态文档，记忆由宿主 agent 管理
- arch-context：技能通过 description 匹配加载到上下文，无独立上下文管理机制
- arch-rag：无独立 RAG 模块，技能检索靠 description 匹配（非语义搜索）
- arch-llm-abstraction：完全依赖宿主 agent 的 LLM，无 LLM 抽象层
- arch-evals：writing-skills 含 testing-skills-with-subagents.md（12KB，教如何用子 agent 测试技能），无独立评估框架
- arch-observability：CREATION-LOG.md 创建留痕，无运行时可观测性
- arch-plan-exec：writing-plans + executing-plans 技能强制计划-执行分离，但无独立计划引擎
- arch-streaming：无流式处理，技能是静态文档
- arch-code-intel：技能含代码智能指导（systematic-debugging 的根因追踪），但无独立代码智能工具
- arch-workflow：隐式技能链工作流，无 DAG/状态机引擎
- arch-session：无独立会话管理，由宿主 agent 管理
- arch-exec-backend：无独立执行后端，执行由宿主 agent 的工具系统完成
- arch-frontend：无独立前端，技能在宿主 agent 的 UI 中展示
- arch-checkpoint：无独立检查点机制，Git 版本控制提供技能版本管理
- arch-fault-tolerance：无独立容错机制，由宿主 agent 的错误处理完成

# claim 台账

| claim | 溯源锚点（repo:file:line） | 置信度 |
|---|---|---|
| 14 个标准化开发工作流技能 | [repo:file:skills/](https://github.com/obra/superpowers/tree/b36e0829c6d0140e93cfef2ca599b1b07d4a7797/skills/) (14 子目录) | EXTRACTED |
| 技能格式 SKILL.md（YAML frontmatter name/description + Markdown） | [repo:file:skills/systematic-debugging/SKILL.md:1-5](https://github.com/obra/superpowers/blob/b36e0829c6d0140e93cfef2ca599b1b07d4a7797/skills/systematic-debugging/SKILL.md#L1-L5) | EXTRACTED |
| 9 个平台适配目录（Claude/Codex/Cursor/Devin/Kimi=plugin.json 5 个；OpenCode/PI=运行时代码；Agents/Hermes=marketplace.json·plugin.yaml；~~10 个~~ 2026-09-10 更正，.github 非适配器） | repo:.claude-plugin/, .codex-plugin/, .cursor-plugin/, .devin-plugin/, .kimi-plugin/, .opencode/plugins/superpowers.js, .pi/extensions/superpowers.ts, .agents/plugins/marketplace.json, .hermes-plugin/plugin.yaml（本地实测 2026-09-10） | EXTRACTED |
| npm 分发 superpowers v6.3.0 | [repo:file:package.json:1](https://github.com/obra/superpowers/blob/b36e0829c6d0140e93cfef2ca599b1b07d4a7797/package.json#L1) | EXTRACTED |
| 282,954★ | GitHub API 实测 | EXTRACTED |
| systematic-debugging Iron Law（先找根因再修） | [repo:file:skills/systematic-debugging/SKILL.md:12](https://github.com/obra/superpowers/blob/b36e0829c6d0140e93cfef2ca599b1b07d4a7797/skills/systematic-debugging/SKILL.md#L12) | EXTRACTED |
| writing-skills 元技能（26KB SKILL.md + 46KB anthropic-best-practices） | [repo:file:skills/writing-skills/SKILL.md:1](https://github.com/obra/superpowers/blob/b36e0829c6d0140e93cfef2ca599b1b07d4a7797/skills/writing-skills/SKILL.md#L1) (26KB), [repo:file:skills/writing-skills/anthropic-best-practices.md:1](https://github.com/obra/superpowers/blob/b36e0829c6d0140e93cfef2ca599b1b07d4a7797/skills/writing-skills/anthropic-best-practices.md#L1) (46KB) | EXTRACTED |
| 技能创建留痕 CREATION-LOG.md（仅 systematic-debugging 一例，全仓实测=1） | [repo:file:skills/systematic-debugging/CREATION-LOG.md:1](https://github.com/obra/superpowers/blob/b36e0829c6d0140e93cfef2ca599b1b07d4a7797/skills/systematic-debugging/CREATION-LOG.md#L1) | EXTRACTED |
| 多 agent 协作技能（subagent-driven-development + dispatching-parallel-agents） | [repo:file:skills/subagent-driven-development/](https://github.com/obra/superpowers/tree/b36e0829c6d0140e93cfef2ca599b1b07d4a7797/skills/subagent-driven-development/), [repo:file:skills/dispatching-parallel-agents/](https://github.com/obra/superpowers/tree/b36e0829c6d0140e93cfef2ca599b1b07d4a7797/skills/dispatching-parallel-agents/) | EXTRACTED |
| 技能即文档（Markdown，无执行能力，依赖宿主 agent） | 技能目录全为 .md/.sh/.ts 辅助文件，无独立运行时 | EXTRACTED |
| 插件机制以静态配置为主 + 部分平台运行时适配（plugin.json 5/9；.opencode superpowers.js / .pi superpowers.ts 运行时代码；.hermes pre_llm_call hook） | [repo:file:.codex-plugin/plugin.json:1](https://github.com/obra/superpowers/blob/b36e0829c6d0140e93cfef2ca599b1b07d4a7797/.codex-plugin/plugin.json#L1), [repo:file:.opencode/plugins/superpowers.js:1-5](https://github.com/obra/superpowers/blob/b36e0829c6d0140e93cfef2ca599b1b07d4a7797/.opencode/plugins/superpowers.js#L1-L5), [repo:file:.hermes-plugin/plugin.yaml:1-7](https://github.com/obra/superpowers/blob/b36e0829c6d0140e93cfef2ca599b1b07d4a7797/.hermes-plugin/plugin.yaml#L1-L7)（本地实测 2026-09-10） | EXTRACTED |
| OpenCode 适配器含运行时 bootstrap（message transform 注入上下文 + config hook 自动注册技能目录） | [repo:file:.opencode/plugins/superpowers.js:1-5](https://github.com/obra/superpowers/blob/b36e0829c6d0140e93cfef2ca599b1b07d4a7797/.opencode/plugins/superpowers.js#L1-L5)（2026-09-10 新增，闭环原"npm bootstrap 待确认"部分项） | EXTRACTED |
| Repomix 381,238 tokens（超 100k 阈值，小仓但文档多） | corpus/repos/superpowers/repomix-output.md | EXTRACTED |

# 矛盾记录（Disputed）
无（C10 首张，无同类别 F 卡对比。与 vault① skills/ 域天然关联，可交叉引用——Superpowers 是外部技能生态，vault① skills/ 是内部技能域）。

# 更新记录
- 2026-09-10 **事实纠错（codex 交叉审查反馈 + 编排者一级事实源实测复核，全单 4 项成立）**：①"每个技能含 CREATION-LOG.md"→全仓仅 1 个（systematic-debugging）；②"10 个平台插件目录"→**9 个平台适配目录**（.github=社区配置非适配器）；③"npm 可能含 runtime bootstrap"→实证落地于 .opencode/plugins/superpowers.js（message transform bootstrap）与 .pi/extensions/superpowers.ts（ExtensionAPI），且 .hermes-plugin/plugin.yaml 声明 pre_llm_call hook——三种适配模式改写 arch-plugins 节；④"每目录含 plugin.json"→仅 5/9。快照：.snapshots/F-C10-001-superpowers.pre-factfix-20260910.md。frontmatter repo_commit 不变（非上游漂移，系蒸馏期分析错误）。

# 对照验证
- 对照源：https://deepwiki.com/obra/superpowers（Tier2：DeepWiki 自动生成的代码文档）
- 访问日期：2026-09-08
- 不一致裁决：deepwiki 页面 HTTP 200 可访问，页面标题 "obra/superpowers | DeepWiki"；核心设计与本地蒸馏结论一致（14 标准化技能/npm 分发 v6.3.0/技能即文档/纪律性设计），未发现不一致。**注（2026-09-10）：本次事实纠错涉及的适配目录细节（9 vs 10、CREATION-LOG 数量、runtime bootstrap 位置）超出 deepwiki 页面颗粒度，以本地一级事实源实测为准。**

# 溯源
- repo:package.json（superpowers v6.3.0，npm 分发）
- repo:skills/（14 个技能目录，核心产物）
- repo:skills/systematic-debugging/SKILL.md（9KB，Iron Law 纪律性调试）
- repo:skills/writing-skills/SKILL.md（26KB，元技能，教写技能）
- repo:skills/writing-skills/anthropic-best-practices.md（46KB，技能编写最佳实践）
- repo:skills/subagent-driven-development/（子 agent 编排技能）
- repo:skills/dispatching-parallel-agents/（并行 agent 调度技能）
- repo:.claude-plugin/ + .codex-plugin/ + .cursor-plugin/ + ...（9 平台适配目录；.github 为社区配置非适配器）
- repo:.claude-plugin/plugin.json + marketplace.json（Claude 平台插件配置）
- repo:.opencode/plugins/superpowers.js（OpenCode 运行时 bootstrap，2026-09-10 补录）
- repo:.pi/extensions/superpowers.ts（PI 扩展适配，2026-09-10 补录）
- repo:.hermes-plugin/plugin.yaml（Hermes 适配，provides_hooks: pre_llm_call，2026-09-10 补录）
- repo:.codex-plugin/plugin.json（Codex 平台插件配置）
- repo:README.md + LICENSE
- corpus/repos/superpowers/repomix-output.md（381,238 tokens，留档）
- corpus/repos/superpowers/codemap-map.md（17KB）

# 待补
- [ ] arch-evals 域：是否有独立技能评估框架（writing-skills 含 testing-skills-with-subagents.md 但是指导文档非框架）
- [x] ~~npm runtime bootstrap 具体实现~~（2026-09-10 部分闭环：适配器层实锚 .opencode/plugins/superpowers.js + .pi/extensions/superpowers.ts + .hermes pre_llm_call；npm 包安装路径的 bootstrap 入口仍待实测）
- [ ] 各平台 plugin.json 的具体 schema 差异（5 个含 plugin.json 的目录待对比；.opencode/.pi/.agents/.hermes 为代码/其他格式适配）
- [ ] 本地部署确认（superpowers 已 clone 到 [本机绝对路径已隐藏] install 待执行）

## 更新记录

- 2026-09-14 | LB-R4 30天复扫 | star=286101（285022→286101） | HEAD=b36e0829c6d0140e93cfef2ca599b1b07d4a7797（pinned=b36e0829c6d0140e93cfef2ca599b1b07d4a7797，commit 漂移 b36e0829c6→b36e0829c6） | L1 微漂移标注（CB-11：仅标注，未重蒸馏）| pushed_at=2026-09-12 archived=false | 锚点 repo_base_url/repo_local_path 不动
