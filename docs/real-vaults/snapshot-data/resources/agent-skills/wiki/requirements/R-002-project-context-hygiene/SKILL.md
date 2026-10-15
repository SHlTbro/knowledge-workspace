---
title: "R-002 给项目洗澡：清理代码噪声、过时规则与上下文"
id: R-002
card: R-002
type: requirement-card
status: distilled
tags: [requirement, context-hygiene, project-maintenance, instruction-rationale]
description: "Use when 老项目中的 agent 反复漏需求、读错规则、越界修改，或需要整理 AGENTS.md/CLAUDE.md、陈旧记忆和上下文；不适用于无证据判断服务端模型降级。"
source:
  video: "https://www.bilibili.com/video/BV15Kh66JE18/"
  paper: "https://arxiv.org/html/2608.11095v1"
  transcript: "references/transcript-raw.md"
confidence: "EXTRACTED=视频建议/论文报告/skill 原文；INFERRED=本库落地组合，均注明依据"
created: 2026-10-04
---

# R-002 给项目洗澡：清理代码噪声、过时规则与上下文

> 需求实现卡；消费端先读 §4。需求归纳为 INFERRED：让项目当前事实、指令和 agent 读取范围保持一致；视频/外源蒸馏已完成；project-bath 执行体已发布并做隔离行为验证，未对真实项目清理或测得性能改善。
> 开工消费：P-006 用于主题/编号查重；P-010 承接上下文治理；P-011 承接按需加载；P-014 提醒长度与质量分开测。P-017 保持未占用。

## §1 摘要与文案指针

视频作者九目AI以新旧项目对照的个人经验引出三个动作：清理与加功能分开、只处理指定模块、把规则当代码维护并记录保留理由。完整转写和时间戳在 [原文](references/transcript-raw.md)，逐项蒸馏与事实纠偏在 [视频与论文核验](references/video-distillation.md)。个人对照没有控制模型、工具和任务输入，不能据此排除服务端或其他原因。

