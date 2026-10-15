# 抽象 Shader Hero 背景（无产品截图时）

- 用途：Component / Recipe（首屏视觉载体）
- 页面任务与交互目的：当产品是抽象 AI/基础设施、没有真实产品截图时，用连续 GPU shader 动画作 Hero 背景，仍给出高级首屏视觉。
- 风格、查找词与实现约束：shader、hero、ai-landing、abstract-visual、gpu-background、animated-background、community-component；具体实现依赖未核验。
- 摘要（EXTRACTED/INFERRED）：21st.dev Animated Shader Hero 用连续 shader 背景 + 稳定文本/CTA 前景，运动与文字分层；结构为 GPU/Canvas 背景 → 深色遮罩/对比层 → H1/副文案 → CTA → 可选社会证明。
- 适用（INFERRED）：抽象 AI、基础设施、数据产品——无截图可用但需要有质感首屏。
- 不适用（INFERRED）：有真实产品界面截图、应优先展示产品本身的页面；低端设备或无法降级的场景。
- 关键未知（UNVERIFIED）：具体 shader 实现与依赖（WebGL2/three/原生 GLSL 未核验）、性能、许可——报告 P250/P253 明确不臆测、需逐条核验。
- 主要证据结论（EXTRACTED，二手报告层）：P247"价值不是炫，而是给抽象产品一个没有截图时仍成立的视觉载体"；P248"连续 shader 背景 + 稳定文本/CTA，运动与文字必须分层"；P252"需设置性能降级和 reduced-motion"。报告原等级见证据文件。
- 证据读取路径（Vault 相对）：content/knowledge/shader-hero-abstract/evidence/report-20-cases-p243-p253.md

## 机制与理由

报告（EXTRACTED，P247）把 Shader Hero 的定位从"炫技"纠正为"缺图时的视觉载体"：抽象产品没有界面可截，纯文字 Hero 又显得空，于是用一个连续、缓慢的 GPU 动效占据背景。P248 给出关键分层纪律——运动在背景层、文字/CTA 在稳定前景层，二者不能互相干扰。整理者推断（INFERRED）这与 spotlight-hero-background 的"背景弱于标题"同源，但 shader 是连续 GPU 动画而非静态渐变，因此 P252 特别强调性能降级与 reduced-motion。

## 页面拆解（EXTRACTED，P249）

GPU/Canvas 背景 → 深色遮罩/对比层 → H1/副文案 → CTA → 可选社会证明。

## 实现配方

- 已观察实现：未取得；P250 仅确认集合页存在该组件，具体依赖需进组件详情核验。
- 建议实现（PROPOSED）：全屏 shader/Canvas 背景做缓慢连续流动；叠深色遮罩保证前景对比；前景文案/CTA 静止；提供静态首帧或降级图；reduced-motion 时退化为静态。
- 错误边界（PROPOSED）：shader 性能成本高，必须有帧率/降级策略；文字对比度不得被背景波动破坏。
- 验证：未运行。

## 来源、证据与权利

source_id=report-20-cases；原工件见证据文件。集合 URL：https://21st.dev/community/components/explore/ai-website-templates（P245）。证据 evidence/report-20-cases-p243-p253.md（P243–P253）。
权利（P253 EXTRACTED）：社区组件许可需逐条核验，聚合平台收录 ≠ 统一商用授权；本库不断言可复用。

## 变体、关联与项目反馈

- 与 spotlight-hero-background（静态径向光斑）同属暗色 Hero 背景谱系；本单元是连续 GPU 动画。
- 与 one-rule-visual-system 的区别：本单元是单屏背景，非全站母题。

## 维护记录

- 整理者与日期：distiller，2026-10-04。
- 本次变化：从 report-20-cases P243–P253 蒸馏。
- 待补证：shader 具体依赖、性能、社区组件许可。
