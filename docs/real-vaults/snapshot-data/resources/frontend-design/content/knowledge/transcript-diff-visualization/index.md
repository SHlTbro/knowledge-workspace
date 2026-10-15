---
title: 转录文本 diff 可视化（strike/dotted/highlight）
---
# 转录文本 diff 可视化（strike/dotted/highlight）

任务：为 AI 转录/清洗类产品在营销页上 before/after 展示"原始转录 → 清洗后文本"的 token 级差异，让访客一眼看到 AI 改了什么。
检索词：transcript diff、before after、strikethrough、token diff、AI transcription、clean transcript、文本对比、复刻。
摘要：把 raw 与 cleaned 两份文本做 token 化对齐，用删除线表达被删内容、点线表达修复、高亮表达保留/修复后片段；不做整段替换，而是逐 token 共存，让"AI 改了什么"可读。报告原等级：组件模式 EXTRACTED（Aloud 首页 Shape 段可见），具体 token 对齐算法未取证。
适用（INFERRED）：AI 转录/校对/改写类产品需要在营销页直观证明"它改了什么"；任何 raw→clean 双文本对比场景。
不适用（INFERRED）：代码 diff（应走语法高亮 diff viewer）；整段重写而非局部修改的场景；需要行级并排 diff 的场景。
关键未知（UNVERIFIED）：token 切分粒度（词/字/标点）、具体 CSS（strike/dotted/highlight 色值与间距）、是否有动画、对齐算法、无障碍文本顺序。不得推广为全站复刻。
主要证据（EXTRACTED）：report-3-sites P064–P066、P119、P126（Aloud）；报告称 TranscriptDiff 组件 raw/cleaned token 化，strike/dotted/highlight 分别表删除/修复/保留。
读取入口：
- evidence_read_path: content/knowledge/transcript-diff-visualization/evidence/report-3-sites-aloud-transcript-diff.md

## 机制与理由

营销页要证明 AI 价值，最有力的不是"AI 很准"四个字，而是把输入输出并排、让访客自己看到删了什么、补了什么。整段替换会丢失修改粒度；逐 token 对齐 + 三种视觉编码（删除线=删、点线=改、高亮=保留/修复）把"修改动作"本身变成可读证据。

## 实现配方（PROPOSED，待验证）

- 数据：rawTokens[] 与 cleanedTokens[]，带 op 标记（equal / delete / insert / replace）。
- 渲染：inline 流；delete → line-through + 降饱和色；insert/replace → dotted underline 或高亮背景；equal → 普通字色。
- 布局：单行流式，不要左右两栏并排（并排会丢掉"同一句被改"的语感）。
- 移动：报告未取证断点；按单列流式退化。
未取得原站 CSS/JS，色值与动画数值保持未知。

## 来源、证据与权利

source_id=report-3-sites；原项目 docs/网页创作/2026-09-30-前端源码蒸馏3站.docx；URL https://www.aloud.sh/ 。报告原等级按原报告记录，不升级。许可证未知，不得断言可复用；本条目仅记录模式与配方方向，不复制原站素材。

## 维护记录

2026-10-04：从 report-3-sites Aloud 段蒸馏，P064–P066/P119/P126；证据为二手报告描述，未回源核验运行态。
