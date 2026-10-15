---
id: RISK-002
type: RISK
status: active
version: '1.0'
digest: sha256:1e3bfd5f7f2e813a
created: '2026-09-29'
category: engineering
severity: high
seen_in:
- PRJ-002
- PRJ-003
- PRJ-004
- PRJ-005
---
# Demo → 生产鸿沟

## 典型表现
黑客松 Demo 在受控样例可跑，真实数据 / 规模 / 边界下崩；关键能力标注"to be implemented"。

## 检测信号
只测少量样例；无错误路径 / 重试 / 幂等；依赖人工前置；无监控；状态不持久。

## 缓解 / 刹车
影子执行 + 证据门（[[PTN-002]]）；显式列出未实现清单；先窄域上线 + 人工兜底 + 可回滚；做幂等与重试设计。

## 证据实例
[[PRJ-004]] 明确附件处理未实现；[[PRJ-002]] 用 shadow 隔离风险。

## 关联
[[PTN-002]]｜实验 [[EXP-002]]
