---
title: 鼠标跟随的卡片局部光斑 hover
---
# 鼠标跟随的卡片局部光斑 hover

任务：为暗色功能卡 / 定价卡 / 能力卡实现指针位置驱动的局部径向高光，替代被滥用的“整张卡永久霓虹边框”。
检索词：spotlight、pointer-follow、card-hover、radial-gradient、microinteraction、shadcn、aceternity。
摘要：Card 容器上做 pointer tracking，把指针坐标映射成 radial gradient mask 的圆心；用户操作成为光源。公开参数含 radius、color、className。本轮仅取得报告二手描述，未取官方源码、运行参照或许可文本。
适用（INFERRED）：暗色主题下的功能卡、定价卡、能力卡列表；需要“材质感”但不要永久发光边框。
不适用（INFERRED）：亮背景卡（光斑对比度不足）；触屏设备无 hover 状态；需要强可点击指示的主 CTA 按钮。
关键未知（UNVERIFIED）：radius / color 具体值、easing、触发范围、pointermove 频率与性能、reduced-motion、许可证条款均未取证。
主要证据（EXTRACTED）：报告 P174–P184 描述 Aceternity Card Spotlight，“光斑只在局部 hover 区域出现”；可拆结构 Card 容器 → pointer tracking → radial gradient mask → 内容层；报告自承 React + Motion，公开 radius / color / className。
读取入口（Vault 相对路径）：
- evidence_read_path: content/knowledge/card-spotlight-hover/evidence/report-20-cases-p174-p184.md

## 机制与理由

Spotlight 把 hover 反馈从“整张卡变色”收敛到指针附近一小圈径向渐变：既给出交互位置，又避免永久霓虹边框的廉价感。指针坐标直接驱动 mask 圆心，用户移动鼠标时光斑跟随，形成“我在照亮这张卡”的隐喻。

## 页面拆解

- Card 容器：定位上下文，监听 pointermove。
- Pointer tracking：读取相对坐标。
- Radial gradient mask：光斑层，圆心跟随指针。
- 内容层：标题 / 描述 / CTA，位于光斑之上。

## 实现配方

未取得。报告列出参数名但未给 radius / color 数值、easing 或实现细节；复刻时最关键是约束光斑半径、对比度和触发范围（报告 P183 原话）。

## 来源、证据与权利

原报告 source_id=report-20-cases；原项目 docs/网页创作/2026-09-30-前端设计案例20选.docx，P174–P184，SHA-256 21c4901d935926ecabf02fc017a6d857e76ce28e48527c345c75cf1eea1ce7b8。
原始 URL（P176）：https://ui.aceternity.com/components/card-spotlight。
报告自承“遵循 Aceternity 对应组件许可”，本轮未核验许可证文本，不得断言可复用。

## 变体、关联与项目反馈

- 关联：Hero Spotlight 背景（同库同思路，但作用域是整页而非单卡）。
- 边界：报告明确“适合替代被滥用的大面积炫光”。

## 维护记录

2026-10-04：从 report-20-cases P174–P184 蒸馏；仅报告二手证据，未取源码或许可。
