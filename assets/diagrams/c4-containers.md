# 可运行单元与文件权威

框架 CLI 与可选本机只读 Web 是两个可独立运行的 Python 入口。MemberStore、BindingStore、Reader、PolicyService 是它们复用的库模块；图中没有把这些模块虚构成独立服务。

![容器与文件权威](c4-containers.png)

[交互图下载](c4-containers.html) · [可编辑 JSON](c4-containers.json) · [C4 Mermaid 源](c4-containers.mmd) · [SVG](c4-containers.svg)

| 来源 → 目标 | 动作与协议 | 源码证据 | 状态 |
| --- | --- | --- | --- |
| 外部 Agent → 框架 CLI | ENTRY / 本机命令 | tools/kb_entry.py:66、tools/kb_cli.py | 已实现 |
| 框架 CLI → 显式本机实例 | 成员与位置约束；JSON | src/kb_core/operations.py:55、members.py、bindings.py | 已实现 |
| 框架 CLI → Vault 文件 | 获准构建与受控文件操作 | src/kb_core/builder.py:259、writer.py:195 | 已实现；不代替领域质量门 |
| Agent → Vault 文件 | 依据目标规则执行原生 Workflow | 原 13d92 的 ENTRY.md §5–6 | 已实现的调用方式 |
| Agent → 共享 CLI / Skills | 按需原生调用 | 原 13d92 的 ENTRY.md §5 | 已接线；各族安装与运行成熟度分别记录 |
| 浏览器阅读页 → 本机 Web | Bearer / HTTP | tools/kb_display_local.py、local_vault_web.py:1425 | 已实现 |
| 本机 Web → Vault 文件 | 可见性及精确 SHA 复核；本机文件 | local_vault_web.py:725、617 | 已实现；有界预览 |
| 本机 Web → 显式本机实例 | 读取共同成员、绑定与权限策略 | local_vault_web.py:295、365、display_policy.py | 已实现 |

C4 Container：框架 CLI、Python Web 进程、浏览器页面。显式本机实例是文件 Data Store；独立 Vault 是系统边界外的原生文件集合。MemberStore / BindingStore 不具有独立部署边界。Web Search 使用请求内 BM25 投影，不构成内容或权限权威。

未绘制 Component：公开读者无需了解类级结构。未绘制 Dynamic：正常／失败／恢复由独立 Workflow 图回答。未绘制 Deployment：当前交付不声称云部署、多人服务或正式生产切换。

这些 ENTRY 引用指原受控源码 13d92 的正式入口契约；它未随本候选分发。候选根目录的 ENTRY.md 仅是公开使用边界说明。
