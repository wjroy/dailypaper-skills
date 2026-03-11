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
3. 对缺失概念创建概念笔记，并按 `paper-reader/references/concept-categories.md` 归类

### 2. 调用 paper-reader 生成单篇笔记

每篇目标论文都通过 `/paper-reader` 生成，不允许手写骨架笔记。

输入路由优先级：

1. `preferred_fulltext_input_type` + `preferred_fulltext_input_value`
2. `local_pdf_paths[0]`
3. `url`
4. 标题检索 Zotero

### 3. 最低质量检查

生成后的笔记至少应包含：

- frontmatter
- `## Research Problem`
- `## Method Summary`
- `## Key Figures`
- `## Main Findings`
- `## Limitations`
- `## Missing Field Report`

如果明显不完整，则删除并重新生成。

### 4. 回填推荐页

对成功生成笔记的论文，在推荐页对应条目下补一行：

```markdown
- 📒 **笔记**: [[笔记名]]
```

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
