---
id: RISK-008
type: RISK
status: active
version: '1.0'
digest: sha256:5fc196d9b857ca98
created: '2026-09-30'
category: evidence
severity: high
seen_in:
- PRJ-012
- PRJ-011
- PRJ-019
---
# 自报指标当独立验证

## 典型表现
把作者/团队自报的"95%+成功率""production-ready""减少70%时间"当作独立验证结果引用，不区分自报与第三方测量。

## 检测信号
指标只出现在项目 README/Devpost/作者博客，无第三方 benchmark、无消融、无复现脚本；数字是整数或过于整齐；评测集未公开。

## 缓解 / 刹车
卡片中严格标注【作者公开】vs【分析推断】vs【未披露】；引用指标时必须写"团队自报"；agent 写代码/做批判时必须经 fetch-core 读源码或原始评测脚本，不能只看卡片摘要。

## 证据实例
[[PRJ-012]]（95%+可编译率为团队自报）｜[[PRJ-011]]（production-ready为作者表述）｜[[PRJ-019]]（synthetic data 演示）

## 关联
[[PTN-014]] [[PTN-020]]
