---
title: 单色主体+语义危险色强调系统
---
# 单色主体 + 语义危险色强调系统

任务：在黑白单色主体上，用有限的语义色（danger/approval/pending/healthy）表达产品状态，而不是散落硬编码颜色。
检索词：semantic-color、danger-token、monochrome-accent、alert-language、design-token、black-white-red、status-color。
摘要（EXTRACTED）：Heron AI 采用黑白主体 + 红色危险/违规强调；报告建议 danger 作为语义 token，不要散落硬编码，并进一步提出 danger/approval/pending/healthy 四状态 token 系统，让视觉语义与产品状态一致。
适用（INFERRED）：工具/开发者产品或安全类产品，需要克制色彩但状态信号必须醒目；设计系统已有 token 层。
不适用（INFERRED）：品牌色主导的营销站、内容驱动的媒体站；本例未证明完整四色 token 已在原站落地，仅 danger 有强推断。
关键未知（UNVERIFIED）：精确 hex 值、approval/pending/healthy 的实际色值与使用场景、token 命名规范、CSS 变量或 Tailwind config 形态、暗模式处理。报告明确 Webflow 平台强推断不等于具体库已确认。
主要证据（EXTRACTED）：P225"黑白主体 + 红色危险/违规强调"；P227"danger 作为语义 token，不要散落硬编码"；P263"Semantic Alert Language：danger/approval/pending/healthy 建 token 系统，让视觉语义与产品状态一致"；P272 PATTERN:semantic-danger-accent-on-monochrome。
读取入口（全部为 Vault 相对路径）：
- evidence_read_path: content/knowledge/semantic-danger-accent/evidence/report-3-sites-heron-danger-accent.md

## 机制与理由

单色主体降低视觉噪音，让内容和数据成为主角；语义色仅用于状态信号，避免彩色干扰。将颜色抽象为 token 后，产品状态（危险/通过/进行中/健康）与视觉表现解耦，后续换肤或暗模式只需改 token 定义。

## 页面拆解

- 主体色：黑白灰（EXTRACTED，P225 强推断）
- danger：红，用于违规/错误/危险提示（EXTRACTED，P225/P227）
- approval / pending / healthy：报告建议建 token，但原站是否实际使用、色值多少，未取证（UNVERIFIED）

## 实现配方（PROPOSED）

定义 --color-danger / --color-approval / --color-pending / --color-healthy 四个 CSS 变量；组件通过语义类名（如 .text-danger）而非硬编码 hex 引用。dark mode 仅调整 token 值，不改组件。

## 来源、证据与权利

原报告 source_id=report-3-sites；原项目 docs/网页创作/2026-09-30-前端源码蒸馏3站.docx，P224–P227、P263、P272，SHA-256 d73649cca6bf1c5c17c7c0730b68e3b57407cb17668e52490d49d70a3b7c498b。
站点 URL：https://www.heron.ai/（报告陈述）。
报告原等级：P225 Color 观察为 STRONG_INFERENCE；P227 复刻建议为报告作者建议，非原站实证。

## 维护记录

2026-10-04：从 report-3-sites P224–P227、P263、P272 蒸馏为独立知识单元。
