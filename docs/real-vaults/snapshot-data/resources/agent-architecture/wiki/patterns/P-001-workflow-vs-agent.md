---
id: P-001
title: Workflow 还是 Agent——复杂度阶梯决策
tags: [decision, orchestration]
sources: [S-001, S-002]
created: 2026-09-05
updated: 2026-09-05
---

> **迁移留痕**：本卡自 vault①「agent相关」迁移至 vault②「agent架构」（2026-09-07，LB-2 S5），原 ID 不变，内容原样保留。跨库引用请用 `vault①>ID` 显式文本。

# 问题
接到一个任务时，该用单次 LLM 调用、workflow（固定代码路径编排 LLM），还是自主 agent（LLM 自己决定过程）？这是所有 agent 设计的第一道分叉，选错会导致成本失控或能力不足。

# 各方解法对比

| 来源 | 主张 | 关键取舍 |
|---|---|---|
| [[S-001-building-effective-agents\|S-001 Anthropic]] | 复杂度阶梯：单次调用+检索/示例 → workflow 五模式 → agent。只在可证明改善结果时升级 | 阶梯每上一级，延迟/成本/调试难度都涨 |
| [[S-002-12-factor-agents\|S-002 12-Factor]] | 大多数生产系统就该是"确定性代码 + 点缀 LLM 步骤"；agent loop 本质只有 4 步（结构化工具调用→执行→追加上下文→循环） | 放弃"全自主"的想象，换取可预测和可维护 |

# 推荐用法（决策规则）
1. 先问：**一次调用 + RAG + 好的示例能解决吗？** 能，结束。
2. 步骤能预先枚举、要求每次一致 → workflow。S-001 的五模式按复杂度递增：
   prompt chaining（可加 gate）→ routing → parallelization（sectioning/voting）→ orchestrator-workers（子任务动态定）→ evaluator-optimizer（生成-评审循环）。
3. 步数无法预知、必须靠 LLM 看环境反馈决定下一步 → agent，且必须定义**停止条件**（完成判据 + 最大迭代数）。
4. 无论哪一级，**自己写控制流和 prompt，不要让框架托管**（S-002 因子 2/8；S-001 的框架调试性警告）。

# 反面教训
- 为"显得智能"用 agent 干本可 workflow 化的活——付出延迟和成本，收益为零（S-001）。
- 全押框架快速冲到 70-80%，客户面前不够用，被迫逆向工程重写（S-002 的 100+ 构建者教训）。
- agent 没有停止条件 → 无限循环烧钱。

# 溯源
- S-001 §When (and when not) to use agents / §Workflows / §Agents — https://www.anthropic.com/engineering/building-effective-agents
- S-002 README 总体理念 + 因子 2/8 — https://github.com/humanlayer/12-factor-agents

# 待补
- [ ] 补充更多框架在此问题上的实际选择（待 opencode/goose 等画像蒸馏后增补本表）
