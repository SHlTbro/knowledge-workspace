---
id: RISK-015
type: RISK
status: active
version: '1.0'
digest: sha256:0b6482a6c5ee4e3b
created: '2026-10-04'
title: LLM-as-judge 可能把同源偏差带入训练数据，修复失败轨迹可能擦掉真实失败模式
source_prj: PRJ-041
tags:
- agent
- data
- evaluation
---
## 刹车点
DataFlow-Agent 的 TrajectoryQualityEvaluator 用 LLM-as-judge 做四轴评分。如果 judge 模型和生成 trajectory 的模型同源，评分会系统性偏好同源模型的输出风格，把偏差带入训练数据。同时 Refine 阶段"修复失败轨迹"可能把真实失败模式擦掉，导致训练数据只留下漂亮结果。

## 为什么危险
- 同源 judge → 训练数据偏差 → 模型自我强化 → 多样性丧失
- 擦掉失败模式 → 模型学不到如何从失败中恢复
- 只保留 refined trajectory → 丢失 raw trajectory 和 quality metadata，无法回溯

## 缓解
同时保留 raw trajectory、quality metadata 和 refined trajectory，不只用漂亮结果。Judge 模型尽量与生成模型不同源。失败轨迹分类为"可学习失败"和"无意义失败"，前者保留用于训练。
