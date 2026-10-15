---
title: 轻量 WebGL 地球仪数据视觉
---
# 轻量 WebGL 地球仪数据视觉

任务：把"全球覆盖/节点/用户分布"这类信息做成轻量 WebGL 地球仪，用数据点和弧线表达，而非再画一张扁平世界地图。
检索词：globe、cobe、webgl、data-visual、geographic-visualization、hero、3d、地球仪、数据视觉、shadcn。
摘要：基于 Cobe 的轻量 WebGL globe，固定比例容器 + 自动旋转 + 可交互，前景叠加数字/标题并做 radial fade；适合 Hero/数据区慢速背景运动。本轮取得报告二手描述及组件名/安装方式。
适用（INFERRED）：内容真与"全球/地域/网络分布"相关的 Hero、数据区；需要慢速背景 3D 运动提升焦点。
不适用（INFERRED）：本地/单一场景产品硬凑国际范；未取得具体数据点/弧线配置证据，不在数据编码细节上做断言。
关键未知（UNVERIFIED）：Cobe props、数据点/弧线配置、旋转速度、性能、可访问性、具体许可条款均未取证；报告只给组件级信息。
主要证据（EXTRACTED）：报告 P185–P195（Magic UI Globe，已确认基于 Cobe、WebGL、shadcn registry 安装；结构 固定比例容器→WebGL globe→前景数字/标题→radial fade）。
读取入口（Vault 相对路径）：
- evidence_read_path: content/knowledge/globe-3d-data-visual/evidence/report-20-cases-p185-p195.md

## 机制与理由

地球仪相对扁平地图的价值是把"全球"从平面示意图变成有体积感的慢速运动背景：自动旋转提供低频动效，数据点/弧线承载分布信息，前景数字/标题保持可读，radial fade 把 globe 边缘融掉避免抢焦点。关键是它只在内容真与地理/全球相关时才成立。

## 页面拆解

- 容器：固定比例容器。
- 主体：WebGL globe（基于 Cobe）。
- 前景：数字 / 标题。
- 融合：radial fade。
- 动效：自动旋转 + 可交互，作 Hero/数据区慢速背景运动。

## 实现配方

未取得具体参数。报告确认基于 Cobe、WebGL、shadcn registry 安装，但未给 props、旋转速度、数据点/弧线配置；实现前需回源 Magic UI/Cobe 文档。

## 来源、证据与权利

原报告 source_id=report-20-cases；原项目 docs/网页创作/2026-09-30-前端设计案例20选.docx，P185–P195，SHA-256 21c4901d935926ecabf02fc017a6d857e76ce28e48527c345c75cf1eea1ce7b8。
原始 URL（P187）：https://magicui.design/docs/components/globe 。
遵循 Magic UI/Cobe 许可与依赖要求；本轮未核验许可证文本，不得断言可复用。

## 变体、关联与项目反馈

- 关联：与 bento-grid-feature-layout（P197–P207）同属 Magic UI 组件体系。
- 边界（报告 P194）：只有内容真与"全球/地域/网络"相关时才该调用，别拿地球仪给本地记账 App 硬装国际范。

## 维护记录

2026-10-04：从 report-20-cases P185–P195 蒸馏；取得组件名/技术栈二手证据，未核验许可文本。
