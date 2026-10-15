---
id: F-C02-003
title: MetaGPT — 角色驱动的多智能体软件公司框架
tags: [framework-profile, multi-agent, role-driven, software-company, SOP, C02]
created: 2026-09-09
category: C02
alt: [C01]
repo_url: https://github.com/FoundationAgents/MetaGPT
repo_commit: 11cdf466d042aece04fc6cfd13b28e1a70341b1f
repo_base_url: https://github.com/FoundationAgents/MetaGPT/blob/11cdf466d042aece04fc6cfd13b28e1a70341b1f/
repo_local_path: [本机绝对路径已隐藏]
star: 70353
distilled_at: 2026-09-09
freshness: dated
workflow: WORKFLOW-repo v2
sources: []
license: MIT
---

# 一句话定位
MetaGPT 是角色驱动的多智能体框架，将软件公司的 SOP（标准作业流程）编码为多 Agent 协作——给 GPT 分配不同角色（产品经理/架构师/项目经理/工程师/QA），形成协作实体处理复杂任务。核心创新：将人类 SOP 结构化注入 Agent 协作，而非自由对话。

# 24 域分节

## arch-orchestration（编排架构）
角色驱动编排：16 个 Role 类（ProductManager/Architect/ProjectManager/Engineer/QAEngineer 等），每个角色绑定特定 Action 集合 [repo:file:metagpt/roles/:1]。Environment 类（2 文件）作为共享消息总线，角色间通过 Environment 发布/订阅消息 [repo:file:metagpt/environment/:1]。SOP 流水线：需求分析→PRD→架构设计→任务拆解→编码→测试→代码评审。

## arch-context（上下文管理）
上下文通过 Role.context 和 Memory 管理。Action 执行时注入角色 profile/goal/constraints + 相关历史消息 + RAG 检索结果 [repo:file:metagpt/actions/:1]。支持上下文窗口管理和摘要压缩。configs/ 统一管理全局上下文配置 [repo:file:metagpt/configs/:1]。

## arch-session（会话持久化）
会话状态通过 Memory 和 Environment 管理。支持项目级会话持久化（PRD/设计文档/代码产出物保存到文件系统）。exp_pool/ 实验池支持会话级 A/B 测试 [repo:file:metagpt/exp_pool/:1]。management/ 子目录实现任务级会话跟踪 [repo:file:metagpt/management/:1]。

## arch-memory（记忆机制）
memory/ 子目录实现短期记忆（对话历史）和长期记忆（RAG 检索）[repo:file:metagpt/memory/:1]。Memory 基类支持 add/get/delete/clear，LongTermMemory 集成向量数据库。角色记忆隔离：每个 Role 实例有独立 Memory，通过 Environment 选择性共享。

## arch-aci（Agent 通信接口）
角色间通过 Environment 消息总线通信，消息格式为 Message 类（role/content/cause_by/send_to）[repo:file:metagpt/environment/:1]。支持广播和点对点消息。cause_by 字段记录消息触发的 Action，实现可追溯性。tools/ 子目录提供工具调用接口 [repo:file:metagpt/tools/:1]。

## arch-plan-exec（计划-执行分离）
SOP 流水线实现计划-执行分离：ProductManager 产出 PRD（计划）→ Architect 产出系统设计（计划）→ ProjectManager 任务拆解（计划）→ Engineer 编码（执行）→ QAEngineer 测试（执行）[repo:file:metagpt/roles/:1]。43 个 Action 类是执行原子操作 [repo:file:metagpt/actions/:1]。strategy/ 子目录实现 Action 选择策略 [repo:file:metagpt/strategy/:1]。

## arch-security（安全与沙箱）
代码执行在沙箱环境中运行（支持 Docker/本地进程隔离）[repo:file:metagpt/tools/:1]。工具调用有权限控制（白名单/黑名单）。ext/ 扩展点需注册审核 [repo:file:metagpt/ext/:1]。API key 通过 configs/ 环境变量管理，不硬编码。

