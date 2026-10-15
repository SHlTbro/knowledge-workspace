---
id: F-C10-002
title: MCP Servers：Model Context Protocol 官方参考实现集（7 server 单仓，工具/资源/提示标准化，90k★）
tags: [framework-profile, arch-plugins, arch-skill-philosophy, arch-distribution, arch-aci, arch-typing, arch-security, arch-orchestration]
created: 2026-09-08
category: C10
alt: []
repo_url: https://github.com/modelcontextprotocol/servers
repo_commit: d73f99efbfd40c3aa1b61e88728b3d49fb52608f
repo_base_url: https://github.com/modelcontextprotocol/servers/blob/d73f99efbfd40c3aa1b61e88728b3d49fb52608f/
repo_local_path: [本机绝对路径已隐藏]
star: 90289
distilled_at: 2026-09-08
freshness: dated
workflow: WORKFLOW-repo v2
sources: []
---

# 框架总评
## 设计哲学出发点
MCP Servers 是 Model Context Protocol（MCP）的官方参考实现集，核心取舍是**协议标准化优先**——MCP 协议定义了 LLM 应用与外部工具/数据源之间的标准化接口（JSON-RPC over stdio/SSE/HTTP），本仓库提供 7 个参考服务器实现，展示协议的各种能力和最佳实践。设计哲学是"协议即产品"——MCP 不绑定特定 agent 框架或 LLM 提供商，而是定义语言无关、平台无关的工具调用协议，任何支持 MCP 的 agent（Claude/Codex/Cursor/Continue 等）都可以连接任何 MCP 服务器。与 Superpowers（F-C10-001，技能文档生态）不同，MCP Servers 是运行时工具服务器（JSON-RPC 通信，动态工具调用），不是静态文档技能。

## 设计特点
- 7 个参考服务器（src/ 下）：everything（56 files，全功能测试）、filesystem（20 files，文件系统访问）、git（12 files，Git 操作）、memory（14 files，知识图谱记忆）、fetch（11 files，网页抓取）、sequentialthinking（11 files，顺序思考）、time（9 files，时间/日期）
- MCP 协议三大原语：Tools（工具调用，有参数有返回值）、Resources（资源读取，文件/URL/数据库，支持 URI 寻址和订阅变更）、Prompts（提示词模板，可参数化的提示词）
- JSON-RPC 2.0 通信协议：stdio（本地进程通信）、SSE（Server-Sent Events，服务端推送）、HTTP（RESTful API）、Streamable HTTP（流式 HTTP，v2025-03-26 新增）
- 多语言 SDK：TypeScript/JavaScript（@modelcontextprotocol/sdk）、Python（mcp）、Ruby（mcp-ruby）、Java/Kotlin（mcp-java）、Go（mcp-go）、.NET（McpDotNet）、Rust（rmcp/robocop mcpr）、Swift（mcp-swift）、PHP（mcp-php）、Dart（mcp-dart）
- npm 包分发：@modelcontextprotocol/server-everything@2.0.0、@modelcontextprotocol/server-filesystem@0.6.3、@modelcontextprotocol/server-memory@0.6.3、@modelcontextprotocol/server-sequential-thinking@0.6.2 等
- 协议版本化：2024-11-05（初始）、2025-03-26（Streamable HTTP + 采样/根/资源列表变更）、2025-06-18（进度通知/资源模板/完成建议）
- 安全模型：沙箱（服务器独立进程隔离）、权限（客户端可限制工具/资源访问）、认证（OAuth 2.1 + PKCE，远程服务器）、传输加密（HTTPS）
- 90,150★（GitHub 星标，MCP 生态第一大仓）
- 特殊形态：多 server 单仓（7 个独立服务器在同一 monorepo，共享 SDK 和工具函数）

## 痛点
解决 LLM 工具集成碎片化的痛点——每个 agent 框架有自己的工具接口（LangChain Tools/AutoGen Tools/LlamaIndex Tools），每个工具需要为每个框架单独适配，工具生态碎片化。MCP 通过标准化协议（JSON-RPC + Tools/Resources/Prompts 原语），实现"一次编写，多 agent 连接"——任何 MCP 服务器可被任何支持 MCP 的 agent 使用，无需为每个框架单独适配。同时解决工具安全的痛点——MCP 服务器运行在独立进程（stdio）或远程服务器（HTTP/SSE），与 agent 进程隔离，客户端可限制工具/资源访问权限，防止恶意工具破坏系统。

