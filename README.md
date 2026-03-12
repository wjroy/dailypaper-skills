# dailypaper-skills

面向科研阅读的 3 个公开入口：`daily-papers`、`paper-reader`、`generate-mocs`。

## 公开入口

- `daily-papers`：发现论文、排序、生成每日推荐页，并尽可能补充 must_read 笔记
- `paper-reader`：读取单篇论文，稳定产出研究笔记；图像增强默认尝试，但失败时自动回退为无图模式
- `generate-mocs`：刷新论文索引与概念索引

## 最常见的用法

```text
今日论文推荐
读一下这篇论文 https://arxiv.org/abs/2509.24527
更新索引
```

## daily-papers 的产品语义

`daily-papers` 是主入口，固定遵循：

发现论文 -> 排序 -> 生成每日推荐页 -> 尽可能生成 must_read 笔记

关键规则：

- 每日推荐页必须优先产出，任何单个子流程失败都不能阻断主结果
- 缺少某篇论文的 PDF 时，推荐页仍然生成，并标记为 `PDF pending`
- 这时用户只需要补充 PDF 后重新运行 `daily-papers`
- 单篇笔记失败不会让每日推荐失败；推荐页会标记为 `note pending`
- 如果笔记成功但图像增强回退，推荐页仍会挂上文本笔记链接

## paper-reader 的产品语义

`paper-reader` 是稳定的单篇阅读入口，执行流程固定为：

读取论文 -> 提取文本 -> 尝试图像提取 -> 生成研究笔记

图像策略：

- 默认尝试图像增强
- 图像提取失败时自动回退，不能阻断研究笔记生成
- 支持三种结果：完整图像模式、部分图像模式、无图回退模式
- 首次运行时可只询问一次是否启用图像增强初始化；初始化失败也不影响当前阅读

笔记中的 `Figures` 区块会稳定表达三种状态：

- 完整图像模式：方法图和结果图都覆盖
- 部分图像模式：保留已提取关键图，并标记缺失图像
- 无图回退模式：写明 `图像覆盖：未提取`，并给出建议关注图

## generate-mocs 的产品语义

`generate-mocs` 表示“刷新所有索引”。

- 概念索引和论文索引独立刷新
- 任一部分失败都不阻断另一部分
- 对外统一结果语义为 `MOCs refreshed`

## 配置

共享配置加载顺序固定为：

`DEFAULT_CONFIG`
-> `skills/_shared/user-config.example.json`
-> `skills/_shared/user-config.local.json`

规则：

- `DEFAULT_CONFIG` 提供全部安全默认值
- `user-config.example.json` 既是示例模板，也是程序运行时会读取的基础配置层
- `user-config.local.json` 是你的本机覆盖层，不提交到 GitHub
- 任一配置文件缺失都不会阻断三个公开 skill 的主任务

首次安装通常只需要复制：

1. `skills/_shared/user-config.example.json`
2. 重命名为 `skills/_shared/user-config.local.json`
3. 修改你的本机路径和领域偏好

通常最先需要改的是：

- `paths.obsidian_vault`
- `paths.zotero_db`
- `paths.zotero_storage`
- `active_domain`

## 输出结果

- 每日推荐页：`{vault}/DailyPapers/YYYY-MM-DD-论文推荐.md`
- 论文笔记：`{vault}/论文笔记/.../*.md`
- 概念索引：`{vault}/论文笔记/_概念/.../*.md`

## FAQ

**如果 published 论文缺 PDF，会不会卡住？**

不会。`daily-papers` 仍然生成推荐页，并把该论文标记为 `PDF pending`。补充 PDF 后重新运行即可。

**如果 paper-reader 的图像能力失败，会不会整篇读不了？**

不会。文本笔记始终优先生成；图像失败只会回退到无图模式。

**如果 must_read 笔记没有成功生成怎么办？**

推荐页仍然可用，只会把对应论文标记为 `note pending`。

**刷新索引时，两个索引要都成功才算完成吗？**

不需要。两部分独立刷新，对外统一表现为索引刷新动作。