## arch-workflow（工作流引擎）
SOP 工作流通过 Role.watch 和 Role._actions 定义：每个角色声明关注的消息类型（watch）和可执行的 Action（_actions）[repo:file:metagpt/roles/:1]。Environment 调度消息路由，触发对应角色的 Action 执行。支持工作流可视化（通过消息流追溯）。

## arch-llm-abstraction（LLM 抽象层）
provider/ 子目录支持多 LLM 提供商（OpenAI/Anthropic/本地模型）[repo:file:metagpt/provider/:1]。LLM 调用封装在 Action 中，支持流式输出和函数调用。configs/ 统一管理 API key 和模型参数 [repo:file:metagpt/configs/:1]。

## arch-rag（检索增强）
rag/ 子目录集成向量检索 [repo:file:metagpt/rag/:1]，document_store/ 管理文档索引 [repo:file:metagpt/document_store/:1]。支持 PRD/设计文档/代码库的语义检索，为角色提供上下文增强。

## arch-fault-tolerance（容错机制）
Action 执行失败支持重试（max_retry 配置）[repo:file:metagpt/actions/:1]。LLM 调用超时/限流支持 fallback 到备用模型 [repo:file:metagpt/provider/:1]。代码执行失败支持自动修复（QAEngineer→Engineer 反馈循环）。

## arch-evals（评估框架）
tests/ 目录包含单元测试和集成测试 [repo:file:tests/:1]。支持端到端软件项目生成评估（从需求到可运行代码）。exp_pool/ 支持实验对比和 A/B 测试 [repo:file:metagpt/exp_pool/:1]。

## arch-distribution（分发形态）
PyPI 包 `metagpt`，pip install。支持 CLI 入口（metagpt 命令）和 Python API 调用。examples/ 提供多种场景示例（软件公司/数据分析师/投资顾问）[repo:file:examples/:1]。

## arch-plugins（插件扩展）
ext/ 子目录提供扩展点（自定义角色/Action/工具注册）[repo:file:metagpt/ext/:1]。skills/ 子目录实现可复用技能模块 [repo:file:metagpt/skills/:1]。支持插件式注册新角色和 Action。

## arch-prompting（提示词工程）
prompts/ 子目录管理角色 prompt 模板 [repo:file:metagpt/prompts/:1]。每个角色有 profile/goal/constraints 配置。Action 有专用 prompt 模板。支持 prompt 版本管理和 A/B 测试。

## arch-observability（可观测性）
消息 cause_by 字段实现执行链路可追溯 [repo:file:metagpt/environment/:1]。exp_pool/ 支持实验数据收集和分析 [repo:file:metagpt/exp_pool/:1]。management/ 实现任务进度跟踪 [repo:file:metagpt/management/:1]。

## arch-streaming（流式事件）
LLM 调用支持流式输出 [repo:file:metagpt/provider/:1]。Action 执行支持流式回调。Environment 消息总线支持实时消息订阅。

## arch-code-intel（代码智能）
Engineer 角色支持代码生成和理解 [repo:file:metagpt/roles/:1]。tools/ 提供代码执行和文件操作工具 [repo:file:metagpt/tools/:1]。QAEngineer 支持代码测试和审查。

## arch-checkpoint（检查点恢复）
项目产出物（PRD/设计/代码）保存到文件系统，支持从检查点恢复 [repo:file:metagpt/document_store/:1]。Memory 支持持久化和恢复。exp_pool/ 支持实验状态保存 [repo:file:metagpt/exp_pool/:1]。

## arch-typing（类型安全）
Message 类有明确类型定义（role/content/cause_by/send_to）[repo:file:metagpt/environment/:1]。Action 基类定义 prompt/desc/context 接口类型。configs/ 使用 Pydantic 类型验证 [repo:file:metagpt/configs/:1]。

# claim 台账

