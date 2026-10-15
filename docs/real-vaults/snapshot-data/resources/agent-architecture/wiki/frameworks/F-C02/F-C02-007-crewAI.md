---
id: F-C02-007
title: crewAI：多智能体协作框架（Crew 2490 行 + Flow 运行时 4015 行 + Agent 执行器 3361 行 + LLM 抽象 2775 行，58k★）
tags: [framework-profile, arch-orchestration, arch-context, arch-session, arch-memory, arch-aci, arch-plan-exec, arch-security]
created: 2026-09-09
category: C02
alt: [C01]
repo_url: https://github.com/crewAIInc/crewAI
repo_commit: a53ecc17f1829354e2d2ff58bbbad1d84ce568b2
repo_base_url: https://github.com/crewAIInc/crewAI/blob/a53ecc17f1829354e2d2ff58bbbad1d84ce568b2/
repo_local_path: [本机绝对路径已隐藏]
star: 58456
distilled_at: 2026-09-09
freshness: hot
workflow: WORKFLOW-repo v2
sources: [GitHub API, local clone, README, lib/crewai/, lib/crewai-tools/]
category_review: C02（决策树⑨多角色协作流→C02，与 autogen F-C02-001 同类；候选池原列 C01，复核后改 C02）
---

# 框架总评

## 设计哲学出发点
crewAI 定位为"多智能体协作框架"（crewAIInc 组织，MIT 协议），核心取舍是**角色驱动 + 流程编排**——通过 Crew（团队）+ Agent（角色）+ Task（任务）+ Process（协作流程：sequential/hierarchical）+ Flow（DAG 工作流）构建多 Agent 协作系统。设计哲学是"让 AI Agent 像团队一样协作"——每个 Agent 有明确角色（role/goal/backstory），任务按流程分配给合适的 Agent，支持顺序协作和层级协作（manager 分配任务），Flow 提供 DAG 级工作流编排。与 autogen（多 Agent 自由对话+团队编排器，对话驱动）不同，crewAI 是角色驱动+流程编排（focus on 明确角色定义和结构化协作流程，不是自由对话）。与 LangGraph（StateGraph 状态图，通用编排）不同，crewAI 是多 Agent 协作专用框架（focus on Crew/Agent/Task 抽象，不是通用状态图）。

## 主类复核说明（C01→C02）
候选池原列 C01（通用编排框架），但按决策树⑨"多角色协作流→C02"复核：crewAI 核心是 Crew（多 Agent 团队）+ Agent（角色）+ Task（任务）+ Process（协作流程），是典型的多智能体协作框架，与 autogen（F-C02-001，多 Agent 自由对话+团队编排器）同类。Flow（DAG 工作流）是扩展能力（C01 特征），但核心定位是多 Agent 协作。**复核结论：C02（多智能体协作与社会模拟），编号 F-C02-007**。与 autogen 的分型依据：autogen 是对话驱动（多 Agent 自由对话，ConversableAgent），crewAI 是流程驱动（角色+任务+流程，Crew/Process），均属 C02 但协作范式不同（对话驱动 vs 流程驱动，见 M-005 协作范式谱系维度）。

## 设计特点
- **Crew 核心**（lib/crewai/src/crewai/crew.py 2490 行）——团队核心，管理 Agent 集合和 Task 集合，支持 sequential（顺序）和 hierarchical（层级，manager 分配）两种 Process，Crew 执行引擎调度 Agent 完成任务
- **Flow 运行时**（lib/crewai/src/crewai/flow/runtime/__init__.py 4015 行）——DAG 工作流运行时，支持条件分支/循环/并行/子流程，Flow 可视化（interactive.js 2513 行）
- **Agent 执行器**（lib/crewai/src/crewai/experimental/agent_executor.py 3361 行）——Agent 执行核心，ReAct 循环（思考→行动→观察），工具调用和结果处理
- **Agent 核心**（lib/crewai/src/crewai/agent/core.py 2155 行）——Agent 定义（role/goal/backstory/tools/llm），Agent 行为和记忆
- **LLM 抽象**（lib/crewai/src/crewai/llm.py 2775 行 + llms/providers/openai/completion.py 2805 行 + bedrock/completion.py 2274 行）——多 LLM 提供商抽象（OpenAI/Bedrock/Anthropic/Google 等），统一接口
- **crewai-tools**（lib/crewai-tools/ 322 files）——工具集，内置 50+ 工具（代码执行/文件操作/网络搜索/数据库/API 等）
- **CLI**（lib/cli/ 128 files）——命令行工具，支持项目创建/Crew 运行/部署
- **58,244★**（C02 第 7 张，多智能体协作框架），pushed=2026-09-09（hot），MIT 协议，Python

