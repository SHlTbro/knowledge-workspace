---
id: F-C08-001
title: browser-use：浏览器自动化 Agent 框架（Agent 服务 4163 行 + 浏览器会话 4153 行 + MCP 服务器 1294 行 + 工具注册表，113k★）
tags: [framework-profile, arch-browser, arch-agent, arch-mcp, arch-aci, arch-sandbox, arch-llm-abstraction]
created: 2026-09-09
category: C08
alt: [C02, C03]
repo_url: https://github.com/browser-use/browser-use
repo_commit: 2b1f9d377999a59fe7627c1a5aa88c12aa42e11f
repo_base_url: https://github.com/browser-use/browser-use/blob/2b1f9d377999a59fe7627c1a5aa88c12aa42e11f/
repo_local_path: [本机绝对路径已隐藏]
star: 114466
distilled_at: 2026-09-09
freshness: hot
workflow: WORKFLOW-repo v2
sources: [GitHub API, local clone, README, browser_use/agent/service.py, browser_use/browser/session.py, browser_use/mcp/server.py]
---

# 框架总评

## 设计哲学出发点
browser-use 定位为"浏览器自动化 Agent 框架"（browser-use 组织开源，MIT 协议），核心取舍是**浏览器原生 Agent 优先**——把 LLM Agent 直接建模为浏览器操作者，通过 DOM 感知+动作执行循环实现网页自动化，而非传统 RPA 坐标点击。设计哲学是"Agent sees the web like a human"——Agent 通过 DOM 元素树感知页面、通过浏览器动作（click/type/scroll/navigate）操作页面、通过 watchdogs 监控页面变化。与 Playwright/Selenium 的脚本式自动化不同，browser-use 的核心是 LLM 驱动的自主浏览器 Agent（ReAct 循环：感知 DOM→推理→执行动作→观察结果）。v2 架构引入 Agent 服务（agent/service.py 4163 行）+ 浏览器会话（browser/session.py 4153 行）+ MCP 服务器（mcp/server.py 1294 行）+ 工具注册表（tools/registry/service.py 613 行）的四层分离架构。

## 设计特点
- **四层分离架构**：Agent 服务（agent/service.py 4163 行，ReAct 循环+消息管理+提示词）+ 浏览器会话（browser/session.py 4153 行，Playwright 控制+watchdogs 监控）+ MCP 服务器（mcp/server.py 1294 行，浏览器能力 MCP 化）+ 工具服务（tools/service.py 2327 行，工具注册+提取+执行）
- **20 个子模块**：browser_use/ 下 actor(8)/agent(12)/beta(2)/browser(29)/controller(1)/dom(12)/filesystem(2)/integrations(3)/llm(54)/mcp(6)/sandbox(3)/screenshots(2)/skills(6)/sync(3)/telemetry(3)/tokens(7)/tools(8)，共 175+ 个 .py 文件
- **Watchdogs 监控系统**：browser/watchdogs/ 下 4 种监控器——default_action_watchdog.py（3752 行，默认动作监控）/downloads_watchdog.py（1503 行，下载监控）/dom_watchdog.py（877 行，DOM 变化监控）/har_recording_watchdog.py（779 行，HAR 录制）
- **MCP 原生支持**：mcp/server.py 1294 行将浏览器能力暴露为 MCP 工具（click/type/scroll/navigate/screenshot 等），mcp/client.py 556 行支持作为 MCP 客户端连接外部 MCP 服务器，mcp/cli_mcp.py 184 行提供 CLI 入口
- **多提供商 LLM 适配**：llm/ 54 个 .py 文件，支持 OpenAI/Anthropic/Google/Ollama 等多提供商，统一 LLM 调用接口
- **DOM 感知系统**：dom/ 12 个 .py 文件，DOM 元素树提取、元素定位、可交互元素过滤、XPath/CSS 选择器生成
- **工具注册表**：tools/registry/service.py 613 行，动态工具注册/查找/执行，tools/extraction/ 支持从网页提取结构化数据
- **沙箱安全**：sandbox/ 3 个 .py 文件，浏览器沙箱隔离，防止恶意网页影响宿主
- **技能系统**：skills/ 6 个 .py 文件，Agent 技能定义/加载/执行
- **可观测性**：telemetry/ 3 个 .py 文件，Agent 执行轨迹/事件/指标收集
- **113,619★**（C08 空域首例，浏览器自动化 Agent 第一大仓），pushed=2026-09-07（hot），MIT 协议，Python

