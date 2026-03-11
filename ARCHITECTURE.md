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
  │   ├─ zotero handoff export (RIS/Bib/DOI)
  │   └─ /tmp/published_raw_200.json
  │      /tmp/published_lite_50.json
  │      /tmp/published_pdf_candidates_20.json
  │      /tmp/published_top20.ris
  │      /tmp/published_top20.bib
  │      /tmp/published_top20_doi.txt
  │
  ├─ Pause/Resume 状态机
  │   ├─ /tmp/pipeline_state.json
  │   ├─ stage=awaiting_published_pdf_import
  │   └─ resume: skills/daily-papers/state/resume_published.py
  │
  ├─ Published 后半段
  │   ├─ published_enrich_from_pdf
  │   ├─ review-rich (internal stage)
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
  ├─ Merge
  │   └─ /tmp/daily_review_merged.json
  │        ├─ rich_reviewed_pool
  │        └─ legacy_compatible_pool (for notes/reader compatibility)
  │
  └─ Notes Stage (internal)
      ├─ concept extraction & creation
      ├─ paper-reader invocation for must-reads
      ├─ link backfill to recommendation file
      └─ MOC refresh (if auto_refresh_indexes=true)
```

推荐页渲染：

- interim: `skills/daily-papers/render/render_daily_recommendation.py --mode interim`
- final: `skills/daily-papers/render/render_daily_recommendation.py --mode final`

## 统一 Schema

位置：`skills/daily-papers/schemas/paper_records.py`

- `RawPaperRecord`
  - 用于抓取和 metadata 排序阶段
  - 包含分项评分：`relevance/freshness/provider_quality/metadata_completeness/publication_type/impact/accessibility/final_meta_score`
- `LiteReviewPaperRecord`
  - `review_tier=lite`
  - `evidence_scope=metadata_only`
  - 仅做"是否值得拿 PDF"的分诊
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
- `/tmp/published_top20.ris`
- `/tmp/published_top20.bib`
- `/tmp/published_top20_doi.txt`

### Pause / Resume

- 默认第一次运行会暂停在 Published PDF 人工检查点
- 状态文件：`/tmp/pipeline_state.json`
- 必填状态字段：
  - `stage=awaiting_published_pdf_import`
  - `expected_pdf_count`
  - `zotero_export_files`
  - `resume_command`
- 恢复命令：`python skills/daily-papers/state/resume_published.py`
- 可选全自动：`published_channel.auto_continue_without_pdf=true`

## review-lite / review-rich 边界

> 这两个阶段已内部化为 `daily-papers` 的流水线步骤，不再作为独立 skill 暴露。
> 模板文件位于 `skills/daily-papers/templates/`。

### review-lite

- 模板: `skills/daily-papers/templates/lite_review_template.md`
- 只吃 metadata-first
- 不依赖 PDF
- 输出"是否值得获取 PDF"

### review-rich

- 模板: `skills/daily-papers/templates/rich_review_template.md`
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

下游路由兼容字段：

- `local_pdf_paths`
- `zotero_attachment_paths`
- `preferred_fulltext_input_type`
- `preferred_fulltext_input_value`

笔记生成阶段（已内部化）默认读取 merged 结果，且默认只处理"必读"。详见 `skills/daily-papers/references/notes-stage-guide.md`。

## Skill 整合说明

v2 整合后，仅保留 3 个面向用户的公开 skill：

| Skill | 用途 |
| --- | --- |
| `daily-papers` | 每日推荐全流程（含 review-lite / review-rich / notes 等内部阶段） |
| `paper-reader` | 读单篇论文 |
| `generate-mocs` | 手动补刷目录页 |

以下旧 skill 已删除或内部化：

| 旧 Skill | 处理 |
| --- | --- |
| `daily-papers-fetch` | 已删除（旧单通道抓取，功能由 v2 双通道覆盖） |
| `daily-papers-review` | 已删除（旧单通道点评，功能由 review-lite + review-rich 分层替代） |
| `daily-papers-notes` | 已内部化（移入 `daily-papers/references/notes-stage-guide.md`） |
| `published-review-lite` | 已内部化（模板移入 `daily-papers/templates/`） |
| `review-rich` | 已内部化（模板移入 `daily-papers/templates/`） |

## 最小可运行 Demo

```bash
python skills/daily-papers/orchestration/run_daily_pipeline.py
# -> pause at awaiting_published_pdf_import
python skills/daily-papers/state/resume_published.py
```

## 已实现 vs MVP 边界 vs 后续增强

### 已实现

- 双通道编排与核心落盘路径
- unified schema
- Published metadata-first ranking
- Preprint adaptive source
- Published PDF bridge（本地 PDF -> enriched JSON）
- rich merge 输出和 notes 兼容入口
- Skill 整合（8 -> 3 公开入口）

### MVP 边界（当前仍需人工参与）

- Published 通道 PDF 获取仍是人工（Zotero/本地下载）
- rich review 的"深度文字点评"仍以结构化自动结果为主，非完整人工审稿级分析

### 后续增强建议

- PDF 解析从 `pdftotext` 启发式升级到版面感知解析
- 将 review-lite / review-rich 的文本点评自动化脚本化
- 增加端到端回归测试和样例数据集
