---
tags: [design-card, cangjie-distilled]
---

# D-002 tdd-for-skills 设计方案卡

> **蒸馏对象**：`_shared-skills/skill-authoring` v0.1.0（MIT）——SKILL.md + DESIGN.md + references/01..04
> **蒸馏日期**：2026-09-13 ｜ **蒸馏者**：线 A（P5-T3）
> **蒸馏引擎**：cangjie-skill v2.5.0（MIT，commit `34e34bc5c7eb1c7d6cae9f84a9bcc62acb2a971b`），RIA-TV++ 七阶段；doctor PASS exit 0
> **合并优先查重**：`wiki/design-cards/` 仅 .gitkeep（T2 空库），无同主题卡 → 新建。查重留痕：T2 骨架 `git status` 实证 design-cards/ 空。
> **编号说明**：D-001 保留给 staging 迁移；本卡为 cangjie 端到端验证产物，占 D-002。
> **置信度声明**：EXTRACTED=原文可指；INFERRED=已写推理依据；UNVERIFIED 不进正文论断。

---

## 一、这张卡解决什么

把"通用 TDD"改造成"skill 专用 TDD"：不靠单元测试，而靠**行为探针**证明一个 agent skill 真的生效、且不会被绕过。它是本体系新建/改 skill 时的验证闭环。

## 二、RIA++ 六段（cangjie 阶段 2 产物）

### R — 原文（≤150 字/段）
> "RED：构造一个应该触发 skill 的场景，派子 agent 执行，**不加载 skill**，观察子 agent 是否做错/绕过……GREEN：只加刚好能通过 RED 场景的规则，加载 skill 重跑……REFACTOR：构造 skill 可能被绕过的边界场景。"
— `_shared-skills/skill-authoring/references/04-testing-with-subagents.md:8-22`　置信度 **EXTRACTED**
> "软件 TDD RED→写压力场景看 skill 失效；GREEN→写最小 skill 通过场景；REFACTOR→补漏洞保持通过。"
— `references/01-skill-anatomy.md:11-15`　置信度 **EXTRACTED**

### I — 自述（用自己的话）
先假装 skill 不存在，派 agent 去干那类活，录下它实际会犯的错（绕路、合理化、漏红线）——那就是 skill 必须解决的真问题。然后只写最少规则让加载 skill 的同一个 agent 做对。最后故意给空子钻（任务模糊/时间紧/只沾一点边/跨平台差异），绕过了就用三招堵死。产物不是测试报告，而是"无 skill 时会错在哪"的证据表，证明规则是被需求逼出来的。
　置信度 **INFERRED**（依据：R 段原文改写，非照搬）

### A1 — 库中案例（作者亲自用过）
- **kb-operator**："红线写正文而非 allowed-tools"一条的 RED 证据 = "客户端静默忽略 allowed-tools"这一已观测失效模式。溯源：D-001 §3.1（跨库 `D-001`）。**EXTRACTED**
- **skill-authoring 自举**：LA-11 从 26KB 真源浓缩到 45 行主文档 = GREEN"最小规则"实践。溯源：`DESIGN.md:19`。**EXTRACTED**
- **压力矩阵**：references/04:23-31 列五类绕过场景（合理化/上下文不足/时间压力/部分适用/平台差异）。**EXTRACTED**

### A2 — 何时用（触发）
- 场景：①新写/改 skill 后证明它生效；②怀疑某规则会被钻空子；③评审 skill 的 RED 证据；④把经验固化成 skill 前先看清失效模式。
- 语言信号："测测这个 skill / 会不会被绕过 / 先写个测试场景 / 压一下 / refactor this skill"。
- 相邻区分：**P-001 SDO** 管"description 怎么写才被发现"；**三闸摘要卡**管入库前静态检查；本卡管动态行为探针。**EXTRACTED/INFERRED 混合**

### E — 执行步骤（带判停）
1. **RED**：写"应触发 skill"的场景；派 agent **不加载 skill** 跑；记录可复现的错误动作。判停：不加载时它也做对 → 场景不成立，换。
2. **GREEN**：只加刚好通过的规则；加载 skill 重跑同场景，确认做对。判停：需 >5 条规则才通过 → 拆 skill 或场景选窄。
3. **REFACTOR**：压力矩阵选 ≥3 绕过场景各跑一次；每被绕过补一招（显式否定"不要做 X"/ 逃避对照表 / Red Flag STOP 信号）；补完重跑 GREEN 确认仍绿。
4. **入库门**：skill-gate 三闸 + vault-lint PASS，勾完测试清单 6 项（references/04:47-53）。
　置信度 **EXTRACTED**（步骤自 references/04 三阶段，判停点为本卡 INFERRED 补）

### B — 边界（何时别用）
- 别用：纯信息查询（无行为可测）；一次性任务（references/02 负清单）；<3 条实质规则（写进 AGENTS.md 即可）。
- 失败模式：V1 作弊（同一失效换说法）；RED 写成"加载后也错"；只测 happy path。
- 易混："派子 agent 跑一遍"只是冒烟，不是 TDD；TDD 的标志是先记录无 skill 时的失败模式。
　置信度 **EXTRACTED**（B 段清单）+ **INFERRED**（易混辨析）

---

## 三、三重验证留痕（cangjie V1/V2/V3）
- **V1 跨域 ✅**：SKILL.md:24（铁律）/ references/01:11-15（映射表）/ references/04:6-37（操作手册）三处独立佐证。
- **V2 预测力 ✅**：新问"给已上线 skill 补规则怎么验"→推得"在已 GREEN 库上补 RED 绕过场景，漏了才补"。
- **V3 独特性 ✅**："先写测试"是常识；"用合理化逃避场景做 skill 的 RED + 三招补漏"不是。
- 完整判定：`artifacts/cangjie-run/books/skill-authoring/verified.md`。

## 四、盲测留痕
- test-prompts 7 条（3 正 4 负），文档级触发分类 7/7 一致；行为回放（真子 agent）记 **[待补]**。
- 留痕：`artifacts/cangjie-run/books/skill-authoring/{test-prompts.json,blindtest-output.md}`。

## 五、蒸馏三律合规自检
| 律 | 合规 |
|---|---|
| 溯源必带 | ✅ 每条主张带 `references/xx.md:行` 或跨库 `D-001` |
| 置信度三级 | ✅ EXTRACTED/INFERRED 标注，无 UNVERIFIED 进论断 |
| 合并优先 | ✅ T2 空库实证，查重留痕 |
| 蒸馏≠搬运 | ✅ I/E 段为可执行浓缩，R 段原文引用 ≤150 字 |

## 六、also_read（跨库引用，禁双链）
- `[[P-001-sdo-description-writing|P-001]]` SDO 描述写法（待 T3 落位）
- `[[D-001-kb-operator-design-card|D-001]]` kb-operator 设计方案卡（红线写正文同源）
- 三闸契约摘要卡（待 T3 落位）
- 引擎：cangjie-skill v2.5.0 @34e34bc（MIT，不复制入本库）
