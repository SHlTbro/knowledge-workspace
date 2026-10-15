# WebGL 滚动电影式叙事

- 用途：Pattern / Recipe（沉浸式叙事首屏）
- 页面任务与交互目的：把滚动条当作电影播放头，用连续 WebGL/实时 3D 场景随滚动推进情绪与论点，让用户"经历"而非"阅读"产品世界观。
- 风格、查找词与实现约束：scroll-cinema、webgl-storytelling、scroll-controlled、webfilm、realtime-3d、gesture-gate、threejs、gsap、lenis；主样本 Why Zero 栈已确认。
- 摘要（EXTRACTED/INFERRED）：主样本 Why Zero 以手势门槛 + 连续 WebGL scroll + 音频/CGI/自定义光标形成电影节奏，视觉先于文案；变体 Chasing the Moment 用五个实时生成场景随滚动推进，"滚动即播放头"，视觉先于文字解释。
- 适用（INFERRED）：反传统/强世界观产品发布、证明型作品集（直接让首页即沉浸体验）；愿意为叙事投入性能预算的项目。
- 不适用（INFERRED）：用户需快速完成实用任务（查价格/查巡演）的站点；无资源做资产压缩与降级的小团队。
- 关键未知（UNVERIFIED）：Chasing the Moment 具体引擎未披露；两案降级策略、移动端手势、精确镜头时长未取证。
- 主要证据结论（EXTRACTED，二手报告层）：Why Zero P054 已确认 GSAP/Howler.js/Lenis/Three.js/WebGL，且把 1GB+ 资产压到约 10MB；P056 重点是学镜头节拍/状态切换/资源预算/交互门槛而非抄 3D。Chasing P110"五场景随滚动，滚动即播放头，视觉先于文案"；P112"every frame is generated live in browser"。报告原等级见证据文件。
- 证据读取路径（Vault 相对）：
  - content/knowledge/webgl-scroll-cinema/evidence/report-20-cases-why-zero-scroll.md
  - content/knowledge/webgl-scroll-cinema/evidence/report-20-cases-chasing-moment.md

## 机制与理由

报告（EXTRACTED，Why Zero P051–P052）的立场是"不是解释产品，而是先让用户经历一次情绪化世界观"：碎裂、燃烧、坠落等意象构成论点，手势解锁 + 连续滚动 + 音频共同形成电影节奏。Chasing the Moment（EXTRACTED，P109–P110）把同一机制用在作品集上——不把 case study 放网格，而是让客户直接经历创作者的节奏。整理者推断（INFERRED）两案共同的可迁移点是"滚动=播放头 + 视觉先于解释 + 体验后才给 CTA"，而非具体 3D 模型。Why Zero 的工程亮点（P054 EXTRACTED）是把 1GB+ 制作资产压到约 10MB 级 WebGL 体验，说明该模式必须配套资产预算。

## 页面拆解

- Why Zero（P053 EXTRACTED）：手势门槛 → 连续 3D 世界 → 价值冲突 → 产品/学校主张 → 行动入口。
- Chasing（P111 EXTRACTED）：可访问性跳转 → 五幕 Webfilm → Why → 工作方式 → Booking CTA。

## 实现配方

- 已观察实现：Why Zero 栈 GSAP/Howler.js/Lenis/Three.js/WebGL（P054 EXTRACTED）；Chasing 实时浏览器生成、引擎未披露（P112）。
- 建议实现（PROPOSED）：滚动进度映射时间轴/摄像机位（播放头）；入口设手势/点击门槛并给跳过/可访问性跳转；文案后置到体验之后；音频可开关；资产做压缩预算；末尾才落 CTA。
- 错误边界（PROPOSED）：必须提供跳过与降级；不可让沉浸挡住实用信息；移动端性能与 reduced-motion 必须预置。
- 验证：未运行。

## 来源、证据与权利

source_id=report-20-cases；原工件见各证据文件。
- Why Zero：https://why.zero.university/（P049），证据 evidence/report-20-cases-why-zero-scroll.md（P047–P057）。
- Chasing the Moment：https://chasing-the-moment.byholm.co/（P107），证据 evidence/report-20-cases-chasing-moment.md（P105–P115）。
权利（P057/P115 EXTRACTED）：不复制 3D 模型、故事脚本、场景镜头、文案或品牌；只提炼叙事与性能机制。

## 变体、关联与项目反馈

- Why Zero=品牌/教育世界观叙事（主）；Chasing=证明型作品集即沉浸体验（变体）。
- 关联：narrative-step-product-story（同为滚动叙事，但那是工作流步骤，本单元是电影镜头）。

## 维护记录

- 整理者与日期：distiller，2026-10-04。
- 本次变化：合并单元，Why Zero 为主样本，Chasing 为变体，两证据分别保留。
- 待补证：Chasing 引擎、两案降级/reduced-motion、精确镜头时长。
