---
id: F-C03-001
title: claude-code：CLI 编码 Agent（查询引擎驱动 + 60+ 工具生态 + LSP 代码智能，source-leak）
tags: [framework-profile, arch-orchestration, arch-context, arch-aci, arch-code-intel, arch-session, arch-security, arch-prompting]
created: 2026-09-08
category: C03
alt: []
repo_url: source-leak:[本机绝对路径已隐藏](仅用于学习交流)/claude-code-main
repo_commit: source-leak
repo_base_url: null
repo_local_path: [本机绝对路径已隐藏](仅用于学习交流)/
star: null
distilled_at: 2026-09-08
freshness: dated
workflow: source-leak
sources: []
---

# 框架总评
## 设计哲学出发点
claude-code 定位为"命令行编码 Agent"（CLI coding agent），核心取舍是把**编码工作流**原生嵌入终端——agent 直接在用户的工作目录中操作文件、执行命令、调用语言服务器，而非在隔离沙箱中运行。设计哲学是"agent as terminal power user"：agent 拥有与资深开发者相同的工具集（文件编辑/Shell/Grep/LSP/Git/Web 搜索），通过工具调用循环完成编码任务，用户通过权限系统控制 agent 的操作范围。claude-code 基于 Anthropic Claude API，TypeScript 实现（claude-js v1.0.2），NAPI 原生模块扩展（音频捕获/图像处理/颜色差异/URL 处理）。

## 设计特点
- 查询引擎驱动的 agent 循环：QueryEngine.ts（48KB）+ query.ts（69KB），核心决策循环
- 60+ 工具生态系统：文件操作（FileRead/FileEdit/FileWrite/Glob/Grep）、代码智能（LSPTool 语言服务器协议）、Shell（Bash/PowerShell/REPL）、MCP 协议（MCPTool/McpAuthTool）、任务管理（TaskCreate/Get/List/Output/Stop/Update）、技能系统（SkillTool/DiscoverSkillsTool）、计划模式（EnterPlanMode/ExitPlanMode/VerifyPlanExecution）、Worktree 隔离（EnterWorktree/ExitWorktree）、Web 工具（WebBrowser/WebFetch/WebSearch）、团队协作（TeamCreate/TeamDelete）
- 权限系统：PermissionMode + CanUseToolFn，工具调用需用户确认（按需授权），支持权限模式切换
- 记忆系统：memdir/（记忆目录，loadMemoryPrompt 加载记忆到系统提示）
- 子 agent 协作：AgentTool + AgentDefinition（agents/ 目录定义子 agent，多 agent 分工）
- 文件历史快照：fileHistory + FileStateCache（文件状态快照，支持撤销/重做/回滚）
- 计划-执行分离：EnterPlanModeTool 进入计划模式（只读，不执行修改），VerifyPlanExecutionTool 验证计划执行
- 成本追踪：cost-tracker.ts（10KB）+ accumulateUsage/updateUsage，实时显示 token 消耗和费用
- 会话持久化：sessionStorage + recordTranscript，会话历史可恢复/重放
- 插件系统：pluginLoader，支持运行时插件扩展
- 多模式：Vim 模式（vim/）、语音（voice/）、伙伴模式（buddy/）、主动式（proactive/）
- CLI 界面：Ink（React CLI 渲染）+ screens/ + components/ + keybindings/

## 痛点
解决开发者在终端中反复执行机械编码操作的痛点——文件编辑、代码搜索、重构、测试、调试等重复性工作可以由 agent 自动化完成。claude-code 不解决通用 agent 编排问题，专注编码工作流：文件操作原生、Shell 执行原生、LSP 代码智能原生、Git 操作原生。与通用 agent 框架（LangChain/AutoGen）不同，claude-code 是垂直编码 agent，工具集和交互模式专为编码优化。