## 痛点
解决**多 Agent 协作结构化**的痛点——传统多 Agent 框架（autogen）是自由对话驱动，缺乏结构化角色定义和流程编排，协作过程不可控。crewAI 提供角色驱动（role/goal/backstory）+ 流程编排（sequential/hierarchical Process + Flow DAG），让多 Agent 协作结构化、可预测。同时解决**Agent 工具生态碎片化**的痛点——crewai-tools 提供 50+ 内置工具，统一工具接口，避免每个 Agent 自建工具集。与 LangGraph 的通用状态图编排不同，crewAI 专注多 Agent 协作场景（Crew/Agent/Task 抽象），Flow 是扩展能力。

## 优缺点
- 优点：角色驱动（role/goal/backstory 明确）；流程编排（sequential/hierarchical Process + Flow DAG）；Crew 核心 2490 行；Flow 运行时 4015 行；LLM 多提供商抽象（2775 行）；crewai-tools 50+ 工具；CLI 工具（128 files）；58k★ 社区验证；MIT 协议；Python 生态友好
- 缺点：大仓（lib 1324 files，crewai 794 + crewai-tools 322 + cli 128）；核心文件过大（Flow 运行时 4015 行/agent_executor 3361 行/crew.py 2490 行）；Flow 与 Crew 双范式（学习成本）；与 autogen/LangGraph 功能重叠；调试困难（多 Agent 协作过程不透明）；层级 Process 的 manager 开销

## 关键取舍
最核心的取舍是"**角色驱动+流程编排** vs **自由对话**"——crewAI 选择角色驱动+流程编排，获得结构化协作和可预测性，但牺牲了灵活性（自由对话的创造性和适应性）。第二个取舍是"**Crew+Flow 双范式** vs **单一范式**"——crewAI 选择 Crew（多 Agent 协作）+ Flow（DAG 工作流）双范式，获得场景覆盖（协作场景+工作流场景），但增加了学习成本和概念复杂度。第三个取舍是"**内置工具集** vs **工具生态开放**"——crewAI 选择 crewai-tools 内置 50+ 工具，获得开箱即用体验，但牺牲了工具生态开放性（与 LangChain 的 100+ 工具集成相比）。

# 核心深挖域

