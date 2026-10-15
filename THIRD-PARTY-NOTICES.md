# 第三方来源与权利边界

项目自有代码采用根目录 LICENSE 中的 MIT 许可。第三方代码、字体及知识来源继续适用各自的许可与权利边界。

- 自有代码：Copyright (c) 2026 SHlTbro，MIT。该许可不替代第三方版权，也不意味着仓库中的知识摘录、来源工件和其他资产全部归作者所有。
- `tools/vault-workspace/src/vault_workspace/search.py`：原文件注明 SPDX MIT，部分 tokenizer / BM25 适配自 `xiaojian968/llm-wiki-kit`，提交 `cc32fd65314e2ed463743ebdc4cfc3f583be1b40`。已从精确提交恢复并保留 [完整原 MIT 许可](licenses/llm-wiki-kit-MIT.txt)，Copyright (c) 2026 xiaojian968。原文为 https://github.com/xiaojian968/llm-wiki-kit/blob/cc32fd65314e2ed463743ebdc4cfc3f583be1b40/LICENSE 。
- Pydantic、PyYAML、pytest 等是安装依赖，保留各自许可；其 wheel、安装目录和离线验证缓存均未随此候选分发。
- 外部 CLI、Skill、模型、权重和视频工具制品不在公开候选内；源码存在不代表第三方资产可再分发。
- `docs/real-vaults/` 是拥有者按具体文件及公开字节批准的真实六库快照，共293篇预览：Agent相关11、Agent架构32、Agent技能6、视频知识3、项目灵感212、前端设计29。它不是原六库全部320条目录项的再分发，也不连接或追踪作者私库。
- 其中25份仅隐藏本机路径，全部293份未截断。公开页区分原文件SHA-256和预览SHA-256；脱敏后的字节、原卡内的digest及其发布资格不能混为一项证明。其余私人文件、凭据、个人配置、原始DOCX、视频与音频、图像、完整转写、pinned source和未列入范围的附件均未获此快照的连带公开授权。
- 真实知识预览包含拥有者的归纳、研究观察、短摘引和外部来源指针，保留各自EXTRACTED/INFERRED/未核验边界。根目录MIT许可不将第三方表达、来源媒体或原组件改成项目自有资产。来源链接是归属与核对线索，不是复制原网站、源码或媒体的许可。
- 三张视频卡内的JSON是结构、动效、风格的研究数据，不是上游程序源码。卡内rights_boundary继续限制原视频帧、音频、原稿、图形、品牌及精确编排复用；公开这些观察不授予原媒体复用权。
- 前端设计入口保留本地报告和公开组件的来源定位；未随快照提供报告完整文件、官方组件完整源码、图标几何或证据附件。Animate UI入口明确记载MIT + Commons Clause，不能因本项目使用MIT而抹去其附加条件。
- `docs/demo/` 内容来自独立、显式标记的虚构公开样例，不含私人 Vault 正文。原样例 NOTICE 随目录保留。
- 本次Hero和图表由本地展示流程生成，Hero是说明图。README主页面截图展示获准公开的真实快照，浏览和来源范围以该快照为限；旧Sample Data截图继续保留为开发样例，不能用它们证明私人库接入。快照截图也不证明原库的实时权限、生产搜索或写入成功。
- 交互图查看器保留 [Archify 许可](assets/diagrams/ARCHIFY-LICENSE.txt) 和 [JetBrains Mono 字体许可](assets/diagrams/JetBrainsMono-OFL.txt)。[图表目录与可编辑来源](assets/diagrams/index.md)、[图表版权说明](assets/diagrams/NOTICE.md) 保留完整资产关系。

任何超出本次293篇具体字节的内容公开，仍须另经内容与再分发范围审阅。不得把原始私人库、凭据、第三方资产或未审阅材料作为软件MIT授权的一部分。
