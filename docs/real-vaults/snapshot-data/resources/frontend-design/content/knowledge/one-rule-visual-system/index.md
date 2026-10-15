# 单一视觉母题贯穿整站

- 用途：Pattern / 设计系统方法（个人品牌/内容站）
- 页面任务与交互目的：用一条可重复的视觉规则（巨型单词 + 标志性对象）贯穿所有栏目，建立强记忆点与整站一致性。
- 风格、查找词与实现约束：giant-type、prop-hero、one-rule-system、collage、personal-brand、concept-consistency；Webflow/WebGL/Rive/Motion；精确色值未取证。
- 摘要（EXTRACTED/INFERRED）：Trevor Noah 站用"巨大粉色单词 + 深蓝背景 + 与栏目相关的实体/剪贴对象"一条规则管全站；2D 素材靠 peeling/空间层次获得 3D 感，对象与文字穿插但不喧宾夺主。
- 适用（INFERRED）：个人品牌、播客/内容栏目、名人/意见领袖站；栏目多但需要一眼可识别的品牌。
- 不适用（INFERRED）：需要多套差异化视觉的大型多品牌矩阵；工具型产品（一致性来自组件而非母题）。
- 关键未知（UNVERIFIED）：粉色精确 hex、深蓝 hex、peeling 实现细节、Rive 动画参数、字体均未取证。
- 主要证据结论（EXTRACTED，二手报告层）：P074"一条视觉规则管全站：巨大粉色单词+深蓝背景+栏目相关实体/剪贴对象，强记忆点来自系统化重复而非每页换风格"；P079"设计系统不是组件统一，而是概念统一"。报告原等级见证据文件。
- 证据读取路径（Vault 相对）：content/knowledge/one-rule-visual-system/evidence/report-20-cases-p070-p080.md

## 机制与理由

报告（EXTRACTED，P074/P079）的核心主张是"概念统一 > 组件统一"：不靠每页换风格求丰富，而靠同一母题在不同栏目换"单词 + 对象"两个变量制造变化。整理者推断（INFERRED）这对 Agent 生成一致风格尤其有用——把母题抽象成"栏目词 + 标志性对象"的生成槽位，比约束每个组件样式更稳。P075 补充了深度手法：2D 拼贴靠 peeling/遮挡穿插产生 3D 感，且刻意"可玩但不喧宾夺主"。

## 页面拆解（EXTRACTED，P076）

单词式 Hero → 最新内容 → 媒体 → About → 动态时间线 → Books/Shows 等分支。

## 实现配方

- 已观察实现：未取得一手源码；P077 记 Webflow、WebGL、3D、Rive、Motion（OFF+BRAND 案例列出）。
- 建议实现（PROPOSED）：固定一套底色 + 一个巨型字重；每栏目只换两件事——栏目大词、与该栏目相关的一个剪贴/实体对象；对象与文字做轻微遮挡/穿插；其余装饰全站收敛。
- 错误边界（PROPOSED）：母题规则必须真正全站一致，破规则处要有明确理由；对象不得压过文字可读性。
- 验证：未运行。

## 来源、证据与权利

source_id=report-20-cases；原工件见证据文件。站点 URL：https://www.trevornoah.com/（P072）。证据 evidence/report-20-cases-p070-p080.md（P070–P080）。
权利（P080 EXTRACTED）：人物肖像、品牌内容、媒体素材不可复用；只学组合规则。

## 变体、关联与项目反馈

- 母题变量化：栏目词 + 标志性对象 → 动态 Hero 生成器（P079）。
- 关联：与 shader-hero-abstract、spotlight-hero-background 同属 Hero 策略，但本单元是全站级母题而非单屏背景。

## 维护记录

- 整理者与日期：distiller，2026-10-04。
- 本次变化：从 report-20-cases P070–P080 蒸馏。
- 待补证：精确配色、字体、peeling/Rive 实现。
