---
name: paper-reader
description: |
  Use when the user wants to read a single paper and get a compact research note.
  Triggers include “读一下这篇论文”, “快速看一下这篇论文”, “分析这篇 paper”,
  an arXiv URL, a local PDF path, or a Zotero single-paper request.

  Supported inputs: arXiv, local PDF, Zotero single item, and structured payload.
  This skill is intentionally narrow: single-paper reading only.
context: fork
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, WebFetch, WebSearch
---

> 开始前先简单打招呼。

# Paper Reader

这是一个紧凑的单篇研究笔记工具。

保留目标：

- 单篇 arXiv 阅读
- 单篇本地 PDF 阅读
- 单篇 Zotero 条目阅读
- 结构化 payload 输入
- arXiv 图片提取
- 研究笔记输出

不要把它当成批量阅读平台。

## Step 0: 读取共享配置

先读取 `../_shared/user-config.json`，如果 `../_shared/user-config.local.json` 存在，再覆盖默认值。

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
| `arxiv_html` | WebFetch `preferred_fulltext_input_value` |
| `local_pdf` | Read 本地 PDF |
| `pdf_url` | WebFetch PDF URL |
| `biorxiv_html` | WebFetch 页面 |
| 其他 / 空 | 回退到手动输入流程 |

可参考字段：`local_pdf_paths`、`figure_captions`。

### 1b. 用户直接调用

| 输入方式 | 示例 | 处理方法 |
| --- | --- | --- |
| 本地 PDF | `C:/Users/win/Downloads/paper.pdf` | 直接读取 PDF |
| arXiv 链接 | `https://arxiv.org/abs/2509.24527` | 优先读 HTML |
| Zotero 单条目 | `读一下 Zotero 里的 Diffusion Policy` | 搜索单篇并定位附件 |
| 结构化 payload | 标题 + URL + PDF 路径 | 按给定字段路由 |

如果 Zotero 条目没有 PDF：

1. 先查 arXiv / bioRxiv HTML
2. 再查 PDF URL / DOI
3. 找不到就明确说明缺失，不要伪造全文细节

单篇 Zotero 操作见 `references/zotero-guide.md`。

## 2. 输出模式

只保留两种：

| 模式 | 触发词 | 输出 |
| --- | --- | --- |
| 快速摘要 | “快速看一下” | 3-5 句摘要 |
| 研究笔记 | 默认 | 使用模板生成完整单篇笔记 |

如果用户说“批判性分析”，把批判内容写进 `Limitations` 和 `Inspiration for My Research`，不要切出额外平台化模式。

## 3. 笔记生成

模板：`assets/paper-note-template.md`

### 核心规则

1. 笔记要覆盖 research problem、method summary、key figures、main findings、limitations
2. 能提取到的 figure / formula / table 尽量保留；提不到的写进 `Missing Field Report`
3. 不要写 ASCII 流程图
4. 关键术语首次出现时尽量加 `[[概念]]` 链接
5. 无法确认的结论明确降级表达，不要硬写成确定事实

详细规则见 `references/quality-standards.md`。

### 图片获取

优先使用：

```bash
python3 assets/extract_arxiv_figures.py "{arxiv_id}"
```

如果图片不全，再按顺序尝试：

1. `https://arxiv.org/html/{arxiv_id}`
2. 项目主页
3. `pdfimages -png` 从 PDF 提取

排错见 `references/image-troubleshooting.md`。

### 缺失字段报告

任何无法稳定提取的内容都写进 `Missing Field Report`，例如：

- figure 缺失
- 表格过长未完整抽取
- 公式无法确认
- 只有 metadata 没有全文

## 4. 保存

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
url: https://arxiv.org/abs/xxxx
doi: ""
zotero_collection: _待整理
domain: geo_timeseries_fm
extraction_confidence: 0.82
created: YYYY-MM-DD
---
```

### 保存后

1. `AUTO_REFRESH_INDEXES=true` 时刷新 MOC
2. `GIT_COMMIT_ENABLED=true` 时才允许 git add / commit
3. `GIT_PUSH_ENABLED=true` 且已配置远端时才 push

## 5. 概念笔记

如果正文中已经写了 `[[概念]]`，就检查概念笔记是否存在；缺失时按 `references/concept-categories.md` 创建。

## 6. 自检

- [ ] frontmatter 完整
- [ ] `Research Problem` 已写
- [ ] `Method Summary` 已写
- [ ] `Key Figures` 已写或在缺失字段报告中说明
- [ ] `Main Findings` 已写
- [ ] `Limitations` 已写
- [ ] `Inspiration for My Research` 已写
- [ ] `Missing Field Report` 已写
- [ ] `extraction_confidence` 已填写

## 参考文件

- `references/zotero-guide.md`
- `references/image-troubleshooting.md`
- `references/concept-categories.md`
- `references/quality-standards.md`
