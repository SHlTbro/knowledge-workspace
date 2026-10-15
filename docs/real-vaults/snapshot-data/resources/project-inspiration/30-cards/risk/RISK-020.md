---
id: RISK-020
type: RISK
status: active
version: '1.0'
digest: sha256:632badc3927bc0eb
created: '2026-10-05'
title: self-play 会学习对手也会偷偷过拟合谁经常和我打；matchmaking 偏 2p 就调成 90% 2p，最终评估偏 4p 变成 distribution shift
source_prj: PRJ-060
tags:
- rl
- agent
- eval
- infra
---
## 刹车点
Orbit Wars 第一名作者复盘指出：比赛期间 top player 的 matchmaking 偏 2p，于是后半程把训练调成 90% 2p；最终评估分布却更偏 4p，使这一优化变成 distribution shift 风险。pure self-play 只有 current self 对 current self，会把策略收敛到狭窄生态，没有 league play 会导致 self-overfitting 和 strategic cycle。

## 为什么危险
- self-overfitting：只和自己打 → 策略收敛到狭窄生态 → 遇到不同对手就崩
- distribution shift：训练分布和评估分布不一致 → 训练时表现好但评估时差
- strategic cycle：两个策略互相克制形成循环 → 没有 league diversity 就跳不出来
- 过拟合 matchmaking：根据当前 top player 的分布调整训练 → 评估分布变了就吃亏

## 缓解
训练分布、league diversity、环境吞吐和模型规模必须一起设计。过去策略、多样对手和真实部署 mix 都应该成为 replay/league 的组成部分。模型/Skill 更新后必须对历史 league 回归，测"对当前 benchmark 变好但对过去 failure modes 退化"的比例。不要根据当前 matchmaking 分布过度调整训练分布。
