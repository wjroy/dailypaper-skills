---
name: paper-reader
description: |
  Use when the user wants to read a paper into an Obsidian-ready research note.
  Triggers include “读一下这篇论文”, “快速看一下这篇论文”, “批判性分析这篇论文”,
  “读一下 Zotero 里的 …”, and “批量读一下 Zotero 里 … 分类下的论文”.

  Supported inputs: arXiv URL, local PDF, Zotero single item, Zotero collection,
  and structured payload.
context: fork
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, WebFetch, WebSearch
---

> 开始前先简单打招呼。

# Paper Reader

这是仓库里唯一的论文阅读入口，输出直接服务 Obsidian。

## Step 0: 读取共享配置

先读取 `../_shared/user-config.example.json`，如果 `../_shared/user-config.local.json` 存在，再覆盖默认值。

统一使用这些变量：

- `VAULT_PATH`
- `NOTES_PATH`
- `CONCEPTS_PATH`
- `ZOTERO_DB`
- `ZOTERO_STORAGE`
- `ACTIVE_DOMAIN`
- `AUTO_REFRESH_INDEXES`
- `GIT_COMMIT_ENABLED`
- `GIT_PUSH_ENABLED`

## 1. 接收输入

### 1a. 来自 daily-papers 内部 notes stage

如果收到 `RichReviewPaperRecord`，优先按以下路由取全文：

| 类型 | 处理方式 |
| --- | --- |
| `arxiv_url` | WebFetch `preferred_fulltext_input_value` |
| `local_pdf` | Read 本地 PDF |
| `pdf_url` | WebFetch PDF URL |
| 其他 / 空 | 回退到手动输入流程 |

可参考字段：`local_pdf_paths`、`figure_captions`、`preferred_fulltext_input_value`。

### 1b. 用户直接调用

| 输入方式 | 示例 | 处理方法 |
| --- | --- | --- |
| 本地 PDF | `/path/to/paper.pdf` | 直接读取 PDF |
| arXiv 链接 | `https://arxiv.org/abs/2509.24527` | 优先下载 PDF 并进入强制提图流程 |
| Zotero 单条目 | `读一下 Zotero 里的 Diffusion Policy` | 搜索单篇并定位附件 |
| Zotero 分类 | `批量读一下 Zotero 里 机器人 这个分类下的论文` | 先定位分类，再逐篇按同一模板生成 |
| 结构化 payload | 标题 + URL + PDF 路径 | 按给定字段路由 |

如果 Zotero 条目没有 PDF：

1. 先查 PDF URL / arXiv PDF
2. 再查 DOI / 期刊页
3. 找不到就明确说明缺失，不要伪造全文细节

分类和条目查询见 `references/zotero-guide.md`。

## 2. 强制图像提取流程

Figure extraction is mandatory before note writing.

流程必须按下面四个阶段执行，没完成 manifest 不进入最终笔记写作：

1. `scripts/extract_embedded_figures.py`
2. `scripts/render_figure_pages.py`
3. `scripts/build_figure_manifest.py`
4. `scripts/link_figures_to_note.py`

正常执行时，优先直接调用：`scripts/run_figure_pipeline.py`

### 强制规则

1. Figure extraction is mandatory before note writing.
2. The agent must not rely on a single extraction path.
3. The extraction policy is recall-first.
4. Prefer over-inclusion to omission.
5. If key method figures or key result figures are incomplete after embedded extraction, fallback rendering must run automatically.
6. If vector/composite figures cannot be cleanly extracted, preserve full-page renderings instead of skipping them.
7. The note must contain both `关键图示 (Key Figures)` and `全部候选图 (All Candidate Figures)`.

### Stage A: embedded image extraction

- 从 PDF 中提取嵌入式图片对象
- 输出到 `assets/papers/<paper_id>/figures/`
- 记录 `embedded_figures.json`

### Stage B: rendered-page fallback

- 扫描带有 `Figure` / `Fig.` / `framework` / `method` / `experiment` / `results` 等关键词的页面
- 如果 embedded 结果偏少、方法图缺失、结果图缺失、或 figure-like 页面明显更多，自动整页渲染
- 无法稳定裁剪时保留整页 PNG 作为兜底

### Stage C: figure manifest construction

- 生成 `figure_manifest.json`
- 记录页码、来源类型、文件名、caption、角色、是否进入关键图示、置信度
- 后续笔记插图必须基于 manifest，而不是临时发挥

### Stage D: note linking

- 基于 manifest 自动写回笔记
- 图片必须落在 vault 内，并使用稳定 wiki-link
- 不允许写本机绝对路径

