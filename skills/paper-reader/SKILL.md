---
name: paper-reader
description: |
  Use when user asks to "read paper", "analyze paper", "summarize paper",
  "读论文", "分析文献", "帮我看一下这篇paper", "论文笔记", or provides a PDF file
  that appears to be an academic paper. Domain-agnostic — works across any
  research field (geotechnical, biology, CS, etc.).

  Also supports Zotero integration: "读一下这篇论文 ...", "快速看一下这篇论文 ...",
  "批判性分析这篇论文 ...", "读一下 Zotero 里的 XXX", "批量读一下 Zotero 里 XXX 分类下的论文"

  **重要触发词**: "读一下 XXX"、"读一下这篇"、"帮我读" → 必须调用此 skill

  **v2 pipeline integration**: 当从 daily-papers-notes 调用时，接收
  `RichReviewPaperRecord` 中的 `preferred_fulltext_input_type/value` 和
  `local_pdf_paths` 字段作为统一输入路由。
context: fork
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, WebFetch, WebSearch
---

> **开始前**: 先跟用户打个招呼 🐕

# 学术论文阅读助手 (Paper Reader)

支持多研究领域，集成 Zotero 和 Obsidian 笔记保存。

## Step 0: 读取共享配置

先读取 `../_shared/user-config.json`，如果 `../_shared/user-config.local.json` 存在，再用它覆盖默认值。

显式生成并在后续统一使用这些变量：

- `VAULT_PATH`
- `NOTES_PATH`
- `CONCEPTS_PATH`
- `ZOTERO_DB`
- `ZOTERO_STORAGE`
- `ACTIVE_DOMAIN` — 当前研究领域（如 `geo_timeseries_fm`、`biology`）
- `AUTO_REFRESH_INDEXES`
- `GIT_COMMIT_ENABLED`
- `GIT_PUSH_ENABLED`

其中：

- `NOTES_PATH = {VAULT_PATH}/{paper_notes_folder}`
- `CONCEPTS_PATH = {NOTES_PATH}/{concepts_folder}`
- `GIT_PUSH_ENABLED` 只有在 `GIT_COMMIT_ENABLED=true` 时才可能为真

后续统一使用上面的变量。

## 1. 接收论文

### 1a. v2 pipeline 输入（从 daily-papers-notes 调用时）

当调用方传入 `RichReviewPaperRecord` 字段时，按以下路由确定全文来源：

| `preferred_fulltext_input_type` | 处理方法 |
|----------------------------------|----------|
| `arxiv_html` | WebFetch `preferred_fulltext_input_value`（arXiv HTML URL） |
| `local_pdf` | Read `preferred_fulltext_input_value`（本地 PDF 路径） |
| `pdf_url` | WebFetch `preferred_fulltext_input_value`（PDF URL） |
| `biorxiv_html` | WebFetch `preferred_fulltext_input_value` |
| 空/未知 | 走 1b 手动输入流程 |

额外参考字段：`local_pdf_paths`（备选本地 PDF）、`figure_captions`（预提取的 caption）。

### 1b. 手动输入（用户直接调用时）

| 输入方式 | 示例 | 处理方法 |
|----------|------|----------|
| PDF 路径 | `/path/to/paper.pdf` | 直接 Read |
| arXiv 链接 | `https://arxiv.org/abs/xxxx` | WebFetch HTML 版本 |
| Zotero 分类 | "VLA 分类的论文" | 查询数据库 → 列出 → 用户选择 |
| Zotero 搜索 | "Zotero 里的 π0.5" | 搜索标题 → 找到 PDF |
| 无 PDF | Zotero 条目无附件 | 从网上获取（见下方） |

### 无 PDF 时的获取流程

1. `python3 assets/zotero_helper.py info {item_id}` 获取论文信息
2. 按优先级获取：arXiv/bioRxiv HTML > arXiv PDF > DOI > WebSearch 标题
3. 判断 arXiv ID：从 URL / Zotero extra 字段 / 标题搜索
4. 推荐直接 WebFetch `https://arxiv.org/html/{arxiv_id}`，无需下载
5. 跳过条件：既无 PDF 也无在线来源 / 非论文内容

> Zotero 详细操作见 `references/zotero-guide.md`

## 2. 阅读模式

| 模式 | 触发词 | 输出 |
|------|--------|------|
| **快速摘要** | "快速看一下"、"quick" | 3-5 句核心贡献 |
| **完整解析** | "详细分析"、默认 | 结构化笔记（用模板） |
| **批判分析** | "批判性分析"、"critique" | 方法论优缺点评估 |
| **知识提取** | "提取公式"、"技术细节" | 公式 + 算法伪代码 |

## 3. 笔记生成

**模板**: 严格遵循 `assets/paper-note-template.md`，不可自行简化。

### 核心质量规则

1. **零遗漏**: 论文中所有 Figure、所有公式、所有 Table 必须全部出现在笔记中
2. **内联概念链接**: 正文中首次出现的技术术语必须用 `[[概念]]` 链接
3. **严禁 ASCII 流程图**: 用结构化 Markdown 列表 + `$数学符号$` 描述架构
4. **公式完整性**: 每个公式必须有名称、LaTeX 公式、含义、符号说明
5. **图片外链优先**: arXiv HTML / 项目主页 / GitHub，找不到再本地下载
6. **诚实报告缺失**: 无法提取的内容必须记录在"缺失字段报告"中，严禁虚构

> 公式/图片/表格的详细质量规范见 `references/quality-standards.md`

### 图片获取流程（代码化 + 多源 fallback）

**目标**: 确保笔记中包含论文的**所有 Figure**，先统计论文 Figure 总数再逐一获取。

