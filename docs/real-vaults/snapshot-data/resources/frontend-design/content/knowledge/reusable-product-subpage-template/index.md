---
title: 可复用产品子页模板（Hero→5 features→3 steps→FAQ）
---
# 可复用产品子页模板：Hero → FeatureDeck[5] → ThreeStep → FAQ

任务：为同一产品的多个子页（如 Chat / Dashboard）共用一套页面骨架，配置化填充各段内容。
检索词：ProductPageTemplate、product-subpage、reusable-layout、feature-deck、three-step、FAQ、config-driven、Chat、Dashboard。
摘要（EXTRACTED）：Heron AI 的 Chat 与 Dashboard 两个产品子页共用同一骨架——ProductHero → FeatureDeck(5) → ThreeStepProcess → FAQ，由同一模板配置驱动，仅替换内容数据。报告明确将其列为 PATTERN:reusable-product-subpage-template。
适用（INFERRED）：同一产品线有 2+ 个功能子页、各页结构相同但内容不同；需要快速新增子页且保持视觉一致。
不适用（INFERRED）：首页（Hero/Story 更复杂）、定价页（有独立 billing 交互）、内容/博客页（模板差异大）；本例未证明组件库复用，仅页面骨架复用。
关键未知（UNVERIFIED）：原站框架、CSS 架构、断点、动画库、FAQ 交互细节（accordion/toggle）、Final CTA 位置与形态均未取证。不得自动推广为全站复刻知识。
主要证据（EXTRACTED）：P217 陈述"产品子页高度复用：Hero → KEY FEATURES(5) → 3-step → FAQ → Final CTA"；P247 组件树给出 ProductPageTemplate → ProductHero → FeatureDeck[5] → ThreeStepProcess → FAQ；P255 指出 FeatureDeck FEATURE_INDEX 0..4、Chat/Dashboard 共用同一交互框架；P261 复刻 Recipe 明确"hero/features[5]/steps[3]/faq[] 配置驱动 Chat 与 Dashboard"。
读取入口（全部为 Vault 相对路径）：
- evidence_read_path: content/knowledge/reusable-product-subpage-template/evidence/report-3-sites-heron-subpage-template.md

## 机制与理由

产品子页的信息架构高度同构：用户进入子页的心智是"这是什么 → 有什么能力 → 怎么用 → 有疑问找谁"。将这四段抽象为模板槽位，可让各子页仅替换内容数组而不改布局，降低新增页面的一致性风险和开发成本。

## 页面拆解

- ProductHero：大标题 + 一句定位 + 产品截图/示意（EXTRACTED，P217/P247）
- FeatureDeck[5]：5 个特性卡片，FEATURE_INDEX 0..4，可配交互（EXTRACTED，P255）
- ThreeStepProcess：3 步使用流程说明（EXTRACTED，P217/P247）
- FAQ：问答列表，交互形式未知（UNVERIFIED）
- Final CTA：报告 P217 提及但组件树 P247 未展开，位置/形态未知（UNVERIFIED）

## 实现配方（PROPOSED）

定义 pageConfig = { hero, features[5], steps[3], faq[], cta }；各产品子页传入不同 config 渲染同一模板。FeatureDeck 的 5 个槽位建议固定为 5，避免数量漂移。

## 来源、证据与权利

原报告 source_id=report-3-sites；原项目 docs/网页创作/2026-09-30-前端源码蒸馏3站.docx，P217、P247、P255、P261、P268–P270，SHA-256 d73649cca6bf1c5c17c7c0730b68e3b57407cb17668e52490d49d70a3b7c498b。
站点 URL：https://www.heron.ai/（报告陈述）。
报告原等级：P224–P233 区域中 Typography/Layout 为 CONFIRMED，本单元核心陈述来自报告 2.5 组件树与 2.7 复刻 Recipe 段落，无单独等级标注。

## 维护记录

2026-10-04：从 report-3-sites P217、P247、P255、P261、P268–P270 蒸馏为独立知识单元。