## 优缺点
- 优点：60+ 工具生态覆盖完整编码工作流；LSPTool 提供真正的代码智能（跳转/补全/重构/诊断）；权限系统安全可控（按需授权）；文件历史快照支持撤销/回滚；计划模式支持计划-执行分离；子 agent 协作支持复杂任务分工；成本追踪透明；会话持久化可恢复；TypeScript 类型安全；NAPI 原生模块性能好
- 缺点：绑定 Anthropic Claude API（非提供商无关）；source-leak 源码无官方 git 历史/版本标签；60+ 工具导致系统提示庞大（token 开销）；权限确认打断 agent 自主执行流；CLI 界面学习曲线（Vim 模式/快捷键）；大仓库上下文管理挑战（query.ts 69KB 单文件过大）；计划模式与执行模式切换增加交互复杂度

## 关键取舍
最核心的取舍是"垂直编码 agent" vs "通用 agent 框架"——claude-code 选择垂直编码，工具集和交互模式专为编码优化（LSP/文件/Shell/Git 原生），但牺牲了通用性（不能直接用于非编码任务）。另一个取舍是"权限确认安全" vs "agent 自主执行"——claude-code 选择权限确认（CanUseToolFn + PermissionMode），工具调用需用户确认，安全可控但打断自主执行流。第三个取舍是"计划-执行分离" vs "端到端执行"——claude-code 提供计划模式（EnterPlanModeTool 只读规划 + VerifyPlanExecutionTool 验证执行），支持复杂任务先规划后执行，但增加了交互步骤。

# 核心深挖域

## arch-orchestration：agent 主循环与决策机制
claude-code 的核心是**查询引擎驱动的 agent 循环**：QueryEngine.ts（48KB，1240+ 行）管理会话状态、工具权限、成本追踪、错误重试，query.ts（69KB）实现核心 LLM 查询循环——接收用户输入 → 构建系统提示（fetchSystemPromptParts）→ 调用 Claude API（@anthropic-ai/sdk）→ 解析工具调用 → 执行工具（ToolUseContext）→ 观察结果 → 循环直到完成。错误处理通过 categorizeRetryableAPIError 分类可重试 API 错误并自动重试。子 agent 协作通过 AgentTool + AgentDefinition（agents/ 目录定义子 agent）实现，主 agent 可委派任务给子 agent。计划模式通过 EnterPlanModeTool/ExitPlanModeTool 实现计划-执行分离——计划模式下 agent 只读不写，输出计划后由用户确认再执行。溯源：[repo:file:claude-code-main/src/QueryEngine.ts:1](file:/[本机绝对路径已隐藏]) (QueryEngine 类 48KB), [repo:file:claude-code-main/src/query.ts:1](file:/[本机绝对路径已隐藏]) (核心查询循环 69KB), [repo:file:claude-code-main/src/Tool.ts:1](file:/[本机绝对路径已隐藏]) (Tool 统一接口), [repo:file:claude-code-main/src/tools/AgentTool/loadAgentsDir.ts:1](file:/[本机绝对路径已隐藏]) (子 agent 定义)

## arch-context：上下文窗口管理与记忆注入
上下文管理通过多层机制实现：①系统提示构建（fetchSystemPromptParts + asSystemPrompt），聚合工具定义/环境信息/记忆/技能等多个部分；②记忆注入（memdir/ 目录，loadMemoryPrompt 加载记忆文件到系统提示，hasAutoMemPathOverride 支持自定义记忆路径）；③上下文压缩（SYNTHETIC_OUTPUT_TOOL_NAME + SyntheticOutputTool，合成输出工具压缩历史）；④文件状态缓存（FileStateCache + cloneFileStateCache，避免重复读取文件）；⑤会话边界（SDKCompactBoundaryMessage + SystemCompactBoundaryMessage，标记会话边界用于上下文截断）。memdir 是 claude-code 的持久记忆系统——记忆以文件形式存储在 memdir/ 目录，agent 启动时 loadMemoryPrompt 加载到系统提示，agent 可通过工具编辑记忆文件。与 letta 的 MemFS+Git 版本化记忆不同，claude-code 的 memdir 是简单文件记忆（无版本控制）。溯源：[repo:file:claude-code-main/src/utils/queryContext.ts:1](file:/[本机绝对路径已隐藏]) (fetchSystemPromptParts), [repo:file:claude-code-main/src/memdir/memdir.ts:1](file:/[本机绝对路径已隐藏]) (loadMemoryPrompt), [repo:file:claude-code-main/src/tools/SyntheticOutputTool/SyntheticOutputTool.ts:1](file:/[本机绝对路径已隐藏]) (上下文压缩), [repo:file:claude-code-main/src/utils/fileStateCache.ts:1](file:/[本机绝对路径已隐藏]) (FileStateCache)

