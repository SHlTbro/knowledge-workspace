---
id: RISK-007
type: RISK
status: active
version: '1.0'
digest: sha256:031bf8a6dd59bc79
created: '2026-09-29'
category: validation
severity: medium
seen_in:
- PRJ-001
- PRJ-007
- PRJ-010
---
# 复现难点 / 误报与过度拦截

## 典型表现
换环境 / 芯片结果不同；安全机制误报过多致使用户绕过；超参 / 硬件细节缺失无法复现。

## 检测信号
无 pinned 版本 / commit；无硬件 / 预算说明；误报率未测；只在单一设备验证。

## 缓解 / 刹车
钉 commit / 版本 / 依赖与硬件说明（本 vault L2 即此做法）；实测误报 / 漏报并设阈值；多设备验证；公开失败方案。

## 证据实例
[[PRJ-008]] NEON 芯片差异；[[PRJ-007]] 强硬件约束；[[PRJ-001]] 长期误报数据未披露。

## 关联
[[PTN-001]] [[PTN-007]]｜实验 [[EXP-001]]
