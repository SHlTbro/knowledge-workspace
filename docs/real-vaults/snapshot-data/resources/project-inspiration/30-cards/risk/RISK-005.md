---
id: RISK-005
type: RISK
status: active
version: '1.0'
digest: sha256:b19a75b881cfd970
created: '2026-09-29'
category: architecture
severity: medium
seen_in:
- PRJ-003
- PRJ-004
---
# 供应商 / 平台锁定

## 典型表现
深度绑定单一低代码平台 / 云 / 模型，迁移成本高、平台变更即失效。

## 检测信号
核心逻辑只存在于专有产物（managed zip / 专有 flow）；无数据导出；接口 / 模型专有。

## 缓解 / 刹车
核心规则与编排放在可移植层（外置规则、开放协议 MCP）；关键路径可替换；数据可导出；加适配抽象。

## 证据实例
[[PRJ-003]] [[PRJ-004]] 强依赖 Microsoft Power Platform。

## 关联
[[PTN-003]]｜实验 [[EXP-003]]