## arch-aci：工具调用接口与 MCP 生态
工具系统是 claude-code 的核心能力——60+ 工具通过 Tool.ts 统一接口（Tools 类型 + ToolUseContext + toolMatchesName）注册和调度。工具分类：①文件操作（FileReadTool/FileEditTool/FileWriteTool/GlobTool/GrepTool/NotebookEditTool）；②代码智能（LSPTool 语言服务器协议，支持跳转/补全/重构/诊断）；③Shell 执行（BashTool/PowerShellTool/REPLTool/TerminalCaptureTool）；④MCP 协议（MCPTool/McpAuthTool/ListMcpResourcesTool/ReadMcpResourceTool，原生支持 Model Context Protocol）；⑤任务管理（TaskCreateTool/TaskGetTool/TaskListTool/TaskOutputTool/TaskStopTool/TaskUpdateTool，后台任务队列）；⑥技能系统（SkillTool/DiscoverSkillsTool，技能发现和加载）；⑦Web 工具（WebBrowserTool/WebFetchTool/WebSearchTool）；⑧团队协作（TeamCreateTool/TeamDeleteTool）；⑨定时任务（ScheduleCronTool）；⑩监控（MonitorTool）。权限控制通过 CanUseToolFn + PermissionMode 实现——每个工具调用前检查权限，需用户确认的工具弹出确认对话框。MCP 支持通过 services/mcp/ 实现，MCPServerConnection 管理 MCP 服务器连接。溯源：[repo:file:claude-code-main/src/Tool.ts:1](file:/[本机绝对路径已隐藏]) (Tool 统一接口), [repo:file:claude-code-main/src/tools/LSPTool/](file:/[本机绝对路径已隐藏]) (LSP 代码智能), [repo:file:claude-code-main/src/tools/MCPTool/](file:/[本机绝对路径已隐藏]) (MCP 协议), [repo:file:claude-code-main/src/hooks/useCanUseTool.ts:1](file:/[本机绝对路径已隐藏]) (CanUseToolFn 权限控制)

## arch-code-intel：代码智能与 LSP 集成
代码智能是 claude-code 区别于通用 agent 的核心能力——**LSPTool**（语言服务器协议工具）提供真正的代码智能：跳转定义（go-to-definition）、查找引用（find-references）、代码补全（completion）、重构（rename/extract）、诊断（diagnostics/errors）、悬停信息（hover）、符号搜索（workspace-symbol）。LSPTool 与项目的语言服务器（如 TypeScript Server/Pyright/Clangd）通信，获取结构化代码信息，而非纯文本搜索。辅助代码智能工具：GrepTool（正则搜索）、GlobTool（文件模式匹配）、FileReadTool（文件读取）、FileEditTool（精确文件编辑，支持行号/范围替换）、NotebookEditTool（Jupyter 笔记本编辑）。文件历史快照（fileHistory + FileStateCache + fileHistoryMakeSnapshot）支持文件级撤销/重做/回滚——agent 修改文件前自动快照，用户可回滚到任意历史版本。与 graphiti 的知识图谱代码智能不同，claude-code 是 LSP 协议级代码智能，与 IDE 同等能力。溯源：[repo:file:claude-code-main/src/tools/LSPTool/](file:/[本机绝对路径已隐藏]) (LSP 语言服务器协议), [repo:file:claude-code-main/src/tools/FileEditTool/](file:/[本机绝对路径已隐藏]) (精确文件编辑), [repo:file:claude-code-main/src/utils/fileHistory.ts:1](file:/[本机绝对路径已隐藏]) (文件历史快照), [repo:file:claude-code-main/src/tools/GrepTool/](file:/[本机绝对路径已隐藏]) (正则搜索)

