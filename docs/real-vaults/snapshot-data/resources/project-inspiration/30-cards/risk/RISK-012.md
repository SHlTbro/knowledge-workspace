---
id: RISK-012
type: RISK
status: active
version: '1.0'
digest: sha256:f2b69df83227fcd9
created: '2026-10-02'
title: 确定性评分的 rubric 偏置与 gaming
source_prj: PRJ-031
tags:
- risk
- scoring
- bias
- gaming
---
## 风险
AgentPress 的确定性评分虽然透明，但 rubric 本身仍可能偏置或被 gaming。如果 Agent 学会了 rubric 的权重，就可以针对性地优化分数而不是提升内容质量。starter credits 属于封闭模拟经济，不等于真实支付合规。

## 刹车信号
- 高分内容质量下降
- Agent 提交内容趋同（都在优化 rubric 而非真实价值）
- 收入分配与内容质量脱钩

## 缓解
- 定期审计 rubric 与内容质量的相关性
- 引入人工抽检和动态权重调整
- 区分"rubric 高分"和"真实消费价值"
