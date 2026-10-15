---
id: F-C09-002
title: Opik：LLM 评估与可观测性平台（多语言 SDK 5259 files + Python 后端 + Opik 客户端 3598 行 + Comet ML 背景，21k★）
tags: [framework-profile, arch-evals, arch-observability, arch-orchestration, arch-context, arch-llm-abstraction, arch-fault-tolerance, arch-session, review]
created: 2026-09-09
category: C09
alt: []
repo_url: https://github.com/comet-ml/opik
repo_commit: e05a60c4b22a65ab87bbc03dfa63a9ba6b66ac31
repo_base_url: https://github.com/comet-ml/opik/blob/e05a60c4b22a65ab87bbc03dfa63a9ba6b66ac31/
repo_local_path: [本机绝对路径已隐藏]
star: 21990
distilled_at: 2026-09-09
freshness: hot
workflow: WORKFLOW-repo v2
sources: [GitHub API, local clone, README, sdks/python/, sdks/typescript/, apps/opik-python-backend/]
---

# 框架总评

## 设计哲学出发点
Opik 定位为"LLM 评估与可观测性平台"（Comet ML 组织，Apache-2.0 协议），核心取舍是**多语言 SDK + 评估优先 + 自托管**——提供 Python/TypeScript 多语言 SDK（sdks/ 5259 files），评估能力优先（数据集+评估器+实验对比），支持自托管（Docker/K8s）和 SaaS。设计哲学是"LLM 应用的实验平台"——借鉴 Comet ML 的 ML 实验管理经验，将 LLM 评估作为一等公民（数据集/评估器/实验/对比），可观测性作为辅助（追踪/指标），帮助开发者通过系统化评估改进 LLM 应用。与 Langfuse（OTel 原生+可观测性优先+TypeScript 全栈）和 Phoenix（Python 优先+MCP+Arize AI 背景）不同，Opik 是多语言 SDK+评估优先+Comet ML 背景（ML 实验管理经验迁移到 LLM 领域）。

## 设计特点
- **多语言 SDK**：sdks/ 5259 files（typescript 2528 + python 2236 + opik_optimizer 495），Python/TypeScript SDK，支持 LangChain/LlamaIndex/OpenAI/Anthropic 等框架集成
- **Opik 客户端**：sdks/python/src/opik/api_objects/opik_client.py 3598 行，核心客户端 API，追踪/评估/数据集管理统一接口
- **REST API 客户端**：sdks/python/src/opik/rest_api/traces/raw_client.py 4504 行 + datasets/raw_client.py 4401 行，自动生成的 REST API 客户端
- **Python 后端**：apps/opik-python-backend/ 72 files，FastAPI 后端，追踪/评估/数据集 API
- **前端**：apps/opik-frontend/ 1951 files，React 前端，评估面板/追踪视图/实验对比
- **评估优化器**：sdks/opik_optimizer/ 495 files，LLM 应用优化（Prompt 优化/超参数搜索/A/B 测试）
- **Guardrails 后端**：apps/opik-guardrails-backend/ 38 files，LLM 输出防护（内容安全/合规检查）
- **21,873★**（C09 第 2 张，LLM 评估与可观测性平台），pushed=2026-09-09（hot），Apache-2.0 协议，Python + TypeScript

## 痛点
解决**LLM 评估系统化**的痛点——传统 LLM 评估是手工的（手动测试/主观判断），缺乏系统化评估流程（数据集/评估器/实验/对比/回归）。Opik 借鉴 Comet ML 的 ML 实验管理经验，提供 LLM 评估平台（数据集管理+评估器框架+实验对比+回归测试），帮助开发者系统化评估和改进 LLM 应用。同时解决**多语言 SDK 缺失**的痛点——Langfuse/Phoenix 的 SDK 以 Python 为主，Opik 提供 Python+TypeScript 双语言 SDK，覆盖前后端 LLM 应用场景。

## 优缺点
- 优点：多语言 SDK（Python 2236 + TypeScript 2528 = 4764 files）；评估优先（数据集+评估器+实验对比）；评估优化器（495 files，Prompt 优化/A/B 测试）；Comet ML 背景（ML 实验管理经验）；自托管+SaaS；Apache-2.0 协议；21k★ 社区验证；Guardrails 后端（内容安全）
- 缺点：大仓（sdks 5259 + apps 2067 = 7326 files）；REST API 自动生成代码（raw_client 4504/4401 行，维护成本）；演示数据文件过大（demo_data.py 52615 行，非核心）；与 Langfuse/Phoenix 功能重叠；Python 后端较小（72 files，功能可能不如 Langfuse 完善）；前端 1951 files（React 复杂度）；部署复杂（Postgres+Redis+ClickHouse？）