## arch-session：会话管理与持久化
会话管理通过多层机制实现：①会话 ID（getSessionId，bootstrap/state.ts），每个会话唯一标识；②会话持久化（flushSessionStorage + recordTranscript，sessionStorage 持久化会话状态，recordTranscript 记录完整对话 transcript）；③会话发现（assistant/sessionDiscovery.ts + AssistantSessionChooser.ts，列出和选择历史会话）；④会话历史（assistant/sessionHistory.ts，会话历史管理）；⑤会话重放（SDKUserMessageReplay，支持重放用户消息）；⑥会话边界（SDKCompactBoundaryMessage + SystemCompactBoundaryMessage，标记会话边界用于上下文截断和压缩）。状态管理通过 AppState（state/AppState.ts）集中管理应用状态，包括会话状态/工具状态/权限状态/成本状态。会话持久化可禁用（isSessionPersistenceDisabled，隐私模式）。与 mem0 的向量记忆持久化不同，claude-code 的会话持久化是完整 transcript 存储（可恢复/重放）。溯源：[repo:file:claude-code-main/src/bootstrap/state.ts:1](file:/[本机绝对路径已隐藏]) (getSessionId), [repo:file:claude-code-main/src/utils/sessionStorage.ts:1](file:/[本机绝对路径已隐藏]) (flushSessionStorage/recordTranscript), [repo:file:claude-code-main/src/assistant/sessionDiscovery.ts:1](file:/[本机绝对路径已隐藏]) (会话发现), [repo:file:claude-code-main/src/state/AppState.ts:1](file:/[本机绝对路径已隐藏]) (AppState 集中状态)

## arch-security：权限控制与安全边界
安全是 claude-code 的核心设计——**权限系统**（PermissionMode + CanUseToolFn + SDKPermissionDenial）控制 agent 的操作边界：每个工具调用前检查权限，需用户确认的工具（如 BashTool/FileEditTool）弹出确认对话框，用户可选择允许/拒绝/始终允许/始终拒绝。权限模式支持切换（如只读模式/全自动模式/按需确认模式）。安全边界：①Worktree 隔离（EnterWorktreeTool/ExitWorktreeTool，agent 在独立 Git worktree 中操作，不污染主工作区）；②计划模式（EnterPlanModeTool，只读模式，agent 不能执行修改操作）；③SSH 支持（ssh/ 目录，安全远程访问）；④沙箱执行（environment-runner/ + self-hosted-runner/，代码执行环境隔离）；⑤文件权限（FileStateCache + 文件历史快照，修改可回滚）；⑥MCP 认证（McpAuthTool，MCP 服务器连接需认证）；⑦上游代理（upstreamproxy/，网络请求代理控制）。与 letta 的 Git 签名验证不同，claude-code 的安全是运行时权限控制（工具级确认）。溯源：[repo:file:claude-code-main/src/hooks/useCanUseTool.ts:1](file:/[本机绝对路径已隐藏]) (CanUseToolFn), [repo:file:claude-code-main/src/entrypoints/agentSdkTypes.ts:1](file:/[本机绝对路径已隐藏]) (PermissionMode/SDKPermissionDenial), [repo:file:claude-code-main/src/tools/EnterWorktreeTool/](file:/[本机绝对路径已隐藏]) (Worktree 隔离), [repo:file:claude-code-main/src/ssh/](file:/[本机绝对路径已隐藏]) (SSH 安全远程)