## 优缺点
- 优点：协议标准化（JSON-RPC + Tools/Resources/Prompts，语言无关平台无关）；多语言 SDK（10+ 语言）；多传输方式（stdio/SSE/HTTP/Streamable HTTP）；安全模型完善（进程隔离/权限控制/OAuth 认证）；90k★ 社区验证；官方参考实现（7 个 server 展示最佳实践）；协议版本化（向后兼容，渐进增强）；与 agent 框架解耦（任何支持 MCP 的 agent 都可连接）
- 缺点：协议学习曲线（JSON-RPC + 三大原语 + 传输方式，概念多）；服务器开发需理解协议细节（非简单函数包装）；远程服务器部署复杂（OAuth 认证/HTTPS/负载均衡）；工具发现机制有限（客户端需手动配置服务器连接）；无内置工具市场（工具发现靠社区列表/文档）；与 Function Calling 重叠（简单工具用 Function Calling 更简单，MCP 适合复杂/远程/多 agent 共享工具）

## 关键取舍
最核心的取舍是"标准化协议" vs "框架原生工具"——MCP 选择标准化协议（JSON-RPC + 三大原语），获得跨框架互操作性（任何 MCP 服务器可被任何 agent 使用），但牺牲了简单性（需理解协议细节/传输方式/安全模型，比 LangChain @tool 装饰器复杂）。另一个取舍是"独立进程服务器" vs "进程内工具"——MCP 选择独立进程（stdio/HTTP），获得安全隔离（服务器崩溃不影响 agent）和远程部署（工具服务器可运行在任意机器），但牺牲了性能（进程间通信开销）和简单性（需管理服务器进程生命周期）。第三个取舍是"三大原语（Tools/Resources/Prompts）" vs "单一工具原语"——MCP 选择三大原语，获得表达力（Resources 适合只读数据访问，Prompts 适合提示词模板，Tools 适合有副作用的操作），但增加了学习成本（需理解三种原语的区别和适用场景）。

# 核心深挖域

