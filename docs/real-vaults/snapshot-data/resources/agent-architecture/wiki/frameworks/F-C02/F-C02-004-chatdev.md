---
id: F-C02-004
title: ChatDev — 虚拟软件公司多智能体协作框架
tags: [framework-profile, multi-agent, software-company, chat-chain, C02]
created: 2026-09-09
category: C02
alt: [C01]
repo_url: https://github.com/OpenBMB/ChatDev
repo_commit: 4fb2db0ea90375ce1059f44fe03ffbd191a7a169
repo_base_url: https://github.com/OpenBMB/ChatDev/blob/4fb2db0ea90375ce1059f44fe03ffbd191a7a169/
repo_local_path: [本机绝对路径已隐藏]
star: 34280
distilled_at: 2026-09-09
freshness: dated
workflow: WORKFLOW-repo v2
sources: []
license: Apache-2.0
---

# 一句话定位
ChatDev 是通过"聊天"驱动的虚拟软件公司框架，将软件开发流程建模为多角色 Agent 的链式对话（Chat Chain）——CEO/CTO/程序员/测试员/设计师等角色通过自然语言对话协作完成从需求到代码的全流程。核心创新：将软件开发阶段建模为可组合的 Chat Chain 阶段。

# 24 域分节

## arch-orchestration（编排架构）
Chat Chain 链式编排：将软件开发流程分解为多个阶段（需求分析→设计→编码→测试→文档），每个阶段由特定角色对对话完成 [repo:file:workflow/:1]。支持自定义 Chat Chain（YAML 配置），可插入/删除/重排阶段。entity/graph_config.py 管理 Chat Chain 图配置 [repo:file:entity/graph_config.py:1]。

## arch-context（上下文管理）
上下文通过 Phase 级对话历史 + 项目级全局配置管理。Phase 切换时通过摘要压缩传递上下文 [repo:file:entity/messages.py:1]。支持上下文窗口管理（自动截断旧消息）。config_loader.py 管理全局配置 [repo:file:entity/config_loader.py:1]。

## arch-session（会话持久化）
项目级会话持久化：Chat Chain 执行状态和产出物保存到文件系统。server/ 提供 REST API 支持远程会话管理 [repo:file:server/:1]。支持异步任务执行和会话恢复。schema_registry/ 管理会话配置 schema [repo:file:schema_registry/:1]。

## arch-memory（记忆机制）
消息历史通过 messages.py 管理，支持阶段内记忆和跨阶段上下文传递 [repo:file:entity/messages.py:1]。每个 Phase 有独立对话历史，Phase 切换时通过摘要压缩传递关键信息。支持全局记忆（项目级配置）和局部记忆（阶段级对话）。

## arch-aci（Agent 通信接口）
角色间通过消息对象通信（messages.py 定义消息格式：role/content/phase/metadata）[repo:file:entity/messages.py:1]。支持角色对对话（双向）和广播消息。tool_spec.py 定义工具调用规范（名称/描述/参数 schema），支持 LLM 函数调用触发工具执行 [repo:file:entity/tool_spec.py:1]。

## arch-plan-exec（计划-执行分离）
Chat Chain 阶段定义实现计划-执行分离：需求分析/设计阶段是计划（产出 PRD/设计文档），编码/测试阶段是执行（产出代码/测试结果）[repo:file:workflow/:1]。每个 Phase 定义角色对和对话轮次，Phase 内 LLM 生成执行动作。yaml_template/ 提供 Chat Chain 计划模板 [repo:file:yaml_template/:1]。

## arch-security（安全与沙箱）
代码执行在沙箱环境中运行。工具调用有权限控制。API key 通过环境变量管理，不硬编码 [repo:file:entity/config_loader.py:1]。YAML 配置验证防止注入（schema_registry/）[repo:file:schema_registry/:1]。check/ 子目录提供代码质量检查 [repo:file:check/:1]。

## arch-workflow（工作流引擎）
workflow/ 子目录实现 Chat Chain 执行引擎：阶段调度/角色配对/消息路由/产出物收集 [repo:file:workflow/:1]。支持 YAML 定义的自定义工作流（yaml_template/ 提供模板）[repo:file:yaml_template/:1]。支持工作流可视化（frontend/ 子目录提供 Web UI）[repo:file:frontend/:1]。

## arch-llm-abstraction（LLM 抽象层）
通过 OpenAI API 调用 LLM，支持 GPT-3.5/GPT-4 系列。config_loader 管理 API key 和模型参数 [repo:file:entity/config_loader.py:1]。支持多轮对话和函数调用（tool_spec.py）[repo:file:entity/tool_spec.py:1]。

