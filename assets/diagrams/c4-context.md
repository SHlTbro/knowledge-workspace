# 系统边界

知识库系统为外部 Agent 提供共同入口、成员与本机位置解析，以及可选只读 Web。Agent 随后遵循各 Vault 的原生规则和 Workflow；Obsidian 继续承担原生编辑与治理。

![系统边界](c4-context.png)

[交互图下载](c4-context.html) · [可编辑 JSON](c4-context.json) · [C4 Mermaid 源](c4-context.mmd) · [SVG](c4-context.svg)

| 来源 → 目标 | 动作与协议 | 源码证据 | 状态 |
| --- | --- | --- | --- |
| 使用者 → 任务 Agent | 提出任务 | 原 13d92 的 ENTRY.md §0、§5–6 | 已实现的接入契约 |
| 任务 Agent → 知识库系统 | ENTRY / 本机 CLI | tools/kb_entry.py:66 | 已实现 |
| 知识库系统 → 独立 Vault | 定位原生规则、获准读取；本机文件 | tools/kb_entry.py:84、src/kb_core/local_vault_web.py:365 | 已实现 |
| 任务 Agent → 独立 Vault | 按目标原生 Workflow 消费 | 原 13d92 的 ENTRY.md §5–6 | 已实现的调用方式；领域任务能力须各自验证 |
| 使用者 → 知识库系统 | 可选本机 HTTP 阅读 | tools/kb_display_local.py、src/kb_core/local_vault_web.py:1521 | 已实现；需本机配置与授权 |
| 使用者 → Obsidian | 原生编辑管理 | 原 13d92 的 ENTRY.md 过渡期及目标原生入口契约 | 外部既有系统，保持黑盒 |
| Obsidian → 独立 Vault | 原生文件编辑 | 原 13d92 的 ENTRY.md 原生 Vault 位置与规则契约 | 外部既有系统，保持黑盒 |
| 使用者 → Sample Demo | 浏览静态样例 | docs/demo/index.html、docs/demo/app.js:37 | 已实现的独立样例 |

C4 类型：使用者是 Person；知识库系统是 Software System；Agent、Obsidian、Sample Demo 是外部 Software System；独立 Vault 是外部文件数据存储。实线表示普通调用，虚线强调原生 Workflow 与样例支路。颜色表示角色种类，不表示权限等级。

不存在 Web → Vault 写入、Sample Demo → 私人 Vault 或中央领域 Schema 的关系。具体本机位置与私人库名称不进入公开图。

这些 ENTRY 引用指原受控源码 13d92 的正式入口契约；它未随本候选分发。候选根目录的 ENTRY.md 仅是公开使用边界说明。
