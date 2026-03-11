# Architecture

## Public Entrypoints

仓库对外只有 3 个入口：

- `skills/daily-papers`
- `skills/paper-reader`
- `skills/generate-mocs`

`skills/_shared` 只放共享配置和脚本，不是可触发 skill。

## Overall Flow

```text
daily-papers
  ├─ published channel
  │   ├─ paper_fetcher_adapter
  │   ├─ metadata_ranker + domain_ranker
  │   ├─ export_zotero_bundle
  │   └─ pause at PDF checkpoint when local PDFs are missing
  │
  ├─ preprint channel
  │   ├─ arxiv_adapter
  │   └─ preprint_enrich_arxiv
  │
  ├─ merge
  │   └─ merge_reviewed_papers.py
  │
  ├─ notes generation
  │   ├─ internal notes-stage rules
  │   ├─ invoke paper-reader on must-read papers
  │   └─ backfill note links into recommendation file
  │
  └─ index refresh
      └─ invoke shared MOC generators when enabled

paper-reader
  ├─ input: arXiv / local PDF / Zotero single item / Zotero collection / structured payload
  ├─ mandatory figure pipeline
  │   ├─ scripts/extract_embedded_figures.py
  │   ├─ scripts/render_figure_pages.py
  │   ├─ scripts/build_figure_manifest.py
  │   └─ scripts/link_figures_to_note.py
  ├─ zotero lookup: skills/paper-reader/assets/zotero_helper.py
  └─ output: note that follows obsidian-templates/论文笔记模板.md

generate-mocs
  ├─ _shared/generate_concept_mocs.py
  └─ _shared/generate_paper_mocs.py
```

## daily-papers

主入口：`skills/daily-papers/orchestration/run_daily_pipeline.py`

职责：

- 跑 Published channel
- 跑 Preprint channel
- 在 PDF 检查点暂停和恢复
- 合并两路 rich review 结果
- 渲染推荐页
- 驱动内部 notes generation

### Published Channel

核心文件：

- `skills/daily-papers/orchestration/run_published_channel.py`
- `skills/daily-papers/adapters/paper_fetcher_adapter.py`
- `skills/daily-papers/ranking/metadata_ranker.py`
- `skills/daily-papers/ranking/domain_ranker.py`
- `skills/daily-papers/export/export_zotero_bundle.py`

主要输出：

- `/tmp/published_raw_200.json`
- `/tmp/published_lite_50.json`
- `/tmp/published_pdf_candidates_20.json`

### PDF Checkpoint / Resume

核心文件：

- `skills/daily-papers/state/pipeline_state.py`
- `skills/daily-papers/state/resume_published.py`

状态文件：

- `/tmp/pipeline_state.json`

### Preprint Channel

核心文件：

- `skills/daily-papers/orchestration/run_preprint_channel.py`
- `skills/daily-papers/adapters/arxiv_adapter.py`
- `skills/daily-papers/enrich/preprint_enrich_arxiv.py`

主要输出：

- `/tmp/preprint_raw.json`
- `/tmp/preprint_enriched.json`
- `/tmp/preprint_review_rich_20.json`

### Merge

核心文件：

- `skills/daily-papers/merge/merge_reviewed_papers.py`
- `skills/daily-papers/render/render_daily_recommendation.py`

主要输出：

- `/tmp/daily_review_merged.json`
- `DailyPapers/YYYY-MM-DD-论文推荐.md`

### Notes Generation

核心资源：

- `skills/daily-papers/references/notes-stage-guide.md`
- `obsidian-templates/论文笔记模板.md`

规则：

- 只给 `must_read` 论文生成笔记
- 笔记由 `paper-reader` 生成，不手写空骨架
- 生成完成后回填推荐页中的笔记链接

## paper-reader

`paper-reader` 负责把单篇论文或一个 Zotero 分类收敛成统一格式的研究笔记。

输入路由：

- arXiv URL
- 本地 PDF
- Zotero 单条目
- Zotero 分类批量读取
- 结构化 payload

笔记契约：

- canonical template: `obsidian-templates/论文笔记模板.md`
- embedded extraction: `skills/paper-reader/scripts/extract_embedded_figures.py`
- rendered fallback: `skills/paper-reader/scripts/render_figure_pages.py`
- manifest build: `skills/paper-reader/scripts/build_figure_manifest.py`
- note linking: `skills/paper-reader/scripts/link_figures_to_note.py`
- zotero lookup: `skills/paper-reader/assets/zotero_helper.py`
- quality rules: `skills/paper-reader/references/quality-standards.md`

图像策略：

- figure extraction 是写笔记前的强制阶段
- 先做 embedded extraction，再根据缺失情况自动做 rendered fallback
- 结果统一落到 `assets/papers/<paper_id>/figures/`
- 笔记只通过 manifest 写入 `关键图示 (Key Figures)` 和 `全部候选图 (All Candidate Figures)`

## generate-mocs

`generate-mocs` 只做目录页刷新：

- `skills/_shared/generate_concept_mocs.py`
- `skills/_shared/generate_paper_mocs.py`

## Config Loading

配置加载顺序固定为：

1. `skills/_shared/user_config.py` 里的 `DEFAULT_CONFIG`
2. `skills/_shared/user-config.example.json`
3. `skills/_shared/user-config.local.json`

提交示例，不提交个人路径。

## State / Resume

- `daily-papers` 在 Published PDF 检查点把状态写入 `/tmp/pipeline_state.json`
- PDF 路径映射写入 `/tmp/published_pdf_inputs.json`
- 恢复命令：`python skills/daily-papers/state/resume_published.py`

## Internal Modules

内部模块保留在 `skills/daily-papers` 的 `adapters/`、`enrich/`、`ranking/`、`merge/`、`render/`、`state/`、`templates/`、`references/` 下。

这些模块服务公开入口，但不面向最终用户单独触发。
