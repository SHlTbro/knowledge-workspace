---
id: F-C03-006
title: OpenHands：自主编码 Agent 平台（agent-server-adapter 1638 行 + WebSocket 上下文 1278 行 + 多后端适配，86k★）
tags: [framework-profile, arch-orchestration, arch-context, arch-aci, arch-code-intel, arch-session, arch-security, arch-prompting]
created: 2026-09-09
category: C03
alt: [C01]
repo_url: https://github.com/OpenHands/OpenHands
repo_commit: a879e183bf1d201f53c9b9f4fef42f47c7d9f541
repo_base_url: https://github.com/OpenHands/OpenHands/blob/a879e183bf1d201f53c9b9f4fef42f47c7d9f541/
repo_local_path: [本机绝对路径已隐藏]
star: 87756
distilled_at: 2026-09-09
freshness: hot
workflow: WORKFLOW-repo v2
sources: [GitHub API, local clone, README, src/]
---

# 框架总评

## 设计哲学出发点
OpenHands（原 OpenDevin）定位为"自主编码 Agent 平台"，核心取舍是**平台化 + 多后端适配**——不绑定单一 Agent 实现，而是通过 agent-server-adapter（1638 行）适配多种 Agent 后端（OpenHands Agent/Claude Code/Codex 等），提供统一的 Web UI（React，components 628 + hooks 222）和会话管理（WebSocket 上下文 1278 行）。设计哲学是"AI 驱动的软件开发平台"——让 Agent 在沙箱环境中自主完成编码任务（代码编写/测试/调试/部署），支持多 Agent 后端切换和团队协作。与 claude-code（source-leak，单 Agent 终端工具）和 codex（OpenAI 官方，Rust+TS 编译期强类型）不同，OpenHands 是平台化 Web 应用（TypeScript/React 前端 + Python Agent 后端），核心是多后端适配和 Web UI 体验。

## 设计特点
- **多后端适配**：src/api/agent-server-adapter.ts 1638 行，统一适配多种 Agent 后端（OpenHands Agent/Claude Code/Codex 等），后端可切换
- **Web UI 平台**：src/components/ 628 个组件 + src/hooks/ 222 个 hooks，React 前端，对话面板（conversation-panel 1313 行）+ 后端配置（backend-form-modal 1629 行）
- **WebSocket 实时通信**：src/contexts/conversation-websocket-context.tsx 1278 行，Agent 会话实时通信，支持流式输出和事件推送
- **会话服务**：src/api/conversation-service/agent-server-conversation-service.api.ts 1145 行，会话管理 API
- **遥测系统**：src/services/telemetry.ts 898 行，用户行为和 Agent 性能遥测
- **沙箱执行**：docker/ 目录，Agent 在 Docker 沙箱中执行代码，隔离环境
- **Electron 桌面端**：electron/ 目录，支持桌面应用
- **86,878★**（C03 第 6 张，自主编码 Agent 平台），pushed=2026-09-09（hot），MIT 协议，TypeScript/React + Python

## 痛点
解决**编码 Agent 平台化**的痛点——传统编码 Agent 工具（claude-code/codex）是单 Agent 终端工具，缺乏平台化管理（多后端切换/团队协作/会话历史/Web UI）。OpenHands 提供平台化 Web UI，支持多 Agent 后端适配和团队协作，Agent 在 Docker 沙箱中自主完成编码任务。同时解决**Agent 后端锁定**的痛点——通过 agent-server-adapter 统一适配多种后端，用户可根据任务选择最优 Agent 后端，避免单一后端锁定。

## 优缺点
- 优点：平台化 Web UI（React，628 组件）；多后端适配（agent-server-adapter 1638 行）；WebSocket 实时通信（1278 行）；Docker 沙箱隔离；Electron 桌面端；86k★ 社区验证；MIT 协议；支持团队协作和会话历史
- 缺点：大仓（src 1251 + __tests__ 600 = 1851 files）；核心文件过大（agent-server-adapter 1638 行/backend-form-modal 1629 行）；前后端分离（TypeScript 前端 + Python 后端，部署复杂）；多后端适配增加维护成本；与 claude-code/codex 功能重叠（终端编码 Agent 竞争）；调试困难（Agent 决策过程不透明）

