---
id: RISK-009
type: RISK
status: active
version: '1.0'
digest: sha256:a6161898bbd213cd
created: '2026-09-30'
category: safety
severity: critical
seen_in:
- PRJ-020
---
# 不可逆动作伪 rollback

## 典型表现
把发邮件、转账、提交表单、外部通知等不可逆动作也叫"rollback"，失败时声称"已撤销"但实际只能补救或无法补救。

## 检测信号
系统只有一个通用 undo()；没有按动作类型区分可逆性；失败后日志写"rolled back"但外部系统状态未恢复；TERMINAL 动作无人工 gate。

## 缓解 / 刹车
每个 tool 预先注册 reversibility_contract；TERMINAL 动作从设计上禁止自动执行，必须 human gate；失败后 receipt 明确区分"已恢复""已补偿""不可逆需人工"，不写"已撤销"。

## 证据实例
[[PRJ-020]]（五级可逆性分类：发邮件=TERMINAL，改文件=RESTORATIVE）

## 关联
[[PTN-021]] [[PTN-024]] [[EXP-021]] [[EXP-022]]