**Step 1: 使用 figure extractor 脚本**（首选，有代码保障）：
```bash
python3 assets/extract_arxiv_figures.py "{arxiv_id}"
```
脚本输出 JSON 数组，包含每个 figure 的 `figure_id`、`caption`、`image_urls`。
将输出解析后直接用于笔记中的图片引用。

**Step 2: 手动 fallback**（脚本失败或图片不全时）：
1. **来源 A — arXiv HTML**：WebFetch `https://arxiv.org/html/{arxiv_id}` 手动提取 `<figure>` 的 img src
2. **来源 B — 项目主页**：从摘要/HTML 查找项目主页 URL，WebFetch 提取展示图片
3. **来源 C — PDF 提取**：`pdfimages -png` 从 PDF 中提取，筛选 >10KB

**Step 3: 写入笔记**：
- 用 `![Figure X](url)` 外链嵌入
- 验证：外链可加载 / 本地文件 >10KB
- **URL 去重**：检查 URL 中是否有重复的 arxiv_id 路径段，详见 `references/image-troubleshooting.md`

> ar5iv 编号不一定对应 Figure 编号，排错见 `references/image-troubleshooting.md`

### 图片可靠性保障（生成后自动执行）

笔记保存后，运行图片可达性检查脚本，自动将不可访问的外链图片下载到本地：
```bash
python3 ../daily-papers/download_note_images.py "{笔记完整路径}"
```
- 可达的外链保持不动，不可达的自动下载到 `assets/` 并替换为 Obsidian wikilink
- 如有本地化操作，frontmatter `image_source` 自动更新为 `mixed`

### 公式格式

每个公式必须包含：名称（`[[概念|名称]]`）、LaTeX `$$` 块（前后留空行）、含义、符号列表。
`$$` 块前后**必须有空行**否则 Obsidian 不渲染。超长公式用 `aligned` 拆分。

### 缺失字段报告

模板末尾有"缺失字段报告"表格。任何无法提取的内容（图片不可用、公式无法辨认、表格缺失等）
**必须**在此表格中如实记录，包括缺失原因。这比虚构内容重要得多。

## 4. Obsidian 保存

### 文件命名

只用**方法名/模型名**：`{方法名}.md`（如 `Pi05.md`，不加年份前缀）。
方法名判断：标题冒号前 / Abstract 中 "We propose XXX" / 希腊字母转 ASCII。
不确定时保存到 `_待整理/`。

### 保存路径

按 Zotero 分类层级：`{NOTES_PATH}/{zotero_collection_path}/{方法名}.md`

### YAML frontmatter

```yaml
---
title: "论文标题"
method_name: "MethodName"
authors: [Author1, Author2]
year: 2025
venue: arXiv
tags: [tag1, tag2]  # 小写连字符，3-8 个
zotero_collection: 3-Robotics/1-VLX/VLA
image_source: online
domain: geo_timeseries_fm  # 来自 ACTIVE_DOMAIN
extraction_confidence: 0.85  # 0-1，整体提取质量自评
created: YYYY-MM-DD
---
```

Tags 判断：看 Related Work 小标题 + Abstract 关键词。第一个 tag 是最核心主题。

### 保存后自动执行

1. 只有在 `AUTO_REFRESH_INDEXES=true` 时才刷新目录页：
   ```bash
   python3 ../_shared/generate_concept_mocs.py
   python3 ../_shared/generate_paper_mocs.py
   ```
2. 只有在 `GIT_COMMIT_ENABLED=true` 时才做 git：
   - 先确认 `VAULT_PATH/.git` 存在
   - `git add {新增文件} {paper_notes_folder}/` 后必须真的有 staged changes
   - 满足条件后再执行：
   ```bash
   cd {VAULT_PATH} && git add {新增文件} {paper_notes_folder}/ && git commit -m "add paper note: {方法名}"
   ```
   - 只有在 `GIT_PUSH_ENABLED=true` 且仓库已配置远端时才 push

## 5. 概念库维护（每篇论文必做）

概念库位置：`{CONCEPTS_PATH}`

### 流程

1. **扫描**论文笔记中所有 `[[概念]]` 链接
2. **检查**每个链接对应的概念笔记是否存在（`ls` + `find`）
3. **创建**不存在的概念（不可跳过），自动归类到对应子目录

> 分类规则和模板见 `references/concept-categories.md`

### 自检

- [ ] 笔记中所有 `[[概念]]` 链接的概念笔记都存在？
- [ ] 概念笔记包含本论文作为"代表工作"？

## 6. 完成后自检（合并 checklist）

- [ ] 所有 Figure 都在笔记中（数量与论文一致）？
- [ ] 所有公式都在笔记中（变量一致、无冲突）？
- [ ] 所有 Table 完整保留（所有行列）？
- [ ] 正文中技术术语有 `[[概念]]` 内联链接？
- [ ] 概念库已更新（缺失的概念已创建）？
- [ ] 图片可用（外链可加载 / 本地 >10KB）？
- [ ] 缺失字段报告已填写（无遗漏无虚构）？
- [ ] frontmatter 中 `extraction_confidence` 已填写？

## 7. 交互式功能

完成解析后询问：深入解释？对比其他论文？保存到 Obsidian？
保存后自动创建缺失概念笔记，报告新增概念数量。

## 8. 批量处理

支持 Zotero 分类批量处理（默认递归子分类）。流程：递归获取论文 → 去重 → 跳过已有笔记 → 依次处理 → 汇总。

## 参考文件（按需查阅）

- **`references/zotero-guide.md`** — Zotero 查询、分类、PDF 路径获取、智能分类判断
- **`references/image-troubleshooting.md`** — ar5iv 图片编号对应、PDF 提取备选
- **`references/concept-categories.md`** — 概念自动归类规则 + 模板
- **`references/quality-standards.md`** — 公式/图片/表格的详细质量规范 + 自检清单
