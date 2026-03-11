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

> 开始前先简单打招呼。对用户只展示必要状态，不展示工程排障细节。

# Paper Reader

这是仓库里唯一的论文阅读入口。默认目标是先稳定产出研究笔记，再按可用性补充轻量图像增强。

## 核心原则

1. 文本研究笔记永远优先，不能被图像初始化、依赖检查或配置缺失阻断。
2. 图像增强是 optional enhancement，不是主流程门槛。
3. 首次图像初始化只问一次；不配置也照常输出本次研究笔记。
4. 初始化结果写入 `paper-reader.state.json`，后续不重复追问。
5. 任意图像步骤失败都自动降级到纯文本或轻量页级模式。
6. 面向用户的输出保持清洁，不暴露路径探索、依赖排查、脚本调用链和安装日志。

## 0. 配置与状态

### 共享配置

- 运行时只读取 `skills/_shared/user-config.local.json`
- `skills/_shared/user-config.example.json` 仅作字段示例，不能当真实配置

### paper-reader 专属配置

- 示例配置：`skills/paper-reader/paper-reader.config.example.json`
- 本地配置：`skills/paper-reader/paper-reader.local.json`
- 运行状态：`skills/paper-reader/paper-reader.state.json`

### 临时模式

如果 `paper-reader.local.json` 不存在：

- 自动进入 temporary mode
- 输出可以直接回到对话中，也可以临时写到 `skills/paper-reader/.temp-output/`
- 绝不能因此中断论文阅读

## 1. 识别输入论文来源

### 1a. 来自 daily-papers 内部 notes stage

如果收到 `RichReviewPaperRecord`，优先按以下路由取全文：

| 类型 | 处理方式 |
| --- | --- |
| `local_pdf` | 优先读取本地 PDF |
| `arxiv_url` | WebFetch arXiv 页面，并尽量转 PDF 或正文 |
| `pdf_url` | 下载或读取 PDF URL |
| 其他 / 空 | 回退到手动输入流程 |

可参考字段：`local_pdf_paths`、`figure_captions`、`preferred_fulltext_input_value`。

### 1b. 用户直接调用

| 输入方式 | 示例 | 处理方法 |
| --- | --- | --- |
| 本地 PDF | `/path/to/paper.pdf` | 直接读取 PDF |
| 上传 PDF | 用户附带 PDF | 直接读取 PDF |
| arXiv 链接 | `https://arxiv.org/abs/2509.24527` | 优先获取 PDF 或 HTML 正文 |
| Zotero 单条目 | `读一下 Zotero 里的 Diffusion Policy` | 搜索条目并定位 PDF |
| Zotero 分类 | `批量读一下 Zotero 里 机器人 这个分类下的论文` | 逐篇读取并按统一模板生成 |
| 结构化 payload | 标题 + URL + PDF 路径 | 按给定字段路由 |

如果 Zotero 条目没有 PDF：

1. 先查 PDF URL / arXiv PDF
2. 再查 DOI / 期刊页
3. 找不到就诚实降级，只基于 metadata 或摘要写有限笔记，不伪造全文细节

## 2. 文本主流程（必须先完成）

先做文本，不要先跑 figure pipeline。

### 2a. 元数据提取

尽量提取：

- 标题
- 作者
- 年份
- 来源 / 期刊 / 会议
- DOI / URL / arXiv ID

### 2b. 正文解析

- 优先使用稳定文本来源完成正文阅读
- 能读 PDF 就读 PDF；PDF 文本层差时尽量利用 metadata、摘要、章节标题和可见正文
- 不要因为图像后端未配置就暂停文本阅读

### 2c. 研究笔记生成

默认产出 canonical research note，至少覆盖：

推荐主入口：

```bash
python skills/paper-reader/scripts/run_paper_reader.py <pdf_path>
python skills/paper-reader/scripts/run_paper_reader.py --record-json <record_json>
```

1. `Paper Snapshot`
2. `One-Line Summary`
3. `Research Problem`
4. `Method Summary`
5. `Key Formula`（或诚实说明缺失）
6. `Main Findings`
7. `Notes on Data / Evaluation`
8. `Limitations`
9. `Inspiration for My Research`
10. `Linked Concepts`
11. `Missing Field Report`
12. `Source Notes`

研究笔记至少应回答：

- 研究问题是什么
- 核心方法是什么
- 模型或算法框架是什么
- 数据与实验设置是什么
- 主要结果和创新点是什么
- 局限性是什么
- 对用户研究有什么借鉴意义

## 3. 图像增强状态检测

文本笔记完成后，再决定是否补图。

### 3a. 读取状态

使用：

```bash
python skills/paper-reader/scripts/manage_image_enhancement.py status
```

关注字段：

- `initialized`
- `user_opt_in`
- `image_backend`
- `backend_ready`
- `auto_setup_images`

