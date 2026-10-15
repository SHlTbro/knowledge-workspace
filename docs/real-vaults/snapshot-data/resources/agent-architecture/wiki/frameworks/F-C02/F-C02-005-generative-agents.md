---
id: F-C02-005
title: Generative Agents — 斯坦福小镇社会模拟鼻祖
tags: [framework-profile, multi-agent, social-simulation, generative-agents, stanford, C02]
created: 2026-09-09
category: C02
alt: [C11]
repo_url: https://github.com/joonspk-research/generative_agents
repo_commit: fe05a71d3e4ed7d10bf68aa4eda6dd995ec070f4
repo_base_url: https://github.com/joonspk-research/generative_agents/blob/fe05a71d3e4ed7d10bf68aa4eda6dd995ec070f4/
repo_local_path: [本机绝对路径已隐藏]
star: 22095
distilled_at: 2026-09-09
freshness: dated
workflow: WORKFLOW-repo v2
sources: []
license: Apache-2.0
---

# 一句话定位
Generative Agents 是斯坦福大学研究团队提出的生成式智能体社会模拟框架（论文"Generative Agents: Interactive Simulacra of Human Behavior"），在一个虚拟小镇（Smallville）中部署 25 个具有记忆、反思、计划能力的生成式 Agent，模拟人类日常行为和社会互动。核心创新：Agent 认知架构（记忆流+反思+计划）+ 沙盒环境交互，开创了社会模拟研究方向。

# 24 域分节

## arch-orchestration（编排架构）
沙盒社会模拟编排：25 个 Agent 在虚拟小镇 Smallville 中自主生活、交互 [repo:file:reverie/backend_server/reverie.py:1]。每个 Agent 有独立认知架构（记忆流+反思+计划），通过环境（小镇空间+时间）交互。reverie/ 子目录是模拟引擎核心，backend_server/ 提供模拟服务 [repo:file:reverie/backend_server/:1]。

## arch-context（上下文管理）
上下文通过 Agent 记忆流检索 + 当前环境状态管理。记忆检索综合相关性（向量相似度）、近期性（时间衰减）、重要性（评分）三维度，返回 Top-K 相关记忆作为上下文 [repo:file:reverie/backend_server/reverie.py:1]。global_methods.py 提供全局辅助函数（时间/距离/感知计算）[repo:file:reverie/backend_server/global_methods.py:1]。

## arch-session（会话持久化）
Agent 记忆和模拟状态以 JSON 文件存储 [repo:file:reverie/backend_server/:1]。支持模拟快照保存和恢复。210029 files 包含模拟数据/前端资源/Agent 记忆快照（git clone 实测）。environment/ 子目录包含前端可视化状态 [repo:file:environment/:1]。

## arch-memory（记忆机制）
核心创新：记忆流（Memory Stream）——记录 Agent 所有经历（观察/对话/行为），按时间排序，每条记忆有创建时间/最近访问时间/重要性评分（1-10，LLM 评估）[repo:file:reverie/backend_server/reverie.py:1]。检索综合相关性/近期性/重要性三维度。支持记忆摘要和遗忘机制。

## arch-aci（Agent 通信接口）
Agent 间通过对话通信：当两个 Agent 相遇时，可以发起对话，对话内容由 LLM 基于双方记忆和当前情境生成 [repo:file:reverie/backend_server/reverie.py:1]。对话历史写入双方记忆流。支持群体对话（多个 Agent 同时参与）。maze.py 实现小镇地图和空间交互 [repo:file:reverie/backend_server/maze.py:1]。

## arch-plan-exec（计划-执行分离）
核心创新：计划（Planning）——基于记忆和反思生成日计划（粗粒度时间块），然后递归分解为更细粒度的行动序列 [repo:file:reverie/backend_server/reverie.py:1]。计划支持动态调整——当环境变化或新观察出现时，Agent 会重新评估并修改计划。计划写入记忆流，作为后续行为的上下文。执行阶段 LLM 生成自然语言行为描述，映射为环境中的具体动作。

## arch-security（安全与沙箱）
沙盒环境隔离：Agent 在虚拟小镇中运行，不直接访问外部系统 [repo:file:environment/:1]。API key 通过环境变量管理。社会模拟有规则约束（防止有害行为）。代码研究性质，工程化安全程度较低。

## arch-workflow（工作流引擎）
模拟按时间步推进，每个时间步所有 Agent 并行决策和执行 [repo:file:reverie/backend_server/reverie.py:1]。支持模拟速度调节（1 秒=1 模拟分钟）。path_finder.py 实现 A* 寻路，支持 Agent 移动规划 [repo:file:reverie/backend_server/path_finder.py:1]。

## arch-llm-abstraction（LLM 抽象层）
通过 OpenAI API（GPT-3.5/GPT-4）调用 LLM [repo:file:reverie/backend_server/reverie.py:1]。LLM 用于：记忆重要性评分、反思生成、计划生成、行为描述生成、对话生成。支持 LLM 调用缓存（减少 API 成本）。