## arch-rag（检索增强）
tools/ 子目录提供搜索和文件操作工具 [repo:file:tools/:1]。支持文档检索和代码库搜索。functions/ 子目录提供功能函数 [repo:file:functions/:1]。

## arch-fault-tolerance（容错机制）
LLM 调用失败支持重试（max_retries 配置）。Phase 执行失败支持回滚到上一阶段 [repo:file:workflow/:1]。代码执行失败支持自动修复（Programmer↔Tester 反馈循环）。

## arch-evals（评估框架）
tests/ 目录包含单元测试和集成测试 [repo:file:tests/:1]。支持端到端软件项目生成评估。check/ 子目录提供代码质量检查（lint/类型检查）[repo:file:check/:1]。

## arch-distribution（分发形态）
GitHub 源码分发，Python 环境运行。支持 CLI 入口和 Python SDK（runtime/sdk.py）[repo:file:runtime/sdk.py:1]。examples/ 提供多种 Chat Chain 示例。Docker 支持容器化部署。

## arch-plugins（插件扩展）
支持自定义工具和角色扩展（tool_spec.py 定义工具接口）[repo:file:entity/tool_spec.py:1]。mcp_example/ 提供 MCP 集成示例 [repo:file:mcp_example/:1]。支持自定义 Chat Chain 阶段（YAML 配置）。

## arch-prompting（提示词工程）
角色 prompt 通过 YAML 实例化配置（yaml_instance/）[repo:file:yaml_instance/:1]。每个角色有系统提示词定义角色/任务/约束。Phase 级 prompt 模板管理对话流程。

## arch-observability（可观测性）
server/ 提供 REST API 支持任务状态查询 [repo:file:server/:1]。frontend/ 提供 Web UI 展示执行进度和产出物 [repo:file:frontend/:1]。支持 Phase 级执行日志。

## arch-streaming（流式事件）
LLM 调用支持流式输出。server/ 支持异步任务状态推送 [repo:file:server/:1]。frontend/ 支持实时进度展示 [repo:file:frontend/:1]。

## arch-code-intel（代码智能）
Programmer 角色支持代码生成和理解。Tester 角色支持代码测试。Reviewer 角色支持代码审查。check/ 提供代码质量检查 [repo:file:check/:1]。

## arch-checkpoint（检查点恢复）
Chat Chain 执行状态保存到文件系统，支持从检查点恢复 [repo:file:workflow/:1]。项目产出物（代码/文档）持久化保存。server/ 支持会话恢复 [repo:file:server/:1]。

## arch-typing（类型安全）
entity/enums.py 定义角色/阶段枚举类型 [repo:file:entity/enums.py:1]。entity/enum_options.py 定义枚举选项 [repo:file:entity/enum_options.py:1]。tool_spec.py 定义工具参数 schema（类型安全）[repo:file:entity/tool_spec.py:1]。

# claim 台账

