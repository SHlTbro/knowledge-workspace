---
id: F-C04-001
title: daytona：开发环境沙箱平台（apps 12 服务+libs 27 库多语言 SDK+runner 容器执行+computer-use，71k★）
tags: [framework-profile, arch-sandbox, arch-dev-environment, arch-container, arch-api, arch-sdk]
created: 2026-09-09
category: C04
alt: [C03, C08]
repo_url: https://github.com/daytonaio/daytona
repo_commit: 01c502bb1f1ff8f2885d0cd490e043736083dca8
repo_base_url: https://github.com/daytonaio/daytona/blob/01c502bb1f1ff8f2885d0cd490e043736083dca8/
repo_local_path: [本机绝对路径已隐藏]
star: 71718
distilled_at: 2026-09-09
freshness: archived
workflow: WORKFLOW-repo v2
sources: [GitHub API, local clone (v0.190.0 tag), README, apps/, libs/]
archived_note: main 分支已于 2026-06 归档（迁移到私有代码库），本卡基于 v0.190.0 tag（最后一个公开版本）蒸馏
---

# 框架总评

## 设计哲学出发点
daytona 定位为"开发环境沙箱平台"（daytonaio 组织开源，MIT 协议），核心取舍是**一次性开发环境+安全沙箱优先**——把开发环境建模为可编排的容器沙箱，支持秒级启动、预配置环境、代码执行、SSH 访问、VS Code 连接，解决"在我机器上能跑"的环境一致性问题。设计哲学是"dev environments as code"——开发环境通过配置文件定义（devcontainer/devfile），支持版本控制和复现，与 CI/CD 流水线集成。与 Docker 的通用容器平台不同，daytona 的核心是开发环境专用沙箱（预配置语言运行时+工具链+IDE 连接+代码同步）。

**重要归档声明**：daytona main 分支已于 2026 年 6 月归档——README 明确声明 "This repository is no longer maintained. As of June 2026, Daytona's core development has moved to a private codebase." main 分支仅保留归档声明 README，实际代码在 v0.190.0 tag（最后一个公开版本，commit 01c502bb）。本卡基于 v0.190.0 tag 蒸馏，诚实记录归档状态。

## 设计特点
- **Monorepo 架构**：apps/ 12 个服务（api/cli/daemon/dashboard/daytona-e2e/docs/otel-collector/proxy/runner/snapshot-manager/ssh-gateway）+ libs/ 27 个库（多语言 SDK+api-client+computer-use+opencode-plugin+pi-extension）
- **Runner 容器执行**：apps/runner 是核心运行器，管理开发环境容器的生命周期（创建/启动/停止/删除），支持 Docker/Kubernetes 后端
- **多语言 SDK**：libs/ 下 sdk-go/sdk-java/sdk-python/sdk-ruby/sdk-typescript（5 种语言 SDK），api-client-go/api-client-java/api-client-python/api-client-python-async/api-client-ruby（5 种语言 API 客户端）
- **CLI 工具**：apps/cli 命令行工具，支持创建/管理开发环境、SSH 连接、VS Code 打开、代码同步
- **API 服务器**：apps/api REST/gRPC API 服务器，管理开发环境生命周期，支持认证/限流/审计
- **Dashboard**：apps/dashboard Web 仪表板，可视化管理开发环境，支持环境监控和日志查看
- **SSH 网关**：apps/ssh-gateway SSH 访问网关，支持 SSH 直接连接开发环境
- **代理**：apps/proxy 反向代理，支持开发环境端口转发和域名路由
- **Computer Use**：libs/computer-use 计算机使用能力库，支持 GUI 自动化（与 browser-use 类似但更通用）
- **IDE 插件**：libs/opencode-plugin（opencode 插件）+ libs/pi-extension（PI 扩展），支持在 IDE 中直接管理 daytona 环境
- **71,755★**（C04 空域首例，开发环境沙箱第一大仓），MIT 协议，Go/TypeScript/Python 多语言