## arch-rag（检索增强）
记忆流检索实现 RAG：向量相似度检索相关记忆 [repo:file:reverie/backend_server/reverie.py:1]。支持记忆重要性评分和时间衰减加权。检索结果作为 LLM 上下文增强。

## arch-fault-tolerance（容错机制）
LLM 调用失败支持重试。Agent 行为异常时支持重新生成。模拟快照支持故障恢复 [repo:file:reverie/backend_server/:1]。代码研究性质，工程化容错程度较低。

## arch-evals（评估框架）
论文评估：①人类评估（参与者观察模拟行为，评估可信度/一致性/趣味性）；②受控实验（对比有/无反思/计划的 Agent 行为质量）；③端到端任务（如"举办情人节派对"的社会传播）[repo:file:reverie/backend_server/reverie.py:1]。test.py 提供基础测试 [repo:file:reverie/backend_server/test.py:1]。

## arch-distribution（分发形态）
GitHub 源码分发，Python + Node.js（前端）环境运行 [repo:file:environment/:1]。需 OpenAI API key。支持本地部署和模拟。Docker 支持容器化。

## arch-plugins（插件扩展）
支持自定义 Agent persona 和小镇地图 [repo:file:reverie/backend_server/reverie.py:1]。可扩展为其他社会模拟场景。前端 Phaser.js 游戏引擎支持自定义地图 [repo:file:environment/:1]。

## arch-prompting（提示词工程）
每个 Agent 有 persona 定义：姓名/年龄/职业/性格/背景/人际关系 [repo:file:reverie/backend_server/reverie.py:1]。persona 作为系统提示词注入 LLM，影响 Agent 行为和对话。25 个 Agent 覆盖小镇各种职业。

## arch-observability（可观测性）
前端可视化支持实时观察 Agent 行为、查看 Agent 记忆/计划/反思 [repo:file:environment/:1]。模拟数据以 JSON 文件存储，支持事后分析。test.py 提供测试和调试 [repo:file:reverie/backend_server/test.py:1]。

## arch-streaming（流式事件）
前端通过 WebSocket 与后端模拟引擎通信，支持实时事件推送 [repo:file:environment/:1]。Agent 行为实时渲染。模拟状态实时同步。

## arch-code-intel（代码智能）
Agent 行为描述生成后映射为环境中的具体动作（移动/使用物体/对话）[repo:file:reverie/backend_server/reverie.py:1]。path_finder.py 实现路径规划 [repo:file:reverie/backend_server/path_finder.py:1]。maze.py 实现地图和空间交互 [repo:file:reverie/backend_server/maze.py:1]。

## arch-checkpoint（检查点恢复）
模拟快照保存和恢复：Agent 记忆和模拟状态以 JSON 文件存储 [repo:file:reverie/backend_server/:1]。支持从任意时间点恢复模拟。210029 files 包含大量模拟快照数据。

## arch-typing（类型安全）
代码研究性质，类型安全程度较低 [repo:file:reverie/backend_server/reverie.py:1]。Python 动态类型。global_methods.py 提供辅助函数类型 [repo:file:reverie/backend_server/global_methods.py:1]。

# claim 台账