### 3b. 首次使用询问

只有在 `user_opt_in == unknown` 时才允许询问，并且只能问一次简洁问题。推荐措辞：

“检测到这是你首次使用论文图像增强功能。我可以做一次性初始化，后续可自动补充关键方法图和结果图。本次即使不配置，我也会先正常输出论文研究笔记。是否现在配置？”

规则：

1. 这句询问只在未知状态出现
2. 明确说明“不配置也不影响本次研究笔记”
3. 用户答应或拒绝后，立即缓存到 state
4. 后续不再反复询问；除非用户显式要求 reset 或重新启用

### 3c. 状态缓存命令

```bash
python skills/paper-reader/scripts/manage_image_enhancement.py initialize --choice yes
python skills/paper-reader/scripts/manage_image_enhancement.py initialize --choice no
python skills/paper-reader/scripts/manage_image_enhancement.py reset
```

初始化只做轻量检查与状态缓存，不做长时间环境安装，不修改用户系统环境。

## 4. 图像增强执行策略

只有当以下条件同时满足时才自动执行图像增强：

1. `user_opt_in == yes`
2. `backend_ready == true`

执行入口：

```bash
python skills/paper-reader/scripts/run_paper_reader.py <pdf_path>
python skills/paper-reader/scripts/run_figure_pipeline.py <pdf_path> --paper-id <paper_id> [--note-path <note_path>]
```

### 后端优先级

1. `PyMuPDF`：默认首选，负责文本抽取、embedded image 枚举、页级渲染
2. `poppler` 工具：`pdfimages` / `pdftoppm` / `pdftotext`，仅作可选增强后端
3. `text_only`：任何后端不可用或失败时立即降级

### 图像模式

#### 模式 A：`full`

- 提取到可用关键图
- 研究笔记中补充图像状态摘要
- 优先放 1 张方法/框架图和 1 张主结果图

#### 模式 B：`page_fallback`

- embedded extraction 不稳定时，保留关键页截图
- 作为可接受降级，不要求脆弱裁剪

#### 模式 C：`text_only`

- 图像完全不可用时，写入简洁占位状态
- 至少注明：`图像覆盖：未提取` 和建议关注图类型

## 5. 错误处理与自动降级

以下规则必须显式执行：

1. 配置文件不存在 -> 进入 temporary mode，继续文本笔记
2. 示例配置存在但本地配置不存在 -> 只把 example 当参考，不当真实配置
3. 图像后端未安装 -> 跳过图像增强，继续文本主流程
4. 图像初始化失败 -> 记录 state，结束初始化，不阻断本次阅读
5. 外部命令不存在 -> 捕获异常，回退到 PyMuPDF 或 `text_only`
6. PDF 图像提取失败 -> 只输出简短图像状态，不报致命错误
7. 中文路径或编码异常 -> 优先使用 Python 路径处理；失败时继续文本模式
8. 任意单步失败 -> 不能让用户最终拿不到研究笔记

## 6. 输出模式

| 模式 | 触发词 | 输出 |
| --- | --- | --- |
| 快速摘要 | “快速看一下” | 3-5 句摘要 + 一行图像状态 |
| 研究笔记 | 默认 | 使用 canonical template 生成完整笔记 |

如果用户说“批判性分析”，把批判内容重点写进 `Limitations` 和 `Inspiration for My Research`。

## 7. 用户可见输出规范

最终面向用户只保留：

- 必要的一两行状态提示
- 高质量研究笔记
- 可选的图像状态摘要 / 关键图说明

不要向用户暴露以下工程噪音：

- 共享配置读取过程
- 脚本路径探索
- PATH / poppler / conda 排障细节
- figure pipeline 的内部阶段日志
- 内部函数调用过程

## 8. 保存与落盘

### 路径策略

- 已配置时：按 `paper-reader.local.json` 写入用户输出目录
- 未配置时：允许只在对话中返回，或写入 `skills/paper-reader/.temp-output/`

### 图像落盘规则

- 图片目录：`assets/papers/<paper_id>/figures/`
- manifest：`assets/papers/<paper_id>/figures/figure_manifest.json`
- 笔记引用：`![[assets/papers/<paper_id>/figures/<filename>.png]]`
- 图片缺失时不插入坏链接，而是写占位状态

## 9. 自检

- [ ] 文本研究笔记已完成
- [ ] 即使没有图像能力，主笔记仍然成立
- [ ] 若图像增强已启用，状态已缓存且只做轻量补充
- [ ] 若图像增强失败，已自动降级且未阻断主任务
- [ ] 用户输出未混入调试噪音

## 参考文件

- `references/zotero-guide.md`
- `references/image-troubleshooting.md`
- `references/concept-categories.md`
- `references/quality-standards.md`
