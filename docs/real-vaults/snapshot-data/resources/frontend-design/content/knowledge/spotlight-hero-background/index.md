# 暗色 Hero 多层径向渐变光斑背景

- 用途：Component / Recipe（Hero 背景光效）
- 页面任务与交互目的：在暗色 Hero 上制造焦点与空间感，替代被滥用的"大面积炫光"，同时不抢标题。
- 风格、查找词与实现约束：spotlight、radial-gradient、hero-background、subtle-animation、dark-hero、accent-light；React + shadcn registry；精确 hex/easing 未取证。
- 摘要（EXTRACTED/INFERRED）：Aceternity Spotlight New 用低透明度多层 radial-gradient 在暗色背景上叠加左右光斑，光斑低频缓慢位移；结构为"绝对定位背景层 → 多个渐变光斑 → 前景 Hero 文案/CTA"。
- 适用（INFERRED）：暗色首屏、需要视觉焦点但无产品截图的 Hero；想给 SaaS/AI 首屏加克制空间感。
- 不适用（INFERRED）：需要光斑跟随鼠标、作用于单张卡片的场景——那是 Card Spotlight（P174–P183），作用域是卡片局部 hover，不是整页背景。
- 关键未知（UNVERIFIED）：精确 gradient 色值、光斑尺寸、duration、xOffset 默认值、是否含 reduced-motion、许可证条款均未独立核验。
- 主要证据结论（EXTRACTED，二手报告层）：P166"低透明度多层 radial gradient 在暗色 Hero 制造焦点和空间感"；P167"低频、低对比运动，不抢标题"；P169 确认 React 组件 + shadcn registry，props 含 gradient/尺寸/duration/xOffset。报告原等级见证据文件。
- 证据读取路径（Vault 相对）：content/knowledge/spotlight-hero-background/evidence/report-20-cases-p162-p172.md

## 机制与理由

报告（EXTRACTED，P166）反对"越亮越高级"：光斑强度用低透明度多层叠加，而非单块高饱和炫光。运动被刻意降到低频低对比（P167：左右 spotlight 缓慢位移），目的是让光斑成为空间暗示，而不是吸引眼球的动画主角。整理者推断（INFERRED）这给 Agent 一条可执行的"暗色 Hero 背景强度规则"：光斑是背景层，永远弱于标题层。

## 页面拆解（EXTRACTED，P168）

绝对定位背景层 → 多个 radial-gradient 光斑 → 前景 Hero 文案/CTA（前景在 DOM 上层）。

## 实现配方

- 已观察实现：未取得一手源码；报告 P169 记 props 含 gradient、尺寸、duration、xOffset。
- 建议实现（PROPOSED）：暗色底上用 2–3 个低透明 radial-gradient 绝对定位光斑；对光斑做很慢的水平位移动画；z-index 低于文案；对比度压低到标题可读不受干扰。
- 错误边界（PROPOSED）：光斑不可常亮高对比；必须提供 reduced-motion 降级（本组件是否内置未取证）。
- 验证：未运行。

## 来源、证据与权利

source_id=report-20-cases；原工件见证据文件。组件 URL：https://ui.aceternity.com/components/spotlight-new（P164）。证据 evidence/report-20-cases-p162-p172.md（P162–P172）。
权利（P172 EXTRACTED）：按组件库许可使用，仍需检查项目版本与许可证；本库不断言可商用。

## 变体、关联与项目反馈

- 作用域区分：本单元=整页 Hero 背景（Spotlight New）；Card Spotlight（report P174–P183，鼠标驱动、卡片局部）是不同组件，勿混用。

## 维护记录

- 整理者与日期：distiller，2026-10-04。
- 本次变化：从 report-20-cases P162–P172 蒸馏。
- 待补证：许可证、默认 props 值、reduced-motion 行为。
