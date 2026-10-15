# 编号步骤叙事型产品落地页

- 用途：Pattern（产品落地页信息架构 / 功能叙事节奏）
- 页面任务与交互目的：把复杂、多步骤的 AI/SaaS 能力讲清楚，让用户"像读工作流一样"看懂产品做什么，而不是用一堆功能卡糊满屏。
- 风格、查找词与实现约束：feature-sequencing、product-storytelling、manifesto-layout、step-narrative、动词型段落、scroll-as-walkthrough、ai-saas、agentic-ui；框架与精确参数未取证。
- 摘要（EXTRACTED/INFERRED）：主样本 illoca 把核心句"Design at the speed of thought, not software"展开成连续的动词型能力段落（sketch→plan、prompt→layout），随滚动逐段解释；变体 The Tie-break 把转化目标藏进"开场→规则→玩法→反馈→产品露出→收束"的体验步骤。两案共同点：用连续步骤替代并列功能列表。
- 适用（INFERRED）：能力链路长、非标准化的 AI/SaaS、建筑/工程类产品；需要先建立世界观再给 CTA 的发布页/联名活动页。
- 不适用（INFERRED）：用户任务是"快速查一个功能是否存在"的工具型产品；步骤少于 3 步、并列功能即可讲清的页面。
- 关键未知（UNVERIFIED）：illoca 前端框架未公开；两案的滚动触发阈值、easing、断点、文案排版细节均未取证；The Tie-break 多人同步栈未核实。
- 主要证据结论（EXTRACTED，二手报告层）：illoca P063–P065 明确"连续动词型能力段落 + 5 个能力场景 + sketch→plan/prompt→layout 状态变换"；The Tie-break P030 给出六步可拆结构，P033 主张"把转化目标藏进体验机制"。报告原等级见各证据文件。
- 证据读取路径（Vault 相对）：
  - content/knowledge/narrative-step-product-story/evidence/report-20-cases-illoca-steps.md
  - content/knowledge/narrative-step-product-story/evidence/report-20-cases-tiebreak-steps.md

## 机制与理由

并列功能卡的默认假设是"用户已理解产品，只在比对参数"。当产品本身是一个陌生的工作流时（illoca 是 AI 建筑/BIM/CAD 产品），并列卡片反而放大认知负担。报告（EXTRACTED，P063/P068）给出的解法是：先用一句宣言定调，再把能力拆成有先后顺序、带动词的连续段落，每段对应一次状态变换（sketch→plan、prompt→layout），让滚动本身成为"跟着产品走一遍流程"。

变体 The Tie-break（EXTRACTED，P029–P033）把同样的"步骤化"思想推到游戏化极端：转化不是额外挂一个 CTA，而是嵌在步骤循环里（击球→得分→Look 解锁→产品露出）。整理者推断（INFERRED）这是同一模式的两端——illoca 是"阅读式步骤"，The Tie-break 是"操作式步骤"，内核都是"按顺序经历"而非"并排比较"。

## 页面拆解

- illoca（P065 EXTRACTED）：核心主张 → 5 个能力场景 → Open Letter → 定价 → FAQ → CTA。
- The Tie-break（P030 EXTRACTED）：开场/引导 → 游戏规则 → 双人/互动玩法 → 得分反馈 → Look/产品露出 → 品牌收束。
- 字体/配色/精确间距：UNKNOWN（未取证，不臆测）。

## 实现配方

- 已观察实现：未取得（无一手源码，仅报告二手描述）。
- 建议实现（PROPOSED）：Hero 放一句宣言式主句；其后每个步骤占一屏或一区，标题用动词（Write→Plan→Ship 式），正文配该步骤的前后状态对比图/演示；滚动到该区再触发该步演示；末区才放定价/FAQ/CTA。
- 错误边界（PROPOSED）：步骤不可多于用户记忆容量；每步必须有可见的状态变化，否则退化为长文案；不得让 CTA 出现在步骤被理解之前。
- 验证：未运行。

## 来源、证据与权利

source_id=report-20-cases；原工件 docs/网页创作/2026-09-30-前端设计案例20选.docx，SHA-256 见各证据文件。
- illoca：https://illoca.unseen.co/（P061），证据 evidence/report-20-cases-illoca-steps.md（P059–P069）。
- The Tie-break：https://thetiebreak.merci-michel.com/（P026），证据 evidence/report-20-cases-tiebreak-steps.md（P024–P034）。
权利（P069/P034 EXTRACTED）：仅复刻信息架构与演示节奏；不复制文案、品牌、产品演示资产、Coco Gauff 形象或游戏创意。许可未取证，不得断言可商用。

## 变体、关联与项目反馈

- 阅读式步骤（illoca）vs 操作/游戏式步骤（The Tie-break）。
- 关联：webgl-scroll-cinema（同为滚动叙事，但那是电影式镜头，本单元是工作流式步骤）。

## 维护记录

- 整理者与日期：distiller，2026-10-04。
- 本次变化：从 report-20-cases 蒸馏合并单元，两来源证据分别保留。
- 待补证：illoca 前端框架、滚动动效参数、两案降级/reduced-motion 行为。