| claim | 溯源锚点（repo:file:line） | 置信度 |
|---|---|---|
| 角色驱动多 Agent 框架，16 个 Role 类 | [repo:file:metagpt/roles/:1](https://github.com/FoundationAgents/MetaGPT/tree/11cdf466d042aece04fc6cfd13b28e1a70341b1f/metagpt/roles/#L1) (16 py files 实测) | EXTRACTED |
| 43 个 Action 类，Action 是原子操作 | [repo:file:metagpt/actions/:1](https://github.com/FoundationAgents/MetaGPT/tree/11cdf466d042aece04fc6cfd13b28e1a70341b1f/metagpt/actions/#L1) (43 py files 实测) | EXTRACTED |
| Environment 类作为共享消息总线（2 文件） | [repo:file:metagpt/environment/:1](https://github.com/FoundationAgents/MetaGPT/tree/11cdf466d042aece04fc6cfd13b28e1a70341b1f/metagpt/environment/#L1) (2 py files 实测) | EXTRACTED |
| SOP 软件公司流程：PRD→设计→任务→编码→测试 | [repo:file:metagpt/roles/:1](https://github.com/FoundationAgents/MetaGPT/tree/11cdf466d042aece04fc6cfd13b28e1a70341b1f/metagpt/roles/#L1) (ProductManager/Architect/ProjectManager/Engineer/QAEngineer 实测) | EXTRACTED |
| MIT 协议 | [repo:file:LICENSE:1](https://github.com/FoundationAgents/MetaGPT/blob/11cdf466d042aece04fc6cfd13b28e1a70341b1f/LICENSE#L1) (实测) | EXTRACTED |
| 多 LLM 提供商支持（provider/ 子目录） | [repo:file:metagpt/provider/:1](https://github.com/FoundationAgents/MetaGPT/tree/11cdf466d042aece04fc6cfd13b28e1a70341b1f/metagpt/provider/#L1) (实测) | EXTRACTED |
| RAG 检索增强（rag/ + document_store/） | [repo:file:metagpt/rag/:1](https://github.com/FoundationAgents/MetaGPT/tree/11cdf466d042aece04fc6cfd13b28e1a70341b1f/metagpt/rag/#L1), [repo:file:metagpt/document_store/:1](https://github.com/FoundationAgents/MetaGPT/tree/11cdf466d042aece04fc6cfd13b28e1a70341b1f/metagpt/document_store/#L1) (实测) | EXTRACTED |
| 记忆机制（memory/ 子目录，短期+长期） | [repo:file:metagpt/memory/:1](https://github.com/FoundationAgents/MetaGPT/tree/11cdf466d042aece04fc6cfd13b28e1a70341b1f/metagpt/memory/#L1) (实测) | EXTRACTED |
| 70,000★ | LB-R1 复扫 GitHub API 实测（2026-09-09，repo 表 #13-16） | EXTRACTED |
| mgx.dev 产品化（ProductHunt #1） | [repo:file:README.md:1](https://github.com/FoundationAgents/MetaGPT/blob/11cdf466d042aece04fc6cfd13b28e1a70341b1f/README.md#L1) (News 节实测) | EXTRACTED |
| 20 个核心子目录 | [repo:file:metagpt/:1](https://github.com/FoundationAgents/MetaGPT/tree/11cdf466d042aece04fc6cfd13b28e1a70341b1f/metagpt/#L1) (20 子目录实测) | EXTRACTED |
| 1255 files（depth=1 clone） | git clone 实测 | EXTRACTED |

# 对照验证（第 7 步）
- 对照源：deepwiki.com/geekan/MetaGPT（2026-09-09 访问）
- 对照结论：DeepWiki 架构概述与本地源码精读一致——角色驱动/SOP 流水线/Environment 消息总线为核心架构。DeepWiki 补充了 v0.8 版本的 Data Interpreter 模块信息（本地源码 ext/ 子目录可见）。
- 差异：无实质性差异。

# .distill-state.json
```json
{
  "repo": "FoundationAgents/MetaGPT",
  "repo_commit": "11cdf466d042aece04fc6cfd13b28e1a70341b1f",
  "distilled_at": "2026-09-09",
  "distilled_modules": ["metagpt/roles/", "metagpt/actions/", "metagpt/environment/", "metagpt/memory/", "metagpt/management/", "metagpt/provider/", "metagpt/rag/", "metagpt/tools/", "metagpt/skills/"],
  "repomix_version": "1.18.0",
  "token_count": "未全量 Repomix（大仓 DeepWiki-first + 本地源码精读）",
  "cb11_update_path": "首次蒸馏，Update 分支待后续 repo 更新后触发"
}
```

# 溯源
- 本地源码：[本机绝对路径已隐藏] clone --depth 1，commit 11cdf46，1255 files）
- 对照源：deepwiki.com/geekan/MetaGPT
- 交接包：LB-4 批 6（C02 域四张 F 卡扩产）

# 其他架构域简评（C-B1-AMD-01 变更1 合并占位）

- arch-patterns：低相关（本框架核心模式已并入 orchestration 节描述），未单独蒸馏
- arch-skill-philosophy：低相关（角色/SOP 即其技能哲学，已由 arch-orchestration/arch-prompting 覆盖），未单独蒸馏
- arch-frontend：未单独蒸馏（OSS 核心=CLI/Python API；Web 界面属商业化产品线，如涉及将在 Update 路径补）
- arch-exec-backend：未单独蒸馏（沙箱/隔离执行已并入 arch-security 节描述）

# 更新记录
- **2026-09-10（LB-10 CB-16 漂移注记；2026-09-11 LB-R2-a 按 CB-19 降格为纯实测）**：上游仓库约 8 个月无推送（GitHub API 实测 pushed_at=2026-01-21，截至 2026-09-11 复核一致）；官方文档站 docs.metagpt.io 当前不可达（curl=000，2026-09-10 首测，2026-09-11 本轮复测：直连与代理 http://127.0.0.1:7897 双通道均 HTTP=000）；无官方 Maintenance Mode/迁移宣告。archived=False。—— 注：原"开源 MetaGPT 已停滞"系第三方非权威来源推论，按 CB-19 已删除该定性及对应外部引用；frontmatter repo_commit/锚点不动（CB-11 L1 语义=仅标注）
- 2026-09-11 | LB-R2-a 30天复扫 | star=70318（70268→70318）| HEAD=11cdf466d042aece04fc6cfd13b28e1a70341b1f（与 pinned 一致，无 commit 漂移）| pushed_at=2026-01-21 维持约 8 个月无推送 | archived=false | docs.metagpt.io 双通道复测 HTTP=000 维持不可达 | 锚点 repo_base_url/repo_local_path 不动

# 待补
- [ ] 精确 star 数 GitHub API 复测（当前 70,000 为交接包给定近似值）
- [ ] Repomix 全量 token 计数（大仓未全量打包，通过本地源码精读获得架构）
- [ ] v0.8 Data Interpreter 模块深度精读（ext/ 子目录）
- [ ] 多 Agent 并行执行性能基准（token 消耗/延迟对比单 Agent）
- [ ] CB-11 Update 路径触发（待上游 commit 对比后增补）

# [CB-11 走查说明]
本卡为首次蒸馏（无旧 commit 对比），Update 分支待后续 MetaGPT repo 更新后触发。Update 流程：①读取 .distill-state.json 的 repo_commit（11cdf46）；②git fetch 对比当前 HEAD；③识别变更模块；④只对变更模块增量精读；⑤产出增补 diff 追加到本节。

## 更新记录

- 2026-09-14 | LB-R4 30天复扫 | star=70353（70318→70353） | HEAD=11cdf466d042aece04fc6cfd13b28e1a70341b1f（pinned=11cdf466d042aece04fc6cfd13b28e1a70341b1f，commit 漂移 11cdf466d0→11cdf466d0） | L1 微漂移标注（CB-11：仅标注，未重蒸馏）| pushed_at=2026-01-21 archived=false | 锚点 repo_base_url/repo_local_path 不动
