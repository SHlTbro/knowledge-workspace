# 节点图作为品牌语言（WebGL 产品隐喻）

用途：把产品本身的数据模型（节点、边、生成物）直接变成营销页的视觉语言——首页像一张正在运行的创意画布，而不是传统 SaaS 功能清单。
页面任务与交互目的：首屏与 Canvas showcase 区段要让访客立刻感到"这是一个以节点画布为核心的 AI 创意平台"；目的是让产品数据模型本身承担品牌识别，而非用图标/渐变硬凑风格。
风格查找词：node graph、WebGL canvas、product metaphor、node-edge visualization、interactive canvas hero、GraphNode、brand language、generative media、progressive node assembly。
摘要：Melius 首页把 CanvasShowcase 抽象为 InteractiveCanvasShowcase，节点带 title/model/mediaType/asset/x/y，边用 SVG 或 WebGL line 连接；WebGL 互动由制作方 Behance 明确披露（CONFIRMED），目的是"让产品可触摸"，不是背景特效。组件模型应围绕 GraphNode / Edge / AssetTile 构建；不得假设 Next.js/React（报告原等级 UNKNOWN）。
适用（INFERRED）：产品本身就是图/画布/节点工作流（AI agent 编排、设计工具、知识图谱、数据管道）；营销页需要强产品隐喻。
不适用（INFERRED）：产品核心是表单/列表/对话时不要硬套节点图；不要把 WebGL 当装饰背景——报告明确"WebGL 服务于产品可触摸感，不是背景特效"。
关键未知（UNVERIFIED）：具体前端框架（报告原等级 UNKNOWN，不得假设 Next.js/React）、CSS 架构、bundle 名、WebGL 库（three.js? 自研?）、节点布局算法、easing、断点、许可证。
主要证据结论（EXTRACTED）：P344–P345 CanvasShowcase"把产品数据模型变成品牌视觉"；P368–P370 报告原等级 CONFIRMED，"应围绕 GraphNode/Edge/AssetTile 构建组件模型"；P388–P390 Graph visual 原等级 CONFIRMED，NodeMeta/NodeType/ModelBadge 数据模型；P411 Recipe"node={title,model,mediaType,asset,x,y}；WebGL/DOM 混合渲染，edge 用 SVG/WebGL lines"；P418 列为 PATTERN:node-graph-as-brand-language。
证据读取路径（Vault 相对路径）：
- evidence_read_path: content/knowledge/node-graph-brand-language/evidence/report-3-sites-melius-node-graph-home.md
- evidence_read_path: content/knowledge/node-graph-brand-language/evidence/report-3-sites-melius-node-graph-extended.md

## 机制与理由

把产品数据模型变成品牌视觉，理由有三：(1) 一致性——如果产品里就是节点+边+生成物，营销页用同一套语法，访客从落地页到产品内零认知切换；(2) 可触摸感——制作方明确写"WebGL interactions make the product tangible"（P362，原等级 CONFIRMED），WebGL 在这里是让节点画布"可以被拨弄"，不是粒子背景；(3) 数据模型即组件模型——报告 P370 直接建议围绕 GraphNode/Edge/AssetTile 构建组件模型，P390 拆出 NodeMeta/NodeType/ModelBadge，P411 给出 node 字段 schema，构成从观察到抽象的完整证据链。

## 页面拆解

首页区段（EXTRACTED，P334–P357）：Hero（AdaptiveHero/HeadlineSwap 同位切换 outcome/campaign）→ Trusted logos（LogoWall/Marquee）→ Canvas showcase（InteractiveCanvasShowcase，五行业+多 node 产物，本模式主载体）→ Personas（PersonaSwitcher 按角色切用例）→ Pricing（PricingConfigurator）→ FAQ。组件树（P406）：Home → AdaptiveHero → LogoWall → CanvasShowcase(GraphNode[]+Edge[]) → PersonaSwitcher → PricingConfigurator → FAQ。

## 实现配方

报告未取得原站前端源码，以下为 PROPOSED 待验证配方：数据模型 node={title,model,mediaType,asset,x,y}，edge={from,to}，AssetTile 是节点里承载 image/video 的子组件；WebGL/DOM 混合——节点用 DOM（便于放文字和 video），边用 SVG path 或 WebGL line（P411）；入场 Progressive Node Assembly（P413）按依赖顺序 enter，先画 edge 再 reveal output；Persona-driven Canvas Presets（P412）各行业映射一组 nodes/media；色彩中性 UI chrome + 生成媒体承担主要色彩（P380，原等级 STRONG_INFERENCE）。WebGL 库选择、布局算法、节点间距、easing、断点、框架均 UNVERIFIED。

## 来源、证据与权利

原报告 source_id=report-3-sites；原项目 docs/网页创作/2026-09-30-前端源码蒸馏3站.docx，P334–P357、P362–P373、P388–P400、P411–P426，SHA-256 d73649cca6bf1c5c17c7c0730b68e3b57407cb17668e52490d49d70a3b7c498b。原站 URL：https://www.melius.com/。报告原等级：WebGL interactions CONFIRMED（P363）、WebGL Developer 团队 CONFIRMED（P366）、node+image/video 画布语法 CONFIRMED（P369）、Graph visual CONFIRMED（P389）、Motion CONFIRMED 制作方（P393）、Color STRONG_INFERENCE（P381）、Typography CONFIRMED（P385）、框架 UNKNOWN 不得假设 Next.js/React（P372）。本库不升级。许可证未取证，不得断言可复用。

## 变体、关联与项目反馈

关联模式：webgl-product-metaphor（P417）、generated-media-as-color-system（P419）、persona-driven-demo-presets（P420）、progressive-node-assembly-motion（P426）。变体：产品是 agent 编排时，节点承载的 asset 换成终端/卡片/日志，graph 语法不变。反馈：待真实复刻后补充 WebGL vs 纯 SVG 取舍、节点布局手动坐标还是力导向、移动端退化方案实测结论。

## 维护记录

2026-10-04：从 report-3-sites P334–P357、P362–P373、P388–P400、P411–P426 蒸馏（合并单元，含首页结构、制作方技术披露、Token/Motion、Recipes 四段）；保留报告原等级；未访问外站、未运行组件。