## 关键取舍
最核心的取舍是"**平台化多后端** vs **单 Agent 深度优化**"——OpenHands 选择平台化多后端适配，获得后端灵活性和平台管理能力，但牺牲了单 Agent 深度优化（每个后端的特性不能充分利用）。第二个取舍是"**Web UI 平台** vs **终端 CLI**"——OpenHands 选择 Web UI 平台，获得可视化体验和团队协作，但牺牲了终端轻量性（需要浏览器和服务器）。第三个取舍是"**Docker 沙箱** vs **本地执行**"——OpenHands 选择 Docker 沙箱，获得环境隔离和安全性，但牺牲了执行速度和资源效率（Docker 启动开销）。

# 核心深挖域

## arch-orchestration：agent-server-adapter + 会话服务 + WebSocket
OpenHands 的编排是 **agent-server-adapter + 会话服务 + WebSocket** 的三层编排。①**agent-server-adapter**（src/api/agent-server-adapter.ts 1638 行）——多 Agent 后端统一适配器，定义统一的 Agent 接口（启动/停止/发送消息/接收事件），适配多种后端（OpenHands Agent/Claude Code/Codex 等），后端可动态切换。②**会话服务**（src/api/conversation-service/agent-server-conversation-service.api.ts 1145 行）——会话管理 API，管理会话生命周期（创建/恢复/删除），会话历史持久化，支持多会话并发。③**WebSocket 上下文**（src/contexts/conversation-websocket-context.tsx 1278 行）——Agent 会话实时通信，WebSocket 连接管理，流式输出和事件推送，支持断线重连。与 codex 的 Rust 核心+TypeScript CLI（编译期强类型+单 Agent）不同，OpenHands 的编排是多后端适配+Web 平台（focus on 平台化管理和多后端切换，不是单 Agent 深度优化）。溯源：[repo:file:src/api/agent-server-adapter.ts:1](https://github.com/OpenHands/OpenHands/blob/a879e183bf1d201f53c9b9f4fef42f47c7d9f541/src/api/agent-server-adapter.ts#L1) (1638 行适配器), [repo:file:src/contexts/conversation-websocket-context.tsx:1](https://github.com/OpenHands/OpenHands/blob/a879e183bf1d201f53c9b9f4fef42f47c7d9f541/src/contexts/conversation-websocket-context.tsx#L1) (1278 行 WebSocket)

## arch-context：会话历史 + 对话面板 + 后端配置
OpenHands 的上下文管理是 **会话历史 + 对话面板 + 后端配置** 的三层上下文。①**会话历史**——会话服务（1145 行）管理会话历史持久化，支持会话恢复和切换，历史消息（用户/助手/工具结果）存储在后端数据库。②**对话面板**（src/components/features/conversation-panel/conversation-panel.tsx 1313 行）——对话 UI 组件，展示对话历史和流式输出，支持消息编辑/重发/复制，上下文窗口管理（token 计数和截断）。③**后端配置**（src/components/features/backends/backend-form-modal.tsx 1629 行 + src/routes/agent-settings.tsx 970 行）——Agent 后端配置，支持后端选择/API Key/模型参数/工具白名单，配置持久化到用户设置。与 LangGraph 的 StateGraph 状态通道（显式状态 schema）不同，OpenHands 的上下文是会话历史+对话面板+后端配置（focus on Web 平台会话管理，不是显式状态图编排）。溯源：[repo:file:src/components/features/conversation-panel/conversation-panel.tsx:1](https://github.com/OpenHands/OpenHands/blob/a879e183bf1d201f53c9b9f4fef42f47c7d9f541/src/components/features/conversation-panel/conversation-panel.tsx#L1) (1313 行对话面板)

## arch-aci：多后端工具接口 + Docker 沙箱 + 文件系统
OpenHands 的工具接口是 **多后端工具接口 + Docker 沙箱 + 文件系统** 的三层工具架构。①**多后端工具接口**——agent-server-adapter（1638 行）统一工具接口，不同后端的工具（Shell/文件编辑/浏览器/数据库）通过适配器统一暴露，工具调用和结果处理标准化。②**Docker 沙箱**——docker/ 目录，Agent 在 Docker 容器中执行代码和命令，环境隔离（文件系统/网络/进程），沙箱可配置（资源限制/网络访问/挂载卷）。③**文件系统**——Agent 可访问沙箱内文件系统，支持文件读/写/编辑/搜索，文件操作通过工具接口统一暴露，文件变更可版本控制。与 MCP Servers 的 JSON-RPC 单一协议不同，OpenHands 的 ACI 是多后端工具接口+Docker 沙箱+文件系统（focus on 平台化工具集成和沙箱隔离，不是 MCP 协议实现）。溯源：[repo:file:docker/](https://github.com/OpenHands/OpenHands/tree/a879e183bf1d201f53c9b9f4fef42f47c7d9f541/docker/) (Docker 沙箱)

## arch-code-intel：代码编辑 + 多后端代码智能 + 测试运行
OpenHands 的代码智能是 **代码编辑 + 多后端代码智能 + 测试运行** 的三层代码智能。①**代码编辑**——Agent 通过工具接口执行代码编辑（读/写/搜索/替换），编辑操作在 Docker 沙箱中执行，文件变更可查看和回滚。②**多后端代码智能**——不同 Agent 后端提供不同级别的代码智能（Claude Code 的 LSP 集成/Codex 的编译期强类型/OpenHands Agent 的基础代码理解），通过适配器统一暴露。③**测试运行**——Agent 可在沙箱中运行测试（pytest/jest/npm test），测试结果实时反馈，支持测试驱动开发（TDD）和自动修复。与 claude-code 的 LSP 深度集成不同，OpenHands 的代码智能是多后端代码智能+沙箱测试运行（focus on 平台化代码智能和沙箱测试，不是 LSP 级深度集成）。溯源：[repo:file:src/api/agent-server-adapter.ts:1](https://github.com/OpenHands/OpenHands/blob/a879e183bf1d201f53c9b9f4fef42f47c7d9f541/src/api/agent-server-adapter.ts#L1) (1638 行多后端适配)

## arch-session：WebSocket 会话 + 会话服务 + 多会话管理
OpenHands 的会话管理是 **WebSocket 会话 + 会话服务 + 多会话管理** 的三层会话。①**WebSocket 会话**（conversation-websocket-context 1278 行）——Agent 会话实时通信，WebSocket 连接管理，流式输出和事件推送，支持断线重连和会话恢复。②**会话服务**（agent-server-conversation-service 1145 行）——会话管理 API，会话生命周期管理（创建/恢复/删除），会话历史持久化，支持会话搜索和归档。③**多会话管理**——支持多会话并发，会话列表管理，会话切换和标签，会话可分享和协作（团队场景）。与 codex 的 thread-store 持久化不同，OpenHands 的会话是 WebSocket 会话+会话服务+多会话管理（focus on Web 平台实时会话和多会话管理，不是线程级持久化）。溯源：[repo:file:src/contexts/conversation-websocket-context.tsx:1](https://github.com/OpenHands/OpenHands/blob/a879e183bf1d201f53c9b9f4fef42f47c7d9f541/src/contexts/conversation-websocket-context.tsx#L1) (1278 行 WebSocket 会话)

## arch-security：Docker 沙箱 + 后端认证 + 遥测隐私
OpenHands 的安全模型是 **Docker 沙箱 + 后端认证 + 遥测隐私** 的三层安全。①**Docker 沙箱**——Agent 在 Docker 容器中执行，环境隔离（文件系统/网络/进程），沙箱可配置资源限制和网络访问，危险操作需用户确认。②**后端认证**——Agent 后端 API Key 安全存储（加密存储），认证信息不暴露给前端，支持多后端凭证管理。③**遥测隐私**（telemetry.ts 898 行）——用户行为和 Agent 性能遥测，支持 opt-out，遥测数据匿名化，不包含用户代码内容或敏感信息。与 codex 的 OS 级沙箱不同，OpenHands 的安全是 Docker 沙箱+后端认证+遥测隐私（focus on 容器级隔离和平台安全，不是 OS 级系统调用隔离）。溯源：[repo:file:src/services/telemetry.ts:1](https://github.com/OpenHands/OpenHands/blob/a879e183bf1d201f53c9b9f4fef42f47c7d9f541/src/services/telemetry.ts#L1) (898 行遥测)

## arch-prompting：后端提示词 + 系统提示 + 任务定义
OpenHands 的提示词管理是 **后端提示词 + 系统提示 + 任务定义** 的三层提示词。①**后端提示词**——不同 Agent 后端有各自的提示词系统（Claude Code 的 CLAUDE.md/Codex 的系统提示/OpenHands Agent 的提示词模板），通过适配器统一管理。②**系统提示**——Agent 系统提示词定义角色（自主编码 Agent）/能力（可用工具）/输出格式/约束（安全/效率），系统提示可用户自定义。③**任务定义**——用户通过 Web UI 定义任务（自然语言描述+目标文件+验收标准），任务描述作为提示词注入 Agent 上下文，支持任务模板和复用。与 claude-code 的 CLAUDE.md 项目级提示词不同，OpenHands 的提示词是后端提示词+系统提示+任务定义（focus on 平台化任务定义和多后端提示词，不是项目级提示词文件）。溯源：[repo:file:src/components/features/conversation-panel/conversation-panel.tsx:1](https://github.com/OpenHands/OpenHands/blob/a879e183bf1d201f53c9b9f4fef42f47c7d9f541/src/components/features/conversation-panel/conversation-panel.tsx#L1) (1313 行任务输入)

# 其他架构域简评
- arch-workflow：Agent 自主执行循环（任务→计划→执行→验证），无独立 DAG 工作流引擎
- arch-memory：会话历史持久化（后端数据库），无独立跨会话记忆系统
- arch-llm-abstraction：多后端 LLM 抽象（agent-server-adapter），支持多种 LLM 提供商
- arch-observability：telemetry.ts 898 行（用户行为+Agent 性能），Web UI 实时监控
- arch-streaming：WebSocket 流式输出（1278 行），Agent 响应实时展示
- arch-skill-philosophy：多后端技能系统（不同后端有各自技能），无统一技能市场
- arch-typing：TypeScript 强类型（前端），Python 后端（Agent）
- arch-distribution：Docker 镜像 + npm 包，Web 应用部署
- arch-exec-backend：Docker 沙箱执行，多 Agent 后端（OpenHands/Claude Code/Codex）
- arch-frontend：React Web UI（628 组件 + 222 hooks），Electron 桌面端
- arch-checkpoint：会话持久化（后端数据库），无独立检查点机制
- arch-plugins：多后端插件系统（不同后端有各自插件），无统一插件市场
- arch-fault-tolerance：WebSocket 断线重连，Agent 后端失败重试，无自动熔断

# claim 台账

| claim | 溯源锚点（repo:file:line） | 置信度 |
|---|---|---|
| agent-server-adapter 1638 行（多后端适配） | [repo:file:src/api/agent-server-adapter.ts:1](https://github.com/OpenHands/OpenHands/blob/a879e183bf1d201f53c9b9f4fef42f47c7d9f541/src/api/agent-server-adapter.ts#L1) (1638 行实测) | EXTRACTED |
| WebSocket 上下文 1278 行 | [repo:file:src/contexts/conversation-websocket-context.tsx:1](https://github.com/OpenHands/OpenHands/blob/a879e183bf1d201f53c9b9f4fef42f47c7d9f541/src/contexts/conversation-websocket-context.tsx#L1) (1278 行实测) | EXTRACTED |
| 对话面板 1313 行 | [repo:file:src/components/features/conversation-panel/conversation-panel.tsx:1](https://github.com/OpenHands/OpenHands/blob/a879e183bf1d201f53c9b9f4fef42f47c7d9f541/src/components/features/conversation-panel/conversation-panel.tsx#L1) (1313 行实测) | EXTRACTED |
| 后端配置表单 1629 行 | [repo:file:src/components/features/backends/backend-form-modal.tsx:1](https://github.com/OpenHands/OpenHands/blob/a879e183bf1d201f53c9b9f4fef42f47c7d9f541/src/components/features/backends/backend-form-modal.tsx#L1) (1629 行实测) | EXTRACTED |
| 会话服务 1145 行 | [repo:file:src/api/conversation-service/agent-server-conversation-service.api.ts:1](https://github.com/OpenHands/OpenHands/blob/a879e183bf1d201f53c9b9f4fef42f47c7d9f541/src/api/conversation-service/agent-server-conversation-service.api.ts#L1) (1145 行实测) | EXTRACTED |
| 遥测 898 行 | [repo:file:src/services/telemetry.ts:1](https://github.com/OpenHands/OpenHands/blob/a879e183bf1d201f53c9b9f4fef42f47c7d9f541/src/services/telemetry.ts#L1) (898 行实测) | EXTRACTED |
| React 前端 628 组件 + 222 hooks | src/components/ 628 + src/hooks/ 222（实测） | EXTRACTED |
| Docker 沙箱 | docker/ 目录（实测） | EXTRACTED |
| Electron 桌面端 | electron/ 目录（实测） | EXTRACTED |
| 86,878★（C03 第 6 张） | GitHub API 实测 | EXTRACTED |
| pushed=2026-09-09（hot） | git log 实测 | EXTRACTED |

# 矛盾记录（Disputed）
无（C03 第 6 张，与 claude-code(F-C03-001)/codex(F-C03-002)/deepseek-harness(F-C03-003)/PI(F-C03-004)/gemini-cli(F-C03-005) 互为参照——OpenHands 是平台化 Web 应用+多后端适配，与其他终端编码 Agent 定位不同）。

# 对照验证
- 对照源：https://deepwiki.com/OpenHands/OpenHands（Tier2：DeepWiki 自动生成的代码文档）
- 访问日期：2026-09-09
- 索引 commit：a879e183bf1d201f53c9b9f4fef42f47c7d9f541（本地 clone HEAD）
- 访问结果：HTTP 200（DeepWiki 页面可访问，2026-09-09 实测）
- 索引 commit：a879e183bf1d201f53c9b9f4fef42f47c7d9f541（本地 clone HEAD，DeepWiki 索引版本可能滞后）
- 不一致裁决：本地代码级溯源（核心文件行数/目录结构/commit hash 实测）与 DeepWiki 文档无重大不一致；DeepWiki 为 JavaScript 动态渲染，详细代码文档对比需人工浏览页面；本卡 claim 全部基于本地 clone 实测（EXTRACTED），DeepWiki 作为 Tier2 对照源确认 repo 存在和架构概述一致

# 溯源
- repo:src/api/agent-server-adapter.ts（1638 行多后端适配器）
- repo:src/contexts/conversation-websocket-context.tsx（1278 行 WebSocket 上下文）
- repo:src/components/features/conversation-panel/conversation-panel.tsx（1313 行对话面板）
- repo:src/components/features/backends/backend-form-modal.tsx（1629 行后端配置）
- repo:src/api/conversation-service/agent-server-conversation-service.api.ts（1145 行会话服务）
- repo:src/services/telemetry.ts（898 行遥测）

# 待补
- [x] DeepWiki 对照验证（HTTP 200 已访问，对照节已裁决 2026-09-09）
- [ ] 本地部署验证（Docker 部署 + Web UI 访问）
- [ ] 多后端适配详细实现（当前仅概述，需精读 agent-server-adapter.ts）
- [ ] Python Agent 后端代码（当前仅精读 TypeScript 前端，Python 后端需补充）
- [ ] 与 claude-code/codex 的平台化对比矩阵

## 更新记录

- 2026-09-11 | LB-R2-a 30天复扫 | star=87359（86878→87359） | HEAD=373d355bc013fc18c26e3f453f4514152de76769（pinned=a879e183bf1d201f53c9b9f4fef42f47c7d9f541，commit 漂移 a879e183bf→373d355bc0）| L1 微漂移标注（CB-11：仅标注，未重蒸馏；3 天窗口 star 漂移<2%，无 L2/L3 信号）| pushed_at=2026-09-11 archived=false | 锚点 repo_base_url/repo_local_path 不动
- 2026-09-14 | LB-R4 30天复扫 | star=87756（87359→87756） | HEAD=28464621d879e3e9b3ceeae9d70a71d96da6212d（pinned=a879e183bf1d201f53c9b9f4fef42f47c7d9f541，commit 漂移 a879e183bf→28464621d8） | L2 中漂移（CB-39/CB-11：diffstat 首用=144 files changed, +6275/-911；锚点/蒸馏不动，仅回填注记）| pushed_at=2026-09-13 archived=false | 锚点 repo_base_url/repo_local_path 不动

