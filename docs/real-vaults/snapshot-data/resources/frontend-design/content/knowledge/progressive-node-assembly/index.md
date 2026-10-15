---
title: 渐进式节点组装动效（营造 agent 工作中）
---
# 渐进式节点组装动效（营造 agent 工作中）

任务：在 node-graph 品牌站上，让节点按依赖顺序逐个 enter、先画 edge 再 reveal output 节点，营造"agent 正在工作"的进行时感，而不是一屏静态图。
检索词：node graph animation、progressive assembly、agent working、edge before output、motion choreography、WebGL canvas、复刻。
摘要：动效编排按数据依赖顺序入场：先起节点、再连边、最后 reveal 输出产物，让静态图看起来像正在被 agent 推导。报告原等级：CONFIRMED（制作方 WebGL 披露 + 首页 node 画布可见，P392–P394）+ Recipe 描述（P413）。
适用（INFERRED）：产品本体是 node graph / agent 工作流，需要营销页传达"系统在跑"；图节点数量适中（可编排顺序）。
不适用（INFERRED）：节点密集到无法编排顺序的大图；纯静态示意图；已有强背景视频且节奏冲突的场景；reduced-motion 用户未处理前不要直接搬。
关键未知（UNVERIFIED）：具体 easing、每节点时长、WebGL/DOM 渲染边界、是否循环、reduced-motion 降级、节点坐标表、Three.js/OGL/Pixi 具体库未确认（P429）。不得推广为 WebGL 背景特效。
主要证据（EXTRACTED）：report-3-sites P392–P394、P413、P417、P426（Melius）；报告原文"按依赖顺序 enter，先画 edge 再 reveal output，营造'agent 正在工作'"。
读取入口：
- evidence_read_path: content/knowledge/progressive-node-assembly/evidence/report-3-sites-melius-node-assembly.md

## 机制与理由

静态 node graph 看起来像架构图；按依赖顺序组装则看起来像一次正在发生的推导。先 edge 后 output 的顺序故意让访客看到"连线先于产物"，呼应 agent 先规划再产出的心智。这是把产品交互隐喻搬到营销页：WebGL 服务于"产品可触摸感"，不是背景装饰（P394）。

## 实现配方（PROPOSED，待验证）

- 数据：node={title, model, mediaType, asset, x, y}（P411）；edge 由依赖推导。
- 顺序：input 节点 enter → edge 连线动画 → output 节点 reveal（P413）。
- 渲染：WebGL/DOM 混合，edge 用 SVG/WebGL lines（P411）；具体库未确认。
- 节奏：报告未给数值；建议单段 < 1s，可循环或 scroll 触发。
未取得原站 bundle，easing/时长/shader 保持未知。

## 来源、证据与权利

source_id=report-3-sites；原项目 docs/网页创作/2026-09-30-前端源码蒸馏3站.docx；URL https://www.melius.com/ 。报告原等级按原报告记录（WebGL CONFIRMED 为制作方披露，非本轮核验），不升级。许可证未知，不得断言可复用；本条目仅记录动效编排模式，不复制原站 shader/素材。

## 维护记录

2026-10-04：从 report-3-sites Melius 3.4/3.7/3.8 节蒸馏，P392–P394/P413/P417/P426；证据为二手报告描述。
