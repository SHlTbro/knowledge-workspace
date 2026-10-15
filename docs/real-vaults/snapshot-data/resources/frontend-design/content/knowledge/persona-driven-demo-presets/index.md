---
title: 按角色切换的演示预设
---
# 按角色切换的演示预设

任务：营销首页提供 Persona 切换器，按受众角色（Agencies / CD / Marketers 等）一键切换画布上的节点、媒体与文案，而非把所有功能堆在一个 demo 里。
检索词：persona switcher、role-based demo、audience tabs、use case switch、marketing canvas、node graph、复刻。
摘要：同一画布骨架，按角色映射一组 nodes/media 预设；切角色 = 换一组数据而非换一整页。报告原等级：CONFIRMED（首页 Personas 段 DOM 可见，P346–P349）+ Recipe 级描述（P412）。
适用（INFERRED）：B2B 产品面向多类买家（代理/创意总监/市场/电商/GTM），首页需要让每类访客都看到"这是给我用的"。
不适用（INFERRED）：单一受众产品；需要为每个角色做独立落地页而非同页切换的场景；角色间数据模型差异极大、无法共用骨架时。
关键未知（UNVERIFIED）：切换动画、预设间 diff 范围、URL 是否反映角色、SEO 如何处理多角色内容、每个角色具体节点数量与媒体清单。不得推广为全站路由方案。
主要证据（EXTRACTED）：report-3-sites P346–P349、P412、P420（Melius）；报告称"Agencies/CD/Marketers 各映射一组 nodes/media"、"按角色切用例，而非堆功能"。
读取入口：
- evidence_read_path: content/knowledge/persona-driven-demo-presets/evidence/report-3-sites-melius-persona-presets.md

## 机制与理由

多角色 B2B 站最容易犯的错是把所有行业案例塞进一个画布，结果每个角色都觉得"这不是我的"。PersonaSwitcher 让共用一套 Canvas 组件骨架，只换数据层（nodes/media 预设）：Agencies 看到广告 campaign 节点，Marketers 看到素材生成节点。访客停留成本低，且首页 SEO 内容不稀释。

## 实现配方（PROPOSED，待验证）

- 数据：personaId → { nodes: [...], media: [...], headline } 的映射表。
- 组件：PersonaSwitcher（tab/segmented）+ CanvasShowcase 接收当前 persona 预设。
- 切换：报告未说动画；建议只替换数据，骨架不动。
- 角色清单（报告原文）：Agencies / CD / Marketers / E-commerce / GTM（P347）；Recipe 另列 Advertising/E-commerce/Film/Fashion/Branding（P412）——两组命名不一致，按报告原等级保留，不强行统一。
未取得原站 bundle，具体节点字段与 WebGL 渲染细节保持未知。

## 来源、证据与权利

source_id=report-3-sites；原项目 docs/网页创作/2026-09-30-前端源码蒸馏3站.docx；URL https://www.melius.com/ 。报告原等级按原报告记录（首页结构 CONFIRMED、Recipe 描述），不升级。许可证未知，不得断言可复用；本条目仅记录模式，不复制原站素材。

## 维护记录

2026-10-04：从 report-3-sites Melius 首页/Persona 段蒸馏，P346–P349/P412/P420；证据为二手报告描述。
