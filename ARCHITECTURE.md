# Architecture

> **本文件面向开发者和维护者。** 最终用户只需要 README 中的三句话入口。

## 设计原则

### 内部节点 ≠ 用户可执行步骤

本仓库的流水线拆分为多个内部节点（adapter、ranker、enrich、merge、render 等），但这些节点**仅供编排器内部调用**，不是最终用户可以或需要单独触发的命令。公开入口只有 3 个 skill。

用户看到的是：

- "今日论文推荐" → 一次性完成整条推荐流水线
- "读一下这篇论文 ..." → 生成单篇研究笔记
- "更新索引" → 刷新目录页

用户**不应该**看到或需要运行：adapter 名、ranker 名、enrich 名、merge 脚本名、resume 脚本名、state JSON 路径、/tmp 中间文件路径。

### 优雅降级优先

所有公开入口在遇到部分失败时，优先保留已有成果并继续，而不是整体中止：

| 场景 | 行为 |
|------|------|
| 已发表渠道缺 PDF | 先用预印本数据生成临时推荐，输出待补清单 |
| 单篇笔记生成失败 | 标记"笔记待生成"，继续其他论文 |
| 单个 enrich/rank/export 节点失败 | 保留其余结果，降级输出 |
| 某个数据源完全不可用 | 用另一个数据源继续 |
| 概念 MOC 生成失败 | 论文 MOC 继续，反之亦然 |
| 配置文件缺失 | 使用安全默认值 + 降级提示 |

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
  │   ├─ multi-source metadata fetch
  │   ├─ scoring + ranking
  │   ├─ export candidate bundle
  │   └─ PDF availability check (graceful: continue without if missing)
  │
  ├─ preprint channel
  │   ├─ arXiv fetch
  │   └─ preprint enrichment
  │
  ├─ merge
  │   └─ combine results from both channels
  │
  ├─ render
  │   └─ generate recommendation page
  │
  ├─ notes generation (best-effort)
  │   ├─ invoke paper-reader on must-read papers
  │   ├─ single failure does not block others
  │   └─ backfill note links into recommendation file
  │
  └─ index refresh
      └─ invoke shared MOC generators when enabled

paper-reader
  ├─ input: arXiv / local PDF / Zotero single item / Zotero collection / structured payload
  ├─ text-first note generation
  ├─ optional image enhancement (graceful: degrades to text-only)
  ├─ zotero lookup
  └─ output: note that follows obsidian-templates/论文笔记模板.md

generate-mocs
  ├─ concept MOC refresh (independent)
  └─ paper MOC refresh (independent)