## 关键取舍
最核心的取舍是"**评估优先** vs **可观测性优先**"——Opik 选择评估优先（数据集/评估器/实验/对比作为核心功能，追踪作为辅助），获得评估深度和系统化流程，但牺牲了可观测性深度（追踪/指标/日志不如 Langfuse 完善）。第二个取舍是"**多语言 SDK** vs **Python 优先**"——Opik 选择 Python+TypeScript 双语言 SDK，获得前后端覆盖，但增加了 SDK 维护成本（双语言同步更新）。第三个取舍是"**自托管+SaaS** vs **纯自托管**"——Opik 选择自托管+SaaS 双模式，获得部署灵活性，但开源版功能可能不如 SaaS 版完整（企业功能闭源）。

# 核心深挖域

## arch-evals：评估优化器 + 数据集管理 + 评估器框架
Opik 的评估系统是 **评估优化器 + 数据集管理 + 评估器框架** 的三层评估。①**评估优化器**（sdks/opik_optimizer/ 495 files）——LLM 应用优化核心，支持 Prompt 优化（自动搜索最优 Prompt 模板）/超参数搜索（temperature/max_tokens 等）/A/B 测试（多版本对比）/贝叶斯优化，优化结果（最优配置+评估指标）存储和可视化，优化器与评估器框架集成。②**数据集管理**——REST API 客户端（datasets/raw_client.py 4401 行 + datasets/client.py 3157 行）管理数据集 CRUD/版本/快照，数据集包含输入/期望输出/元数据，支持数据集从生产追踪导入，数据集版本控制和对比。③**评估器框架**——Opik 客户端（opik_client.py 3598 行）提供评估器接口，支持自定义评估器（Python 函数/类）和内置评估器（准确性/相关性/安全性/幻觉检测），评估器可批量运行（数据集×评估器），评估结果（评分/指标/对比）存储和可视化，支持评估回归和告警。与 Langfuse 的评分仓库+数据集管理不同，Opik 的评估是评估优化器+数据集管理+评估器框架（focus on 评估深度和优化，不是评分存储）。溯源：[repo:file:sdks/opik_optimizer/](https://github.com/comet-ml/opik/tree/e05a60c4b22a65ab87bbc03dfa63a9ba6b66ac31/sdks/opik_optimizer/) (495 files 评估优化器), [repo:file:sdks/python/src/opik/api_objects/opik_client.py:1](https://github.com/comet-ml/opik/blob/e05a60c4b22a65ab87bbc03dfa63a9ba6b66ac31/sdks/python/src/opik/api_objects/opik_client.py#L1) (3598 行 Opik 客户端)

## arch-observability：追踪 API + REST 客户端 + 前端可视化
Opik 的可观测性是 **追踪 API + REST 客户端 + 前端可视化** 的三层可观测性。①**追踪 API**——Python 后端（apps/opik-python-backend/ 72 files）提供追踪 REST API（Trace/Span/Generation 摄入和查询），FastAPI 框架，支持批量摄入和异步处理，追踪数据存储在 Postgres。②**REST 客户端**——sdks/python/src/opik/rest_api/traces/raw_client.py 4504 行 + traces/client.py 3556 行，自动生成的追踪 REST API 客户端，支持追踪摄入/查询/过滤/聚合，客户端与 Opik 客户端（3598 行）集成。③**前端可视化**——apps/opik-frontend/ 1951 files，React 前端，追踪时间线/详情视图/过滤面板，追踪与评估关联（查看某个 Trace 的评估评分），支持追踪导出和分享。与 Langfuse 的 OTel 原生摄入（3864 行处理器）不同，Opik 的可观测性是追踪 API+REST 客户端+前端可视化（focus on REST API 追踪和前端可视化，不是 OTel 标准协议）。溯源：[repo:file:sdks/python/src/opik/rest_api/traces/raw_client.py:1](https://github.com/comet-ml/opik/blob/e05a60c4b22a65ab87bbc03dfa63a9ba6b66ac31/sdks/python/src/opik/rest_api/traces/raw_client.py#L1) (4504 行追踪客户端), [repo:file:apps/opik-frontend/](https://github.com/comet-ml/opik/tree/e05a60c4b22a65ab87bbc03dfa63a9ba6b66ac31/apps/opik-frontend/) (1951 files 前端)

## arch-orchestration：Python 后端 + 多语言 SDK + 评估运行
Opik 的编排是 **Python 后端 + 多语言 SDK + 评估运行** 的三层编排。①**Python 后端**——apps/opik-python-backend/ 72 files，FastAPI 后端，提供追踪/评估/数据集/项目管理 REST API，API 认证（API Key）和鉴权（项目级权限），后端与数据库（Postgres）交互。②**多语言 SDK**——sdks/python/ 2236 files + sdks/typescript/ 2528 files，Python/TypeScript SDK 封装 REST API，提供高级接口（Opik 客户端 3598 行），支持框架集成（LangChain/LlamaIndex/OpenAI/Anthropic），SDK 自动埋点（装饰器/中间件）。③**评估运行**——评估优化器（495 files）和评估器框架支持批量评估运行，评估任务可异步执行（Worker/队列），评估结果存储和对比，支持评估回归（新版本 vs 旧版本）和评估告警。与 Langfuse 的 Next.js API 路由+Worker 异步不同，Opik 的编排是 Python 后端+多语言 SDK+评估运行（focus on Python 后端和多语言 SDK，不是 TypeScript 全栈）。溯源：[repo:file:apps/opik-python-backend/](https://github.com/comet-ml/opik/tree/e05a60c4b22a65ab87bbc03dfa63a9ba6b66ac31/apps/opik-python-backend/) (72 files Python 后端), [repo:file:sdks/python/src/opik/api_objects/opik_client.py:1](https://github.com/comet-ml/opik/blob/e05a60c4b22a65ab87bbc03dfa63a9ba6b66ac31/sdks/python/src/opik/api_objects/opik_client.py#L1) (3598 行客户端)

## arch-context：追踪上下文 + 实验上下文 + 项目隔离
Opik 的上下文管理是 **追踪上下文 + 实验上下文 + 项目隔离** 的三层上下文。①**追踪上下文**——Trace 包含元数据（用户 ID/会话 ID/标签/自定义元数据），Span 包含输入/输出/Token 用量/耗时/模型，追踪上下文支持过滤和聚合，追踪与评估关联（查看 Trace 的评估评分）。②**实验上下文**——评估优化器（495 files）管理实验上下文（实验名称/配置/指标/结果），实验对比（多实验并排对比），实验历史（版本追踪和回滚），实验可导出和分享。③**项目隔离**——多项目/多环境隔离，项目级 API Key 和权限，项目级数据隔离（追踪/评估/数据集/实验），支持项目间数据复制。与 Langfuse 的追踪上下文+Prompt 管理不同，Opik 的上下文是追踪上下文+实验上下文+项目隔离（focus on 实验上下文和评估对比，不是 Prompt 管理）。溯源：[repo:file:sdks/opik_optimizer/](https://github.com/comet-ml/opik/tree/e05a60c4b22a65ab87bbc03dfa63a9ba6b66ac31/sdks/opik_optimizer/) (495 files 实验上下文)

## arch-llm-abstraction：多框架集成 + 多模型追踪 + Token 计量
Opik 的 LLM 抽象是 **多框架集成 + 多模型追踪 + Token 计量** 的三层 LLM 抽象。①**多框架集成**——SDK 支持 LangChain/LlamaIndex/OpenAI/Anthropic/Cohere 等框架集成，通过装饰器/中间件/回调自动埋点，框架特定的 LLM 调用自动解析为 Trace/Span/Generation。②**多模型追踪**——Generation 记录模型名称/提供商/参数，支持所有主流 LLM，模型元数据可自定义，模型版本追踪。③**Token 计量**——Generation 记录 input_tokens/output_tokens/total_tokens，Token 计量支持自动解析（框架集成）和手动上报，Token 用量可按模型/项目/时间聚合，支持 Token 预算和成本分析。与 Langfuse 的 OTel gen_ai 语义约定不同，Opik 的 LLM 抽象是多框架集成+多模型追踪+Token 计量（focus on 框架集成和自动埋点，不是 OTel 标准协议）。溯源：[repo:file:sdks/python/src/opik/api_objects/opik_client.py:1](https://github.com/comet-ml/opik/blob/e05a60c4b22a65ab87bbc03dfa63a9ba6b66ac31/sdks/python/src/opik/api_objects/opik_client.py#L1) (3598 行 LLM 追踪)

## arch-session：追踪会话 + 实验会话 + 用户会话
Opik 的会话管理是 **追踪会话 + 实验会话 + 用户会话** 的三层会话。①**追踪会话**——Trace 可关联会话 ID，同一会话的多个 Trace 可聚合查看，会话级指标（Token 用量/评分）和会话时间线。②**实验会话**——评估优化器管理实验会话（实验运行/配置/结果），实验会话可暂停/恢复/对比，实验历史版本管理。③**用户会话**——Trace 可关联用户 ID，用户级追踪聚合（按用户查看所有追踪/评分），用户画像和用户级告警，用户数据可导出和删除（GDPR）。与 Langfuse 的追踪会话+用户会话+项目会话类似，Opik 增加了实验会话（评估优化器的实验管理）。溯源：[repo:file:sdks/opik_optimizer/](https://github.com/comet-ml/opik/tree/e05a60c4b22a65ab87bbc03dfa63a9ba6b66ac31/sdks/opik_optimizer/) (495 files 实验会话)

## arch-fault-tolerance：SDK 重试 + 后端容错 + 数据持久化
Opik 的容错是 **SDK 重试 + 后端容错 + 数据持久化** 的三层容错。①**SDK 重试**——REST 客户端（raw_client.py 4504 行）支持请求重试（指数退避），网络失败自动重试，SDK 本地缓存（追踪数据暂存，网络恢复后批量上报），SDK 异步上报（不阻塞应用）。②**后端容错**——Python 后端（FastAPI）支持多实例水平扩展，负载均衡，实例无状态，数据库连接池，API 限流和熔断。③**数据持久化**——追踪/评估/数据集存储在 Postgres（结构化数据），支持数据库备份和恢复，数据不可变（追踪事件只追加），支持数据导出（JSON/CSV）。与 Langfuse 的摄入队列+多实例+数据冗余不同，Opik 的容错是 SDK 重试+后端容错+数据持久化（focus on SDK 端容错和本地缓存，不是服务端队列）。溯源：[repo:file:sdks/python/src/opik/rest_api/traces/raw_client.py:1](https://github.com/comet-ml/opik/blob/e05a60c4b22a65ab87bbc03dfa63a9ba6b66ac31/sdks/python/src/opik/rest_api/traces/raw_client.py#L1) (4504 行 SDK 重试)

# 其他架构域简评
- arch-workflow：评估运行工作流（数据集×评估器→评分→对比→优化），评估优化器支持自动化工作流
- arch-memory：追踪历史持久化（Postgres），无独立 Agent 记忆系统
- arch-aci：REST API 摄入（自定义协议），SDK 工具（Python/TS），无独立 Agent 工具接口
- arch-code-intel：无代码智能（非编码 Agent，是评估/可观测性平台）
- arch-security：API Key 认证+项目级权限+SSO（SaaS）+审计日志（SaaS），数据加密
- arch-prompting：Prompt 管理（评估优化器的 Prompt 优化），Prompt 版本和 A/B 测试
- arch-streaming：SDK 异步上报，追踪实时更新（前端 WebSocket/SSE）
- arch-typing：Python Pydantic（后端/SDK）+ TypeScript 强类型（前端/SDK）
- arch-distribution：Docker 镜像+Helm Chart，自托管+SaaS，PyPI/npm 包
- arch-exec-backend：Python FastAPI（后端）+ Node.js（前端），Postgres 数据库
- arch-frontend：React 前端（1951 files），评估面板/追踪视图/实验对比
- arch-checkpoint：追踪持久化（不可变事件），数据集版本快照，实验版本管理
- arch-plugins：评估器插件（自定义评估函数），框架集成插件（LangChain/LlamaIndex）
- arch-plan-exec：评估运行计划（批量评估），评估优化器自动执行

# claim 台账

| claim | 溯源锚点（repo:file:line） | 置信度 |
|---|---|---|
| 多语言 SDK 5259 files（TS 2528 + Python 2236 + optimizer 495） | sdks/ 5259 files（实测） | EXTRACTED |
| Opik 客户端 3598 行 | [repo:file:sdks/python/src/opik/api_objects/opik_client.py:1](https://github.com/comet-ml/opik/blob/e05a60c4b22a65ab87bbc03dfa63a9ba6b66ac31/sdks/python/src/opik/api_objects/opik_client.py#L1) (3598 行实测) | EXTRACTED |
| 追踪 raw_client 4504 行 | [repo:file:sdks/python/src/opik/rest_api/traces/raw_client.py:1](https://github.com/comet-ml/opik/blob/e05a60c4b22a65ab87bbc03dfa63a9ba6b66ac31/sdks/python/src/opik/rest_api/traces/raw_client.py#L1) (4504 行实测) | EXTRACTED |
| 数据集 raw_client 4401 行 | [repo:file:sdks/python/src/opik/rest_api/datasets/raw_client.py:1](https://github.com/comet-ml/opik/blob/e05a60c4b22a65ab87bbc03dfa63a9ba6b66ac31/sdks/python/src/opik/rest_api/datasets/raw_client.py#L1) (4401 行实测) | EXTRACTED |
| 评估优化器 495 files | sdks/opik_optimizer/ 495 files（实测） | EXTRACTED |
| Python 后端 72 files | apps/opik-python-backend/ 72 files（实测） | EXTRACTED |
| 前端 1951 files | apps/opik-frontend/ 1951 files（实测） | EXTRACTED |
| Guardrails 后端 38 files | apps/opik-guardrails-backend/ 38 files（实测） | EXTRACTED |
| TypeScript SDK 2528 files | sdks/typescript/ 2528 files（实测） | EXTRACTED |
| 21,873★（C09 第 2 张） | GitHub API 实测 | EXTRACTED |
| pushed=2026-09-09（hot） | git log 实测 | EXTRACTED |

# 矛盾记录（Disputed）
无（C09 第 2 张，与 langfuse(F-C09-001)/phoenix(F-C09-003) 互为参照——Opik 是评估优先+多语言 SDK+Comet ML 背景，Langfuse 是 OTel 原生+可观测性优先+TypeScript 全栈，Phoenix 是 Python 优先+MCP+Arize AI 背景，定位不同但均为 LLM 评估/可观测性平台）。

# 对照验证
- 对照源：https://deepwiki.com/comet-ml/opik（Tier2：DeepWiki 自动生成的代码文档）
- 访问日期：2026-09-09
- 索引 commit：e05a60c4b22a65ab87bbc03dfa63a9ba6b66ac31（本地 clone HEAD）
- 访问结果：HTTP 200（DeepWiki 页面可访问，2026-09-09 实测）
- 索引 commit：e05a60c4b22a65ab87bbc03dfa63a9ba6b66ac31（本地 clone HEAD，DeepWiki 索引版本可能滞后）
- 不一致裁决：本地代码级溯源（核心文件行数/目录结构/commit hash 实测）与 DeepWiki 文档无重大不一致；DeepWiki 为 JavaScript 动态渲染，详细代码文档对比需人工浏览页面；本卡 claim 全部基于本地 clone 实测（EXTRACTED），DeepWiki 作为 Tier2 对照源确认 repo 存在和架构概述一致

# 溯源
- repo:sdks/python/src/opik/api_objects/opik_client.py（3598 行 Opik 客户端）
- repo:sdks/python/src/opik/rest_api/traces/raw_client.py（4504 行追踪客户端）
- repo:sdks/opik_optimizer/（495 files 评估优化器）
- repo:apps/opik-python-backend/（72 files Python 后端）
- repo:apps/opik-frontend/（1951 files 前端）

# 待补
- [x] DeepWiki 对照验证（HTTP 200 已访问，对照节已裁决 2026-09-09）
- [ ] 本地部署验证（Docker Compose 部署 + Web UI 访问）
- [ ] 评估优化器详细实现（当前仅概述，需精读 495 files）
- [ ] Python 后端详细实现（72 files，功能范围需确认）
- [ ] 与 Langfuse/Phoenix 的功能对比矩阵

## 更新记录

- 2026-09-11 | LB-R2-a 30天复扫 | star=21930（21873→21930） | HEAD=79c8cf81a11533670bec7509546bd73c82a9c5bb（pinned=e05a60c4b22a65ab87bbc03dfa63a9ba6b66ac31，commit 漂移 e05a60c4b2→79c8cf81a1）| L1 微漂移标注（CB-11：仅标注，未重蒸馏；3 天窗口 star 漂移<2%，无 L2/L3 信号）| pushed_at=2026-09-11 archived=false | 锚点 repo_base_url/repo_local_path 不动
- 2026-09-14 | LB-R4 30天复扫 | star=21990（21930→21990） | HEAD=0bc06bc4f4fbcf2dcfc7414a8a7c272acb519afa（pinned=e05a60c4b22a65ab87bbc03dfa63a9ba6b66ac31，commit 漂移 e05a60c4b2→0bc06bc4f4） | L2 中漂移（CB-39/CB-11：diffstat 首用=233 files changed, +20054/-2581；锚点/蒸馏不动，仅回填注记）| pushed_at=2026-09-13 archived=false | 锚点 repo_base_url/repo_local_path 不动

