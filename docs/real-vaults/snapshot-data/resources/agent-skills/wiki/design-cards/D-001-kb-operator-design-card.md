# D-001 kb-operator 设计方案卡

> **蒸馏对象**：vault① `skills/kb-operator` v0.1.0（internal 通道，2026-09-07 入库）
> **蒸馏日期**：2026-09-07 ｜ **蒸馏者**：线 A（豆包）
> **状态**：✅ 2026-09-13 自 staging 迁移入库（P5-T3），编号 D-001 定稿
> **合并优先查重**：staging 空库，vault③ 未建库（迁移时）→ 新建（非增补）。查重动作留痕：`Get-ChildItem staging` 返回空；迁移时 vault③ design-cards/ 仅 .gitkeep（T2 骨架空库实证），无同主题卡。
> **重建说明**：本卡为 LA-6 验收 FAIL 后重建版（首版因 Write 工具并行调用未落盘，已 log 勘误）。

---

## 一、结构设计决策

### 1.1 渐进披露三层结构
- **主文档（SKILL.md）**：56 行（≤150 行预算），只留路由表 + 红线 + 标准动作速查 + 兼容性声明。细节全部下放 references/。
  - 溯源：`skills/kb-operator/SKILL.md:18-28`（七章节路由表）、`:30-37`（红线）、`:39-44`（标准动作）
  - 置信度：**EXTRACTED**（原文可查）
- **references/ 分节文件**：七章节各一文件（01~07），主文档通过路由表显式指向。
  - 溯源：`skills/kb-operator/SKILL.md:20-28`（路由表逐一列出 references 文件名）
  - 置信度：**EXTRACTED**
- **设计意图**：主文档是"操作宪法速查卡"，agent 加载后先看红线和标准动作，需要细节时才读 references/。避免单文件过长导致 compaction 后丢失关键红线。
  - 置信度：**INFERRED**（推理依据：SKILL.md:33 明确提到"长会话 compaction 后 skill bootstrap 可能丢失"，主文档只留核心红线是对此的对策）

### 1.2 frontmatter 规范适配
- **允许字段**：只用 agentskills 规范允许的 6 字段（name/description/compatibility/license/metadata/allowed-tools），不私加顶层字段。
  - 溯源：`skills/kb-operator/SKILL.md:1-11`（实际 frontmatter）
  - 置信度：**EXTRACTED**
- **version 移入 metadata**：规范不允许顶层 `version` 字段，改用 `metadata.version: "0.1.0"`。
  - 溯源：`skills/kb-operator/SKILL.md:7`
  - 置信度：**EXTRACTED**
- **compatibility 用字符串**：skills-ref 校验要求 compatibility 为 string，不接受 YAML 列表。
  - 溯源：`skills/kb-operator/SKILL.md:4`（`compatibility: "codex, opencode, Zcode, 豆包, claude-code"`）
  - 置信度：**EXTRACTED**
- **metadata 扩展键**：source_channel / version / fidelity / scan_date / registry_status，全走 metadata（规范允许的 string→string map）。
  - 溯源：`skills/kb-operator/SKILL.md:5-10`
  - 置信度：**EXTRACTED**

### 1.3 声明式边界
- **零调度代码**：SKILL.md 和 references/ 全是规则与标准动作，无 Python/bash 调度脚本。
  - 溯源：`skills/kb-operator/SKILL.md:16`（"声明式边界：只写规则与标准动作，零 Python/bash 调度代码"）
  - 置信度：**EXTRACTED**
- **定时能力外包**：做梦整理的"每周日 03:00"不造 cron/调度器，而是 agent 加载后调用平台自身自动化（Claude hooks / opencode 插件 / TT loop）。
  - 溯源：`skills/kb-operator/SKILL.md:16`、`references/04-dream-tidy.md`
  - 置信度：**EXTRACTED**

---

## 二、触发词设计

### 2.1 description 写法
- **场景描述 + 显式触发词列表**：description 先写"当 agent 需要对 vault 执行 X/Y/Z 操作时加载"，再列显式触发词。
  - 溯源：`skills/kb-operator/SKILL.md:3`
  - 置信度：**EXTRACTED**
- **触发词清单**：kb-operator / 知识库操作 / skill 入库 / vault 写入 / 多库路由 / 做梦整理 / 会话恢复。
  - 溯源：`skills/kb-operator/SKILL.md:3`
  - 置信度：**EXTRACTED**
- **设计意图**：触发词覆盖"操作类"意图（写入/入库/路由/整理/恢复），与 vault① 其他 AA skill 的"内容生产类"触发词（热点采集/动效生成/字幕封面）形成域隔离。
  - 置信度：**INFERRED**（推理依据：AA skill 的 description 均为内容生产场景，kb-operator 为操作规范场景，二者无重叠）

---

## 三、权限设计决策

