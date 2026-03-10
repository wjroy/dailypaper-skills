# Architecture

本文档描述当前实现状态：

- 主项目：`dailypaper-skills`
- 上游能力源：`paper-fetcher`（Published metadata 多源召回）

## 总览

```text
run_daily_pipeline
  ├─ Published 前半段
  │   ├─ paper_fetcher_adapter (multi-source metadata)
  │   ├─ metadata/domain ranker
  │   └─ /tmp/published_raw_200.json
  │      /tmp/published_lite_50.json
  │      /tmp/published_pdf_candidates_20.json
  │
  ├─ Published 后半段
  │   ├─ published_enrich_from_pdf
  │   ├─ review-rich
  │   └─ /tmp/published_enriched_20.json
  │      /tmp/published_review_rich_20.json
  │
  ├─ Preprint 通道
  │   ├─ source_mode = adaptive(arxiv | biorxiv)
  │   ├─ preprint enrich
  │   └─ /tmp/preprint_raw.json
  │      /tmp/preprint_enriched.json
  │      /tmp/preprint_review_rich_20.json
  │
  └─ Merge
      └─ /tmp/daily_review_merged.json
           ├─ rich_reviewed_pool
           └─ legacy_compatible_pool (for notes/reader compatibility)
```

## 统一 Schema

位置：`skills/daily-papers/schemas/paper_records.py`

- `RawPaperRecord`
  - 用于抓取和 metadata 排序阶段
  - 包含分项评分：`relevance/freshness/provider_quality/metadata_completeness/publication_type/impact/accessibility/final_meta_score`
- `LiteReviewPaperRecord`
  - `review_tier=lite`
  - `evidence_scope=metadata_only`
  - 仅做“是否值得拿 PDF”的分诊
- `RichReviewPaperRecord`
  - `review_tier=rich`
  - 吃 enrich 结果（preprint enrich 或 published PDF enrich）
  - 支持 notes/reader 的下游消费

字段来源说明由 `FIELD_SOURCE_NOTES` 提供，明确每个阶段哪些字段来自何处。

## 领域自适应

配置：`skills/_shared/user-config.json`

- `active_domain`
- `domain_profiles`

内置 profile：

1. `intelligent_construction`
2. `biology`

`domain_profile` 至少包含：

- `queries`
- `positive_keywords`
- `negative_keywords`
- `boost_keywords`
- `source_preferences`
- `preprint_source`

Preprint 默认路由：

- 工程/机器人相关域 -> `arxiv`
- biology/immunology/molecular_biology/bioinformatics -> `biorxiv`

## Published 通道

### 上游接入

`skills/daily-papers/adapters/paper_fetcher_adapter.py`

- 主路径：Python internal call (`SearchAggregator.search`)
- fallback：本地 repo 注入 import -> CLI `paper-fetcher search --json`
- 不耦合 MCP 交互层

### metadata-first 排序

`skills/daily-papers/ranking/metadata_ranker.py`

```text
final_meta_score =
0.40 * relevance_score
+ 0.15 * freshness_score
+ 0.10 * provider_quality_score
+ 0.10 * metadata_completeness_score
+ 0.10 * publication_type_score
+ 0.10 * impact_score
+ 0.05 * accessibility_score
```

`skills/daily-papers/ranking/domain_ranker.py`

- 标题命中 > 摘要命中
- 精确短语 > 离散关键词
- `negative_keywords` 强惩罚/过滤
- `boost_keywords` 加分
- `source_preferences` 域调权

### 落盘

- `/tmp/published_raw_200.json`
- `/tmp/published_lite_50.json`
- `/tmp/published_pdf_candidates_20.json`

## review-lite / review-rich 边界

### review-lite

- skill: `skills/published-review-lite/SKILL.md`
- 只吃 metadata-first
- 不依赖 PDF
- 输出“是否值得获取 PDF”

### review-rich

- skill: `skills/review-rich/SKILL.md`
- 输入 enrich 结果
- 输出 rich decision 与结构化点评
- 必须对缺失字段和低置信度诚实标注

## Preprint 通道

### 抓取

- `skills/daily-papers/adapters/arxiv_adapter.py`
- `skills/daily-papers/adapters/biorxiv_adapter.py`

### enrich

- `skills/daily-papers/enrich/preprint_enrich_arxiv.py`
- `skills/daily-papers/enrich/preprint_enrich_biorxiv.py`

说明：bioRxiv enrich 没有复用 arXiv 解析逻辑，而是使用生物领域线索抽取。

### 落盘

- `/tmp/preprint_raw.json`
- `/tmp/preprint_enriched.json`
- `/tmp/preprint_review_rich_20.json`

## Published PDF Bridge

`skills/daily-papers/enrich/published_enrich_from_pdf.py`

输入：

- `/tmp/published_pdf_candidates_20.json`
- `/tmp/published_pdf_inputs.json`（`paper_id -> pdf_path`）

输出：

- `/tmp/published_enriched_20.json`

至少尝试提取：

- authors / affiliations
- section headers
- figure/table captions
- method summary / method names
- experiment clues
- real-world / simulation clues
- baseline candidates
- extraction confidence
- missing field report

提不到的字段不会伪造，会写入 `missing_field_report`。

## Merge 与下游兼容

`skills/daily-papers/merge/merge_reviewed_papers.py`

- 合并两路 rich 结果
- 去重并排序
- 输出 `/tmp/daily_review_merged.json`

为兼容旧流程，merge 输出：

- `rich_reviewed_pool`（新主数据）
- `legacy_compatible_pool`（给 notes/reader 的兼容字段）

`daily-papers-notes` 已改为默认读取 merged 结果，且默认只处理“必读”。

## 旧模块新角色

- `daily-papers-fetch`：旧单通道抓取，保留为兼容/调试入口
- `daily-papers-review`：旧点评 skill，已由 `published-review-lite` + `review-rich` 分层替代
- `daily-papers-notes`：保留，默认消费 merged rich pool

## 最小可运行 Demo

```bash
python skills/daily-papers/orchestration/run_published_channel.py
python skills/daily-papers/orchestration/run_preprint_channel.py
python skills/daily-papers/orchestration/run_published_rich_channel.py
python skills/daily-papers/merge/merge_reviewed_papers.py
```

或一键串行：

```bash
python skills/daily-papers/orchestration/run_daily_pipeline.py
```

## 已实现 vs MVP 边界 vs 后续增强

### 已实现

- 双通道编排与核心落盘路径
- unified schema
- Published metadata-first ranking
- Preprint adaptive source
- Published PDF bridge（本地 PDF -> enriched JSON）
- rich merge 输出和 notes 兼容入口

### MVP 边界（当前仍需人工参与）

- Published 通道 PDF 获取仍是人工（Zotero/本地下载）
- rich review 的“深度文字点评”仍以结构化自动结果为主，非完整人工审稿级分析

### 后续增强建议

- PDF 解析从 `pdftotext` 启发式升级到版面感知解析
- 将 review-lite / review-rich 的文本点评自动化脚本化
- 增加断点恢复状态机（phase checkpoint）
- 增加端到端回归测试和样例数据集
