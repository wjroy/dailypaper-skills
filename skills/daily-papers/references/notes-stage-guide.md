# Notes Stage Guide

`daily-papers` 的内部笔记阶段说明。

这不是独立 skill，只给 `daily-papers` 流水线内部使用。

## 输入

- merged 文件：`/tmp/daily_review_merged.json`
- 推荐页：`{DAILY_PAPERS_PATH}/YYYY-MM-DD-论文推荐.md`

默认只给 `must_read` / `必读` 论文生成笔记。

## 工作流

### 1. 创建缺失概念

1. 扫描当天推荐页里的 `[[概念]]`
2. 额外读取 merged 结果中的方法名和关键术语
3. 对缺失概念创建概念笔记，并按 `skills/paper-reader/references/concept-categories.md` 归类

### 2. 调用 paper-reader 生成单篇笔记

每篇目标论文都通过公开入口 `paper-reader` 生成，不允许手写骨架笔记。

输入路由优先级：

1. `preferred_fulltext_input_type` + `preferred_fulltext_input_value`
2. `local_pdf_paths[0]`
3. `url`
4. 标题检索 Zotero

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

并且必须已经生成：

- `assets/papers/<paper_id>/figures/figure_manifest.json`

如果明显不完整，则删除并重新生成。

### 4. 回填推荐页

对成功生成笔记的论文，在推荐页对应条目下补轻量摘要：

```markdown
- 📒 **笔记**: [[笔记名]]
- **图像覆盖**: 方法图✓ 结果图△
```

如果 figure manifest 可用，还可以补充代表图路径或 figure summary 到 merged 结果，供推荐页渲染器消费；但 notes stage 不负责重新提图。

### 5. 刷新目录页

只有在 `AUTO_REFRESH_INDEXES=true` 时才执行：

```bash
python3 ../../_shared/generate_concept_mocs.py
python3 ../../_shared/generate_paper_mocs.py
```

## 注意事项

- 如果 merged 文件不存在，notes stage 不能继续
- 对 Published must-read，优先使用本地 PDF
- `paper-reader` 自己负责图片、公式、缺失字段的诚实记录
- 默认自动刷新目录页，但默认不做 git commit / push
