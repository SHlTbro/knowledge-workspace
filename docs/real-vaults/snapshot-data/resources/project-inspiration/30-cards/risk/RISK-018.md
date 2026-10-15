---
id: RISK-018
type: RISK
status: active
version: '1.0'
digest: sha256:9da1d67a81ab6358
created: '2026-10-05'
title: 攻击者和守门员共享盲区：本地模型猜不出来不代表真正的外部模型、数据经纪商或攻击者猜不出来
source_prj: PRJ-051
tags:
- agent
- security
- privacy
---
## 刹车点
Airlock 的 attack-test 用本地模型尝试重新猜回脱敏占位符。但本地模型猜不出来，不代表真正的外部模型、数据经纪商或攻击者猜不出来。脱敏后的语义组合也可能构成准标识符（quasi-identifier）——单个字段替换了，但多个剩余字段的组合仍然可以唯一识别一个人。

## 为什么危险
- 共享盲区：攻击者和守门员用同一类模型，攻击测试通过给了虚假安全感
- 准标识符：姓名替换了，但"公司+职位+金额+日期"组合仍可识别
- 外部模型能力未知：本地 Qwen 3.5 猜不出，不代表 GPT-5 或专门的 re-identification 模型猜不出

## 缓解
生产版应增加不同模型/规则族的 adversarial probe（至少用 2-3 个不同家族的模型做 attack-test），并单独测 false negative（本地模型没猜出来但外部模型猜出来的比例）。脱敏后语义组合的准标识符风险需要专门检测。
