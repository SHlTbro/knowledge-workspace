---
title: Agent 交接终端视觉 mock
---
# Agent 交接终端视觉 mock

任务：在营销页上模拟"把转录/笔记交给 coding agent（如 Claude Code）执行"的终端窗口，用纯前端视觉 mock 表达交接可信度，不接真 shell。
检索词：agent handoff、terminal mock、CLI mock、cwd、prompt、enter to run、Claude Code、开发工具营销、复刻。
摘要：画一个假终端窗口（cwd 路径行 + 命令 prompt + 按 enter 运行的提示），视觉上像真 CLI，但不执行任何命令；目的是让访客相信"产品输出可以直接喂给 agent 跑"。报告原等级：EXTRACTED（Aloud Ship 段可见组件 AgentHandoff）。
适用（INFERRED）：面向开发者/AI agent 的产品需要表达"可交接/可执行"；产品本身不提供真终端，但营销要传达工作流闭环。
不适用（INFERRED）：真终端/IDE 内嵌场景；需要可交互运行沙箱的产品；访客需要实际试用命令的场景。
关键未知（UNVERIFIED）：具体 prompt 文案、cwd 路径、enter 后是否有打字机动画、是否模拟输出流、配色字体、键盘事件是否真实响应。不得推广为真终端组件。
主要证据（EXTRACTED）：report-3-sites P068–P070、P121、P127（Aloud）；报告明确"纯前端 mock cwd/prompt/enter-to-run，强调视觉可信度，不需要真实 shell"。
读取入口：
- evidence_read_path: content/knowledge/agent-handoff-terminal-mock/evidence/report-3-sites-aloud-terminal-mock.md

## 机制与理由

开发者看到终端界面会瞬间理解"这是可执行的工作流"。把交接动作视觉化成 cwd + prompt + enter，比文字描述"我们支持导出到 Claude Code"更有说服力；同时因为是 mock，不需要真接 shell，性能与安全成本极低。关键是视觉可信度（窗口 chrome、提示符、路径样式），不是功能真实度。

## 实现配方（PROPOSED，待验证）

- 窗口：macOS 风格红黄绿圆点 + 标题栏（可写 cwd 路径）。
- 主体：`$ <command>` 或 `➜ <cwd>` 提示符一行，下方固定一段说明。
- 交互：可加"按 Enter 运行"的静态提示；报告未说是否真绑键盘。
- 不要：不要真 fork shell、不要跑命令、不要暴露真实凭证路径。
未取得原站 CSS/JS，色值/字体/动画保持未知。

## 来源、证据与权利

source_id=report-3-sites；原项目 docs/网页创作/2026-09-30-前端源码蒸馏3站.docx；URL https://www.aloud.sh/ 。报告原等级按原报告记录，不升级。许可证未知，不得断言可复用；本条目仅记录模式，不复制原站截图/文案。

## 维护记录

2026-10-04：从 report-3-sites Aloud Ship 段蒸馏，P068–P070/P121/P127；证据为二手报告描述。
