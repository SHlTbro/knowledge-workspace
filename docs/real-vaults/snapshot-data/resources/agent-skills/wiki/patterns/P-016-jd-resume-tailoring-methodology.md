> 状态：landed（owner 批复 2026-09-25 批①④A⑤，attempt-1；lifecycle B 案快照；蒸馏批次 auto-exec-dispatch-distill-top5-20260924）
> 产出单：auto-exec-dispatch-distill-top5（2026-09-24）｜蒸馏前 5 之 Resume-Matcher 源

---
domain: rewriting
tags: [pattern, jd-matching, resume-tailoring, anti-fabrication, multi-pass-refinement, diff-editing, llm-engineering]
description: 当 skill 需要做「JD↔简历匹配/定向改写」或任何「以源文档为真相源、让 LLM 定向改写文档」的任务时使用（保真改写方法论域，非结构化输出协议非 skill 写法）：master 真相源契约（改写后逐字段对源校验，伪造即违例）；关键词可注入性分区（JD 关键词先按 master 是否含证据分为可注入/不可注入，禁止无证据注入）；LLM 提案→确定性后处理的多遍流水（LLM 只提案，清洗/校验由确定性代码强制兜底）；diff 定向编辑（改写以逐条变更+原文逐字回执交付，可验证可回滚）；编辑强度三档与真相规则联动。触发词：JD 匹配、简历定制、改写保真、防伪造、关键词注入、diff 编辑、master 简历、truthfulness。不适用：单次 LLM 调用的解析重试协议（P-015）、skill 文本写法（P-009）、渐进披露（P-011）。
---

# P-016 保真定向改写方法论（srbhr/Resume-Matcher 对照蒸馏：master 真相源契约·关键词可注入性分区·多遍 LLM/确定性流水·diff 定向编辑·强度三档）

> id: P-016（landed 2026-09-25，revision rev-1；vault③ wiki/patterns/ 本体）
> **来源**：srbhr/Resume-Matcher 快照 `[本机绝对路径已隐藏]`（下称 `SO:`；README.md 301 行 + apps/backend 核心约 6,300 行，通读 README 全文 + services/refiner.py 全文 848 行 + services/improver.py 头 90 行+注入节 + services/parser.py 头 60 行 + llm.py complete_json 节 + prompts/templates.py 真相规则节与 diff 节 + services/ats.py 结构）。
> **许可事实锚**：根 `SO:LICENSE`（Apache-2.0，README badge 同）在案；本卡仅取方法论，不搬文本资产。
> **置信度声明**：EXTRACTED=源文可指；INFERRED=已写依据；UNVERIFIED=0。厂商宣传（27k+ stars、赞助商表）零入论断。

## 一、这张卡解决什么

「把 A 文档向 B 需求定向改写」是 resume-tailor 类 skill 的核心动作，其特有失败模式是**伪造**：LLM 为提高匹配度编造用户没有的技能/数字/经历。Resume-Matcher 的价值不在「会不会用 LLM 改简历」，而在**系统性地把伪造变成可检测、可阻断、可回滚的工程对象**。五条纪律直接服务 resume-tailor 与 job-jd-distiller 的设计。

## 二、五条纪律（EXTRACTED 溯源）

### 规则 A：master 真相源契约（EXTRACTED）
- 改写结果逐项对 master 校验：技能/认证/公司必须在 master 中存在，否则记 AlignmentViolation（SO:apps/backend/app/services/refiner.py:349-379 validate_master_alignment docstring "Verify tailored resume doesn't contain fabricated content" + :175 注释 `LLM-008: Alignment validation is MANDATORY - not optional fallback`——校验是强制步不是可选兜底）。
- prompt 侧同步硬声明：9 条 CRITICAL TRUTHFULNESS RULES（不添技能/不造数字/不改职级/不改日期/原项必留，SO:apps/backend/app/prompts/templates.py:211-224 逐字）。
- **提炼（INFERRED）**：真相约束必须**双层发布**——prompt 里写禁令（软）、代码里做逐字段对源校验（硬）；只写 prompt 不写校验=把保真押在模型自觉上，属事故设计。JD 明文出现的技能是唯一合法新增白名单（`_extract_jd_skill_keys` 提取"required/preferred skills 且字面在 JD 中出现"者，SO:refiner.py:82-99，传作 `allowed_new_skills` SO:refiner.py:181-185）。

### 规则 B：关键词可注入性分区（EXTRACTED）
JD 关键词先过证据审查再谈注入：缺失关键词分 `injectable`（master 里确有证据，可注入）与 `non_injectable`（master 无证据，禁止注入），并分别给出 current/potential 两个匹配率（SO:refiner.py:240-289 analyze_keyword_gaps，:270-276 分区核心）。
- **提炼（INFERRED）**：「提高匹配率」的正确姿势不是逼 LLM 硬塞关键词，而是先做证据分区、把匹配率上限定义为**有证据部分的天花板**（potential_match 挖尽即止）——防指标造假的同时给出诚实的优化边界。

