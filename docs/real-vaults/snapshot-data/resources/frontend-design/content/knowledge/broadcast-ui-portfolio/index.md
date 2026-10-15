---
title: 广播式界面作品集（ticker / lower-third）
---
# 广播式界面作品集

任务：为创意制作公司/个人作品集实现"强人格但不抢作品"的界面语法，用粗重标题、滚动字幕条和 lower-third 信息层让作品画面承担视觉重量。
检索词：ticker、lower-third、broadcast-ui、bold-type、studio-portfolio、media-first、production-studio、广播界面、字幕条、作品集模板。
摘要：把电视广播视觉语言（粗重标题、对比色、滚动 ticker、全屏作品切换、暂停/播放控制）做成作品集外壳，作品视频/摄影本身才是主角。本轮仅取得报告二手描述，未取技术栈、运行参照或许可文本。
适用（INFERRED）：创意制作公司、影像/动效工作室、强个人品牌的作品集；需要展示高饱和作品且保留鲜明人格。
不适用（INFERRED）：内容低调、需长篇文字说明的设计/咨询站点；未取得响应式断点证据，不在小屏行为上做断言。
关键未知（UNVERIFIED）：技术栈未披露、ticker 速度、排版字号、断点、性能、可访问性、许可证条款均未取证；不得自动推广为全站规则。
主要证据（EXTRACTED）：报告 P036–P046（Warm & Fuzzy / Neutral Studio，粗重标题+对比色+ticker/lower-third，作品承担视觉重量，结构 品牌宣言→最新作品→项目瀑布→服务→地域/团队→联系 CTA）。
读取入口（Vault 相对路径）：
- evidence_read_path: content/knowledge/broadcast-ui-portfolio/evidence/report-20-cases-p036-p046.md

## 机制与理由

广播 UI 的核心是"信息层退后、内容层上前"：ticker/lower-third 是电视里叠加在画面上的标注，不是画面本身。作品集借这套语法，让粗标题和字幕条提供人格与导航，而把视觉重量交给作品——人格强，但不与作品抢注意力。

## 页面拆解

- 信息层：粗重标题 + 对比色 + 滚动 ticker + lower-third 字幕条。
- 内容层：全屏作品切换、暂停/播放控制、项目瀑布/精选。
- 导航骨架：品牌宣言 → 最新作品 → 项目瀑布/精选 → 服务 → 地域/团队 → 联系 CTA。

## 实现配方

未取得。报告只给语法与骨架，未给 ticker 速度、字号、断点或类名；实现前需回源或自行定义广播信息层密度。

## 来源、证据与权利

原报告 source_id=report-20-cases；原项目 docs/网页创作/2026-09-30-前端设计案例20选.docx，P036–P046，SHA-256 21c4901d935926ecabf02fc017a6d857e76ce28e48527c345c75cf1eea1ce7b8。
原始 URL（P038）：https://www.warmnfuzzy.tv/ 。
作品视频与摄影不可直接复用；可学习字幕条、排版密度、作品排序和信息层级。技术栈未披露、许可证未知，不得断言可复用。

## 变体、关联与项目反馈

- 关联：与 media-first-neutral-shell（P151–P161）同为作品驱动，但本案主动加广播人格层，后者用中性壳退后。
- 边界：目标是"强人格但不抢作品"，ticker/标题密度需服务作品排序，不是堆满信息。

## 维护记录

2026-10-04：从 report-20-cases P036–P046 蒸馏；仅报告二手证据，未取技术栈或许可。