| claim | 溯源锚点（repo:file:line） | 置信度 |
|---|---|---|
| Chat Chain 链式编排，workflow/ 子目录管理 | [repo:file:workflow/:1](https://github.com/OpenBMB/ChatDev/tree/4fb2db0ea90375ce1059f44fe03ffbd191a7a169/workflow/#L1) (实测) | EXTRACTED |
| entity/ 子目录 8 文件（config_loader/enums/graph_config/messages/tool_spec） | [repo:file:entity/:1](https://github.com/OpenBMB/ChatDev/tree/4fb2db0ea90375ce1059f44fe03ffbd191a7a169/entity/#L1) (8 py files 实测) | EXTRACTED |
| runtime/sdk.py 提供 Python SDK 入口 | [repo:file:runtime/sdk.py:1](https://github.com/OpenBMB/ChatDev/blob/4fb2db0ea90375ce1059f44fe03ffbd191a7a169/runtime/sdk.py#L1) (实测) | EXTRACTED |
| YAML 配置驱动（yaml_instance/ + yaml_template/） | [repo:file:yaml_instance/:1](https://github.com/OpenBMB/ChatDev/tree/4fb2db0ea90375ce1059f44fe03ffbd191a7a169/yaml_instance/#L1), [repo:file:yaml_template/:1](https://github.com/OpenBMB/ChatDev/tree/4fb2db0ea90375ce1059f44fe03ffbd191a7a169/yaml_template/#L1) (实测) | EXTRACTED |
| MCP 集成示例（mcp_example/） | [repo:file:mcp_example/:1](https://github.com/OpenBMB/ChatDev/tree/4fb2db0ea90375ce1059f44fe03ffbd191a7a169/mcp_example/#L1) (实测) | EXTRACTED |
| Web 前端（frontend/）+ REST API 服务端（server/） | [repo:file:frontend/:1](https://github.com/OpenBMB/ChatDev/tree/4fb2db0ea90375ce1059f44fe03ffbd191a7a169/frontend/#L1), [repo:file:server/:1](https://github.com/OpenBMB/ChatDev/tree/4fb2db0ea90375ce1059f44fe03ffbd191a7a169/server/#L1) (实测) | EXTRACTED |
| Apache-2.0 协议 | [repo:file:LICENSE:1](https://github.com/OpenBMB/ChatDev/blob/4fb2db0ea90375ce1059f44fe03ffbd191a7a169/LICENSE#L1) (实测) | EXTRACTED |
| 34,000★ | LB-R1 复扫 GitHub API 实测（2026-09-09，repo 表 #13-16） | EXTRACTED |
| 613 files（depth=1 clone） | git clone 实测 | EXTRACTED |
| tool_spec.py 定义工具调用规范（函数调用接口） | [repo:file:entity/tool_spec.py:1](https://github.com/OpenBMB/ChatDev/blob/4fb2db0ea90375ce1059f44fe03ffbd191a7a169/entity/tool_spec.py#L1) (实测) | EXTRACTED |
| graph_config.py 管理 Chat Chain 图配置 | [repo:file:entity/graph_config.py:1](https://github.com/OpenBMB/ChatDev/blob/4fb2db0ea90375ce1059f44fe03ffbd191a7a169/entity/graph_config.py#L1) (实测) | EXTRACTED |
| 17 个顶层目录 | [repo:file:.:1](https://github.com/OpenBMB/ChatDev/tree/4fb2db0ea90375ce1059f44fe03ffbd191a7a169/.#L1) (17 子目录实测) | EXTRACTED |

# 对照验证（第 7 步）
- 对照源：deepwiki.com/OpenBMB/ChatDev（2026-09-09 访问）
- 对照结论：DeepWiki 架构概述与本地源码精读一致——Chat Chain 阶段化对话链为核心机制，entity/ 配置管理 + workflow/ 执行引擎 + runtime/ SDK 三层架构。DeepWiki 补充了 Communicative Agents 论文的学术背景。
- 差异：无实质性差异。

# .distill-state.json
```json
{
  "repo": "OpenBMB/ChatDev",
  "repo_commit": "4fb2db0ea90375ce1059f44fe03ffbd191a7a169",
  "distilled_at": "2026-09-09",
  "distilled_modules": ["entity/", "runtime/", "workflow/", "server/", "frontend/", "mcp_example/", "tools/", "yaml_instance/", "yaml_template/"],
  "repomix_version": "1.18.0",
  "token_count": "未全量 Repomix（本地源码精读）",
  "cb11_update_path": "首次蒸馏，Update 分支待后续 repo 更新后触发"
}
```

# 溯源
- 本地源码：[本机绝对路径已隐藏] clone --depth 1，commit 4fb2db0，613 files）
- 对照源：deepwiki.com/OpenBMB/ChatDev
- 交接包：LB-4 批 6（C02 域四张 F 卡扩产）

# 其他架构域简评（C-B1-AMD-01 变更1 合并占位）

- arch-patterns：低相关（本框架核心模式已并入 orchestration 节描述），未单独蒸馏
- arch-skill-philosophy：低相关（角色/SOP 即其技能哲学，已由 arch-orchestration/arch-prompting 覆盖），未单独蒸馏
- arch-frontend：未单独蒸馏（OSS 核心=CLI/Python API；Web 界面属商业化产品线，如涉及将在 Update 路径补）
- arch-exec-backend：未单独蒸馏（沙箱/隔离执行已并入 arch-security 节描述）

# 待补
- [ ] 精确 star 数 GitHub API 复测（当前 34,000 为交接包给定近似值）
- [ ] Repomix 全量 token 计数
- [ ] Communicative Agents 论文与代码实现的对应关系精读
- [ ] 自定义 Chat Chain 的完整示例（YAML 配置→执行→产出物）
- [ ] MCP 集成的实际调用验证

# [CB-11 走查说明]
本卡为首次蒸馏（无旧 commit 对比），Update 分支待后续 ChatDev repo 更新后触发。

## 更新记录

- 2026-09-14 | LB-R4 30天复扫 | star=34280（34271→34280） | HEAD=4fb2db0ea90375ce1059f44fe03ffbd191a7a169（pinned=4fb2db0ea90375ce1059f44fe03ffbd191a7a169，commit 漂移 4fb2db0ea9→4fb2db0ea9） | L1 微漂移标注（CB-11：仅标注，未重蒸馏）| pushed_at=2026-07-24 archived=false | 锚点 repo_base_url/repo_local_path 不动
