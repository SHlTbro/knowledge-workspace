---
id: RISK-004
type: RISK
status: active
version: '1.0'
digest: sha256:bdb9a1caf600ddee
created: '2026-09-29'
category: security
severity: high
seen_in:
- PRJ-003
- PRJ-004
---
# 权限 / 安全 / Secret 泄露

## 典型表现
Agent 持过宽权限常驻、可直接写生产；MCP / API key 泄露；越权操作；Prompt 注入诱导动作。

## 检测信号
用高权限账号；密钥硬编码；无动作审计；非最小权限；输入与动作未隔离。

## 缓解 / 刹车
最小权限 + 意图层闸门（[[PTN-001]]）+ 高后果人批（[[PTN-005]]）；密钥走环境 / 密钥管理；全动作审计；写操作白名单。

## 证据实例
[[PRJ-003]] Dataverse MCP、[[PRJ-004]] Jira 写入均为有副作用动作。

## 关联
[[PTN-001]] [[PTN-005]]｜旗舰 [[EXP-011]]