```

## daily-papers

主入口：`skills/daily-papers/orchestration/run_daily_pipeline.py`

职责：

- 并行运行 Published channel 和 Preprint channel
- 当 Published PDF 不可用时生成临时推荐（而非阻塞等待）
- 当用户重新运行且 PDF 已就位时自动恢复并完成剩余评审
- 合并两路 rich review 结果
- 渲染推荐页
- 驱动 notes generation（最佳努力，单篇失败不阻断整体）

### Published Channel

核心文件：

- `skills/daily-papers/orchestration/run_published_channel.py`
- `skills/daily-papers/adapters/paper_fetcher_adapter.py`
- `skills/daily-papers/ranking/metadata_ranker.py`
- `skills/daily-papers/ranking/domain_ranker.py`
- `skills/daily-papers/export/export_zotero_bundle.py`

### PDF Availability & Auto-Resume

核心文件：

- `skills/daily-papers/state/pipeline_state.py` — 流水线状态持久化
- `skills/daily-papers/state/resume_published.py` — 内部恢复逻辑（由编排器自动调用，不面向用户）

行为：

1. Published channel 完成初筛后检查候选论文是否有本地 PDF
2. 如果 PDF 缺失：保存状态 → 继续用已有数据生成临时推荐 → 输出待补清单
3. 用户补好 PDF 后重新运行 `今日论文推荐`：编排器自动检测状态并恢复

> **注意**：`resume_published.py` 是内部实现，不应出现在任何面向用户的提示中。

### Preprint Channel

核心文件：

- `skills/daily-papers/orchestration/run_preprint_channel.py`
- `skills/daily-papers/adapters/arxiv_adapter.py`
- `skills/daily-papers/enrich/preprint_enrich_arxiv.py`

### Merge & Render

核心文件：

- `skills/daily-papers/merge/merge_reviewed_papers.py`
- `skills/daily-papers/render/render_daily_recommendation.py`

主要输出：

- `DailyPapers/YYYY-MM-DD-论文推荐.md`

### Notes Generation

核心资源：

- `skills/daily-papers/references/notes-stage-guide.md`
- `obsidian-templates/论文笔记模板.md`

规则：

- 只给 `must_read` 论文生成笔记
- 笔记由 `paper-reader` 子进程生成，隔离运行
- 单篇 paper-reader 失败不阻断其他笔记，也不阻断推荐页
- 失败的论文在推荐页标注为"笔记待生成"
- 生成完成后回填推荐页中的笔记链接

### 中间文件

流水线在运行过程中会在临时目录生成若干中间 JSON 文件（原始候选列表、筛选结果、PDF 候选清单、预印本 enrichment 结果、合并结果等）。这些文件是内部实现细节，路径和文件名可能随版本变化，不应在面向用户的输出中引用。

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
- orchestrator: `skills/paper-reader/scripts/run_paper_reader.py`
- text-first note generation: always runs before any image work
- embedded extraction: `skills/paper-reader/scripts/extract_embedded_figures.py`
- rendered fallback: `skills/paper-reader/scripts/render_figure_pages.py`
- manifest build: `skills/paper-reader/scripts/build_figure_manifest.py`
- note linking: `skills/paper-reader/scripts/link_figures_to_note.py`
- image init/state manager: `skills/paper-reader/scripts/manage_image_enhancement.py`
- zotero lookup: `skills/paper-reader/assets/zotero_helper.py`
- quality rules: `skills/paper-reader/references/quality-standards.md`

图像策略：

- figure extraction 是增强阶段，不是写笔记前置条件
- 先做文本阅读和研究笔记，再根据状态自动补充图像增强
- 优先 PyMuPDF；可选回退到 poppler 命令行工具
- 结果统一落到 `assets/papers/<paper_id>/figures/`
- 笔记只通过 manifest 写入 `关键图示 (Key Figures)` 和 `全部候选图 (All Candidate Figures)`
- 图像增强失败时自动降级到 `text_only`

### paper-reader 隔离规则

当 `daily-papers` 调用 `paper-reader` 生成笔记时：

- paper-reader 的任何失败（包括图像增强失败）不传播到 daily-papers 主流程
- daily-papers 不依赖 paper-reader 的内部状态文件
- 超时和异常由 daily-papers 编排器捕获并降级处理

## generate-mocs

`generate-mocs` 做目录页刷新，包含两个独立子任务：

- `skills/_shared/generate_concept_mocs.py` — 概念目录页
- `skills/_shared/generate_paper_mocs.py` — 论文目录页

两个子任务独立运行：一个失败不阻断另一个。返回结构化结果，包含成功/失败/跳过的目录信息。

## Config Loading

共享配置加载顺序固定为：

1. `skills/_shared/user_config.py` 里的 `DEFAULT_CONFIG`
2. `skills/_shared/user-config.local.json`

`skills/_shared/user-config.example.json` 只作示例说明。

`paper-reader` 额外维护：

- `skills/paper-reader/paper-reader.config.example.json`
- `skills/paper-reader/paper-reader.local.json`
- `skills/paper-reader/paper-reader.state.json`

如果没有 `paper-reader.local.json`，运行时进入临时模式，不阻断文本阅读。

配置缺失时的降级策略：所有配置字段都有 `DEFAULT_CONFIG` 中的安全默认值。如果 `user-config.local.json` 不存在，系统使用全部默认值运行并在输出中提示。

## Internal Modules

内部模块保留在 `skills/daily-papers` 的 `adapters/`、`enrich/`、`ranking/`、`merge/`、`render/`、`state/`、`templates/`、`references/` 下。

这些模块服务公开入口，但不面向最终用户单独触发。维护者修改这些模块时，需确保编排器的对外行为契约（推荐页始终产出、笔记最佳努力、降级而非阻断）不被破坏。
