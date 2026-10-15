---
title: 代码逐字写入演示动画
---
# 代码逐字写入演示动画

任务：为开发者产品、AI Coding、CLI/SDK 教程把代码块做成进入视口后逐字打出的动画，而不是贴一张静态截图。
检索词：code-animation、typing、writing、inview、developer-marketing、progressive-reveal、code-demo、shadcn。
摘要：CodeBlock 提供 writing、cursor、duration、delay、inView 参数；进入视口后再启动逐字写入，配合光标。本轮仅取得报告二手描述，未取官方源码、运行参照或许可文本。
适用（INFERRED）：AI Coding / Agent / CLI / SDK 产品的 Hero 或功能演示区；代码短、用户期望“看它跑起来”的场景。
不适用（INFERRED）：用户必须复制粘贴的生产代码块（动画期间不可选、不可复制）；长代码、需要无障碍朗读的代码；未取得 reduced-motion 行为证据。
关键未知（UNVERIFIED）：具体 duration / delay 数值、syntax 主题、光标样式、性能、可访问性、许可证条款均未取证。
主要证据（EXTRACTED）：报告 P220–P230 描述 Animate UI Code，“代码不是静态截图，而是逐步写出来”；可拆结构 Code wrapper → Header → CodeBlock → syntax theme → writing state；API 含 writing / duration / delay / inView。
读取入口（Vault 相对路径）：
- evidence_read_path: content/knowledge/code-typing-demo/evidence/report-20-cases-p220-p230.md

## 机制与理由

逐字写入把“阅读代码”变成“观看过程”，降低首屏认知负担；inView 触发避免首屏多段代码同时打字造成混乱；cursor 给出写入位置锚点。关键边界：动画状态下代码不可交互，所以只用于演示，不用于复制源。

## 页面拆解

- Code wrapper：外壳容器。
- Header：文件标签 / 窗口装饰。
- CodeBlock：语法高亮主题 + writing state。
- writing 状态：逐字符推进、光标、duration / delay、inView 触发。

## 实现配方

未取得。报告列出 API 名称但未给数值、主题或实现细节；实现前需回源 Animate UI 文档。

## 来源、证据与权利

原报告 source_id=report-20-cases；原项目 docs/网页创作/2026-09-30-前端设计案例20选.docx，P220–P230，SHA-256 21c4901d935926ecabf02fc017a6d857e76ce28e48527c345c75cf1eea1ce7b8。
原始 URL（P222）：https://animate-ui.com/docs/components/animate/code。
报告自承“遵循 Animate UI 项目许可”，本轮未核验许可证文本，不得断言可复用。

## 变体、关联与项目反馈

- 报告建议蒸馏“代码演示何时动画、何时保持静态”的使用准则：演示用动画，复制源用静态块。
- 关联：Animate UI Files（P231–P241）同属 shadcn registry 体系。

## 维护记录

2026-10-04：从 report-20-cases P220–P230 蒸馏；仅报告二手证据，未取源码或许可。