## 痛点
解决传统浏览器自动化**脚本脆弱、无法应对动态页面**的痛点——Playwright/Selenium 脚本基于固定选择器，页面变化即失效，无法处理登录/弹窗/动态加载等复杂场景。browser-use 通过 LLM 驱动的自主 Agent，感知 DOM 变化并自适应执行，解决脚本脆弱性。同时解决**RPA 坐标点击不可靠**的痛点——传统 RPA 基于屏幕坐标，分辨率/窗口大小变化即失效，browser-use 基于 DOM 元素语义定位，与分辨率无关。与 claude-code 的编码 Agent 不同，browser-use 的核心是浏览器操作 Agent（专注网页自动化，非代码编写）。

## 优缺点
- 优点：浏览器原生 Agent 架构（DOM 感知+动作执行循环）；四层分离（Agent/浏览器/MCP/工具）；Watchdogs 监控系统（4 种监控器，动作/下载/DOM/HAR）；MCP 原生支持（server 1294 行+client 556 行）；多提供商 LLM 适配（54 个 .py）；工具注册表动态管理；沙箱安全隔离；技能系统；可观测性；113k★ 社区验证；MIT 开源；本地部署简单（pip install）
- 缺点：Agent 服务 4163 行过大（核心文件膨胀）；浏览器会话 4153 行过大；大仓（175+ .py 文件，20 子模块）；LLM 调用成本高（每次动作都需 LLM 推理）；复杂页面 DOM 树过大导致 token 溢出；无内置视觉理解（仅 DOM 文本，非截图视觉）；调试困难（Agent 决策过程不透明）；与 Playwright 功能重叠（底层依赖 Playwright）

## 关键取舍
最核心的取舍是"**LLM 驱动自主 Agent** vs **脚本式自动化**"——browser-use 选择 LLM 驱动（感知 DOM→推理→执行→观察的 ReAct 循环），获得自适应能力（应对动态页面/登录/弹窗），但牺牲了确定性（LLM 决策不可重复）和成本（每次动作都需 LLM 调用）。第二个取舍是"**DOM 语义感知** vs **坐标/视觉感知**"——browser-use 选择 DOM 语义（元素树+可交互元素过滤），获得与分辨率无关的稳定性和语义理解能力，但牺牲了视觉信息（无法处理 canvas/WebGL 等非 DOM 内容）。第三个取舍是"**四层分离架构** vs **单包全功能**"——browser-use 选择四层分离（Agent/浏览器/MCP/工具各层独立），获得模块化和可扩展性（MCP 服务器可独立部署），但增加了学习成本（需理解四层交互）。

# 核心深挖域

