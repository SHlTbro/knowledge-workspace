---
id: RISK-013
type: RISK
status: active
version: '1.0'
digest: sha256:99b49d1a5d12e2a0
created: '2026-10-02'
title: 嵌入式安全测试的生产干扰与隐私
source_prj: PRJ-033
tags:
- risk
- security
- honeypot
- privacy
---
## 风险
Litmus 把安全测试嵌在正常工具接口中，虽然 canary 是无伤害的，但过度把安全测试混进生产工具可能影响性能或引入隐私问题。canary 载荷可能被正常 Agent 误触发（误报），也可能被攻击者识别后规避。

## 刹车信号
- 正常 Agent 频繁命中 canary（误报率高）
- 工具响应延迟增加
- 用户报告工具返回内容异常
- canary 载荷被公开识别和规避

## 缓解
- canary 载荷设计为"只有服从注入才会触发"，正常 Agent 不应命中
- 性能监控：嵌入测试对响应时间的影响 < 5%
- 隐私：canary token 是随机无意义字符串，不包含真实数据
- 可开关：生产环境可配置是否启用嵌入测试