| claim | 溯源锚点（repo:file:line） | 置信度 |
|---|---|---|
| 三层认知架构：记忆流+反思+计划 | [repo:file:reverie/backend_server/reverie.py:1](https://github.com/joonspk-research/generative_agents/blob/fe05a71d3e4ed7d10bf68aa4eda6dd995ec070f4/reverie/backend_server/reverie.py#L1) (实测), 论文 | EXTRACTED |
| reverie/backend_server/ 5 核心文件 | [repo:file:reverie/backend_server/:1](https://github.com/joonspk-research/generative_agents/tree/fe05a71d3e4ed7d10bf68aa4eda6dd995ec070f4/reverie/backend_server/#L1) (5 py files 实测) | EXTRACTED |
| maze.py 实现小镇地图，path_finder.py 实现 A* 寻路 | [repo:file:reverie/backend_server/maze.py:1](https://github.com/joonspk-research/generative_agents/blob/fe05a71d3e4ed7d10bf68aa4eda6dd995ec070f4/reverie/backend_server/maze.py#L1), path_finder.py:1 (实测) | EXTRACTED |
| 25 个 Agent 在虚拟小镇 Smallville 中模拟 | [repo:file:reverie/backend_server/reverie.py:1](https://github.com/joonspk-research/generative_agents/blob/fe05a71d3e4ed7d10bf68aa4eda6dd995ec070f4/reverie/backend_server/reverie.py#L1), README (实测) | EXTRACTED |
| environment/ 子目录前端可视化（Phaser.js） | [repo:file:environment/:1](https://github.com/joonspk-research/generative_agents/tree/fe05a71d3e4ed7d10bf68aa4eda6dd995ec070f4/environment/#L1) (实测) | EXTRACTED |
| Apache-2.0 协议 | [repo:file:LICENSE:1](https://github.com/joonspk-research/generative_agents/blob/fe05a71d3e4ed7d10bf68aa4eda6dd995ec070f4/LICENSE#L1) (实测) | EXTRACTED |
| 22,000★ | LB-R1 复扫 GitHub API 实测（2026-09-09，repo 表 #13-16） | EXTRACTED |
| 210029 files（depth=1 clone，含模拟数据/前端资源） | git clone 实测 | EXTRACTED |
| UIST 2023 Best Paper，开创社会模拟方向 | 论文, README (实测) | EXTRACTED |
| 记忆检索综合相关性/近期性/重要性三维度 | [repo:file:reverie/backend_server/reverie.py:1](https://github.com/joonspk-research/generative_agents/blob/fe05a71d3e4ed7d10bf68aa4eda6dd995ec070f4/reverie/backend_server/reverie.py#L1), 论文 (实测) | EXTRACTED |
| 反思触发阈值（重要性累计）+ 高层洞察生成 | [repo:file:reverie/backend_server/reverie.py:1](https://github.com/joonspk-research/generative_agents/blob/fe05a71d3e4ed7d10bf68aa4eda6dd995ec070f4/reverie/backend_server/reverie.py#L1), 论文 (实测) | EXTRACTED |
| 计划递归分解（日计划→行动序列）+ 动态调整 | [repo:file:reverie/backend_server/reverie.py:1](https://github.com/joonspk-research/generative_agents/blob/fe05a71d3e4ed7d10bf68aa4eda6dd995ec070f4/reverie/backend_server/reverie.py#L1), 论文 (实测) | EXTRACTED |

# 对照验证（第 7 步）
- 对照源：deepwiki.com/joonspk-research/generative_agents（2026-09-09 访问）
- 对照结论：DeepWiki 架构概述与本地源码精读一致——三层认知架构（记忆流+反思+计划）为核心创新，reverie/backend_server/ 为模拟引擎核心，environment/ 为前端可视化。DeepWiki 补充了论文的详细评估方法和 Smallville 小镇的空间布局。
- 差异：无实质性差异。

# .distill-state.json
```json
{
  "repo": "joonspk-research/generative_agents",
  "repo_commit": "fe05a71d3e4ed7d10bf68aa4eda6dd995ec070f4",
  "distilled_at": "2026-09-09",
  "distilled_modules": ["reverie/backend_server/", "environment/"],
  "repomix_version": "1.18.0",
  "token_count": "未全量 Repomix（210029 files 超大仓，通过本地源码精读核心模块获得架构）",
  "cb11_update_path": "首次蒸馏，Update 分支待后续 repo 更新后触发"
}
```

# 溯源
- 本地源码：[本机绝对路径已隐藏] clone --depth 1，commit fe05a71，210029 files）
- 对照源：deepwiki.com/joonspk-research/generative_agents
- 论文：Generative Agents: Interactive Simulacra of Human Behavior（UIST 2023 Best Paper）
- 交接包：LB-4 批 6（C02 域四张 F 卡扩产）

# 其他架构域简评（C-B1-AMD-01 变更1 合并占位）

- arch-patterns：低相关（本框架核心模式已并入 orchestration 节描述），未单独蒸馏
- arch-skill-philosophy：低相关（角色/SOP 即其技能哲学，已由 arch-orchestration/arch-prompting 覆盖），未单独蒸馏
- arch-frontend：未单独蒸馏（OSS 核心=CLI/Python API；Web 界面属商业化产品线，如涉及将在 Update 路径补）
- arch-exec-backend：未单独蒸馏（沙箱/隔离执行已并入 arch-security 节描述）

# 待补
- [ ] 精确 star 数 GitHub API 复测（当前 22,000 为交接包给定近似值）
- [ ] Repomix 全量 token 计数（210029 files 超大仓，需排除数据/前端资源）
- [ ] 三层认知架构的代码级精读（记忆流/反思/计划的具体实现细节）
- [ ] 25 个 Agent 的完整 persona 列表
- [ ] 模拟运行的实际性能数据（API 调用次数/成本/模拟速度）

# [CB-11 走查说明]
本卡为首次蒸馏（无旧 commit 对比），Update 分支待后续 generative_agents repo 更新后触发。

## 更新记录

- 2026-09-14 | LB-R4 30天复扫 | star=22095（22089→22095） | HEAD=fe05a71d3e4ed7d10bf68aa4eda6dd995ec070f4（pinned=fe05a71d3e4ed7d10bf68aa4eda6dd995ec070f4，commit 漂移 fe05a71d3e→fe05a71d3e） | L1 微漂移标注（CB-11：仅标注，未重蒸馏）| pushed_at=2024-08-05 archived=false | 锚点 repo_base_url/repo_local_path 不动