视频对应论文研究的是规则增长和指令遵循：+226% 指指令数量增长；23.1% 是一个实验中的相对约束满足率提升，并非代码准确率承诺。保留理由还需失败证据与结果；随便补一句解释不能等同于论文干预。[论文 §3.1 / §4.2 / §4.3](https://arxiv.org/html/2608.11095v1)

## §2 实体与复用清单

| 实体 | 解决哪个子问题 | 证据与去向 |
|---|---|---|
| 视频 BV15Kh66JE18 | 三条清理指令和新旧项目观察 | references/video-distillation.md；作者观点与实证分开 |
| Catastrophic Remembering 论文 v1 | 为何规则只加不删；保留理由应记录什么 | 同上；记录失败、假设、结果，避免无证据叙事 |
| mcollina/skills `init` | AGENTS.md 逐条验真、增量修订、优先修工具根因 | [同类 skill 蒸馏](references/related-skills.md) 第 1 项 |
| `context-degradation` | 区分污染、干扰、串任务和版本冲突 | 同上第 3 项；先移除错误前提再恢复 |
| `context-optimization` | 精简已解决的工具输出，保留可回取引用 | 同上第 5 项；调试中的错误证据保留 |
| `filesystem-context` | 原文外置、薄索引、按需定位读取 | 同上第 4 项；下沉必须能找回 |
| `memory-systems` | 失效标注、历史保留、有效期和冲突处置 | 同上第 2 项；不引入记忆运行时 |
| ECC `strategic-compact` | 阶段边界压缩和先落盘交接 | 同上第 6 项；与 P-010 已有规则 B 对位 |

六个 skill 来自三个仓库，固定提交、许可证与 SHA-256 见 [来源清单](references/source-manifest.json)。本库只存方法论；六件上游本体未安装。组合执行体 project-bath 留共享库，见 §4。

## §3 目标功能方法论

以下流程为 INFERRED 组合，依据视频三指令、论文机制及 §2 六件源码；具体机制已合并入 P-010 增补。

1. **立失败基线**：记一个漏需求/越界/用旧规则的任务，固定需求、模型、配置和范围；清理前保留产物与检查结果。Done when：失败可重放，成功判据已列明；个人感觉不算基线。
2. **限定读写范围**：先查入口与目标模块，只在依赖证据需要时扩范围；本轮不加功能。视频的 800 行是作者启发式，拆分应由职责和可验证行为决定。Done when：有允许路径、排除路径和扩范围理由。
3. **列清理候选**：死代码/重复逻辑/旧注释/重复或矛盾规则分别列证据、风险与建议。无文本引用不等于无运行时使用，动态加载件暂留待查。Done when：候选清单可逐项审核，尚未误删运行行为。
4. **核对并修订规则**：按当前代码、配置、测试与权威文档逐条核实；保留项记触发范围、失败原因和结果，不编造历史。已废止项退出活动入口，必要历史保留。Done when：活动规则无已知事实冲突，保留项有理由/来源，删除有回滚路径。
5. **把细节下沉并接线**：大原文/日志/专用流程放文件，用触发词、路径和检索方式指回；错误摘要只保留已核验事实。Done when：从薄入口能恢复所需证据，不靠读完整仓库才能找到。
6. **重放同任务与关键回归**：长度/上下文负载和需求通过率、越界次数分别报告；收益无证据就不宣称提高。Done when：原失败任务恢复、关键行为不退化、diff 限于约定范围；不满足则回退该项。

## §4 串联与解决方案

| 症状 | 路由 | 最小交付 |
|---|---|---|
| 反复用旧前提或错误摘要 | context-degradation → 已核验状态恢复 | 错误来源与权威来源对照、恢复后的任务结果 |
| AGENTS/CLAUDE 过长过时 | init → P-010 项目指令增补 | 逐条保留/合并/下沉/废止清单与理由 |
| 中途漏需求、工具输出挤占窗口 | context-optimization + filesystem-context → P-011 | 可回取原文、当前目标/约束/未决事项 |
| 跨会话记忆与现状矛盾 | memory-systems → P-010 GC/有效期 | 有效事实、失效历史、来源优先级 |
| 多阶段任务窗口接近耗尽 | strategic-compact → P-010 规则 B | 已验证/已失败/待做三段交接，阶段边界压缩 |

实际操作：先只读审计 → 给出最小可审阅 diff → 按项目授权边界实施 → 重放任务并决定保留或回退。视频里的“确认后再改”是作者建议；已授权的常规可逆工作沿会话授权执行，本库 AGENTS/purpose/冻结契约修改仍沿本地审批规则。

可直接使用的审计请求：本轮只审计指定模块和相关指令文件，不加功能。先列死代码、重复逻辑、与现状不符的规则；每项给证据、风险、处置和回归检查。保留规则说明触发条件、失败原因及验证结果；没有历史证据就明确标注。输出范围有限的 diff，修订后重放原任务。

**执行入口（2026-10-04，当前 0.1.3）**：`[本机绝对路径已隐藏]`，Codex `$project-bath`；本地 tag `project-bath/v0.1.3`。归档与编辑前备份统一 `[本机绝对路径已隐藏]<项目目录>/<批次>/`，项目目录按名称与规范化根路径短哈希固定；禁止 C 盘和项目内分散落点，目标不可用保留原件。规则来自本轮用户要求及 shared:project-bath/SKILL.md 的备份与恢复段；验证见工程区 `sublines/lineA-skill-distill/staging/project-bath-central-archive-20261004/`。

**历史发布（0.1.2，2026-10-04）**：`[本机绝对路径已隐藏]`，Codex `$project-bath`；本地发布 tag `project-bath/v0.1.2`（shared/Vault），运行目录仅自包含 SKILL.md + LICENSE，5209 bytes。执行正文无外链，来源与研究信息保留本卡原 `references/source-manifest.json`；MIT 版权许可独立保存，旧 references 全部文件移入共享库包外 `.snapshots/project-bath-usable-20261004-v0.1.2/retired/project-bath/references/`，旧版全部原字节先备份核验。新 pressure 12 项、green 纯审计 20 文件零写、recovery 6 项与静态闸见工程区 `sublines/lineA-skill-distill/staging/project-bath-usable-20261004/REVIEW.md`；未宣称 token/性能收益。

**历史发布（0.1.0，2026-10-04）**：`[本机绝对路径已隐藏]`，Codex `$project-bath`；安装包仅 SKILL.md + references/checks.md。范围/预算先定，整文件归档、文件内编辑前备份，恢复清单保存本轮差异；优先现有冷归档，否则 .agent-archive/project-bath/<run-id>/，默认不读、不永久删除。例行维护用已有检查基线，真实故障才重放失败。设计/独立基线、两次隔离执行、归档与后续编辑恢复、静态闸记录见工程区 `sublines/lineA-skill-distill/staging/project-bath-build-20261004/REVIEW.md`；行为结果与 token 收益分开，真实消耗数据不可得不估报。 原件置共享库包外 `.snapshots/project-bath-compact-20261004-v0.1.1/`。

## also_read

- [[P-010-ecc-harness-performance|P-010]]：预算、恢复、压缩与项目指令治理的唯一方法论落点。
- [[P-009-engineering-skill-craft|P-009]]：调用轴与生产级写法；[[P-011-anthropics-official-craft|P-011]]：资源分层。
- [[P-014-caveman-token-minimalism|P-014]]：测量保真；[[P-006-card-dedup-quadruple-alignment|P-006]]：建卡查重。