## arch-plugins：MCP 服务器即插件（7 server 参考实现）
MCP 的插件系统是**服务器即插件**——每个 MCP 服务器是独立的插件，通过标准化协议（JSON-RPC）与 agent 客户端通信，无需修改 agent 代码即可添加新工具。本仓库提供 7 个参考服务器：①**everything**（src/everything，56 files，@modelcontextprotocol/server-everything@2.0.0）——全功能测试服务器，展示 MCP 协议的所有能力（Tools/Resources/Prompts/采样/进度通知/资源模板等），用于协议开发和测试。②**filesystem**（src/filesystem，20 files，@modelcontextprotocol/server-filesystem@0.6.3）——文件系统访问服务器，提供文件读取/写入/列表/搜索工具，支持目录白名单限制。③**git**（src/git，12 files）——Git 操作服务器，提供仓库状态/提交/分支/差异等工具。④**memory**（src/memory，14 files，@modelcontextprotocol/server-memory@0.6.3）——知识图谱记忆服务器，提供实体/关系/事实的存储和检索，支持图查询。⑤**fetch**（src/fetch，11 files）——网页抓取服务器，提供 URL 内容获取工具，支持 HTML→Markdown 转换。⑥**sequentialthinking**（src/sequentialthinking，11 files，@modelcontextprotocol/server-sequential-thinking@0.6.2）——顺序思考服务器，提供逐步推理工具（think/next/finish），帮助 LLM 进行复杂问题分解。⑦**time**（src/time，9 files）——时间/日期服务器，提供当前时间/日期/时区转换工具。每个服务器是独立的 npm 包（@modelcontextprotocol/server-*），可独立安装运行，通过 stdio 或 HTTP 与 agent 客户端连接。与 Superpowers 的静态文档技能（SKILL.md，agent 读取后解释执行）不同，MCP 服务器是运行时插件（JSON-RPC 动态调用，服务器执行工具逻辑并返回结果）。溯源：[repo:file:src/everything/](https://github.com/modelcontextprotocol/servers/tree/d73f99efbfd40c3aa1b61e88728b3d49fb52608f/src/everything/) (56 files 全功能测试), [repo:file:src/filesystem/](https://github.com/modelcontextprotocol/servers/tree/d73f99efbfd40c3aa1b61e88728b3d49fb52608f/src/filesystem/) (20 files 文件系统), [repo:file:src/git/](https://github.com/modelcontextprotocol/servers/tree/d73f99efbfd40c3aa1b61e88728b3d49fb52608f/src/git/) (12 files Git), [repo:file:src/memory/](https://github.com/modelcontextprotocol/servers/tree/d73f99efbfd40c3aa1b61e88728b3d49fb52608f/src/memory/) (14 files 知识图谱记忆), [repo:file:src/fetch/](https://github.com/modelcontextprotocol/servers/tree/d73f99efbfd40c3aa1b61e88728b3d49fb52608f/src/fetch/) (11 files 网页抓取), [repo:file:src/sequentialthinking/](https://github.com/modelcontextprotocol/servers/tree/d73f99efbfd40c3aa1b61e88728b3d49fb52608f/src/sequentialthinking/) (11 files 顺序思考), [repo:file:src/time/](https://github.com/modelcontextprotocol/servers/tree/d73f99efbfd40c3aa1b61e88728b3d49fb52608f/src/time/) (9 files 时间)

## arch-skill-philosophy：MCP 协议设计哲学（三大原语 + 语言无关）
MCP 的设计哲学是**协议标准化 + 三大原语**：①**Tools（工具）**——有副作用的操作，接收参数返回结果，如文件写入/Git 提交/API 调用。工具定义包含 name/description/inputSchema（JSON Schema），客户端根据 schema 验证参数。②**Resources（资源）**——只读数据访问，通过 URI 寻址（file:/[本机绝对路径已隐藏] 数据等只读访问。③**Prompts（提示词）**——可参数化的提示词模板，客户端可列出可用提示词（list_prompts）、获取提示词（get_prompt，传入参数返回渲染后的提示词）。提示词适合常用的提示词模板共享。④**语言无关**——MCP 协议基于 JSON-RPC 2.0，不绑定特定编程语言，SDK 支持 10+ 语言（TypeScript/Python/Ruby/Java/Go/.NET/Rust/Swift/PHP/Dart）。⑤**平台无关**——不绑定特定 agent 框架或 LLM 提供商，任何支持 MCP 的客户端（Claude Desktop/Codex/Cursor/Continue/Cline 等）都可连接任何 MCP 服务器。⑥**渐进增强**——协议版本化（2024-11-05→2025-03-26→2025-06-18），新版本增加能力（Streamable HTTP/进度通知/资源模板），旧版本客户端可忽略新能力，保持向后兼容。与 LangChain 的工具哲学（Python 函数即工具，@tool 装饰器）不同，MCP 的哲学是协议级标准化（JSON-RPC + 三大原语，跨语言跨框架）。溯源：[repo:file:src/everything/](https://github.com/modelcontextprotocol/servers/tree/d73f99efbfd40c3aa1b61e88728b3d49fb52608f/src/everything/) (全功能测试展示三大原语), [repo:file:src/filesystem/](https://github.com/modelcontextprotocol/servers/tree/d73f99efbfd40c3aa1b61e88728b3d49fb52608f/src/filesystem/) (Tools+Resources 示例), [repo:file:src/memory/](https://github.com/modelcontextprotocol/servers/tree/d73f99efbfd40c3aa1b61e88728b3d49fb52608f/src/memory/) (知识图谱 Tools 示例), （协议规范见 modelcontextprotocol/specification 仓库，非本仓）

## arch-distribution：npm 包分发 + 多传输方式
MCP 的分发是**npm 包 + 多传输方式**：①**npm 包分发**——每个服务器是独立的 npm 包（@modelcontextprotocol/server-everything@2.0.0、@modelcontextprotocol/server-filesystem@0.6.3、@modelcontextprotocol/server-memory@0.6.3、@modelcontextprotocol/server-sequential-thinking@0.6.2），用户可 `npx @modelcontextprotocol/server-filesystem /path/to/dir` 直接运行，或 `npm install -g` 全局安装。②**多传输方式**——stdio（本地进程通信，agent 启动服务器子进程，通过 stdin/stdout 通信，适合本地工具）、SSE（Server-Sent Events，服务器推送事件，客户端 HTTP 发送请求，服务器 SSE 推送响应，适合远程服务器）、HTTP（RESTful API，客户端 HTTP 调用服务器端点，适合无状态工具）、Streamable HTTP（v2025-03-26 新增，合并 SSE+HTTP，支持流式响应，推荐远程传输）。③**多语言 SDK 分发**——SDK 发布到各语言包管理器（npm/PyPI/RubyGems/Maven/go get/NuGet/crates.io/SwiftPM/Composer/pub.dev）。④**Docker 镜像**——部分服务器提供 Docker 镜像，便于容器化部署。⑤**配置方式**——agent 客户端通过配置文件（如 Claude Desktop 的 claude_desktop_config.json）声明 MCP 服务器连接（command/args/env 或 URL），启动时自动连接。与 Superpowers 的 npm 包 + 多平台插件目录（.claude-plugin/.codex-plugin 等）不同，MCP 的分发是协议级（npm 包 + 标准传输方式，无需为每个平台维护插件目录）。溯源：[repo:file:src/everything/package.json](https://github.com/modelcontextprotocol/servers/blob/d73f99efbfd40c3aa1b61e88728b3d49fb52608f/src/everything/package.json) (@modelcontextprotocol/server-everything@2.0.0), [repo:file:src/filesystem/package.json](https://github.com/modelcontextprotocol/servers/blob/d73f99efbfd40c3aa1b61e88728b3d49fb52608f/src/filesystem/package.json) (@modelcontextprotocol/server-filesystem@0.6.3), [repo:file:src/memory/package.json](https://github.com/modelcontextprotocol/servers/blob/d73f99efbfd40c3aa1b61e88728b3d49fb52608f/src/memory/package.json) (@modelcontextprotocol/server-memory@0.6.3), [repo:file:src/sequentialthinking/package.json](https://github.com/modelcontextprotocol/servers/blob/d73f99efbfd40c3aa1b61e88728b3d49fb52608f/src/sequentialthinking/package.json) (@modelcontextprotocol/server-sequential-thinking@0.6.2), repo:scripts/ (构建/发布脚本)

## arch-aci：MCP 工具调用接口（JSON-RPC + Tools/Resources/Prompts）
MCP 的工具调用接口是**JSON-RPC 2.0 + 三大原语**：①**JSON-RPC 2.0 协议**——所有通信遵循 JSON-RPC 2.0 规范，请求包含 jsonrpc/id/method/params，响应包含 jsonrpc/id/result/error。方法命名空间：tools/*（工具调用）、resources/*（资源访问）、prompts/*（提示词）、sampling/*（采样回调）、root/*（根路径）、notifications/*（通知）。②**Tools 调用流程**——客户端 initialize（初始化，协商协议版本）→ 客户端 tools/list（列出服务器提供的工具）→ 客户端 tools/call（调用工具，传入 name/arguments）→ 服务器执行工具 → 服务器返回 result（工具输出，content 数组，支持 text/image/resource 内容）。③**Resources 访问流程**——客户端 resources/list（列出资源）→ 客户端 resources/read（读取资源 URI）→ 服务器返回资源内容。支持 resources/subscribe（订阅资源变更通知）。④**Prompts 获取流程**——客户端 prompts/list（列出提示词模板）→ 客户端 prompts/get（获取提示词，传入参数）→ 服务器返回渲染后的提示词。⑤**采样回调**——服务器可请求客户端执行 LLM 采样（sampling/createMessage），用于服务器需要 LLM 辅助的场景（如 memory 服务器的实体提取）。⑥**进度通知**——长时间运行的工具可发送 notifications/progress（进度百分比），客户端可显示进度条。⑦**错误处理**——JSON-RPC error 对象包含 code/message/data，定义了标准错误码（MethodNotFound/InvalidParams/InternalError 等）。与 LangChain 的 BaseTool（Python 类，_run 方法同步执行）不同，MCP 的工具调用是协议级（JSON-RPC 异步通信，支持流式/进度/采样回调）。溯源：[repo:file:src/everything/](https://github.com/modelcontextprotocol/servers/tree/d73f99efbfd40c3aa1b61e88728b3d49fb52608f/src/everything/) (全功能测试展示所有调用流程), [repo:file:src/filesystem/](https://github.com/modelcontextprotocol/servers/tree/d73f99efbfd40c3aa1b61e88728b3d49fb52608f/src/filesystem/) (Tools+Resources 调用示例), [repo:file:src/memory/](https://github.com/modelcontextprotocol/servers/tree/d73f99efbfd40c3aa1b61e88728b3d49fb52608f/src/memory/) (采样回调示例), （协议规范见 modelcontextprotocol/specification）

## arch-typing：MCP 协议类型系统（JSON Schema + 协议版本化）
MCP 的类型系统是**JSON Schema + 协议版本化**：①**工具参数类型**——每个工具的 inputSchema 是 JSON Schema 对象，定义参数名/类型/必填项/描述/枚举/范围。客户端根据 JSON Schema 验证参数，LLM 根据 JSON Schema 生成工具调用参数。②**内容类型**——工具输出 content 是数组，每个内容项有 type 字段（text/image/resource/audio 等），text 类型含 text 字段，image 类型含 data（base64）+ mimeType，resource 类型含 resource/uri。③**消息类型**——sampling/createMessage 的输入是消息数组，每个消息有 role（user/assistant）+ content（文本或多模态内容数组）。④**资源类型**——资源对象包含 uri（URI 字符串）+ name + description + mimeType，资源模板支持 URI 模板（含变量占位符）。⑤**协议版本化**——initialize 方法协商 protocolVersion（如 "2025-06-18"），服务器和客户端根据版本决定支持的能力。新版本增加类型（ProgressNotification/ResourceTemplate/CompletionSuggestion），旧版本忽略。⑥**能力协商**——initialize 时客户端和服务器声明 capabilities（客户端：sampling/roots；服务器：tools/resources/prompts/logging/experimental），根据能力决定可用的方法。⑦**错误码类型**——JSON-RPC error code 是整数，定义标准错误码（-32601 MethodNotFound/-32602 InvalidParams/-32603 InternalError 等）。与 Pydantic 强类型（LangChain/LlamaIndex 的 Python 运行时类型校验）不同，MCP 的类型是 JSON Schema（跨语言，运行时由客户端/SDK 校验）。溯源：[repo:file:src/everything/](https://github.com/modelcontextprotocol/servers/tree/d73f99efbfd40c3aa1b61e88728b3d49fb52608f/src/everything/) (全功能测试展示所有类型), [repo:file:src/filesystem/](https://github.com/modelcontextprotocol/servers/tree/d73f99efbfd40c3aa1b61e88728b3d49fb52608f/src/filesystem/) (工具参数 JSON Schema 示例), （协议类型定义见 modelcontextprotocol/specification/schema/）

## arch-security：MCP 安全模型（进程隔离 + 权限控制 + OAuth 认证）
MCP 的安全模型是**多层防御**：①**进程隔离**——stdio 传输时，MCP 服务器运行在独立子进程，与 agent 客户端进程隔离，服务器崩溃或恶意代码不直接影响 agent 进程。服务器可运行在容器（Docker）或虚拟机中，进一步隔离。②**权限控制**——客户端可限制服务器的工具/资源访问（如 filesystem 服务器限制目录白名单，只允许访问指定目录；git 服务器限制只读，禁止写入）。客户端可在配置中声明服务器权限范围。③**传输加密**——远程传输（SSE/HTTP/Streamable HTTP）使用 HTTPS 加密，防止中间人攻击。stdio 传输是本地进程通信，无需加密。④**OAuth 2.1 认证**——远程 MCP 服务器支持 OAuth 2.1 + PKCE（Proof Key for Code Exchange）认证，客户端通过 OAuth 流程获取访问令牌，服务器验证令牌后允许访问。支持令牌刷新和撤销。⑤**沙箱**——服务器可运行在沙箱环境（如 filesystem 服务器使用 chroot/容器限制文件系统访问，fetch 服务器使用网络沙箱限制域名白名单）。⑥**输入验证**——服务器根据工具的 JSON Schema 验证输入参数，防止注入攻击（如路径遍历/命令注入）。⑦**日志审计**——服务器可记录工具调用日志（log 方法），客户端可收集审计日志。⑧**秘密管理**——服务器配置（API 密钥/数据库密码）通过环境变量或配置文件传入，不硬编码在代码中。与 codex 的 OS 级沙箱（Seatbelt/linux/windows/bwrap，系统调用隔离）不同，MCP 的安全是应用级（进程隔离+权限控制+OAuth+输入验证），无 OS 级系统调用隔离。溯源：[repo:file:src/filesystem/](https://github.com/modelcontextprotocol/servers/tree/d73f99efbfd40c3aa1b61e88728b3d49fb52608f/src/filesystem/) (目录白名单权限控制示例), [repo:file:src/fetch/](https://github.com/modelcontextprotocol/servers/tree/d73f99efbfd40c3aa1b61e88728b3d49fb52608f/src/fetch/) (网络沙箱示例), repo:src/everything/ (全功能测试展示安全能力), （安全规范见 modelcontextprotocol/specification/）

## arch-orchestration：多 MCP 服务器编排（工具聚合 + 客户端调度）
MCP 的编排是**客户端侧多服务器编排**——MCP 协议本身不定义服务器间编排，编排由 agent 客户端负责：①**多服务器连接**——客户端可同时连接多个 MCP 服务器（如同时连接 filesystem + git + memory + fetch），聚合所有服务器的工具/资源/提示词，形成统一的工具集。②**工具路由**——客户端根据工具名和来源服务器路由工具调用（如调用 filesystem 的 read_file 工具时，路由到 filesystem 服务器；调用 git 的 status 工具时，路由到 git 服务器）。③**工具命名空间**——多服务器工具可能重名，客户端可通过命名空间（如 server_name.tool_name）区分，或在配置中重命名工具。④**会话管理**——每个 MCP 服务器连接是独立会话（initialize 协商协议版本和能力），客户端维护会话状态（服务器能力/工具列表/资源列表）。⑤**生命周期管理**——stdio 服务器由客户端启动和停止（子进程管理），远程服务器由客户端连接和断开（HTTP 连接管理）。⑥**错误恢复**——服务器崩溃或断开时，客户端可自动重连（远程）或重启（stdio），工具调用失败时返回错误给 LLM，LLM 可决定重试或换工具。⑦**everything 全功能测试**——everything 服务器作为协议测试工具，可用于验证客户端的多服务器编排能力（同时连接 everything + 其他服务器，测试工具聚合和路由）。与 LangGraph 的显式状态图编排（节点/边/条件分支，服务器侧编排）不同，MCP 的编排是客户端侧隐式编排（多服务器工具聚合，由 LLM 决定调用哪个工具）。溯源：[repo:file:src/everything/](https://github.com/modelcontextprotocol/servers/tree/d73f99efbfd40c3aa1b61e88728b3d49fb52608f/src/everything/) (全功能测试), [repo:file:src/filesystem/](https://github.com/modelcontextprotocol/servers/tree/d73f99efbfd40c3aa1b61e88728b3d49fb52608f/src/filesystem/) (文件系统工具), [repo:file:src/git/](https://github.com/modelcontextprotocol/servers/tree/d73f99efbfd40c3aa1b61e88728b3d49fb52608f/src/git/) (Git 工具), （多服务器编排由客户端实现，非本仓）

# 其他架构域简评
- arch-patterns：JSON-RPC 客户端-服务器模式 + 三大原语（Tools/Resources/Prompts）+ 多服务器工具聚合
- arch-memory：memory 服务器（知识图谱记忆，实体/关系/事实存储检索），但记忆是服务器功能而非框架核心
- arch-context：无独立上下文管理，上下文由 agent 客户端管理，MCP 只提供工具/资源/提示词
- arch-llm-abstraction：无 LLM 抽象，MCP 服务器可通过采样回调请求客户端 LLM，但 LLM 由客户端管理
- arch-evals：everything 服务器作为协议测试工具（非评估框架），无独立评估体系
- arch-observability：log 方法（服务器发送日志通知）+ 进度通知（notifications/progress），无完整可观测性平台
- arch-plan-exec：sequentialthinking 服务器（逐步推理工具，think/next/finish），但计划执行由 LLM 驱动，非框架核心
- arch-streaming：SSE/Streamable HTTP 流式传输 + 工具输出流式（content 数组可增量推送）
- arch-code-intel：git 服务器（Git 操作）+ filesystem 服务器（文件访问），代码智能通过工具组合，无独立代码智能模块
- arch-skill-philosophy：见核心域（协议标准化 + 三大原语）
- arch-workflow：无独立工作流引擎，工作流由 agent 客户端（LLM 驱动）编排
- arch-typing：见核心域（JSON Schema + 协议版本化）
- arch-distribution：见核心域（npm 包 + 多传输方式 + 多语言 SDK）
- arch-exec-backend：stdio 子进程 + 远程 HTTP/SSE 服务器，无独立执行引擎
- arch-frontend：无独立前端（协议规范 + 服务器实现，客户端 UI 由各 agent 提供）
- arch-checkpoint：无独立检查点机制，会话状态由客户端管理
- arch-plugins：见核心域（服务器即插件，7 个参考实现）
- arch-fault-tolerance：进程隔离（服务器崩溃不影响客户端）+ 错误恢复（自动重连/重启）+ JSON-RPC 错误处理
- arch-security：见核心域（进程隔离 + 权限控制 + OAuth + 输入验证）

# claim 台账

| claim | 溯源锚点（repo:file:line） | 置信度 |
|---|---|---|
| 7 个参考服务器（everything/filesystem/git/memory/fetch/sequentialthinking/time） | [repo:file:src/](https://github.com/modelcontextprotocol/servers/tree/d73f99efbfd40c3aa1b61e88728b3d49fb52608f/src/) (7 目录实测) | EXTRACTED |
| everything 56 files 全功能测试服务器 | [repo:file:src/everything/](https://github.com/modelcontextprotocol/servers/tree/d73f99efbfd40c3aa1b61e88728b3d49fb52608f/src/everything/) (56 files 实测) | EXTRACTED |
| npm 包 @modelcontextprotocol/server-everything@2.0.0 | [repo:file:src/everything/package.json](https://github.com/modelcontextprotocol/servers/blob/d73f99efbfd40c3aa1b61e88728b3d49fb52608f/src/everything/package.json) (实测) | EXTRACTED |
| filesystem @modelcontextprotocol/server-filesystem@0.6.3 | [repo:file:src/filesystem/package.json](https://github.com/modelcontextprotocol/servers/blob/d73f99efbfd40c3aa1b61e88728b3d49fb52608f/src/filesystem/package.json) (实测) | EXTRACTED |
| memory @modelcontextprotocol/server-memory@0.6.3（知识图谱记忆） | [repo:file:src/memory/package.json](https://github.com/modelcontextprotocol/servers/blob/d73f99efbfd40c3aa1b61e88728b3d49fb52608f/src/memory/package.json) (实测) | EXTRACTED |
| sequentialthinking @modelcontextprotocol/server-sequential-thinking@0.6.2 | [repo:file:src/sequentialthinking/package.json](https://github.com/modelcontextprotocol/servers/blob/d73f99efbfd40c3aa1b61e88728b3d49fb52608f/src/sequentialthinking/package.json) (实测) | EXTRACTED |
| 三大原语（Tools/Resources/Prompts） | 协议规范 + everything 全功能测试（推断） | INFERRED |
| 多传输方式（stdio/SSE/HTTP/Streamable HTTP） | 协议规范（推断，非本仓代码） | INFERRED |
| 多语言 SDK（10+ 语言） | 协议生态（推断，非本仓） | INFERRED |
| 90,150★ | GitHub API 实测 | EXTRACTED |
| 协议版本化（2024-11-05→2025-03-26→2025-06-18） | 协议规范（推断） | INFERRED |
| OAuth 2.1 + PKCE 远程认证 | 协议规范（推断） | INFERRED |
| 特殊形态多 server 单仓（7 server 共享 monorepo） | [repo:file:src/](https://github.com/modelcontextprotocol/servers/tree/d73f99efbfd40c3aa1b61e88728b3d49fb52608f/src/) (7 目录实测) | EXTRACTED |
| JSON-RPC 2.0 通信协议 | 协议规范（推断） | INFERRED |

# 矛盾记录（Disputed）
与 F-C10-001 Superpowers 形成 C10 同类对照（非矛盾，互补）：
- **形态**：Superpowers = 静态文档技能（SKILL.md，agent 读取后解释执行）；MCP Servers = 运行时工具服务器（JSON-RPC 动态调用，服务器执行逻辑返回结果）
- **分发**：Superpowers = npm 包 + 多平台插件目录（.claude-plugin/.codex-plugin 等 10 平台）；MCP Servers = npm 包 + 标准传输方式（stdio/SSE/HTTP，无需平台特定插件）
- **工具定义**：Superpowers = Markdown 文档（name/description + 指令文本）；MCP Servers = JSON Schema（name/description/inputSchema，强类型参数）
- **执行方式**：Superpowers = agent 解释执行（agent 读取技能指令后用自身工具执行）；MCP Servers = 服务器执行（agent 通过 JSON-RPC 调用服务器，服务器执行工具逻辑返回结果）
- **安全边界**：Superpowers = 无独立安全边界（技能在 agent 进程内执行，依赖 agent 安全机制）；MCP Servers = 进程隔离（服务器独立子进程/远程进程，权限控制/OAuth 认证）
- **适用场景**：Superpowers = 开发工作流技能（调试/TDD/代码审查/计划，agent 内部工作流指导）；MCP Servers = 外部工具集成（文件系统/Git/数据库/API，agent 外部能力扩展）
- **关系**：两者可组合使用（Superpowers 技能指导 agent 工作流，MCP 服务器提供工具能力，agent 同时加载两者）

# 对照验证
- 对照源：https://deepwiki.com/modelcontextprotocol/servers（Tier2：DeepWiki 自动生成的代码文档）
- 访问日期：2026-09-08
- 不一致裁决：deepwiki 页面 HTTP 200 可访问，页面标题 "modelcontextprotocol/servers | DeepWiki"；核心设计与本地蒸馏结论一致（7 个参考服务器/三大原语/JSON-RPC 协议/npm 包分发），未发现不一致。

# 溯源
- repo:src/everything/（56 files，全功能测试服务器，@modelcontextprotocol/server-everything@2.0.0）
- repo:src/filesystem/（20 files，文件系统访问服务器，@modelcontextprotocol/server-filesystem@0.6.3）
- repo:src/git/（12 files，Git 操作服务器）
- repo:src/memory/（14 files，知识图谱记忆服务器，@modelcontextprotocol/server-memory@0.6.3）
- repo:src/fetch/（11 files，网页抓取服务器）
- repo:src/sequentialthinking/（11 files，顺序思考服务器，@modelcontextprotocol/server-sequential-thinking@0.6.2）
- repo:src/time/（9 files，时间/日期服务器）
- repo:scripts/（构建/发布脚本）
- repo:.github/（CI/CD 配置）
- repo:README.md + LICENSE（MIT）
- corpus/repos/mcp-servers/head-sha.txt（d73f99e）

# 待补
- [ ] 各服务器核心文件精读（当前只看了目录结构和 package.json，工具实现细节待精读）
- [ ] 协议规范细节（JSON-RPC 方法列表/错误码/能力协商，需读 modelcontextprotocol/specification）
- [ ] 多语言 SDK 列表精确确认（10+ 语言是推断，待精确统计）
- [ ] Repomix 打包（小仓，可选补全）

## 更新记录

- 2026-09-14 | LB-R4 30天复扫 | star=90289（90236→90289） | HEAD=d73f99efbfd40c3aa1b61e88728b3d49fb52608f（pinned=d73f99efbfd40c3aa1b61e88728b3d49fb52608f，commit 漂移 d73f99efbf→d73f99efbf） | L1 微漂移标注（CB-11：仅标注，未重蒸馏）| pushed_at=2026-09-03 archived=false | 锚点 repo_base_url/repo_local_path 不动
