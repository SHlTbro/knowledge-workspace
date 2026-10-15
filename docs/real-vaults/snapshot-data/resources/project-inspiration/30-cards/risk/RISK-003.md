---
id: RISK-003
type: RISK
status: active
version: '1.0'
digest: sha256:de7b8b45bfb7c002
created: '2026-09-29'
category: ops
severity: medium
seen_in:
- PRJ-008
- PRJ-001
- PRJ-002
---
# 延迟 / 成本不可控

## 典型表现
多 Agent 串行 / 重试、反复编解码、长 build，导致延迟与 token / 算力成本飙升。

## 检测信号
未 profile 就优化；p95/p99 未测；token / 调用成本未计量；并发失控。

## 缓解 / 刹车
先 profile 找热点（ATOM 方法）；热路径下沉（[[PTN-008]]）；设并发 / 重试上限；缓存；设预算与超时。

## 证据实例
[[PRJ-008]] 先 profile，且 NEON 在不同芯片表现相反而不盲目合并。

## 关联
[[PTN-008]]｜实验 [[EXP-008]]