## 痛点
解决开发环境**配置不一致、复现困难**的痛点——"在我机器上能跑"是经典问题，开发者本地环境与生产/CI 环境不一致导致难以调试。daytona 通过开发环境即代码（devcontainer/devfile）实现环境一致性和复现。同时解决**云开发环境安全隔离**的痛点——多人共享开发服务器时环境互相干扰，daytona 的容器沙箱提供隔离的开发环境，支持资源限制和网络隔离。与 GitHub Codespaces 的商业云服务不同，daytona 是开源自托管方案，支持部署在私有基础设施上。

## 优缺点
- 优点：开发环境即代码（devcontainer/devfile 配置）；Monorepo 架构清晰（apps 12 服务+libs 27 库）；多语言 SDK（5 种语言 SDK+5 种语言 API 客户端）；CLI 工具完善；Web Dashboard 可视化；SSH 网关直接连接；IDE 插件支持（opencode/PI）；Computer Use 能力；开源自托管（MIT 协议）；71k★ 社区验证
- 缺点：**已归档**（2026-06 迁移到私有代码库，公开版本停更）；大仓（apps 12+libs 27，多语言 monorepo）；部署复杂（需 Kubernetes/Docker+API+Runner+Proxy+SSH 网关多服务）；学习曲线陡峭（devcontainer/devfile 规范+多服务架构）；与 Docker/Kubernetes 功能重叠（底层依赖容器编排）；商业版本与开源版本功能差异（核心开发已私有化）

## 关键取舍
最核心的取舍是"**开发环境专用沙箱** vs **通用容器平台**"——daytona 选择开发环境专用（预配置语言运行时+工具链+IDE 连接+代码同步），获得开发体验优化（秒级启动+VS Code 连接+环境复现），但牺牲了通用性（不能运行任意容器，仅限开发环境场景）。第二个取舍是"**开源自托管** vs **商业云服务**"——daytona 选择开源自托管（MIT 协议，可部署私有基础设施），获得数据主权和成本控制，但牺牲了托管便利性（需自行部署和维护多服务架构）。第三个取舍是"**Monorepo 多服务** vs **单二进制**"——daytona 选择 Monorepo 多服务（api/runner/proxy/ssh-gateway 独立部署），获得可扩展性和独立升级，但增加了部署复杂度和运维成本。

# 核心深挖域