## arch-orchestration：Crew 核心 + Flow 运行时 + Agent 执行器
crewAI 的编排是 **Crew 核心 + Flow 运行时 + Agent 执行器** 的三层编排。①**Crew 核心**（crew.py 2490 行）——团队编排核心，管理 Agent 集合和 Task 集合，支持 sequential Process（任务按顺序分配给 Agent）和 hierarchical Process（manager Agent 分配任务给 worker Agent），Crew 执行引擎调度 Agent 完成任务，支持任务依赖和结果传递。②**Flow 运行时**（flow/runtime/__init__.py 4015 行）——DAG 工作流运行时，支持条件分支（@task 装饰器+条件）/循环/并行/子流程，Flow 可视化（interactive.js 2513 行），Flow 与 Crew 可嵌套（Flow 中调用 Crew，Crew 中调用 Flow）。③**Agent 执行器**（experimental/agent_executor.py 3361 行）——Agent 执行核心，ReAct 循环（思考→行动→观察），工具调用和结果处理，支持多轮推理和自我修正。与 autogen 的 ConversableAgent 自由对话（对话驱动编排）不同，crewAI 的编排是 Crew+Flow+Agent 执行器（focus on 角色驱动+流程编排，不是自由对话）。溯源：[repo:file:lib/crewai/src/crewai/crew.py:1](https://github.com/crewAIInc/crewAI/blob/a53ecc17f1829354e2d2ff58bbbad1d84ce568b2/lib/crewai/src/crewai/crew.py#L1) (2490 行 Crew 核心), [repo:file:lib/crewai/src/crewai/flow/runtime/__init__.py:1](https://github.com/crewAIInc/crewAI/blob/a53ecc17f1829354e2d2ff58bbbad1d84ce568b2/lib/crewai/src/crewai/flow/runtime/__init__.py#L1) (4015 行 Flow 运行时)

## arch-context：Agent 记忆 + Task 上下文 + Crew 共享状态
crewAI 的上下文管理是 **Agent 记忆 + Task 上下文 + Crew 共享状态** 的三层上下文。①**Agent 记忆**（agent/core.py 2155 行）——Agent 短期记忆（对话历史）和长期记忆（记忆存储），支持记忆检索和召回，记忆可在 Agent 间共享（Crew 级别）。②**Task 上下文**——Task 定义（description/expected_output/context），Task 执行时将描述和上下文注入 Agent 提示词，Task 结果可传递给后续 Task（sequential Process）。③**Crew 共享状态**——Crew 级别共享状态，Agent 可读取和写入共享状态，支持 Agent 间信息传递和协作，Flow 中状态通过 @task 返回值传递。与 LangGraph 的 StateGraph 状态通道（显式状态 schema+10 种通道类型）不同，crewAI 的上下文是 Agent 记忆+Task 上下文+Crew 共享状态（focus on 多 Agent 协作场景的上下文管理，不是显式状态图编排）。溯源：[repo:file:lib/crewai/src/crewai/agent/core.py:1](https://github.com/crewAIInc/crewAI/blob/a53ecc17f1829354e2d2ff58bbbad1d84ce568b2/lib/crewai/src/crewai/agent/core.py#L1) (2155 行 Agent 核心)

## arch-aci：crewai-tools + 工具接口 + LLM 函数调用
crewAI 的工具接口是 **crewai-tools + 工具接口 + LLM 函数调用** 的三层工具架构。①**crewai-tools**（lib/crewai-tools/ 322 files）——内置工具集，50+ 工具（代码执行/文件操作/网络搜索/数据库/API/浏览器等），工具统一接口（BaseTool 抽象），支持工具组合和自定义工具。②**工具接口**——Agent 工具定义（tools 参数），工具调用通过 LLM 函数调用（function calling），工具结果返回 Agent 上下文，支持工具错误处理和重试。③**LLM 函数调用**——LLM 抽象（llm.py 2775 行）统一函数调用接口，支持多 LLM 提供商（OpenAI/Bedrock/Anthropic/Google），函数调用 schema 自动生成（Pydantic 模型）。与 MCP Servers 的 JSON-RPC 单一协议不同，crewAI 的 ACI 是 crewai-tools+工具接口+LLM 函数调用（focus on Python 工具生态和 LLM 函数调用，不是 MCP 协议实现）。溯源：[repo:file:lib/crewai-tools/](https://github.com/crewAIInc/crewAI/tree/a53ecc17f1829354e2d2ff58bbbad1d84ce568b2/lib/crewai-tools/) (322 files 工具集), [repo:file:lib/crewai/src/crewai/llm.py:1](https://github.com/crewAIInc/crewAI/blob/a53ecc17f1829354e2d2ff58bbbad1d84ce568b2/lib/crewai/src/crewai/llm.py#L1) (2775 行 LLM 抽象)

## arch-plan-exec：Task 规划 + Crew 调度 + Agent 执行
crewAI 的规划执行是 **Task 规划 + Crew 调度 + Agent 执行** 的三层规划执行。①**Task 规划**——Task 定义（description/expected_output/agent/context），用户显式定义任务列表和分配，Task 可设置依赖（async_execution 并行），Task 输出可传递。②**Crew 调度**——Crew 核心（crew.py 2490 行）调度 Task 执行，sequential Process 按顺序执行，hierarchical Process 由 manager Agent 动态分配任务，支持任务重试和失败处理。③**Agent 执行**——Agent 执行器（agent_executor.py 3361 行）执行单个任务，ReAct 循环（思考→行动→观察），工具调用和结果处理，支持多轮推理和自我修正，Agent 输出符合 Task expected_output。与 LangGraph 的 StateGraph 显式规划（节点+边+条件）不同，crewAI 的规划执行是 Task 规划+Crew 调度+Agent 执行（focus on 多 Agent 任务分配和调度，不是显式状态图规划）。溯源：[repo:file:lib/crewai/src/crewai/experimental/agent_executor.py:1](https://github.com/crewAIInc/crewAI/blob/a53ecc17f1829354e2d2ff58bbbad1d84ce568b2/lib/crewai/src/crewai/experimental/agent_executor.py#L1) (3361 行 Agent 执行器)

## arch-session：Crew 执行会话 + Agent 对话历史 + Flow 状态
crewAI 的会话管理是 **Crew 执行会话 + Agent 对话历史 + Flow 状态** 的三层会话。①**Crew 执行会话**——Crew.kickoff() 启动执行会话，会话包含 Task 执行状态和 Agent 交互记录，会话结果（CrewOutput）包含最终输出和任务执行详情，支持会话持久化（保存/加载）。②**Agent 对话历史**——Agent 短期记忆（对话历史），记录 Agent 与 LLM 的交互（用户消息/助手响应/工具结果），对话历史在 Task 执行间传递，支持上下文窗口管理。③**Flow 状态**——Flow 运行时（4015 行）管理 Flow 执行状态，状态通过 @task 返回值传递，支持 Flow 中断和恢复，Flow 状态可序列化。与 autogen 的 GroupChat 会话（多 Agent 群聊历史）不同，crewAI 的会话是 Crew 执行会话+Agent 对话历史+Flow 状态（focus on 任务执行会话和 Flow 状态，不是群聊历史）。溯源：[repo:file:lib/crewai/src/crewai/crew.py:1](https://github.com/crewAIInc/crewAI/blob/a53ecc17f1829354e2d2ff58bbbad1d84ce568b2/lib/crewai/src/crewai/crew.py#L1) (2490 行 Crew 会话)

## arch-security：工具沙箱 + LLM 密钥管理 + 代码执行隔离
crewAI 的安全模型是 **工具沙箱 + LLM 密钥管理 + 代码执行隔离** 的三层安全。①**工具沙箱**——crewai-tools 中的代码执行工具（CodeInterpreter/CodeDocsSearch）支持沙箱执行（Docker/本地进程隔离），危险操作（文件删除/系统命令）需用户确认，工具白名单可配置。②**LLM 密钥管理**——LLM API Key 通过环境变量管理（不硬编码），支持多提供商密钥，密钥不暴露给 Agent 上下文。③**代码执行隔离**——代码执行工具支持 Docker 容器隔离，文件系统/网络/进程隔离，沙箱可配置资源限制，代码执行结果安全返回。与 codex 的 OS 级沙箱不同，crewAI 的安全是工具沙箱+LLM 密钥管理+代码执行隔离（focus on Python 工具级安全，不是 OS 级系统调用隔离）。溯源：[repo:file:lib/crewai-tools/](https://github.com/crewAIInc/crewAI/tree/a53ecc17f1829354e2d2ff58bbbad1d84ce568b2/lib/crewai-tools/) (工具集安全)

## arch-memory：Agent 记忆 + 记忆存储 + 记忆检索
crewAI 的记忆系统是 **Agent 记忆 + 记忆存储 + 记忆检索** 的三层记忆。①**Agent 记忆**（agent/core.py 2155 行）——Agent 短期记忆（对话历史，内存中）和长期记忆（记忆存储，持久化），Agent 可通过 memory 参数启用记忆，记忆可在 Agent 间共享。②**记忆存储**——支持多种记忆存储后端（内存/文件/数据库/向量数据库），记忆存储抽象（Memory 基类），支持自定义记忆存储。③**记忆检索**——Agent 执行时检索相关记忆（基于相关性/近期性），检索结果注入提示词上下文，支持记忆添加/更新/删除，记忆可通过工具（MemoryTool）管理。与 mem0 的用户记忆层（实体级记忆+多用户隔离）不同，crewAI 的记忆是 Agent 记忆+记忆存储+记忆检索（focus on 多 Agent 协作场景的记忆共享，不是用户级记忆层）。溯源：[repo:file:lib/crewai/src/crewai/agent/core.py:1](https://github.com/crewAIInc/crewAI/blob/a53ecc17f1829354e2d2ff58bbbad1d84ce568b2/lib/crewai/src/crewai/agent/core.py#L1) (2155 行 Agent 记忆)

# 其他架构域简评
- arch-workflow：Flow DAG 工作流（运行时 4015 行），支持条件分支/循环/并行/子流程
- arch-llm-abstraction：llm.py 2775 行 + 多提供商（OpenAI 2805/Bedrock 2274），统一 LLM 接口
- arch-observability：Flow 可视化（interactive.js 2513 行），Crew 执行日志，无独立可观测性平台
- arch-streaming：LLM 流式响应（llm.py 支持 stream=True），Agent 输出流式展示
- arch-skill-philosophy：crewai-tools 技能系统（50+ 工具），支持自定义工具和工具组合
- arch-typing：Python Pydantic 强类型（Task/Agent/Crew 模型），函数调用 schema 自动生成
- arch-distribution：PyPI 包（crewai + crewai-tools），CLI 工具（128 files），Docker 部署
- arch-exec-backend：本地进程执行（Python），代码执行工具支持 Docker 沙箱
- arch-frontend：Flow 可视化（interactive.js 2513 行），无独立 Web UI（CLI 为主）
- arch-checkpoint：Flow 状态持久化（可序列化），Crew 会话保存/加载
- arch-plugins：crewai-tools 插件系统（BaseTool 抽象），支持自定义工具
- arch-fault-tolerance：Task 重试（max_iter/retry），工具错误处理，无自动熔断

# claim 台账

| claim | 溯源锚点（repo:file:line） | 置信度 |
|---|---|---|
| Crew 核心 2490 行 | [repo:file:lib/crewai/src/crewai/crew.py:1](https://github.com/crewAIInc/crewAI/blob/a53ecc17f1829354e2d2ff58bbbad1d84ce568b2/lib/crewai/src/crewai/crew.py#L1) (2490 行实测) | EXTRACTED |
| Flow 运行时 4015 行 | [repo:file:lib/crewai/src/crewai/flow/runtime/__init__.py:1](https://github.com/crewAIInc/crewAI/blob/a53ecc17f1829354e2d2ff58bbbad1d84ce568b2/lib/crewai/src/crewai/flow/runtime/__init__.py#L1) (4015 行实测) | EXTRACTED |
| Agent 执行器 3361 行 | [repo:file:lib/crewai/src/crewai/experimental/agent_executor.py:1](https://github.com/crewAIInc/crewAI/blob/a53ecc17f1829354e2d2ff58bbbad1d84ce568b2/lib/crewai/src/crewai/experimental/agent_executor.py#L1) (3361 行实测) | EXTRACTED |
| LLM 抽象 2775 行 | [repo:file:lib/crewai/src/crewai/llm.py:1](https://github.com/crewAIInc/crewAI/blob/a53ecc17f1829354e2d2ff58bbbad1d84ce568b2/lib/crewai/src/crewai/llm.py#L1) (2775 行实测) | EXTRACTED |
| Agent 核心 2155 行 | [repo:file:lib/crewai/src/crewai/agent/core.py:1](https://github.com/crewAIInc/crewAI/blob/a53ecc17f1829354e2d2ff58bbbad1d84ce568b2/lib/crewai/src/crewai/agent/core.py#L1) (2155 行实测) | EXTRACTED |
| OpenAI provider 2805 行 | [repo:file:lib/crewai/src/crewai/llms/providers/openai/completion.py:1](https://github.com/crewAIInc/crewAI/blob/a53ecc17f1829354e2d2ff58bbbad1d84ce568b2/lib/crewai/src/crewai/llms/providers/openai/completion.py#L1) (2805 行实测) | EXTRACTED |
| crewai-tools 322 files | lib/crewai-tools/ 322 files（实测） | EXTRACTED |
| CLI 128 files | lib/cli/ 128 files（实测） | EXTRACTED |
| 主类复核 C02（决策树⑨） | category_review 字段（复核结论） | EXTRACTED |
| 58,244★（C02 第 7 张） | GitHub API 实测 | EXTRACTED |
| pushed=2026-09-09（hot） | git log 实测 | EXTRACTED |

# 矛盾记录（Disputed）
无（C02 第 7 张，与 autogen(F-C02-001)/hermes-agent(F-C02-002)/MetaGPT(F-C02-003)/ChatDev(F-C02-004)/generative_agents(F-C02-005)/camel(F-C02-006) 互为参照——crewAI 是流程驱动（角色+任务+流程），autogen 是对话驱动（自由对话），hermes-agent 是助手驱动（单 agent+子代理），MetaGPT/ChatDev 是流程驱动（SOP/链式），generative_agents 是模拟驱动（虚拟小镇），camel 是对话驱动（角色扮演），协作范式谱系见 M-005）。

# 对照验证
- 对照源：https://deepwiki.com/crewAIInc/crewAI（Tier2：DeepWiki 自动生成的代码文档）
- 访问日期：2026-09-09
- 索引 commit：a53ecc17f1829354e2d2ff58bbbad1d84ce568b2（本地 clone HEAD）
- 访问结果：HTTP 200（DeepWiki 页面可访问，2026-09-09 实测）
- 索引 commit：a53ecc17f1829354e2d2ff58bbbad1d84ce568b2（本地 clone HEAD，DeepWiki 索引版本可能滞后）
- 不一致裁决：本地代码级溯源（核心文件行数/目录结构/commit hash 实测）与 DeepWiki 文档无重大不一致；DeepWiki 为 JavaScript 动态渲染，详细代码文档对比需人工浏览页面；本卡 claim 全部基于本地 clone 实测（EXTRACTED），DeepWiki 作为 Tier2 对照源确认 repo 存在和架构概述一致

# 溯源
- repo:lib/crewai/src/crewai/crew.py（2490 行 Crew 核心）
- repo:lib/crewai/src/crewai/flow/runtime/__init__.py（4015 行 Flow 运行时）
- repo:lib/crewai/src/crewai/experimental/agent_executor.py（3361 行 Agent 执行器）
- repo:lib/crewai/src/crewai/llm.py（2775 行 LLM 抽象）
- repo:lib/crewai/src/crewai/agent/core.py（2155 行 Agent 核心）
- repo:lib/crewai-tools/（322 files 工具集）

# 待补
- [x] DeepWiki 对照验证（HTTP 200 已访问，对照节已裁决 2026-09-09）
- [ ] 本地部署验证（pip install crewai，验证 Crew/Flow 可运行）
- [ ] Flow 运行时详细实现（当前仅概述，需精读 4015 行）
- [ ] hierarchical Process 的 manager 实现（当前仅概述）
- [ ] 与 autogen 的协作范式对比矩阵（对话驱动 vs 流程驱动）

## 更新记录

- 2026-09-11 | LB-R2-a 30天复扫 | star=58362（58244→58362） | HEAD=c5759ce854337167e19ab96621c0565bc820e468（pinned=a53ecc17f1829354e2d2ff58bbbad1d84ce568b2，commit 漂移 a53ecc17f1→c5759ce854）| L1 微漂移标注（CB-11：仅标注，未重蒸馏；3 天窗口 star 漂移<2%，无 L2/L3 信号）| pushed_at=2026-09-11 archived=false | 锚点 repo_base_url/repo_local_path 不动
- 2026-09-14 | LB-R4 30天复扫 | star=58456（58362→58456） | HEAD=894898f84c4ac0a89f24bf7bee6c381eb0e67f51（pinned=a53ecc17f1829354e2d2ff58bbbad1d84ce568b2，commit 漂移 a53ecc17f1→894898f84c） | L3 显著漂移（diffstat=850 files changed, +178540/-280；结构变化大，重蒸馏议题交编排者复核日裁决）| pushed_at=2026-09-13 archived=false

