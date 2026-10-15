---
id: RISK-006
type: RISK
status: active
version: '1.0'
digest: sha256:142b0fc4c1bda009
created: '2026-09-29'
category: data
severity: medium
seen_in:
- PRJ-006
- PRJ-009
---
# 数据许可 / 过拟合 / 评测失真

## 典型表现
数据许可不清；在小 / 单一数据上过拟合；裁判与被测同源致指标虚高；隐私问题。

## 检测信号
数据来源 / 许可不明；评测与训练分布雷同；单一裁判；无外部 ground truth；含敏感个人数据。

## 缓解 / 刹车
核查许可与来源；扰动 + 多裁判 + CI（[[PTN-009]]）；引入人类专家 ground truth；做隐私治理 / 脱敏。

## 证据实例
[[PRJ-009]] 双 judge + perturbation；[[PRJ-006]] 涉及受灾者隐私。

## 关联
[[PTN-009]]｜实验 [[EXP-009]]
