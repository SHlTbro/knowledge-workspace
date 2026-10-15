# 从真实任务到可复用知识

这张图说明外部 Agent 与目标 Vault 的原生工作流如何协作。它不是后台全自动蒸馏服务的架构。不同领域自行定义知识结构、证据与质量检查。

![完整蒸馏流程](distillation.png)

[查看完整 PNG](distillation.png) · [交互 HTML 下载](distillation.html) · [可编辑 JSON](distillation.json) · [双主题 SVG](distillation.svg)

1. 先按真实任务选择已有库；没有适用库时由 Agent 设计类型、目录和规则，用户确认有限文件计划后用 Builder 落盘并登记。
2. 读完整原生规则和索引，在获准素材范围内查重、提炼机制与证据，区分事实、推断和未知。
3. 按该库自己的 Writer/Workflow 写入并执行原生质量门；失败则修复后重试，不把框架收尾当成领域通过。
4. 发布后，让后续任务使用知识、来源和适用边界；若知识不足，仅补真实消费暴露的缺口。

| 关系 | 含义与依据 | 范围 |
| --- | --- | --- |
| 选库/建库 → 规则与索引 | ENTRY.md 的目标规则与用户确认契约；builder.py 的 stage/validate/place | 框架机制与外部 Agent 协作 |
| 规则 → 提炼 | ENTRY.md 要求获准素材、原生索引与完整 Workflow | 方法；不是内置模型调用 |
| 提炼 → 原生质量门 | writer.py 的受控文件变更与 caller-supplied domain_result | 领域检查须由目标库执行 |
| 质量门 → 发布与收尾 | completion.py 保留分层结果与对应来源 SHA | 领域通过与系统完成分别判断 |
| 发布 → 后续消费 | ENTRY.md 的知识与证据消费说明 | 真实效果仍由任务验证 |
| 规则 → 停止 | 缺授权/适用素材不进入执行；ENTRY.md | 不扩大读取或外发范围 |
| 质量门 → 修复 → 提炼 | 原生失败不得跳过；writer.py/domain_result | 由领域原生流程重试 |
| 消费 → 缺口 → 提炼 | 只补实际知识不足；ENTRY.md | 不声称系统自动学习 |

图中箭头表示协作步骤，不表示部署进程。较窄的 README 中请结合上方文字或打开完整图查看；交互 HTML 需下载本机打开，GitHub 文件预览不会执行。