### 规则 C：LLM 提案→确定性后处理多遍流水（EXTRACTED）
三遍结构，LLM 只占第一遍，其余全是确定性代码：
1. 关键词注入（唯一 LLM 改写遍，SO:refiner.py:132-157）；
2. AI 腔清除——本地黑名单替换、零 LLM 调用，且 JD 中出现的短语受保护不被删（SO:refiner.py:164-172 + :292-346 remove_ai_phrases）；
3. 对齐校验+修复+**复验**（修复后再跑一次 validate_master_alignment 数清剩余 critical 违例，SO:refiner.py:174-216）。
- 另一条硬规则：关键词写入是「最后一个整简历作者」，其后立即重放真相源合同 finalize_ai_resume，保证后续确定性清洗不受污染（SO:refiner.py:159-162 注释逐字）。
- **提炼（INFERRED）**：LLM 输出永远当作「提案」而非「成品」；整流水按「每遍后立即重放不变式」组织，而不是全做完再总检。

### 规则 D：diff 定向编辑而非整篇重写（EXTRACTED）
改写以变更列表交付，每条必须携带原文逐字回执：`"5. Each change MUST include the original text (copied exactly) so it can be verified"` + 白名单 PATHS（summary/具体 bullet 下标/skills 重排等）+ 禁改区（personalInfo/日期/公司名，SO:apps/backend/app/prompts/templates.py:527-560 DIFF_IMPROVE_PROMPT 规则 1-12，逐字 :534；策略按档位注入 :486-490）。
- **提炼（INFERRED）**：diff 形态给保真改写三个免费属性——可验证（原文回执可 grep）、可回滚（逐条拒绝）、可审计（每条带 why）。整篇重写则三者全失。

### 规则 E：编辑强度三档与真相规则联动（EXTRACTED）
nudge/keywords/full 三档，档位差异落在一附加禁令：nudge 不许加新 bullet、keywords 只许改写、full 可扩写但禁造新职责（SO:templates.py:231-241 CRITICAL_TRUTHFULNESS_RULES 字典 + :486-490 DIFF_STRATEGY_INSTRUCTIONS）。
- **提炼（INFERRED）**：「改多狠」是一个显式档位参数，且每档配自己的真相边界；不给档位=用户预期与模型行为错配的常发源。

## 三、相邻区分声明（合并优先律）

- **对 P-015（结构化输出重试环）**：P-015 管**单次调用**的解析-验证-回灌协议（传输层可靠性）；本卡管**任务级**的保真改写流水（语义层防伪造）。resume-tailor 同时消费两者：单次提取套 P-015，改写流水套本卡。互挂不合并。
- **对 P-009（skill 写法/完成判据）**：P-009 的 Done when 是步骤级判据写法；本卡是特定任务域（保真改写）的域方法论，非写法面。
- **对 P-013（品味守恒）**：相邻点=都讲「不该动的别动」；P-013 对象=产出物审美，本卡对象=事实真实性（可逐字段机检），对象与手段（机检 vs 审美负清单）均不同。
- **对 P-006**：建卡查重已实跑——"简历|resume|JD|truthfulness" 于 wiki/patterns/ 全目录零同主题命中（2026-09-24）。
- **编号对位**：取 index.md:44 下一可用序列 P-016（P-015 同批在先，P-008 预留不占）。

## 四、三律自检

| 律 | 合规 |
|---|---|
| 溯源必带 | ✅ 五条规则带 SO:file:line（共 14 处锚，报告附回源 grep 验真 2 锚） |
| 置信度三级 | ✅ EXTRACTED/INFERRED 分级标注，UNVERIFIED=0 |
| 合并优先 | ✅ 与 P-015/P-009/P-013 逐卡裁决不合并（§三）；README 厂商宣传零入论断 |

## 五、编排层批判（源库自身缺陷，采卡时规避）
- improver.py 单文件 1,529 行混装注入清洗/验证/策略分派/diff 应用（SO:improver.py 全件）——skill-ization 时必须拆，勿照搬文件组织。
- 关键词注入失败被 `logger.warning` 后静默回滚、该遍不计入 passes（SO:refiner.py:153-157）——降级路径无用户可见信号，采卡时降级必须显式上报。
- MAX_JD_LENGTH=2000 硬截断 JD（SO:refiner.py:37-38）——长 JD 静默丢真需求；阈值应为配置并显式告知。
- 通用重试层内嵌厂商特判（azure_foundry 降 reasoning effort、opencode zen no_think，SO:app/llm.py:1574-1597 注释块）——provider 泄漏进通用层，采方法论时按 P-010 配置治理面隔离。

## 六、迁移边界
本卡适用域=「以源文档为真相源、向明确需求定向改写」（resume-tailor/JD 匹配类任务）；自由创作（无真相源可对）不适用——真相源契约无从谈起；真相源不可逐字段机检时（纯审美目标），保真面让位于 P-013 品味守恒，本卡仅保留 diff 交付形态与档位参数两条；迁移成本评估：换真相源类型（代码/文档/数据表）时五条纪律全部可平移，无需改构。
