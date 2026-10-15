---
title: Bento Grid 功能信息权重布局
---
# Bento Grid 功能信息权重布局

任务：为 SaaS / Agent / 知识库产品的功能区实现不等宽卡片网格，用尺寸差异表达功能权重，而不是把所有功能排成等宽三列流水账。
检索词：bento-grid、feature-grid、responsive-grid、progressive-density、dashboard-marketing、col-span、不等宽、权重分配。
摘要：CSS Grid 基础上让主功能卡跨多列、次要功能卡占单列，形成视觉主次；容器稳定，每张卡内部可独立嵌入 Marquee / AnimatedList / AnimatedBeam 等局部动效。本轮仅取得报告二手描述，未取官方源码、运行参照或许可文本。
适用（INFERRED）：SaaS、Agent、知识库产品的功能概览区；需要把 6–12 个功能点分出主次、并配局部 demo 画面。
不适用（INFERRED）：严肃数据表、长表单、用户必须逐条对齐的列表；内容条数极少（≤3）时等宽反而更稳；未取得响应式断点证据，不在小屏行为上做断言。
关键未知（UNVERIFIED）：具体 col-span 比例、断点、Tailwind 类名、动效参数、性能、可访问性、许可证条款均未取证；不得自动推广为全站布局规则。
主要证据（EXTRACTED）：报告 P197–P207 描述 Magic UI Bento Grid，“不同尺寸卡片制造信息权重”，可拆结构为 CSS Grid → col-span → 卡片背景 demo → 标题/描述/CTA；技术栈报告自承 React + Tailwind，示例组合 Marquee / AnimatedList / AnimatedBeam。
读取入口（Vault 相对路径）：
- evidence_read_path: content/knowledge/bento-grid-feature-layout/evidence/report-20-cases-p197-p207.md

## 机制与理由

Bento Grid 的核心不是“花哨的方块”，而是用栅格跨度把信息分层：一个主打功能占大卡（画面、截图、动效），若干次要功能占小卡（图标 + 一句话）。容器本身保持静止，动效下放到卡片内部，避免整页跳动。

## 页面拆解

- 外层：响应式 CSS Grid（报告未给断点，UNKNOWN）。
- 卡片：col-span 差异化；主卡跨列，次卡单列。
- 卡内结构：背景 demo 区 → 标题 → 描述 → CTA。
- 可选内嵌动效：Marquee / AnimatedList / AnimatedBeam（来自其他组件，本案例只描述组合方式）。

## 实现配方

未取得。报告只给出结构骨架和技术栈，未给 col-span 数值、断点、类名或参数；实现前需回源 Magic UI 文档或自行定义权重规则。

## 来源、证据与权利

原报告 source_id=report-20-cases；原项目 docs/网页创作/2026-09-30-前端设计案例20选.docx，P197–P207，SHA-256 21c4901d935926ecabf02fc017a6d857e76ce28e48527c345c75cf1eea1ce7b8。
原始 URL（P199）：https://magicui.design/docs/components/bento-grid。
报告自承“遵循 Magic UI 许可；示例内容需替换”，本轮未核验许可证文本，不得断言可复用。

## 变体、关联与项目反馈

- 关联：Marquee（P208–P218）、AnimatedList、AnimatedBeam 是 Bento 卡内常见内嵌动效。
- 边界：报告明确“蒸馏重点应是权重分配规则，不是把所有页面都 Bento 化”。

## 维护记录

2026-10-04：从 report-20-cases P197–P207 蒸馏；仅报告二手证据，未取源码或许可。
