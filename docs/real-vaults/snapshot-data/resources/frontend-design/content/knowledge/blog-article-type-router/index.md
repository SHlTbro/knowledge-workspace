---
title: 三种 Blog 文章模板路由（Comparison/HowTo/Launch）
---
# 三种 Blog 文章模板路由（Comparison/HowTo/Launch）

任务：Blog 系统不要把所有文章塞进同一个富文本模板，而要按文章类型路由到 Comparison / HowTo / Launch 三套骨架，table/FAQ 等块按类型可选挂载。
检索词：blog template、article type、page type router、comparison article、how-to、launch post、content model、复刻。
摘要：每类文章有固定区块顺序：Comparison（takeaways→table→numbered products→FAQ）、HowTo（framing→原则→step→why canvas→related）、Launch（声明→范围→限制，明显短）。报告原等级：EXTRACTED（报告 3.5 节直接抽象）。
适用（INFERRED）：内容营销型 SaaS 站同时写 SEO 比较文、教程、产品发布；需要结构化 CMS 模板而非纯 Markdown。
不适用（INFERRED）：个人博客/随笔；文章形态高度自由、无法归类的内容站；技术文档站（应走 doc template）。
关键未知（UNVERIFIED）：CMS schema 字段名、URL 结构、SEO 元数据差异、是否真用同一 BlogArticle 壳 + 可选 blocks、写作团队如何标记 type。不得推广为任意 CMS 方案。
主要证据（EXTRACTED）：report-3-sites P399–P403、P408、P415、P424–P425（Melius）；报告明确"应把三种文章当独立 page_type，不要把 Blog 全塞一个富文本模板"。
读取入口：
- evidence_read_path: content/knowledge/blog-article-type-router/evidence/report-3-sites-melius-blog-router.md

## 机制与理由

SEO 比较文需要长表 + numbered products + FAQ 才能拿长尾；how-to 需要 step-by-step 与"why it belongs on canvas"承接转化；launch 文要短、要诚实写限制。三者塞进一个富文本模板会导致：比较文缺表格结构、how-to 缺步骤锚点、launch 文被写成长文稀释新闻性。按 type 路由骨架，让 table/FAQ 成为可选 block，既保 SEO 结构又不强迫每篇都长。

## 实现配方（PROPOSED，待验证）

- 数据：article.type ∈ { comparison, howto, launch }。
- 骨架（报告原文区块顺序）：
  - ComparisonArticle：日期/阅读时长 → H1 → Key takeaways → comparison table → numbered products → FAQ。
  - HowToArticle：问题 framing → 原则 → step-by-step → why it belongs on canvas → related use cases。
  - LaunchArticle：状态声明 → 功能范围 → 当前限制/未来方向（明显短于 comparison long-form）。
- 壳：BlogArticle → ArticleMeta → HeroMedia? → RichTextSections → ComparisonTable? → FAQ?（P408，可选块用 ? 标注）。
未取得原站 CMS schema 与渲染代码，字段名与样式保持未知。

## 来源、证据与权利

source_id=report-3-sites；原项目 docs/网页创作/2026-09-30-前端源码蒸馏3站.docx；URL https://www.melius.com/ 。报告原等级按原报告记录，不升级。许可证未知，不得断言可复用；本条目仅记录内容模型模式，不复制原站文章文案。

## 维护记录

2026-10-04：从 report-3-sites Melius 3.5/3.6/3.7 节蒸馏，P399–P403/P408/P415/P424–P425；证据为二手报告描述。
