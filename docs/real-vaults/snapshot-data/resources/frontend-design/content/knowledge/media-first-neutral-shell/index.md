---
title: 媒体优先的中性框架作品集
---
# 媒体优先的中性框架作品集

任务：当作品本身足够强时，用黑白/中性框架让内容做主角，文本只做锚点，避免额外"炫技 UI"抢戏。
检索词：cgi-portfolio、showreel、media-first、neutral-shell、creative-studio、motion-showcase、中性壳、作品驱动、黑白框架。
摘要：网站把 CGI/媒体作品当作界面主角，文本仅作锚点；黑白中性壳统一高饱和作品之间的视觉，动效只服务观看路径。本轮仅取得报告二手描述。
适用（INFERRED）：CGI/动效/影像工作室作品集、showreel 主导的站点；素材质量足够高，需要框架退后。
不适用（INFERRED）：素材普通、需靠 UI 设计补位的站点；未取得前端框架证据，不在技术实现上做断言。
关键未知（UNVERIFIED）：前端框架未披露、媒体网格栅格、滚动进场参数、断点、性能、可访问性、许可证条款均未取证。
主要证据（EXTRACTED）：报告 P151–P161（Wonder Vision / CSS Winner，作品当主角、文本做锚点、黑白中性壳，结构 Showreel→Recent Work→Expertise→Services→社媒/Contact）。
读取入口（Vault 相对路径）：
- evidence_read_path: content/knowledge/media-first-neutral-shell/evidence/report-20-cases-p151-p161.md

## 机制与理由

"内容足够强时框架要退后"是一个判断顺序问题：先评估素材质量，再决定 UI 存在感。中性黑白壳的作用是统一不同高饱和作品之间的视觉——作品之间不再靠装饰 UI 过渡，而是靠一致的中性边框/留白衔接；动效（showreel、项目预览、滚动进场、媒体网格）只服务观看路径。

## 页面拆解

- 主角层：CGI/媒体作品、showreel。
- 锚点层：文本仅做锚点（标题/标签）。
- 框架：黑白/中性壳，统一高饱和作品。
- 导航骨架：Showreel → Recent Work → Expertise → Services → 社媒/Contact。
- 动效：showreel、项目预览、滚动进场、媒体网格（服务观看路径）。

## 实现配方

未取得。报告给"内容优先+中性壳"原则与骨架，未给媒体网格栅格、断点或进场参数；实现前需回源或自行定义中性壳密度。

## 来源、证据与权利

原报告 source_id=report-20-cases；原项目 docs/网页创作/2026-09-30-前端设计案例20选.docx，P151–P161，SHA-256 21c4901d935926ecabf02fc017a6d857e76ce28e48527c345c75cf1eea1ce7b8。
原始 URL（P153）：https://www.wonder-vision.com/ 。
项目影像受客户/工作室权利保护。官网明确服务含 CGI+motion、creative technology，但前端框架未披露；许可证未知，不得断言可复用。

## 变体、关联与项目反馈

- 关联：与 broadcast-ui-portfolio（P036–P046）同为作品驱动；对比在于本案中性壳退后，后者主动加广播人格层。
- 边界（报告 P160）：Agent 生成作品集应先判断素材质量，再决定 UI 存在感。

## 维护记录

2026-10-04：从 report-20-cases P151–P161 蒸馏；仅报告二手证据，未取框架或许可。