## 3. 输出模式

只保留两种：

| 模式 | 触发词 | 输出 |
| --- | --- | --- |
| 快速摘要 | “快速看一下” | 3-5 句摘要 + 图像提取摘要 |
| 研究笔记 | 默认 | 使用 canonical template 生成完整笔记 |

如果用户说“批判性分析”，把批判内容写进 `Limitations` 和 `Inspiration for My Research`。

## 4. 笔记生成

唯一模板：`obsidian-templates/论文笔记模板.md`

### 核心规则

1. frontmatter 和 section 名必须与 canonical template 完全一致，不删字段、不改标题
2. `关键图示 (Key Figures)` 和 `全部候选图 (All Candidate Figures)` 必须来自 figure manifest
3. 不要写 ASCII 流程图
4. 关键术语首次出现时尽量加 `[[概念]]` 链接
5. 无法确认的结论明确降级表达，不要硬写成确定事实

详细规则见 `references/quality-standards.md`。

### 图像目录与引用

- 图片统一保存到：`assets/papers/<paper_id>/figures/`
- manifest 文件：`assets/papers/<paper_id>/figures/figure_manifest.json`
- 笔记中的图片引用统一使用：`![[assets/papers/<paper_id>/figures/<filename>.png]]`
- 若图片不存在，不插入坏链接；把缺失写进 manifest 和 `Missing Field Report`

### 缺失字段报告

任何无法稳定提取的内容都写进 `Missing Field Report`，例如：

- only partial embedded figures were available; rendered pages were added as fallback
- PDF mainly uses vector figures; full-page rendered fallbacks were preserved
- 关键公式无法确认
- 表格过长未完整抽取
- 只有 metadata 没有全文

## 5. 保存

### 文件名

优先使用方法名；不确定时使用标题缩写并放进 `_待整理/`。

### 保存路径

默认保存到：`{NOTES_PATH}/{zotero_collection_path 或 _待整理}/{文件名}.md`

### frontmatter 最少字段

```yaml
---
title: "论文标题"
authors: [Author1, Author2]
year: 2025
source: arXiv
venue: ""
doi: ""
url: https://arxiv.org/abs/xxxx
arxiv_id: xxxx
zotero_collection: _待整理
tags: [paper]
domain: intelligent_construction
image_source: vault_local
extraction_confidence: 0.82
created: YYYY-MM-DD
---
```

### section 列表

输出顺序保持为：

1. `Paper Snapshot`
2. `One-Line Summary`
3. `Research Problem`
4. `Method Summary`
5. `关键图示 (Key Figures)`
6. `全部候选图 (All Candidate Figures)`
7. `Key Formula`
8. `Main Findings`
9. `Notes on Data / Evaluation`
10. `Limitations`
11. `Inspiration for My Research`
12. `Linked Concepts`
13. `Missing Field Report`
14. `Source Notes`

### 保存后

1. `AUTO_REFRESH_INDEXES=true` 时刷新 MOC
2. `GIT_COMMIT_ENABLED=true` 时才允许 git add / commit
3. `GIT_PUSH_ENABLED=true` 且已配置远端时才 push

## 6. 概念笔记

如果正文中已经写了 `[[概念]]`，就检查概念笔记是否存在；缺失时按 `references/concept-categories.md` 归类。

## 7. 日志要求

处理一篇论文时，至少汇报：

- embedded figures extracted: X
- rendered fallback pages: Y
- total candidate figures: Z
- key method/framework figures: A
- key result figures: B
- figure manifest saved to: ...
- note linked with figures: yes/no

## 8. 自检

- [ ] frontmatter 完整
- [ ] `One-Line Summary` 已写
- [ ] `Research Problem` 已写
- [ ] `Method Summary` 已写
- [ ] `关键图示 (Key Figures)` 已写
- [ ] `全部候选图 (All Candidate Figures)` 已写
- [ ] `Key Formula` 已写或在 `Missing Field Report` 中说明
- [ ] `Main Findings` 已写
- [ ] `Notes on Data / Evaluation` 已写
- [ ] `Limitations` 已写
- [ ] `Inspiration for My Research` 已写
- [ ] `Linked Concepts` 已写
- [ ] `Missing Field Report` 已写
- [ ] `Source Notes` 已写
- [ ] `figure_manifest.json` 已生成
- [ ] `extraction_confidence` 已填写

## 参考文件

- `references/zotero-guide.md`
- `references/image-troubleshooting.md`
- `references/concept-categories.md`
- `references/quality-standards.md`
