---
id: RISK-017
type: RISK
status: active
version: '1.0'
digest: sha256:bf363c4353505ae8
created: '2026-10-04'
title: 如果数字通过复制粘贴出现在 Excel/邮件/PPT 多个地方，只修正文档一处会制造新的不一致
source_prj: PRJ-045
tags:
- enterprise
- agent
- evidence
---
## 刹车点
Evidence Domino 在供应商价格变化后重新计算 margin 并定位受影响句子生成 repair。但最大风险是传播链不完整：如果 proposal 中的某个数字通过复制粘贴出现在 Excel、邮件、PPT、Slack 消息等多个地方，只修正文档一处会制造新的不一致——文档更新了但 Excel 还是旧数字。

## 为什么危险
- 部分修复 → 系统内出现多个版本的"事实" → 比不修复更危险
- 依赖图不完整 → 漏掉隐式依赖（复制粘贴、截图、口头传达）
- 自动修复 → 用户以为全部同步了，实际还有 stale 副本

## 缓解
生产版需要明确 dependency graph 和 source-of-truth。修复时列出所有发现的派生资产，标记"可能还有未发现的副本"。不自动覆盖，owner 审批后应用。高风险数字变更要求人工确认所有副本已同步。
