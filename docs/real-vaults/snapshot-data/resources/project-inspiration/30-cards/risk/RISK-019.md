---
id: RISK-019
type: RISK
status: active
version: '1.0'
digest: sha256:afcfc550b60a54a1
created: '2026-10-05'
title: 共享 memory 会把单 Agent 的错误放大成全团队错误；跨设备还要处理并发写、过期 decision、撤销和访问控制
source_prj: PRJ-056
tags:
- ai-coding
- memory
- agent
---
## 刹车点
mesh-code 的 shared project memory 让不同 Agent / provider 读取同一个中间状态。但共享 memory 会把单 Agent 的错误放大成全团队错误——一个 Agent 写入的错误 decision 会被所有其他 Agent 读取并基于此行动。跨设备还要处理并发写、过期 decision、撤销和访问控制。

## 为什么危险
- 错误放大：单 Agent 错误 → 写入 shared memory → 全团队 Agent 基于错误决策行动
- 并发写：两个 Agent 同时修改同一个 decision → 冲突或覆盖
- 过期 decision：之前决定的方案后来被证明是错的，但 memory 里没有标记过期
- 访问控制：不是所有 Agent 都应该能读写所有 state

## 缓解
Memory 不是越多越好，最难的是 lifecycle。每个 state 需要 source hash、timestamp、confidence、expiry。并发写需要 conflict resolution。过期 decision 需要主动标记和撤销。访问控制需要按 Agent role 限制读写权限。新会话加载 state 时需要验证 source hash 是否仍然有效。
