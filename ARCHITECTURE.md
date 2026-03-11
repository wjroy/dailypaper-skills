# Architecture

当前仓库已经收敛为 3 个公开入口：

- `daily-papers`
- `paper-reader`
- `generate-mocs`

其余抓取、review、notes 都是内部阶段，不再作为独立 skill 存在。

## 总览

```text
daily-papers
  ├─ published channel
  │   ├─ paper_fetcher_adapter
  │   ├─ metadata_ranker + domain_ranker
  │   ├─ export_zotero_bundle
  │   └─ /tmp/published_raw_200.json
  │      /tmp/published_lite_50.json
  │      /tmp/published_pdf_candidates_20.json
  │
  ├─ pause / resume
  │   ├─ /tmp/pipeline_state.json
  │   └─ state/resume_published.py
  │
  ├─ published rich stage
  │   ├─ enrich/published_enrich_from_pdf.py
  │   └─ /tmp/published_enriched_20.json
  │      /tmp/published_review_rich_20.json
  │
  ├─ preprint channel
  │   ├─ adapters/arxiv_adapter.py
  │   ├─ adapters/biorxiv_adapter.py
  │   ├─ enrich/preprint_enrich_arxiv.py
  │   └─ enrich/preprint_enrich_biorxiv.py
  │
  ├─ merge
  │   └─ /tmp/daily_review_merged.json
  │
  └─ internal notes stage
      ├─ references/notes-stage-guide.md
      ├─ invoke paper-reader for must-read papers
      ├─ backfill note links into recommendation file
      └─ refresh MOCs when enabled

paper-reader
  ├─ input: arXiv / local PDF / Zotero single item / structured payload
  ├─ figure extraction: assets/extract_arxiv_figures.py
  ├─ note template: assets/paper-note-template.md
  └─ output: single-paper research note

generate-mocs
  ├─ _shared/generate_concept_mocs.py
  └─ _shared/generate_paper_mocs.py
```

## daily-papers

主入口：`skills/daily-papers/orchestration/run_daily_pipeline.py`

职责：

- 运行 Published 通道
- 运行 Preprint 通道
- 在 PDF 检查点暂停或恢复
- 合并两路 rich review 结果
- 渲染推荐页
- 驱动内部 notes stage

### Published 通道

核心文件：

- `skills/daily-papers/orchestration/run_published_channel.py`
- `skills/daily-papers/adapters/paper_fetcher_adapter.py`
- `skills/daily-papers/ranking/metadata_ranker.py`
- `skills/daily-papers/ranking/domain_ranker.py`
- `skills/daily-papers/export/export_zotero_bundle.py`

输出：

- `/tmp/published_raw_200.json`
- `/tmp/published_lite_50.json`
- `/tmp/published_pdf_candidates_20.json`

### Published rich stage

核心文件：

- `skills/daily-papers/orchestration/run_published_rich_channel.py`
- `skills/daily-papers/enrich/published_enrich_from_pdf.py`

输出：

- `/tmp/published_enriched_20.json`
- `/tmp/published_review_rich_20.json`

### Preprint 通道

核心文件：

- `skills/daily-papers/orchestration/run_preprint_channel.py`
- `skills/daily-papers/adapters/arxiv_adapter.py`
- `skills/daily-papers/adapters/biorxiv_adapter.py`
- `skills/daily-papers/enrich/preprint_enrich_arxiv.py`
- `skills/daily-papers/enrich/preprint_enrich_biorxiv.py`

输出：

- `/tmp/preprint_raw.json`
- `/tmp/preprint_enriched.json`
- `/tmp/preprint_review_rich_20.json`

### Merge 与推荐页

核心文件：

- `skills/daily-papers/merge/merge_reviewed_papers.py`
- `skills/daily-papers/render/render_daily_recommendation.py`

主输出：

- `/tmp/daily_review_merged.json`
- `DailyPapers/YYYY-MM-DD-论文推荐.md`

### 内部资源

- `skills/daily-papers/templates/lite_review_template.md`
- `skills/daily-papers/templates/rich_review_template.md`
- `skills/daily-papers/references/notes-stage-guide.md`

这些文件只作为内部阶段资源存在，不是公开 skill。

## paper-reader

paper-reader 已收紧为单篇研究笔记生成器。

保留能力：

- 单篇 arXiv 阅读
- 单篇本地 PDF 阅读
- 单篇 Zotero 条目阅读
- 结构化 payload 输入
- arXiv HTML figure 提取
- 研究笔记输出

不再承担：

- 批量 Zotero 阅读入口
- 长驻式后台运行
- 大而全多模式平台化扩张

## 配置

配置文件：`skills/_shared/user-config.json`

当前只围绕以下主键：

- `active_domain`
- `domain_profiles`
- `published_channel`
- `preprint_channel`
- `automation`

内置 domain profile：

- `geo_timeseries_fm`
- `intelligent_construction`
- `biology`

## 最小验证命令

```bash
python skills/daily-papers/orchestration/run_daily_pipeline.py
python skills/daily-papers/state/resume_published.py
python skills/_shared/generate_concept_mocs.py
python skills/_shared/generate_paper_mocs.py
```

`paper-reader` 没有额外 CLI 包装层，主校验点是：

- `skills/paper-reader/SKILL.md`
- `skills/paper-reader/assets/extract_arxiv_figures.py`
- `skills/paper-reader/assets/paper-note-template.md`

## 设计取向

- 对外入口少
- 内部阶段清楚
- 配置以 domain-aware 为中心
- 单篇阅读和每日推荐分工明确
- 优先可维护，不保留旧单通道遗留壳层
