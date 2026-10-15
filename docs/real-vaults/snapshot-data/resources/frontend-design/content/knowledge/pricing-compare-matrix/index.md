---
title: 定价卡+比较矩阵统一数据驱动
---
# 定价卡 + 比较矩阵：同一 plan schema 驱动

任务：定价页同时展示价格卡片和详细比较矩阵，二者共享同一数据源，避免 feature 双写漂移。
检索词：pricing、compare-matrix、billing-toggle、plan-schema、data-driven、monthly-annual、seats、credits。
摘要（EXTRACTED）：Heron AI 与 Melius 两站均采用"价格卡片 + 比较矩阵"的定价页结构，且共享同一 plan 数据 schema——Heron 明确"同一 plan schema 同时驱动卡片和比较表，避免 feature 数据双写漂移"；Melius 组件树为 BillingToggle → PlanCards → CreditSelector → SeatStepper → CompareMatrix → FAQ。
适用（INFERRED）：SaaS / 按席位或按量计费的产品；需要同时给"快速决策"（卡片）和"详细对比"（矩阵）两类用户。
不适用（INFERRED）：单一价格或免费产品；纯展示型定价（无交互切换）；本例未证明计费逻辑实现，仅前端数据结构观察。
关键未知（UNVERIFIED）：原站框架、精确价格数字、计费后端实现、比较矩阵的列数与行数、seats/credits 的步进逻辑、年付折扣比例。
主要证据（EXTRACTED）：
- Heron：P248 组件树 Pricing → BillingToggle → PricingCard[] → CompareMatrix → FAQ；P256 BILLING = MONTHLY | YEARLY 价格同步变化；P262"同一 plan schema 同时驱动卡片和比较表，避免 feature 数据双写漂移"；P271 PATTERN:pricing-cards-plus-comparison-matrix。
- Melius：P396 Monthly/Annual + seats/credits；P398 状态驱动价格与权益；P407 Pricing → BillingToggle → PlanCards → CreditSelector → SeatStepper → CompareMatrix → FAQ。
读取入口（全部为 Vault 相对路径）：
- evidence_read_path_heron: content/knowledge/pricing-compare-matrix/evidence/report-3-sites-heron-pricing.md
- evidence_read_path_melius: content/knowledge/pricing-compare-matrix/evidence/report-3-sites-melius-pricing.md

## 机制与理由

价格卡片面向"快速比较三档"的用户，比较矩阵面向"逐条核对 feature"的用户。如果两者各写一份 feature 列表，任何一次权益调整都需要改两处，极易漂移。将 plan 抽象为统一 schema（含 name/price/features[]/limits），卡片和矩阵都是 schema 的不同视图，从根本上消除双写。

## 页面拆解（Heron 变体）

- BillingToggle：月付/年付切换，价格同步变化（EXTRACTED，P256）
- PricingCard[]：价格卡片，数组形态（EXTRACTED，P248）
- CompareMatrix：比较矩阵表格（EXTRACTED，P248）
- FAQ：定价常见问题（EXTRACTED，P248）

## 页面拆解（Melius 变体）

- BillingToggle：月付/年付（EXTRACTED，P396/P407）
- PlanCards：价格卡片（EXTRACTED，P407）
- CreditSelector：额度选择器（EXTRACTED，P407，Heron 无此组件）
- SeatStepper：席位步进器（EXTRACTED，P407，Heron 无此组件）
- CompareMatrix：比较矩阵（EXTRACTED，P407）
- FAQ：常见问题（EXTRACTED，P407）

## 实现配方（PROPOSED）

定义 planSchema = { id, name, monthlyPrice, annualPrice, features[], limits, badge? }；PricingCard 和 CompareMatrix 均从同一 plans[] 数组渲染。BillingToggle 切换时仅改视图字段，不改数据源。Melius 变体额外增加 seats/credits 作为价格乘数或附加选择。

## 来源、证据与权利

原报告 source_id=report-3-sites；原项目 docs/网页创作/2026-09-30-前端源码蒸馏3站.docx。
- Heron 证据段落：P248、P256、P262、P271
- Melius 证据段落：P396–P398、P407
SHA-256：d73649cca6bf1c5c17c7c0730b68e3b57407cb17668e52490d49d70a3b7c498b。
站点 URL：Heron https://www.heron.ai/；Melius https://www.melius.com/（均为报告陈述）。
报告原等级：Melius P396 Pricing config 为 CONFIRMED（P397）；Heron 相关段落无单独等级标注。

## 变体、关联与项目反馈

- Heron 变体：轻量——卡片 + 矩阵，billing 切换同步价格。
- Melius 变体：重量——增加 CreditSelector + SeatStepper，按量计费特征更明显。
- 共同点：BillingToggle + PlanCards + CompareMatrix + FAQ 的四件套骨架。

## 维护记录

2026-10-04：从 report-3-sites 合并 Heron（P248/P256/P262/P271）与 Melius（P396–P398/P407）证据，蒸馏为统一知识单元。