### 3.1 红线全部写进正文（非 allowed-tools）
- **6 条红线**：权限边界不靠 allowed-tools / 会话恢复首动作重读 / 写前快照 / AGENTS.md 不可写 / blocked 不可删 / _shared-skills 只读。
  - 溯源：`skills/kb-operator/SKILL.md:30-37`
  - 置信度：**EXTRACTED**
- **设计意图**：allowed-tools 是规范实验性位，opencode 等客户端静默忽略。权限红线必须写进正文并由 vault-lint.sh 机验，不能寄托在字段上。
  - 溯源：`skills/kb-operator/SKILL.md:32`（"allowed-tools 不得作为权限边界"）
  - 置信度：**EXTRACTED**

### 3.2 单写者制
- **REGISTRY 单写者 = 入库管线**：其他 agent 不得直接编辑 REGISTRY.md，需变更走入库/退役流程。
  - 溯源：`references/01-read-write-permissions.md`（skills/REGISTRY.md 行）
  - 置信度：**EXTRACTED**
- **标签租约单写者**：skill-design（线A）/ skill-security（线A+gate）/ skill-registry（入库管线），三标签各有单写者。
  - 溯源：`references/03-domain-isolation.md`（标签租约表）
  - 置信度：**EXTRACTED**

### 3.3 不可删/只读边界
- **blocked skill 不可删**：REGISTRY 状态=blocked 的目录只能保留并标注，不得删除。
  - 溯源：`skills/kb-operator/SKILL.md:36`
  - 置信度：**EXTRACTED**
- **_shared-skills 只读引用**：各 vault 不得直接写入共享库，写操作仅限 F10 治理管线。
  - 溯源：`skills/kb-operator/SKILL.md:37`
  - 置信度：**EXTRACTED**

---

## 四、调用保真设计（F6 双约束）

### 4.1 allowed-tools 静默忽略对策
- **对策三件套**：① 红线写正文+lint 机验；② compatibility 如实声明；③ metadata.fidelity 分级（verified/pending/best-effort）。
  - 溯源：`references/06-call-fidelity.md:6-11`
  - 置信度：**EXTRACTED**

### 4.2 post-compaction 丢失对策
- **对策三件套**：① 关键状态外置到 vault 文件（REGISTRY/快照/提案/设计方案文档）；② 恢复首动作=重读本 skill+查 REGISTRY；③ 有 hook 平台配重注入，无 hook 平台降级声明。
  - 溯源：`skills/kb-operator/SKILL.md:33`、`references/06-call-fidelity.md:15-20`
  - 置信度：**EXTRACTED**

### 4.3 保真分级声明
- **四平台 verified**：codex / opencode / Zcode / 豆包。
- **claude-code pending**：待加入测试矩阵，当前 best-effort。
- **其余平台不承诺**：按 AGENTS.md §1 降级声明。
  - 溯源：`skills/kb-operator/SKILL.md:48-50`、`:8`（metadata.fidelity）
  - 置信度：**EXTRACTED**

---

## 五、anti-patterns 规避

| anti-pattern | kb-operator 的规避方式 | 溯源 |
|---|---|---|
| 把权限寄托在 allowed-tools | 红线全写正文+lint 机验，明确"allowed-tools 不得作为权限边界" | SKILL.md:32 |
| 造调度器/cron | 声明式零代码，定时能力外包给平台自动化 | SKILL.md:16 |
| 依赖会话内存存状态 | 关键状态全外置 vault 文件，恢复首动作重读 | SKILL.md:33 |
| 单文件过长导致 compaction 丢失 | 渐进披露：主文档 56 行只留红线，细节下放 references/ | SKILL.md:18-28 |
| 直接改库（整理/归档） | 做梦整理提案制，不直接改库，等用户批准 | references/04 |
| 私改规范字段 | 扩展全走 metadata，不私加顶层字段 | SKILL.md:5-10 |

---

## 六、蒸馏三律合规自检

| 律 | 合规情况 |
|---|---|
| 溯源必带 | ✅ 每条主张带 `skills/kb-operator/SKILL.md:<行>` 或 `references/xx.md`，共 17+ 处溯源 |
| 置信度标注 | ✅ EXTRACTED（原文可查）/ INFERRED（写推理依据），无 UNVERIFIED 进入正文论断 |
| 合并优先 | ✅ staging 空库+ vault③ 未建，查重动作留痕（本卡顶部） |

---

## 七、迁移回执（P5-T3）

1. ✅ 卡迁移至 vault③ 设计方案卡区，编号 D-001 定稿。
2. ✅ vault③ index.md 加卡指针 + log.md 加迁移回执。
3. ✅ 卡内"暂挂 staging"标注已替换为迁移留痕（见卡头状态行）。
4. ✅ vault③ 无同主题卡（design-cards/ 仅 .gitkeep），直接落位，未触发合并。