## arch-prompting：系统提示与工具提示工程
提示工程是 claude-code 的核心竞争力——系统提示通过 fetchSystemPromptParts 聚合多个部分：①工具定义（60+ 工具的名称/描述/参数 schema，注入到 Claude API 的 tools 参数）；②环境信息（cwd/OS/Shell/Git 状态等）；③记忆（memdir/ 记忆文件，loadMemoryPrompt）；④技能（已加载技能的定义和使用说明）；⑤系统指令（asSystemPrompt，agent 角色定义和行为规范）；⑥ slash 命令技能（getSlashCommandToolSkills，斜杠命令触发的技能）。工具提示工程：每个工具的 description 精心设计，告诉 agent 何时使用该工具、如何使用、注意事项。计划模式提示：EnterPlanModeTool 进入计划模式时注入计划模式专用系统提示（只读/输出计划格式/不执行修改）。结构化输出强制（registerStructuredOutputEnforcement，确保 LLM 输出符合工具调用 schema）。与 mem0 的 ADDITIVE_EXTRACTION_PROMPT 单一提取提示不同，claude-code 的系统提示是多层聚合的复杂提示工程。溯源：[repo:file:claude-code-main/src/utils/queryContext.ts:1](file:/[本机绝对路径已隐藏]) (fetchSystemPromptParts), [repo:file:claude-code-main/src/utils/systemPromptType.ts:1](file:/[本机绝对路径已隐藏]) (asSystemPrompt), [repo:file:claude-code-main/src/memdir/memdir.ts:1](file:/[本机绝对路径已隐藏]) (loadMemoryPrompt 记忆注入), [repo:file:claude-code-main/src/utils/hooks/hookHelpers.ts:1](file:/[本机绝对路径已隐藏]) (registerStructuredOutputEnforcement)

# 其他架构域简评
- arch-patterns：工具调用循环模式（ReAct 变体）+ 计划-执行分离模式 + 子 agent 协作模式
- arch-memory：memdir/ 文件记忆（loadMemoryPrompt 注入系统提示），无向量检索/图谱记忆，记忆规模受上下文窗口限制
- arch-rag：无独立 RAG 模块，代码检索通过 LSPTool/GrepTool/GlobTool 实现（工具级检索，非语义 RAG）
- arch-llm-abstraction：绑定 Anthropic Claude API（@anthropic-ai/sdk），非提供商无关；getMainLoopModel/parseUserSpecifiedModel 支持模型选择
- arch-evals：无独立评估框架，OverflowTestTool（溢出测试工具）用于测试上下文边界，integration-tests/ 目录含集成测试
- arch-observability：cost-tracker.ts 成本追踪 + accumulateUsage token 统计 + getInMemoryErrors 错误日志 + headlessProfiler 性能分析
- arch-plan-exec：显式计划-执行分离（EnterPlanModeTool/ExitPlanModeTool/VerifyPlanExecutionTool），计划模式只读不写
- arch-streaming：支持流式输出（Ink 实时渲染 + BetaMessageDeltaUsage 流式 token 统计），WebSocket 实时通信
- arch-skill-philosophy：skills/ 目录 + SkillTool/DiscoverSkillsTool，技能可发现可加载，技能通过系统提醒注入（非 per-project 记忆块）
- arch-workflow：WorkflowTool 工作流工具 + ScheduleCronTool 定时任务 + TaskCreateTool 任务队列，支持简单工作流编排
- arch-typing：TypeScript 强类型贯穿（@types + Pydantic 等价为 Zod/TS 接口），NAPI 原生模块有类型定义
- arch-distribution：npm 发布（claude-js v1.0.2），支持 npm install -g 全局安装，插件系统支持扩展
- arch-exec-backend：Node.js 运行时 + NAPI 原生模块（音频/图像/颜色），Bun 打包（bun:bundle feature flag）
- arch-frontend：Ink（React CLI 渲染）+ screens/ + components/ + keybindings/，交互式终端 UI，支持 Vim 模式
- arch-checkpoint：文件历史快照（fileHistory + FileStateCache）+ 会话持久化（sessionStorage），支持文件级和会话级回滚
- arch-plugins：plugins/ 目录 + pluginLoader（loadAllPluginsCacheOnly），支持运行时插件扩展，无插件市场
- arch-fault-tolerance：categorizeRetryableAPIError 自动重试 + 文件历史快照回滚 + 权限确认防误操作 + Worktree 隔离防污染，无自动熔断