## arch-aci：多语言 SDK + API 客户端 + CLI + IDE 插件
daytona 的工具接口是 **多语言 SDK + API 客户端 + CLI + IDE 插件** 的四层接入架构。①**多语言 SDK**（libs/sdk-go/sdk-java/sdk-python/sdk-ruby/sdk-typescript）——5 种语言的高级 SDK，封装开发环境管理操作（create/start/stop/delete/ssh/code），提供类型安全的 API 和异步支持。②**API 客户端**（libs/api-client-go/api-client-java/api-client-python/api-client-python-async/api-client-ruby）——5 种语言的低级 API 客户端，直接调用 REST/gRPC API，支持自定义认证和中间件。③**CLI**（apps/cli）——命令行工具，支持 `daytona create`/`daytona start`/`daytona stop`/`daytona ssh`/`daytona code`（VS Code 打开）/`daytona list`/`daytona delete` 等命令，支持 shell 补全和配置文件。④**IDE 插件**（libs/opencode-plugin + libs/pi-extension）——opencode 插件和 PI 扩展，支持在 IDE 中直接创建/管理 daytona 开发环境，无需切换到终端。⑤**Computer Use**（libs/computer-use）——计算机使用能力库，支持 GUI 自动化操作（鼠标/键盘/截图），可用于开发环境内的自动化测试。与 browser-use 的 MCP 服务器（1294 行，浏览器工具 MCP 化）不同，daytona 的 ACI 是多语言 SDK+API 客户端+CLI+IDE 插件（focus on 多语言接入和 IDE 集成，不是 MCP 协议）。溯源：[repo:file:libs/](https://github.com/daytonaio/daytona/blob/01c502bb1f1ff8f2885d0cd490e043736083dca8/libs/) (27 个库，含 5 语言 SDK+5 语言 API 客户端), [repo:file:apps/cli/](https://github.com/daytonaio/daytona/blob/01c502bb1f1ff8f2885d0cd490e043736083dca8/apps/cli/) (CLI 工具)

## arch-orchestration：API 编排 + Runner 调度 + Proxy 路由 + SSH 网关
daytona 的编排是 **API 编排 + Runner 调度 + Proxy 路由 + SSH 网关** 的多服务协作架构。①**API 服务器**（apps/api）——中央编排器，接收用户请求（创建环境/启动/停止），验证认证和权限，调度 Runner 执行，管理环境状态数据库，支持 REST 和 gRPC 接口。②**Runner 调度**——API 服务器根据资源可用性和标签调度 Runner 执行环境创建/启动，支持多 Runner 实例（水平扩展）和亲和性调度（特定环境调度到特定 Runner）。③**Proxy**（apps/proxy）——反向代理，根据子域名或路径路由到对应开发环境的端口，支持 HTTPS 终止和 WebSocket 代理，让开发环境的 Web 服务可通过统一域名访问。④**SSH 网关**（apps/ssh-gateway）——SSH 访问网关，用户通过 SSH 连接到网关，网关根据用户名/环境 ID 路由到对应开发环境的 SSH 服务器，支持 SSH 密钥认证和审计日志。⑤**Daemon**（apps/daemon）——守护进程，管理 Runner 节点的注册和心跳，监控节点健康状态，支持节点自动发现和故障转移。与 Kubernetes 的容器编排（Scheduler+Controller+etcd）不同，daytona 的编排是开发环境专用多服务协作（focus on 开发环境生命周期和访问路由，不是通用容器编排）。溯源：[repo:file:apps/api/](https://github.com/daytonaio/daytona/blob/01c502bb1f1ff8f2885d0cd490e043736083dca8/apps/api/) (API 编排器), [repo:file:apps/proxy/](https://github.com/daytonaio/daytona/blob/01c502bb1f1ff8f2885d0cd490e043736083dca8/apps/proxy/) (反向代理), [repo:file:apps/ssh-gateway/](https://github.com/daytonaio/daytona/blob/01c502bb1f1ff8f2885d0cd490e043736083dca8/apps/ssh-gateway/) (SSH 网关)

## arch-security：认证授权 + 网络隔离 + 资源限制 + 审计
daytona 的安全模型是 **认证授权 + 网络隔离 + 资源限制 + 审计日志** 的多层安全。①**认证授权**——API 服务器支持 API Key/OAuth2/JWT 认证，RBAC 角色权限控制（管理员/开发者/只读），环境级权限隔离（用户只能访问自己的环境）。②**网络隔离**——每个开发环境独立网络命名空间，Proxy 只暴露指定端口，SSH 网关限制源 IP，支持 NetworkPolicy 限制环境间通信。③**资源限制**——容器级 CPU/内存/磁盘配额，Runner 节点资源超售控制，支持资源限制和优先级调度。④**审计日志**——所有 API 操作和 SSH 访问记录审计日志，apps/otel-collector 收集可观测性数据（指标/日志/追踪），支持合规审计。⑤**安全上下文**——容器非 root 用户运行，只读根文件系统选项，seccomp/AppArmor 配置，支持安全加固。与 codex 的 OS 级沙箱（Seatbelt/linux/windows/bwrap，系统调用隔离）不同，daytona 的安全是容器级隔离+认证授权+审计（focus on 多租户开发环境安全，不是单 Agent OS 级沙箱）。溯源：[repo:file:apps/api/](https://github.com/daytonaio/daytona/blob/01c502bb1f1ff8f2885d0cd490e043736083dca8/apps/api/) (认证授权), [repo:file:apps/otel-collector/](https://github.com/daytonaio/daytona/blob/01c502bb1f1ff8f2885d0cd490e043736083dca8/apps/otel-collector/) (可观测性收集)


## arch-exec-backend：Docker/Kubernetes 容器后端 + Runner 执行引擎
daytona 的执行后端是 **Docker/Kubernetes 容器后端 + Runner 执行引擎 + 多运行时支持** 的三层执行后端。①容器后端——支持 Docker（单机开发环境）和 Kubernetes（集群生产环境）两种容器后端，开发环境以容器/容器组形式运行，支持容器镜像自定义（devcontainer/devfile 定义）。②Runner 执行引擎（apps/runner）——核心运行器，管理开发环境容器的完整生命周期（创建/启动/停止/删除/资源限制），支持容器健康检查、日志收集、端口转发，Runner 可水平扩展（多实例部署）。③多运行时支持——支持多种容器运行时（containerd/CRI-O），支持 GPU 加速（NVIDIA GPU 直通），支持特权容器和设备挂载，适合需要特殊硬件的开发场景。与 Docker 的通用容器运行时（containerd + Docker Engine）不同，daytona 的执行后端是 Docker/K8s+Runner+多运行时（focus on 开发环境专用容器执行，不是通用容器运行时）。溯源：[repo:file:apps/runner/](https://github.com/daytonaio/daytona/blob/01c502bb1f1ff8f2885d0cd490e043736083dca8/apps/runner/) (Runner 执行引擎), [repo:file:docker/](https://github.com/daytonaio/daytona/blob/01c502bb1f1ff8f2885d0cd490e043736083dca8/docker/) (Docker 配置)

## arch-session：开发环境会话 + SSH 会话 + IDE 连接会话
daytona 的会话管理是 **开发环境会话 + SSH 访问会话 + IDE 连接会话** 的三层会话。①开发环境会话——每个开发环境是一个独立的容器会话，包含文件系统（持久化卷）、运行进程、网络配置，会话状态通过容器状态管理（running/stopped/paused），支持会话暂停和恢复（容器 stop/start）。②SSH 访问会话（apps/ssh-gateway）——SSH 网关管理用户到开发环境的 SSH 会话，支持 SSH 密钥认证、会话审计、端口转发，SSH 会话可持久化（tmux/screen 支持），支持多用户并发 SSH 访问同一环境。③IDE 连接会话——支持 VS Code Server/JetBrains Gateway 等 IDE 远程连接，IDE 会话通过 WebSocket/HTTP 隧道传输，支持代码编辑、终端、调试器的远程访问，IDE 会话与开发环境生命周期绑定。与 LangGraph 的 Checkpoint 持久化（独立包 sqlite/postgres，时间旅行+中断恢复）不同，daytona 的会话是开发环境会话+SSH 会话+IDE 连接会话（focus on 开发环境访问和远程开发，不是通用 Agent 状态会话）。溯源：[repo:file:apps/ssh-gateway/](https://github.com/daytonaio/daytona/blob/01c502bb1f1ff8f2885d0cd490e043736083dca8/apps/ssh-gateway/) (SSH 网关), [repo:file:apps/runner/](https://github.com/daytonaio/daytona/blob/01c502bb1f1ff8f2885d0cd490e043736083dca8/apps/runner/) (开发环境管理)

## arch-checkpoint：环境快照 + 容器镜像版本 + 配置版本化
daytona 的检查点是 **环境快照 + 容器镜像版本 + 配置版本化** 的三层检查点。①环境快照（apps/snapshot-manager）——Snapshot Manager 管理开发环境的快照创建和恢复，支持文件系统快照（基于容器卷快照）、运行状态快照（进程+内存），快照可用于环境备份、版本回滚、环境复制。②容器镜像版本——开发环境基于容器镜像创建，镜像版本通过 tag 管理（devcontainer/devfile 定义基础镜像），支持镜像版本回滚和多版本并存，镜像构建可自动化（CI/CD 集成）。③配置版本化——开发环境配置（devcontainer.json/devfile.yaml）支持版本控制（Git 仓库管理），配置变更可追溯和回滚，支持配置模板和继承。与 LangGraph 的 Checkpoint 持久化（执行状态检查点，支持时间旅行和中断恢复）不同，daytona 的检查点是环境快照+镜像版本+配置版本化（focus on 开发环境状态和配置的版本管理，不是 Agent 执行状态检查点）。溯源：[repo:file:apps/snapshot-manager/](https://github.com/daytonaio/daytona/blob/01c502bb1f1ff8f2885d0cd490e043736083dca8/apps/snapshot-manager/) (快照管理), [repo:file:.devcontainer/](https://github.com/daytonaio/daytona/blob/01c502bb1f1ff8f2885d0cd490e043736083dca8/.devcontainer/) (devcontainer 配置)

## arch-fault-tolerance：Runner 故障转移 + API 高可用 + Proxy 负载均衡
daytona 的容错是 **Runner 故障转移 + API 高可用 + Proxy 负载均衡** 的三层容错。①Runner 故障转移——多 Runner 实例部署，API 服务器根据 Runner 健康状态和资源可用性调度环境创建，Runner 节点故障时环境自动迁移到健康节点（基于 Kubernetes 容器调度），支持节点自动发现和心跳检测（apps/daemon 守护进程）。②API 高可用——API 服务器支持多实例部署（无状态设计，状态存储在数据库），负载均衡器分发请求，支持滚动升级和零停机部署，API 限流和熔断防止过载。③Proxy 负载均衡——反向代理支持多实例部署，负载均衡分发 WebSocket/HTTP 请求，支持健康检查和故障节点自动剔除，支持连接重试和超时。与 Kubernetes 的容器编排（Scheduler+Controller+etcd，自动故障转移）不同，daytona 的容错是 Runner 故障转移+API 高可用+Proxy 负载均衡（focus on 开发环境平台的服务高可用，不是通用容器编排容错）。溯源：[repo:file:apps/api/](https://github.com/daytonaio/daytona/blob/01c502bb1f1ff8f2885d0cd490e043736083dca8/apps/api/) (API 服务器), [repo:file:apps/daemon/](https://github.com/daytonaio/daytona/blob/01c502bb1f1ff8f2885d0cd490e043736083dca8/apps/daemon/) (守护进程)

## arch-observability：OpenTelemetry 收集器 + 日志/指标/追踪 + 审计
daytona 的可观测性是 **OpenTelemetry 收集器 + 日志/指标/追踪三支柱 + 审计日志** 的四层可观测性。①OpenTelemetry 收集器（apps/otel-collector）——基于 OpenTelemetry 的可观测性数据收集器，统一收集指标、日志、追踪数据，支持多种导出器（Prometheus/Jaeger/Zipkin/Elasticsearch），支持数据过滤和采样。②三支柱——指标（环境资源使用率/API 延迟/错误率）、日志（环境运行日志/API 访问日志/审计日志）、追踪（请求链路追踪/环境创建耗时/操作耗时），支持 Dashboard 可视化（apps/dashboard Web 仪表板）。③审计日志——所有 API 操作和 SSH 访问记录审计日志（用户/时间/操作/目标环境/结果），支持合规审计和安全分析，审计日志不可篡改（追加写入）。与 LangSmith 的全链路追踪（LLM 调用/工具调用/状态变化可视化）不同，daytona 的可观测性是 OpenTelemetry+三支柱+审计（focus on 开发环境平台的运维可观测性，不是 LLM 应用追踪）。溯源：[repo:file:apps/otel-collector/](https://github.com/daytonaio/daytona/blob/01c502bb1f1ff8f2885d0cd490e043736083dca8/apps/otel-collector/) (OpenTelemetry 收集器), [repo:file:apps/dashboard/](https://github.com/daytonaio/daytona/blob/01c502bb1f1ff8f2885d0cd490e043736083dca8/apps/dashboard/) (Web 仪表板)

# 其他架构域简评
- arch-context：开发环境配置即代码（devcontainer/devfile），环境状态通过配置文件管理，无独立上下文管理
- arch-memory：无独立记忆系统，开发环境状态通过容器镜像和持久化卷存储
- arch-rag：无独立 RAG 模块
- arch-llm-abstraction：无 LLM 抽象（非 LLM 应用框架，是开发环境平台）
- arch-evals：apps/daytona-e2e 端到端测试，无独立评估框架
- arch-observability：apps/otel-collector OpenTelemetry 收集器，支持指标/日志/追踪
- arch-streaming：API 支持流式响应（环境日志流式输出），SSH 支持交互式流
- arch-frontend：apps/dashboard Web 仪表板（React/TypeScript），可视化管理开发环境
- arch-typing：Go 强类型（后端服务）+ TypeScript 强类型（前端+SDK）+ Pydantic（Python SDK）
- arch-distribution：多语言包分发（Go module/PyPI/npm/Maven/RubyGems），Docker 镜像分发
- arch-exec-backend：Docker/Kubernetes 容器后端，支持本地和云端部署
- arch-checkpoint：apps/snapshot-manager 快照管理，支持环境快照和恢复
- arch-plugins：IDE 插件（opencode-plugin/pi-extension），支持扩展
- arch-fault-tolerance：Runner 故障转移+API 高可用+Proxy 负载均衡，支持自动恢复

# claim 台账

| claim | 溯源锚点（repo:file:line） | 置信度 |
|---|---|---|
| apps/ 12 个服务（api/cli/daemon/dashboard/daytona-e2e/docs/otel-collector/proxy/runner/snapshot-manager/ssh-gateway） | [repo:file:apps/](https://github.com/daytonaio/daytona/blob/01c502bb1f1ff8f2885d0cd490e043736083dca8/apps/) (12 目录实测) | EXTRACTED |
| libs/ 27 个库（5 语言 SDK+5 语言 API 客户端+computer-use+opencode-plugin+pi-extension 等） | [repo:file:libs/](https://github.com/daytonaio/daytona/blob/01c502bb1f1ff8f2885d0cd490e043736083dca8/libs/) (27 目录实测) | EXTRACTED |
| main 分支已归档（2026-06 迁移到私有代码库） | [repo:file:README.md:1](https://github.com/daytonaio/daytona/blob/01c502bb1f1ff8f2885d0cd490e043736083dca8/README.md#L1) (README 归档声明实测) | EXTRACTED |
| 本卡基于 v0.190.0 tag（commit 01c502bb） | git tag v0.190.0 + git rev-parse HEAD 实测 | EXTRACTED |
| 5 种语言 SDK（go/java/python/ruby/typescript） | [repo:file:libs/](https://github.com/daytonaio/daytona/blob/01c502bb1f1ff8f2885d0cd490e043736083dca8/libs/) (sdk-go/sdk-java/sdk-python/sdk-ruby/sdk-typescript 实测) | EXTRACTED |
| 5 种语言 API 客户端 | [repo:file:libs/](https://github.com/daytonaio/daytona/blob/01c502bb1f1ff8f2885d0cd490e043736083dca8/libs/) (api-client-go/java/python/python-async/ruby 实测) | EXTRACTED |
| Runner 核心运行器（apps/runner） | [repo:file:apps/runner/](https://github.com/daytonaio/daytona/blob/01c502bb1f1ff8f2885d0cd490e043736083dca8/apps/runner/) (实测) | EXTRACTED |
| SSH 网关（apps/ssh-gateway） | [repo:file:apps/ssh-gateway/](https://github.com/daytonaio/daytona/blob/01c502bb1f1ff8f2885d0cd490e043736083dca8/apps/ssh-gateway/) (实测) | EXTRACTED |
| Computer Use 库（libs/computer-use） | [repo:file:libs/computer-use/](https://github.com/daytonaio/daytona/blob/01c502bb1f1ff8f2885d0cd490e043736083dca8/libs/computer-use/) (实测) | EXTRACTED |
| IDE 插件（opencode-plugin + pi-extension） | [repo:file:libs/opencode-plugin/](https://github.com/daytonaio/daytona/blob/01c502bb1f1ff8f2885d0cd490e043736083dca8/libs/opencode-plugin/), [repo:file:libs/pi-extension/](https://github.com/daytonaio/daytona/blob/01c502bb1f1ff8f2885d0cd490e043736083dca8/libs/pi-extension/) (实测) | EXTRACTED |
| 71,755★（C04 空域首例） | GitHub API 实测 | EXTRACTED |
| Snapshot Manager（apps/snapshot-manager） | [repo:file:apps/snapshot-manager/](https://github.com/daytonaio/daytona/blob/01c502bb1f1ff8f2885d0cd490e043736083dca8/apps/snapshot-manager/) (实测) | EXTRACTED |

# 矛盾记录（Disputed）
无（C04 首张，无同类别 F 卡对比。与 Docker/Kubernetes 互为参照——Docker 是通用容器运行时，Kubernetes 是通用容器编排，daytona 是开发环境专用沙箱平台（预配置+IDE 连接+环境即代码），定位不同但底层依赖容器技术。与 hermes-agent 的七沙箱后端（含 Daytona）互为参照——hermes-agent 将 Daytona 作为沙箱后端之一，daytona 是沙箱提供方）。

# 对照验证
- 对照源：https://deepwiki.com/daytonaio/daytona（Tier2：DeepWiki 自动生成的代码文档）
- 访问日期：2026-09-09
- 编排者复验：DeepWiki 已访问（Last indexed 2026-06-05, commit 46f29d5b——**恰为 main 归档前完整版本**）——三平面架构（Interface/Control/Compute）/ 沙箱隔离 / 5 语言 SDK / Runner 系统 / apps+libs monorepo 结构与卡内结论一致；与卡内 v0.190.0 tag（01c502bb）版本差异如实记录。**编排者复验裁决：一致（2026-09-09）**

# 溯源
- repo:apps/runner/（Runner 核心运行器，开发环境容器生命周期管理）
- repo:apps/api/（API 服务器，中央编排器，REST/gRPC 接口）
- repo:apps/proxy/（反向代理，开发环境端口转发和域名路由）
- repo:apps/ssh-gateway/（SSH 访问网关，SSH 直接连接开发环境）
- repo:apps/cli/（命令行工具，开发环境管理）
- repo:apps/dashboard/（Web 仪表板，可视化管理）
- repo:libs/（27 个库，5 语言 SDK+5 语言 API 客户端+computer-use+IDE 插件）
- repo:README.md（归档声明，2026-06 迁移到私有代码库）

# 待补
- [ ] DeepWiki 对照验证（需指定 v0.190.0 tag，main 分支已归档空壳）
- [ ] Runner 容器执行的具体实现（Docker/Kubernetes 后端代码，需精读 apps/runner/）
- [ ] devcontainer/devfile 配置规范的支持程度（当前仅概述，需精读配置解析代码）
- [ ] API 服务器的认证授权实现（API Key/OAuth2/JWT/RBAC，需精读 apps/api/）
- [ ] Proxy 路由机制（子域名/路径路由+HTTPS+WebSocket，需精读 apps/proxy/）
- [ ] SSH 网关的认证和审计实现（需精读 apps/ssh-gateway/）
- [ ] Computer Use 库的具体能力（鼠标/键盘/截图，需精读 libs/computer-use/）
- [ ] 与 GitHub Codespaces/Gitpod 的功能对比（当前仅文字描述，需结构化对比）
- [ ] 归档后的替代方案（私有代码库版本的功能差异和迁移路径，需调研）
- [ ] 本地部署验证（需 Docker/Kubernetes 环境，验证 daytona 可用）

## 更新记录

- 2026-09-11 | LB-R2-a 30天复扫 | star=71737（71755→71737） | HEAD=ec4c21b2d597091ac09ecc278f3bcc172575a987（pinned=01c502bb1f1ff8f2885d0cd490e043736083dca8，commit 漂移 01c502bb1f→ec4c21b2d5）| L1 微漂移标注（CB-11：仅标注，未重蒸馏；3 天窗口 star 漂移<2%，无 L2/L3 信号）| pushed_at=2026-07-24 archived=false | 锚点 repo_base_url/repo_local_path 不动
- 2026-09-14 | LB-R4 30天复扫 | star=71718（71737→71718） | HEAD=ec4c21b2d597091ac09ecc278f3bcc172575a987（pinned=01c502bb1f1ff8f2885d0cd490e043736083dca8，commit 漂移 01c502bb1f→ec4c21b2d5） | L3 显著漂移（diffstat=5768 files changed, +8/-1244092；结构变化大，重蒸馏议题交编排者复核日裁决）| pushed_at=2026-07-24 archived=false

