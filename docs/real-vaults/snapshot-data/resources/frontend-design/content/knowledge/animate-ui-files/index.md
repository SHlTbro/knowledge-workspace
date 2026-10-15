---
title: Animate UI Files：可重建的目录层级与展开交互参考
---
# Animate UI Files：项目文件浏览器

任务：为 Agent / Knowledge 产品实现可展开文件树，表达目录层级及展开收起。
检索词：文件树、file-tree、层级、展开、收起、knowledge-base、hierarchy、collapsible、developer-ui、复刻、重建。
摘要：多个目录可独立打开，子项缩进并用细线连接；文件夹图标随状态替换；悬停背景跟随行；Git 状态用颜色与标记共同表达。现在除原报告外，已取得固定官方源码、许可和本地参照；限定目标的盲重建仍待消费实验裁决。
适用（INFERRED）：项目、Vault、插件等稳定父子层级；用户需要逐层浏览，并辅以搜索。
不适用（INFERRED）：关系图、跨域探索；本例没有文件选择/打开业务回调，不是完整 IDE tree；没有大树虚拟化或性能证明。
关键未知（UNVERIFIED）：原站所有布局/字体、完整屏幕阅读器行为、超大树、不同浏览器、原组件 reduced-motion 行为、版本未来变化。不得自动推广为全站复刻知识。
主要证据（EXTRACTED）：官方 Base Files 固定 commit efeb96ffd7a3b7a4868667e4ac3c346620fb3044；源码有 350ms 面板、150ms 文件夹图标和 spring 悬停默认值。原报告陈述保持二手层，不因本次源码核查全部升级。
读取入口（全部为 Vault 相对路径）：
- implementation_read_path: content/knowledge/animate-ui-files/implementation.md
- evaluation_read_path: content/knowledge/animate-ui-files/evaluation-v2.json
- visual_read_path: content/knowledge/animate-ui-files/visual.json
- evidence_read_path: content/knowledge/animate-ui-files/evidence/official-source.md
- source_manifest_read_path: content/knowledge/animate-ui-files/evidence/official-source.json
- report_read_path: content/knowledge/animate-ui-files/evidence/report-20-cases-p231-p241.md

## 如何使用

先 read 本入口选型，再 read implementation.md + visual.json 取得有限目标、结构、交互、参数、依赖和 Recipe；关键来源定位可 read official-source.md / official-source.json。所有文件小于公共 read 的 20000 字符上限；无需 heading/offset、原网站访问或 DOCX Reader。visual.json 仅为本知识的领域数据，不要求 Factory 解释其字段。

## 两种能力不要混淆

参考选型：已有报告、边界与回源链，可以解释何时使用文件树。
限定实现：当前材料已补足进入单案例消费实验的条件；只有独立 Agent 经公共接口重建并经对照裁决后，才可声称已证明哪部分可重建。
本次不会提供官方完整组件源码给消费者；原源码仅供取证和参照。图标的少量 SVG 几何保留 Lucide 来源及其通知，是资源复用，不是整组件复制。

## 原件与权限

原报告 source_id=report-20-cases；原项目 docs/网页创作/2026-09-30-前端设计案例20选.docx，P231–P241，SHA-256 21c4901d935926ecabf02fc017a6d857e76ce28e48527c345c75cf1eea1ce7b8。
官方 URL：https://animate-ui.com/docs/components/base/files。
官方 LICENSE.md 实际为 MIT + Commons Clause，不写纯 MIT；原组件形态销售/再分发受其附加条款约束，细节见短证据。实验不证明所有将来再分发用途合规。

## 维护记录

2026-10-04：保留 N11 原笔记快照和原报告证据；增加一手源码、运行参照与消费材料。没有增加知识类型、资产或 Factory Core 接口；本实体仍计 1 资产。独立消费结论由真实实验报告维护，不由蒸馏者自证。

2026-10-04 knowledge v2：仅增加颜色作用域、guide坐标基准及预冻结motion/hover评价。第一轮基础设施PASS、领域消费PARTIAL；本文件修订不自证消费成功。
