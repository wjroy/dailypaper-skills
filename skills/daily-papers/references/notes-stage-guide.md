# Notes Stage Guide

`daily-papers` 的内部笔记阶段说明。

这不是独立 skill，只给 `daily-papers` 流水线内部使用。

## 核心原则

笔记生成是"尽力而为"阶段。每日推荐页必须优先产出，不能被单篇笔记生成阻塞。

## 输入

- merged 文件：`/tmp/daily_review_merged.json`
- 推荐页：`{DAILY_PAPERS_PATH}/YYYY-MM-DD-论文推荐.md`

默认只给 `must_read` / `必读` 论文生成笔记。

如果 merged 文件不存在但 preprint rich review 文件存在，则从可用数据中筛选 must_read 论文。

## 工作流

### 1. 创建缺失概念

1. 扫描当天推荐页里的 `[[概念]]`
2. 额外读取 merged 结果中的方法名和关键术语
3. 对缺失概念创建概念笔记，并按 `skills/paper-reader/references/concept-categories.md` 归类

概念创建失败不阻断后续步骤。

### 2. 调用 paper-reader 生成单篇笔记

每篇目标论文都通过公开入口 `paper-reader` 生成，不允许手写骨架笔记。

输入路由优先级：

1. `preferred_fulltext_input_type` + `preferred_fulltext_input_value`
2. `local_pdf_paths[0]`
3. `url`
4. 标题检索 Zotero

**paper-reader 子流程隔离规则（必须遵守）**：

- 逐篇调用 paper-reader，每篇独立处理。
- 单篇 paper-reader 调用失败时：记录失败原因，跳过该篇，继续下一篇。
- 单篇 paper-reader 超时时：跳过该篇，继续下一篇。
- paper-reader 图像增强降级到纯文本时：照常接受其输出，不视为失败。
- 所有 paper-reader 调用都失败时：notes stage 标记为"未生成笔记"，但不阻断推荐页的最终输出。

### 3. 最低质量检查

生成后的笔记必须符合 `obsidian-templates/论文笔记模板.md`，至少包含：

- frontmatter
- `## Paper Snapshot`
- `## One-Line Summary`
- `## Research Problem`
- `## Method Summary`
- `## 关键图示 (Key Figures)`
- `## 全部候选图 (All Candidate Figures)`
- `## Key Formula`
- `## Main Findings`
- `## Notes on Data / Evaluation`
- `## Limitations`
- `## Inspiration for My Research`
- `## Linked Concepts`
- `## Missing Field Report`
- `## Source Notes`

如果图像增强已启用且可用，则应生成：

- `assets/papers/<paper_id>/figures/figure_manifest.json`

如果图像增强未启用、用户拒绝初始化、或后端不可用，则允许保持 `text_only`，但研究笔记正文必须完整。

**判定标准：笔记正文完整即为通过，不因图像缺失而判定失败。**

如果正文明显不完整，则删除并重新生成；不能因为缺图就把本次笔记判为失败。

### 4. 回填推荐页

对成功生成笔记的论文，在推荐页对应条目下补轻量摘要和笔记链接。

对未能生成笔记的论文，标记为"笔记待生成"，而不是留空或报错。

### 5. 刷新目录页

只有在 `AUTO_REFRESH_INDEXES=true` 时才执行。

目录页刷新失败不影响已生成的推荐页和笔记。

## 注意事项

- 如果 merged 文件不存在，检查是否有可用的 preprint rich review 或 published lite review 数据
- 对 Published must-read，优先使用本地 PDF
- `paper-reader` 自己负责图片、公式、缺失字段的诚实记录
- 默认自动刷新目录页，但默认不做 git commit / push
- **整个 notes stage 的任何失败都不能阻止推荐页作为最终产物交付给用户**