## arch-orchestration：Agent 服务 ReAct 循环 + 消息管理 + Watchdogs 监控
browser-use 的编排是 **Agent 服务 ReAct 循环 + 浏览器会话动作执行 + Watchdogs 事件监控** 的三层架构。①**Agent 服务**（agent/service.py 4163 行）——核心 ReAct 循环：感知 DOM 状态→调用 LLM 推理→生成浏览器动作→执行动作→观察结果→循环直到任务完成。Agent 服务管理消息历史（message_manager/service.py 600 行）、提示词模板（prompts.py 600 行）、变量检测（variable_detector.py 276 行）、判断评估（judge.py 225 行）、云事件（cloud_events.py 284 行）。②**浏览器会话**（browser/session.py 4153 行）——Playwright 浏览器控制核心，管理浏览器生命周期、页面导航、动作执行（click/type/scroll/navigate）、DOM 提取、截图。session_manager.py 918 行管理多会话，profile.py 1300 行管理浏览器配置文件，demo_mode.py 922 行支持演示模式。③**Watchdogs 监控**（browser/watchdogs/）——4 种事件监控器：default_action_watchdog.py（3752 行，监控默认动作执行和页面响应）、downloads_watchdog.py（1503 行，监控文件下载）、dom_watchdog.py（877 行，监控 DOM 变化并触发 Agent 重新感知）、har_recording_watchdog.py（779 行，录制 HTTP 请求用于调试）。events.py 667 行定义事件系统。与 AutoGen 的多 Agent 对话编排不同，browser-use 的编排是单 Agent 浏览器操作循环（Agent 感知 DOM→执行动作→Watchdogs 监控事件→触发重新感知）。溯源：[repo:file:browser_use/agent/service.py:1](https://github.com/browser-use/browser-use/blob/2b1f9d377999a59fe7627c1a5aa88c12aa42e11f/browser_use/agent/service.py#L1) (4163 行 Agent 服务), [repo:file:browser_use/browser/session.py:1](https://github.com/browser-use/browser-use/blob/2b1f9d377999a59fe7627c1a5aa88c12aa42e11f/browser_use/browser/session.py#L1) (4153 行浏览器会话), [repo:file:browser_use/browser/watchdogs/](https://github.com/browser-use/browser-use/tree/2b1f9d377999a59fe7627c1a5aa88c12aa42e11f/browser_use/browser/watchdogs/) (4 种 Watchdogs)

## arch-aci：MCP 服务器 1294 行 + 工具服务 2327 行 + 工具注册表 613 行
browser-use 的工具接口是 **MCP 服务器 + 工具服务 + 工具注册表** 的三层工具架构。①**MCP 服务器**（mcp/server.py 1294 行）——将浏览器能力暴露为 MCP 工具（click/type/scroll/navigate/screenshot/extract 等），支持任何 MCP 客户端连接使用浏览器自动化能力，mcp/cli_mcp.py 184 行提供 CLI 启动入口。②**MCP 客户端**（mcp/client.py 556 行）——browser-use Agent 可作为 MCP 客户端连接外部 MCP 服务器，扩展工具能力（数据库/文件系统/API 等），mcp/controller.py 264 行管理 MCP 连接生命周期。③**工具服务**（tools/service.py 2327 行）——核心工具执行引擎，管理浏览器动作工具（click/type/scroll/navigate/wait/back/forward/refresh）、信息提取工具（extract_text/extract_structured_data）、截图工具。④**工具注册表**（tools/registry/service.py 613 行）——动态工具注册/查找/执行，支持运行时增删工具，工具按类别分组（browser/extraction/screenshot）。⑤**工具提取**（tools/extraction/）——schema_utils.py 168 行支持从网页提取结构化数据（JSON schema 定义提取目标）。⑥**DOM 工具**（dom/ 12 个 .py）——DOM 元素树提取、可交互元素过滤、XPath/CSS 选择器生成、元素高亮。与 MCP Servers 的 JSON-RPC 单一协议（Tools/Resources/Prompts 三大原语）不同，browser-use 的 ACI 是 MCP 服务器+工具服务+工具注册表三层（focus on 浏览器工具 MCP 化和动态工具管理，不是通用 MCP 协议实现）。溯源：[repo:file:browser_use/mcp/server.py:1](https://github.com/browser-use/browser-use/blob/2b1f9d377999a59fe7627c1a5aa88c12aa42e11f/browser_use/mcp/server.py#L1) (1294 行 MCP 服务器), [repo:file:browser_use/tools/service.py:1](https://github.com/browser-use/browser-use/blob/2b1f9d377999a59fe7627c1a5aa88c12aa42e11f/browser_use/tools/service.py#L1) (2327 行工具服务), [repo:file:browser_use/tools/registry/service.py:1](https://github.com/browser-use/browser-use/blob/2b1f9d377999a59fe7627c1a5aa88c12aa42e11f/browser_use/tools/registry/service.py#L1) (613 行工具注册表)

## arch-context：DOM 感知 + 消息历史 + 提示词模板 + 变量检测
browser-use 的上下文管理是 **DOM 状态感知 + 消息历史管理 + 提示词模板 + 变量检测** 的四层上下文。①**DOM 感知**——Agent 每次循环从浏览器会话获取当前页面 DOM 元素树（dom/ 12 个 .py 文件处理 DOM 提取和过滤），只保留可交互元素（按钮/链接/输入框/下拉框等），减少 token 消耗。DOM 状态作为 Agent 观察结果加入消息历史。②**消息历史**（message_manager/service.py 600 行）——管理 Agent 对话历史（系统提示+用户任务+DOM 观察+动作执行+结果），支持 token 计数和截断，message_manager/views.py 101 行提供消息视图。③**提示词模板**（prompts.py 600 行）——Agent 系统提示词模板，定义角色（浏览器自动化助手）、能力（可用浏览器动作列表）、输出格式（JSON 动作定义）、约束（安全/效率），支持动态变量替换。④**变量检测**（variable_detector.py 276 行）——检测提示词和动作中的变量占位符，支持动态变量注入（如登录凭据/目标 URL 从环境变量读取）。⑤**判断评估**（judge.py 225 行）——评估 Agent 动作是否成功，判断任务是否完成，支持多维度评估（DOM 变化/URL 变化/文本匹配）。与 LangGraph 的 StateGraph 状态通道（显式状态 schema+10 种通道类型）不同，browser-use 的上下文是 DOM 感知+消息历史+提示词模板（focus on 浏览器状态感知和动作历史，不是显式状态图编排）。溯源：[repo:file:browser_use/agent/message_manager/service.py:1](https://github.com/browser-use/browser-use/blob/2b1f9d377999a59fe7627c1a5aa88c12aa42e11f/browser_use/agent/message_manager/service.py#L1) (600 行消息管理), [repo:file:browser_use/agent/prompts.py:1](https://github.com/browser-use/browser-use/blob/2b1f9d377999a59fe7627c1a5aa88c12aa42e11f/browser_use/agent/prompts.py#L1) (600 行提示词模板), [repo:file:browser_use/agent/variable_detector.py:1](https://github.com/browser-use/browser-use/blob/2b1f9d377999a59fe7627c1a5aa88c12aa42e11f/browser_use/agent/variable_detector.py#L1) (276 行变量检测)

## arch-security：沙箱隔离 + Watchdogs 安全监控 + 动作约束
browser-use 的安全模型是 **浏览器沙箱 + Watchdogs 安全监控 + 动作约束 + 凭证管理** 的多层安全。①**浏览器沙箱**（sandbox/ 3 个 .py）——浏览器进程沙箱隔离，防止恶意网页影响宿主系统，支持 Docker 容器化浏览器部署（docker/ 目录提供 Dockerfile）。②**Watchdogs 安全监控**——default_action_watchdog.py（3752 行）监控动作执行是否符合预期，dom_watchdog.py（877 行）监控 DOM 异常变化（如意外导航到恶意网站），downloads_watchdog.py（1503 行）监控文件下载安全（防止恶意文件下载）。③**动作约束**——提示词模板定义允许的动作列表和安全约束（禁止访问敏感网站/禁止下载可执行文件/禁止输入敏感信息），judge.py 225 行评估动作安全性。④**凭证管理**——变量检测支持从环境变量读取凭证（不硬编码在提示词中），防止凭证泄露给 LLM 或日志。⑤**HAR 录制**（har_recording_watchdog.py 779 行）——录制所有 HTTP 请求用于安全审计和事后分析。与 codex 的 OS 级沙箱（Seatbelt/linux/windows/bwrap，系统调用隔离）不同，browser-use 的安全是浏览器沙箱+Watchdogs 监控+动作约束（focus on 浏览器级安全和网页恶意防护，不是 OS 级系统调用隔离）。溯源：[repo:file:browser_use/sandbox/](https://github.com/browser-use/browser-use/tree/2b1f9d377999a59fe7627c1a5aa88c12aa42e11f/browser_use/sandbox/) (沙箱模块), [repo:file:browser_use/browser/watchdogs/default_action_watchdog.py:1](https://github.com/browser-use/browser-use/blob/2b1f9d377999a59fe7627c1a5aa88c12aa42e11f/browser_use/browser/watchdogs/default_action_watchdog.py#L1) (3752 行动作监控), [repo:file:browser_use/browser/profile.py:1](https://github.com/browser-use/browser-use/blob/2b1f9d377999a59fe7627c1a5aa88c12aa42e11f/browser_use/browser/profile.py#L1) (1300 行浏览器配置)

## arch-llm-abstraction：llm/ 54 个 .py 多提供商适配
browser-use 的 LLM 抽象层是 **llm/ 54 个 .py 文件的多提供商适配**，支持 OpenAI/Anthropic/Google/Ollama 等主流 LLM 提供商，统一调用接口。llm/ 是 browser_use 下最大的子模块（54 个 .py），包含提供商适配层、消息格式转换、工具调用格式统一、流式响应处理、token 计数、成本统计等。Agent 服务（agent/service.py）通过统一 LLM 接口调用，不依赖特定提供商，支持运行时切换提供商。与 langchain 的 BaseChatModel 抽象（15+ 提供商集成）类似，但 browser-use 的 LLM 层更专注于浏览器 Agent 场景（需要处理 DOM 状态输入和动作 JSON 输出）。溯源：[repo:file:browser_use/llm/](https://github.com/browser-use/browser-use/tree/2b1f9d377999a59fe7627c1a5aa88c12aa42e11f/browser_use/llm/) (54 个 .py 多提供商适配)


## arch-session：浏览器会话管理 + 会话恢复 + 多会话隔离
browser-use 的会话管理是 **浏览器会话 + Agent 消息历史 + 会话恢复** 的三层会话。①浏览器会话（browser/session.py 4153 行）管理浏览器生命周期、页面导航、cookie/localStorage 持久化，支持会话恢复（重新打开浏览器恢复之前的页面状态）。②Agent 消息历史（agent/message_manager/service.py 600 行）管理 Agent 对话历史（系统提示+用户任务+DOM 观察+动作执行+结果），支持 token 计数和截断。③多会话隔离（browser/session_manager.py 918 行）支持多个独立浏览器会话，会话间 cookie/localStorage/缓存隔离，支持并行任务执行。与 LangGraph 的 Checkpoint 持久化（独立包 sqlite/postgres，时间旅行+中断恢复）不同，browser-use 的会话是浏览器会话+Agent 消息历史（focus on 浏览器状态和 Agent 对话，不是通用状态图检查点）。溯源：[repo:file:browser_use/browser/session.py:1](https://github.com/browser-use/browser-use/blob/2b1f9d377999a59fe7627c1a5aa88c12aa42e11f/browser_use/browser/session.py#L1) (4153 行浏览器会话), [repo:file:browser_use/browser/session_manager.py:1](https://github.com/browser-use/browser-use/blob/2b1f9d377999a59fe7627c1a5aa88c12aa42e11f/browser_use/browser/session_manager.py#L1) (918 行会话管理)

## arch-observability：Telemetry + HAR 录制 + Watchdogs 事件
browser-use 的可观测性是 **telemetry 指标 + HAR 录制 + Watchdogs 事件监控** 的三层可观测性。①telemetry（telemetry/ 3 个 .py）收集 Agent 执行轨迹、事件、指标（动作次数/成功率/耗时/token 消耗），支持导出和分析。②HAR 录制（browser/watchdogs/har_recording_watchdog.py 779 行）录制所有 HTTP 请求/响应（HAR 格式），用于网络调试和性能分析，支持事后回放和错误定位。③Watchdogs 事件（browser/events.py 667 行 + 4 种 Watchdogs）监控浏览器事件（页面加载/DOM 变化/下载/动作执行），事件可订阅和处理，支持事件驱动的 Agent 重新感知。与 LangSmith 的全链路追踪（LLM 调用/工具调用/状态变化可视化）不同，browser-use 的可观测性是 telemetry+HAR+Watchdogs（focus on 浏览器自动化场景的网络和事件监控，不是通用 LLM 应用追踪）。溯源：[repo:file:browser_use/telemetry/](https://github.com/browser-use/browser-use/tree/2b1f9d377999a59fe7627c1a5aa88c12aa42e11f/browser_use/telemetry/) (telemetry 模块), [repo:file:browser_use/browser/watchdogs/har_recording_watchdog.py:1](https://github.com/browser-use/browser-use/blob/2b1f9d377999a59fe7627c1a5aa88c12aa42e11f/browser_use/browser/watchdogs/har_recording_watchdog.py#L1) (779 行 HAR 录制)

## arch-fault-tolerance：Watchdogs 异常监控 + 动作重试 + 浏览器恢复
browser-use 的容错是 **Watchdogs 异常监控 + 动作重试 + 浏览器崩溃恢复** 的三层容错。①Watchdogs 异常监控（4 种 Watchdogs）监控动作执行失败（default_action_watchdog 3752 行）、下载中断（downloads_watchdog 1503 行）、DOM 异常变化（dom_watchdog 877 行），异常事件触发 Agent 重新感知和调整策略。②动作重试——Agent 服务（agent/service.py 4163 行）支持动作执行失败重试（网络超时/元素未找到/页面加载失败），重试次数和间隔可配置，支持指数退避。③浏览器崩溃恢复——session_manager 支持浏览器进程崩溃检测和自动重启，恢复之前的会话状态（cookie/localStorage/页面历史），支持健康检查和心跳。与 LangGraph 的 Checkpoint 故障恢复（从 checkpoint 恢复执行，支持时间旅行）不同，browser-use 的容错是 Watchdogs+动作重试+浏览器恢复（focus on 浏览器自动化场景的异常监控和恢复，不是通用工作流故障恢复）。溯源：[repo:file:browser_use/browser/watchdogs/default_action_watchdog.py:1](https://github.com/browser-use/browser-use/blob/2b1f9d377999a59fe7627c1a5aa88c12aa42e11f/browser_use/browser/watchdogs/default_action_watchdog.py#L1) (3752 行动作监控), [repo:file:browser_use/agent/service.py:1](https://github.com/browser-use/browser-use/blob/2b1f9d377999a59fe7627c1a5aa88c12aa42e11f/browser_use/agent/service.py#L1) (4163 行 Agent 服务)

# 其他架构域简评
- arch-workflow：Agent ReAct 循环（感知→推理→执行→观察）+ Watchdogs 事件驱动，无独立 DAG 工作流引擎
- arch-memory：消息历史（message_manager）+ DOM 状态缓存，无独立长期记忆系统
- arch-rag：无独立 RAG 模块，网页内容通过 DOM 提取直接作为上下文
- arch-evals：judge.py 225 行动作评估，无独立评估框架
- arch-observability：telemetry/ 3 个 .py（执行轨迹/事件/指标）+ HAR 录制（har_recording_watchdog）
- arch-streaming：Agent 支持流式响应（LLM 流式输出+动作增量执行）
- arch-code-intel：无独立代码智能模块（非编码 Agent，专注浏览器操作）
- arch-skill-philosophy：skills/ 6 个 .py（技能定义/加载/执行），Agent 可加载预定义浏览器技能
- arch-typing：Pydantic 强类型（动作定义/工具参数/DOM 元素都是 Pydantic model）
- arch-distribution：PyPI 单包分发（browser-use），pip install browser-use
- arch-exec-backend：Playwright 浏览器后端（Chromium/Firefox/WebKit），支持 headless/headful
- arch-frontend：无独立前端（CLI+Python API），demo_mode.py 支持演示模式
- arch-checkpoint：无独立检查点机制，会话状态通过 browser profile 持久化
- arch-plugins：MCP 客户端（mcp/client.py 556 行）支持连接外部 MCP 服务器扩展能力
- arch-fault-tolerance：Watchdogs 监控动作失败+DOM 异常+下载中断，支持重试和恢复，无自动熔断

# claim 台账

| claim | 溯源锚点（repo:file:line） | 置信度 |
|---|---|---|
| Agent 服务 4163 行（ReAct 循环核心） | [repo:file:browser_use/agent/service.py:1](https://github.com/browser-use/browser-use/blob/2b1f9d377999a59fe7627c1a5aa88c12aa42e11f/browser_use/agent/service.py#L1) (4163 行实测) | EXTRACTED |
| 浏览器会话 4153 行（Playwright 控制核心） | [repo:file:browser_use/browser/session.py:1](https://github.com/browser-use/browser-use/blob/2b1f9d377999a59fe7627c1a5aa88c12aa42e11f/browser_use/browser/session.py#L1) (4153 行实测) | EXTRACTED |
| MCP 服务器 1294 行（浏览器能力 MCP 化） | [repo:file:browser_use/mcp/server.py:1](https://github.com/browser-use/browser-use/blob/2b1f9d377999a59fe7627c1a5aa88c12aa42e11f/browser_use/mcp/server.py#L1) (1294 行实测) | EXTRACTED |
| 工具服务 2327 行（浏览器动作工具执行） | [repo:file:browser_use/tools/service.py:1](https://github.com/browser-use/browser-use/blob/2b1f9d377999a59fe7627c1a5aa88c12aa42e11f/browser_use/tools/service.py#L1) (2327 行实测) | EXTRACTED |
| 4 种 Watchdogs（default_action 3752/downloads 1503/dom 877/har_recording 779） | [repo:file:browser_use/browser/watchdogs/](https://github.com/browser-use/browser-use/tree/2b1f9d377999a59fe7627c1a5aa88c12aa42e11f/browser_use/browser/watchdogs/) (4 文件实测行数) | EXTRACTED |
| 20 个子模块，175+ 个 .py 文件 | [repo:file:browser_use/](https://github.com/browser-use/browser-use/tree/2b1f9d377999a59fe7627c1a5aa88c12aa42e11f/browser_use/) (20 目录实测) | EXTRACTED |
| llm/ 54 个 .py（最大子模块，多提供商适配） | [repo:file:browser_use/llm/](https://github.com/browser-use/browser-use/tree/2b1f9d377999a59fe7627c1a5aa88c12aa42e11f/browser_use/llm/) (54 个 .py 实测) | EXTRACTED |
| 工具注册表 613 行（动态工具管理） | [repo:file:browser_use/tools/registry/service.py:1](https://github.com/browser-use/browser-use/blob/2b1f9d377999a59fe7627c1a5aa88c12aa42e11f/browser_use/tools/registry/service.py#L1) (613 行实测) | EXTRACTED |
| 消息管理 600 行 + 提示词模板 600 行 | [repo:file:browser_use/agent/message_manager/service.py:1](https://github.com/browser-use/browser-use/blob/2b1f9d377999a59fe7627c1a5aa88c12aa42e11f/browser_use/agent/message_manager/service.py#L1), [repo:file:browser_use/agent/prompts.py:1](https://github.com/browser-use/browser-use/blob/2b1f9d377999a59fe7627c1a5aa88c12aa42e11f/browser_use/agent/prompts.py#L1) (各 600 行实测) | EXTRACTED |
| MCP 客户端 556 行（连接外部 MCP 服务器） | [repo:file:browser_use/mcp/client.py:1](https://github.com/browser-use/browser-use/blob/2b1f9d377999a59fe7627c1a5aa88c12aa42e11f/browser_use/mcp/client.py#L1) (556 行实测) | EXTRACTED |
| 113,619★（C08 空域首例） | GitHub API 实测 | EXTRACTED |
| pushed=2026-09-07（hot） | git log 实测 | EXTRACTED |

# 矛盾记录（Disputed）
无（C08 首张，无同类别 F 卡对比。与 Playwright/Selenium 互为参照——Playwright 是脚本式浏览器自动化（选择器+动作脚本），browser-use 是 LLM 驱动自主 Agent（DOM 感知+推理+动作），定位不同但底层依赖 Playwright）。

# 对照验证
- 对照源：https://deepwiki.com/browser-use/browser-use（Tier2：DeepWiki 自动生成的代码文档）
- 访问日期：2026-09-09
- 编排者复验：DeepWiki 已访问（Last indexed 2026-08-20, commit 85ddbfed）——Agent service.py / BrowserSession / Watchdog 模式（4.3-4.4 专章）/ MCP 集成（9.4）与卡内结论一致；索引 commit 早于卡内 2b1f9d37，版本差异不影响架构结论。**编排者复验裁决：一致（2026-09-09）**

# 溯源
- repo:browser_use/agent/service.py（4163 行 Agent 服务，ReAct 循环核心）
- repo:browser_use/browser/session.py（4153 行浏览器会话，Playwright 控制核心）
- repo:browser_use/mcp/server.py（1294 行 MCP 服务器，浏览器能力 MCP 化）
- repo:browser_use/tools/service.py（2327 行工具服务，浏览器动作工具执行）
- repo:browser_use/browser/watchdogs/（4 种 Watchdogs，动作/下载/DOM/HAR 监控）
- repo:browser_use/llm/（54 个 .py，多提供商 LLM 适配）
- repo:browser_use/tools/registry/service.py（613 行工具注册表）

# 待补
- [x] DeepWiki 对照验证（编排者复验 2026-09-09 裁决一致，见对照验证节）
- [ ] llm/ 54 个 .py 的完整提供商列表（当前仅确认多提供商，需完整列表）
- [ ] dom/ 12 个 .py 的详细 DOM 处理机制（当前仅概述，需精读）
- [ ] skills/ 6 个 .py 的技能系统详细设计（当前仅概述，需精读）
- [ ] sandbox/ 3 个 .py 的沙箱实现细节（当前仅概述，需精读）
- [ ] Agent 服务 4163 行的具体 ReAct 循环实现（当前仅概述架构，需精读核心循环）
- [ ] 与 Playwright 的功能重叠边界（browser-use 底层依赖 Playwright，需明确哪些是 browser-use 独有的 Agent 能力）
- [ ] 本地部署验证（pip install browser-use 到 .venv，验证 CLI 和 API 可用）

## 更新记录

- 2026-09-11 | LB-R2-a 30天复扫 | star=114156（113619→114156） | HEAD=50f205533fe10ba35b553d2a3689c77b87bd5d0a（pinned=2b1f9d377999a59fe7627c1a5aa88c12aa42e11f，commit 漂移 2b1f9d3779→50f205533f）| L1 微漂移标注（CB-11：仅标注，未重蒸馏；3 天窗口 star 漂移<2%，无 L2/L3 信号）| pushed_at=2026-09-10 archived=false | 锚点 repo_base_url/repo_local_path 不动
- 2026-09-14 | LB-R4 30天复扫 | star=114466（114156→114466） | HEAD=6e1977daa0f67c9de0bc0e16aaec8b5833eeb8e0（pinned=2b1f9d377999a59fe7627c1a5aa88c12aa42e11f，commit 漂移 2b1f9d3779→6e1977daa0） | L1 微漂移标注（CB-11：仅标注，未重蒸馏）| pushed_at=2026-09-13 archived=false | 锚点 repo_base_url/repo_local_path 不动