# claim 台账

| claim | 溯源锚点（source:path:line） | 置信度 |
|---|---|---|
| 查询引擎驱动 agent 循环（QueryEngine 48KB + query 69KB） | [repo:file:claude-code-main/src/QueryEngine.ts:1](file:/[本机绝对路径已隐藏]), [repo:file:claude-code-main/src/query.ts:1](file:/[本机绝对路径已隐藏]) | EXTRACTED |
| 60+ 工具生态（文件/LSP/Shell/MCP/任务/技能/计划/Web/团队） | [repo:file:claude-code-main/src/tools/](file:/[本机绝对路径已隐藏]) (60+ 工具子目录) | EXTRACTED |
| LSPTool 语言服务器协议代码智能 | [repo:file:claude-code-main/src/tools/LSPTool/](file:/[本机绝对路径已隐藏]) | EXTRACTED |
| 权限系统（PermissionMode + CanUseToolFn） | [repo:file:claude-code-main/src/hooks/useCanUseTool.ts:1](file:/[本机绝对路径已隐藏]), [repo:file:claude-code-main/src/entrypoints/agentSdkTypes.ts:1](file:/[本机绝对路径已隐藏]) | EXTRACTED |
| memdir 文件记忆（loadMemoryPrompt 注入系统提示） | [repo:file:claude-code-main/src/memdir/memdir.ts:1](file:/[本机绝对路径已隐藏]) | EXTRACTED |
| 子 agent 协作（AgentTool + AgentDefinition） | [repo:file:claude-code-main/src/tools/AgentTool/loadAgentsDir.ts:1](file:/[本机绝对路径已隐藏]) | EXTRACTED |
| 文件历史快照（fileHistory + FileStateCache） | [repo:file:claude-code-main/src/utils/fileHistory.ts:1](file:/[本机绝对路径已隐藏]), [repo:file:claude-code-main/src/utils/fileStateCache.ts:1](file:/[本机绝对路径已隐藏]) | EXTRACTED |
| 计划-执行分离（EnterPlanMode/ExitPlanMode/VerifyPlanExecution） | [repo:file:claude-code-main/src/tools/EnterPlanModeTool/](file:/[本机绝对路径已隐藏]), [repo:file:claude-code-main/src/tools/VerifyPlanExecutionTool/](file:/[本机绝对路径已隐藏]) | EXTRACTED |
| Worktree 隔离（EnterWorktree/ExitWorktree） | [repo:file:claude-code-main/src/tools/EnterWorktreeTool/](file:/[本机绝对路径已隐藏]) | EXTRACTED |
| MCP 协议原生支持（MCPTool/McpAuthTool） | [repo:file:claude-code-main/src/tools/MCPTool/](file:/[本机绝对路径已隐藏]), [repo:file:claude-code-main/src/services/mcp/](file:/[本机绝对路径已隐藏]) | EXTRACTED |
| 成本追踪（cost-tracker 10KB + accumulateUsage） | [repo:file:claude-code-main/src/cost-tracker.ts:1](file:/[本机绝对路径已隐藏]), [repo:file:claude-code-main/src/services/api/claude.ts:1](file:/[本机绝对路径已隐藏]) | EXTRACTED |
| 绑定 Anthropic Claude API（非提供商无关） | [repo:file:claude-code-main/src/QueryEngine.ts:2](file:/[本机绝对路径已隐藏]) (@anthropic-ai/sdk import) | EXTRACTED |
| TypeScript 实现（claude-js v1.0.2） | [repo:file:claude-code-main/package.json](file:/[本机绝对路径已隐藏]) (name/version) | EXTRACTED |
| NAPI 原生模块（音频/图像/颜色/URL） | [repo:file:claude-code-main/packages/](file:/[本机绝对路径已隐藏]) (6 个 NAPI 模块) | EXTRACTED |
| source-leak 源码无官方 git 历史 | 源码目录无 .git（用户提供 source-leak） | EXTRACTED |

