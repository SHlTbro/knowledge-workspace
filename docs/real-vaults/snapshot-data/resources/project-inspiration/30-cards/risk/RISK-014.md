---
id: RISK-014
type: RISK
status: active
version: '1.0'
digest: sha256:2d993ad6ad850985
created: '2026-10-02'
title: 成本优化与任务质量的冲突
source_prj: PRJ-040
tags:
- risk
- finops
- cost
- quality-tradeoff
---
## 风险
MarsadOps 的成本治理如果只优化 cost/request，系统会倾向更短上下文、更弱模型或减少验证，反而增加返工。"便宜"可能与任务质量冲突。成本指标必须与成功率、人工返工和错误损失绑定，否则会导致"更便宜但更多返工"的反效果。

## 刹车信号
- 单次成本下降但总成本上升（因为返工增加）
- 任务成功率下降
- 人工返工率上升
- 用户满意度下降

## 缓解
- 核心指标用 cost per verified success，不是 cost per request
- 成本优化必须与质量指标联合监控
- 设置质量底线：成本优化不能导致成功率低于阈值
- A/B 测试：任何成本优化策略必须先在小范围验证不降低质量
