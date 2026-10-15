# 交互式图纸 Hero（违规标注 + 坐标读数）

用途：在建筑/工程/审查类 AI 产品的首屏 Hero，把一张建筑图纸作为可交互底图，在其上以绝对定位图钉标注"违规点"，并随指针移动实时显示 X/Y 坐标，让营销页本身像一个正在被审查的工具界面。
页面任务与交互目的：首屏需要立刻让访客理解"这是一个能看懂图纸、能标出问题的 AI"；目的是用具象的工具感替代抽象口号，hover 违规点即可看到问题类型。
风格查找词：blueprint hero、interactive blueprint、violation overlay、pin annotation、SVG canvas hero、pointer coordinate、architectural AI、red flag overlay、monochrome + danger accent。
摘要：SVG/Canvas 绘制的黑白图纸作为底图，违规点以绝对定位红色图钉叠加；指针在底图上移动时角落实时显示 X/Y 读数；hover 某 pin 进入 VIOLATION_HOVER，点击进入 SELECT。pin 数据配置化，不写死在 DOM。报告原等级：框架 STRONG_INFERENCE = Webflow；未取得原始 CSS、class 全集与动画 timeline。
适用（INFERRED）：AI 审查/巡检/质检类产品（建筑、代码、合规、医疗影像），产品核心动作是"在一张底图上标出问题"。
不适用（INFERRED）：产品没有可指认底图（纯文本对话、纯表格）时不要硬套；不要把它做成完整 CAD 查看器，Hero 只需要示意性工具感。
关键未知（UNVERIFIED）：底图是 SVG 还是 Canvas（报告只说"SVG/Canvas"二选一）、Webflow 之外是否用了 GSAP/Lenis（报告明确"不等于已确认"）、easing、断点、pin hover 弹层内容、坐标读数单位、许可证。
主要证据结论（EXTRACTED）：P253 状态机"IDLE → POINTER_MOVE → VIOLATION_HOVER/SELECT；X/Y readout 增强工具感"；P259 Recipe"SVG/Canvas 底图 + absolute violation pins + pointer coordinate readout；pin 数据配置化"；P265 列为 PATTERN:interactive-blueprint-hero。报告原等级：Webflow STRONG_INFERENCE。
证据读取路径（Vault 相对路径）：
- evidence_read_path: content/knowledge/interactive-blueprint-hero/evidence/report-3-sites-heron-blueprint-hero.md

## 机制与理由

把 Hero 做成"可交互的图纸"而不是"图纸截图"，理由有三：(1) 隐喻具象——建筑 AI 的价值是"看懂图、指出错"，截图只能说"我们做这个"，可点 pin 让访客亲手 hover 一个违规点，定位一秒传递；(2) 状态机克制——只有 IDLE/POINTER_MOVE/VIOLATION_HOVER/SELECT 四态，不做拖拽缩放、不做图层切换，Hero 不承担查看器职责；(3) 坐标读数增强工具感——角落 X/Y 数字随指针跳动，是 CAD/工程软件的肌肉记忆符号，它的存在本身就在说"这是专业工具"。pin 数据配置化（P259）意味着 pins 是一个坐标数组映射到底图，改数据不改布局。

## 页面拆解

在 Heron AI 首页是首屏主视觉（EXTRACTED，P253/P259）。相邻交互状态机（P254）是 Observe/Advise/Act/Learn 的 scroll-story，与本 Hero 是同页不同区段——BlueprintHero 是首屏静态可交互，Scroll Story 是后续滚动驱动，不要混淆。报告未给出该 Hero 在 SiteShell 下的完整子树命名，仅在 Recipe 层抽象为 Blueprint Violation Hero。

## 实现配方

报告未取得原站源码与 CSS，以下为 PROPOSED 待验证配方：底图推荐 SVG（便于取坐标和 pin 对齐），黑白线稿风格；pin 层绝对定位覆盖，每个 pin 红色圆点+半透明光圈，left/top 用百分比；容器监听 pointermove，把偏移换算成整数坐标显示在角落；hover pin 进入 VIOLATION_HOVER 显示 label 弹层，click 进入 SELECT 显示详细违规说明（报告未取证弹层内容）；配色遵循 P272 PATTERN:semantic-danger-accent-on-monochrome——黑白底+唯一红色危险强调，不要加第二种强调色。底图技术选择、pin 弹层、坐标单位、easing、断点均 UNVERIFIED。

## 来源、证据与权利

原报告 source_id=report-3-sites；原项目 docs/网页创作/2026-09-30-前端源码蒸馏3站.docx，P253、P259–P273（重点 P253、P259、P265），SHA-256 d73649cca6bf1c5c17c7c0730b68e3b57407cb17668e52490d49d70a3b7c498b。原站 URL：https://heronaiapp.com/。报告原等级：框架 STRONG_INFERENCE = Webflow（P138，公开图片节点来自 cdn.prod.website-files.com，未取得完整 runtime bundle，不升级 CONFIRMED）；P278 明确"Webflow 平台强推断不等于 GSAP/Lenis 等库已确认"。本库不升级。许可证未取证，不得断言可复用。

## 变体、关联与项目反馈

关联模式：code-violation-overlay（P266，同一 pin-on-ground 思路移到代码编辑器底图）；semantic-danger-accent-on-monochrome（P272，配色约束）。变体：产品是代码审查时，底图换成代码编辑器/语法高亮层，pin 思路不变。反馈：待真实复刻后补充 SVG vs Canvas 取舍、pin hover 弹层内容、坐标读数是否真有用的实测结论。

## 维护记录

2026-10-04：从 report-3-sites P253、P259–P273 蒸馏；保留报告原等级（Webflow STRONG_INFERENCE）；未访问外站、未运行组件。