# 矛盾记录（Disputed）
无（C03 首张，无同类别 F 卡对比）。

# 对照验证
- 对照源：社区分析 URL（source-leak 无官方文档，Tier3：无覆盖）
- 访问日期：2026-09-08
- 不一致裁决：source-leak 通道无官方文档/DeepWiki 覆盖（Tier3），对照验证基于源码精读 + 社区公开信息。核心设计（查询引擎/60+ 工具/LSP/权限/memdir/计划模式/Worktree）与社区公开的 claude-code 功能描述一致，未发现不一致。

# 溯源
- [repo:file:claude-code-main/src/QueryEngine.ts（48KB，查询引擎，会话/权限/成本/错误管理）](file:/[本机绝对路径已隐藏])
- [repo:file:claude-code-main/src/query.ts（69KB，核心](file:/[本机绝对路径已隐藏]) LLM 查询循环）
- [repo:file:claude-code-main/src/Tool.ts（Tool](file:/[本机绝对路径已隐藏]) 统一接口）
- [repo:file:claude-code-main/src/tools/（60+](file:/[本机绝对路径已隐藏]) 工具子目录，核心能力）
- [repo:file:claude-code-main/src/tools/LSPTool/（LSP](file:/[本机绝对路径已隐藏]) 语言服务器协议，代码智能核心）
- [repo:file:claude-code-main/src/tools/MCPTool/](file:/[本机绝对路径已隐藏]) + src/services/mcp/（MCP 协议支持）
- [repo:file:claude-code-main/src/memdir/（记忆目录，loadMemoryPrompt）](file:/[本机绝对路径已隐藏])
- [repo:file:claude-code-main/src/hooks/useCanUseTool.ts（权限控制）](file:/[本机绝对路径已隐藏])
- [repo:file:claude-code-main/src/state/AppState.ts（集中状态管理）](file:/[本机绝对路径已隐藏])
- [repo:file:claude-code-main/src/utils/fileHistory.ts](file:/[本机绝对路径已隐藏]) + fileStateCache.ts（文件历史快照）
- [repo:file:claude-code-main/src/cost-tracker.ts（成本追踪）](file:/[本机绝对路径已隐藏])
- [repo:file:claude-code-main/package.json（claude-js](file:/[本机绝对路径已隐藏]) v1.0.2）
- [repo:file:claude-code-main/packages/（6](file:/[本机绝对路径已隐藏]) 个 NAPI 原生模块）
- corpus/repos/claude-code/repomix-output.md（全量 Repomix 产物 1.92M tokens，留档）
- corpus/repos/claude-code/codemap-map.md（codemap 地图 242KB）

# 待补
- [ ] arch-evals 域：是否有独立评估框架（OverflowTestTool 是测试工具非评估框架）
- [ ] query.ts（69KB）核心循环细节待精读（工具调用解析/错误处理/流式输出）
- [ ] MCP 协议实现细节（services/mcp/ 待精读）
- [ ] 子 agent 协作机制（AgentTool 如何委派/回收结果）
- [ ] 社区分析 URL 补充（source-leak Tier3 对照验证源）
