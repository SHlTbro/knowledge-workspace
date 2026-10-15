# Before/After 视觉对比证明（clip-path 滑块）

用途：在产品叙事页中用同一画面的两态叠加，让用户拖动滑块或点按切换，直观看到 AI 处理前后的差异，把"产品价值"变成可操作的视觉证据。
页面任务与交互目的：位于长叙事页的"Shape it / Ship it"步骤，承接转录清洗或 agent 交接的结果展示；目的是用最少解释证明 AI 改变了输入，而不是堆功能截图。
风格查找词：before-after、comparison slider、clip-path、image reveal、before-after toggle、product proof、AI diff、slider compare。
摘要：两帧同尺寸画面叠加，上层用 clip-path 按滑块百分比裁切，拖动即揭示下层；移动端无拖拽手柄时退化为 tap toggle 在 BEFORE/AFTER 间切换。报告称该模式适合"直接证明 AI 价值"，但未取得原站 CSS、easing、断点与组件源码。
适用（INFERRED）：输入/输出差异显著的产品（转录清洗、图片修复、代码改写、设计变体）；长叙事步骤中需要一张"证据卡"收口。
不适用（INFERRED）：两态差异微小、需要并排阅读细节的场景；没有真实 before/after 素材时不要硬凑；不是完整对比表或价格矩阵。
关键未知（UNVERIFIED）：原站框架（报告原等级 UNKNOWN）、clip-path 具体实现是 CSS 还是库、滑块手柄样式、tap toggle 切换动画时长、移动端断点、键盘/读屏可访问性、许可证。不得自动推广为全站复刻知识。
主要证据结论（EXTRACTED）：P105"BEFORE | AFTER 两态，适合 clip-path drag 或 tap toggle"；P122"两个同尺寸 frame 叠加，clip-path 由滑块百分比控制，移动端提供 tap toggle"；P128 列为 PATTERN:before-after-visual-proof。报告原等级：框架 UNKNOWN（P028），色彩 STRONG_INFERENCE（P090），排版/间距 CONFIRMED。
证据读取路径（Vault 相对路径）：
- evidence_read_path: content/knowledge/before-after-visual-proof/evidence/report-3-sites-aloud-before-after.md

## 机制与理由

两态叠加的核心是"同一视口、同一坐标系"：before 帧作为底层铺满容器，after 帧作为上层同样铺满，上层 clip-path 随滑块位置变化。拖动手柄时，裁切百分比从 0（全显 after）到 100（全显 before）连续变化，用户在同一画面里看到边界扫过。并排两图需要眼睛来回移动，而叠加滑块把"差异边界"本身变成交互对象，认知负担更低，也更像"擦拭显影"的隐喻。

移动端 tap toggle 的理由：触屏没有 hover，窄屏里拖手柄命中区小；退化为点按容器在两帧间切换，比硬塞一个小拖柄更可用。报告只说"提供 tap toggle"，未给动画参数。

## 页面拆解

在 Aloud 首页出现在两处（EXTRACTED，P066/P069）："03 Shape it"原始转录 vs clean transcript，旁边配 WorkflowRail；"04 Ship it"与 AgentHandoffTerminal 并列，作为"从反馈闭环到 coding agent 执行"的收口证据。组件树位置（P114）：Ship → AgentHandoffTerminal + BeforeAfter。注意 TranscriptDiff（P119，token 级 strike/highlight）与 BeforeAfter（P122，整帧叠加）是两种不同 diff 表达，不要混用。

## 实现配方

报告未取得原站组件源码与 CSS，以下为 PROPOSED 待验证配方：容器固定宽高比、relative、overflow hidden；底层 before 帧 absolute inset 0；上层 after 帧同定位，clip-path 由滑块 0–100 驱动；手柄竖线+圆钮垂直居中；pointerdown 后监听 pointermove 换算百分比并 clamp；移动端 pointer:coarse 或窄屏断点下隐藏拖柄，改 tap 切换 0/100。easing、时长、手柄视觉、键盘可达性均 UNVERIFIED。

## 来源、证据与权利

原报告 source_id=report-3-sites；原项目 docs/网页创作/2026-09-30-前端源码蒸馏3站.docx，P105–P106、P118–P129（重点 P105、P122、P128），SHA-256 d73649cca6bf1c5c17c7c0730b68e3b57407cb17668e52490d49d70a3b7c498b。原站 URL：https://www.aloud.sh/。报告原等级：框架 UNKNOWN（P028）、色彩 STRONG_INFERENCE（P090）、排版 CONFIRMED（P094）、间距 CONFIRMED（P098），本库不升级。许可证未取证，不得断言可复用。

## 变体、关联与项目反馈

关联模式：transcript-before-after-diff（P126，token 级文本 diff，与本模式整帧图像 diff 互补）。变体：若两态是视频，clip-path 思路可沿用但需同步播放进度，报告未涉及。反馈：待真实复刻后补充手柄命中区、tap 动画时长、移动端断点实测结论。

## 维护记录

2026-10-04：从 report-3-sites P105–P106、P118–P129 蒸馏；保留报告原等级；未访问外站、未运行组件。
