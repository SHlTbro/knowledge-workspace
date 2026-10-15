# 无限循环连续信息流（Logo/评价墙）

- 用途：Component / Recipe（社会证明展示）
- 页面任务与交互目的：用连续滚动的信息流表达"数量感"——客户 Logo、评价、工具生态、素材墙，而不是让用户逐条读完。
- 风格、查找词与实现约束：marquee、infinite-scroll、infinite-loop、social-proof、logo-wall、edge-mask、reviews；React 组件；精确速度未取证。
- 摘要（EXTRACTED/INFERRED）：Magic UI Marquee 把内容队列重复后做 translate 无缝循环，配边缘渐隐 mask；支持 reverse、pauseOnHover、vertical，3D 示例用 perspective 形成空间墙。
- 适用（INFERRED）：客户 Logo 墙、评价滚动、工具/素材生态展示——只需传达"很多"，不需要逐条精读。
- 不适用（INFERRED）：承载用户必须读完/读完才能决策的核心信息（P217 明确边界）；信息条数少、并排即可放下的场景。
- 关键未知（UNVERIFIED）：循环速度 px/s、repeat 份数、3D perspective 参数、性能与 reduced-motion 行为、Magic UI 许可细节未独立核验。
- 主要证据结论（EXTRACTED，二手报告层）：P212"边缘渐隐比生硬裁剪更自然"；P213"无限循环，可 reverse/pauseOnHover/vertical"；P214 结构 overflow hidden → 重复队列 → translate loop → edge mask；P215 props 含 reverse/pauseOnHover/vertical/repeat。报告原等级见证据文件。
- 证据读取路径（Vault 相对）：content/knowledge/marquee-infinite-flow/evidence/report-20-cases-p209-p219.md

## 机制与理由

报告（EXTRACTED，P212）把 marquee 的用途锚定在"数量感"：连续滚动暗示供给充足，比静态网格更能传递生态规模。关键细节是边缘处理（P212/P214）——用 edge mask 渐隐代替硬切，循环才不被察觉。报告同时给出一条易被忽略的选型红线（EXTRACTED，P217）：marquee 只用于"很多"，不用于"必读"。整理者推断（INFERRED）这应直接写进 Agent 规则，避免把定价、法律条款等塞进滚动带。

## 页面拆解（EXTRACTED，P214）

overflow hidden 容器 → 重复内容队列 → translate loop 动画 → 两侧 edge mask 渐隐。

## 实现配方

- 已观察实现：未取得一手源码；P215 记 props：reverse、pauseOnHover、vertical、repeat。
- 建议实现（PROPOSED）：内容复制两份并排，对容器做一次 translateX 0→-50% 的匀速无限循环；两端 mask-image 渐隐；hover 时暂停；方向可 reverse；纵向换 translateY。
- 错误边界（PROPOSED）：滚动速度必须慢到可扫读、快到不无聊；必须 pauseOnHover；reduced-motion 下降为静态排列；核心文案禁止入带。
- 验证：未运行。

## 来源、证据与权利

source_id=report-20-cases；原工件见证据文件。组件 URL：https://magicui.design/docs/components/marquee（P210）。证据 evidence/report-20-cases-p209-p219.md（P209–P219）。
权利（P218 EXTRACTED）：组件可按 Magic UI 许可复用；客户 Logo/评价需各自取得使用权。许可细节未取证。

## 变体、关联与项目反馈

- 水平 / 垂直 / 3D perspective 空间墙（P209/P213）。
- 关联：常嵌入 Bento Grid 卡片内做局部动效（report P202）。

## 维护记录

- 整理者与日期：distiller，2026-10-04。
- 本次变化：从 report-20-cases P209–P219 蒸馏。
- 待补证：循环速度默认值、许可、reduced-motion。
