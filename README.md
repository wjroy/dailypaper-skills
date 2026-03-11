# dailypaper-skills

我平时读论文用的一套 Claude Code skills。跟 Claude 说句话就能筛论文、读论文、写笔记，最后自动存进 Obsidian。

> **新分支更新**
> Codex / Humanoid 的分支：[`codex+humanoid`](https://github.com/huangkiki/dailypaper-skills/tree/codex%2Bhumanoid)。
> 如果你想直接看 Codex 适配版本，建议先从这个分支开始。

> 📺 [用 Claude Code 打造我的论文流水线](http://xhslink.com/o/1dhQCn40EWY) — 我随手拍的一段视频展示效果

## 🦴 这套东西会帮我做什么

- 抓取每日新论文，初筛后生成推荐列表。
- 支持完整解析、快速摘要和批判性分析。
- 术语可沉淀为概念笔记，方便后续串联。
- 自动写入 Obsidian，并维护目录页和导航页。
- 可接入 Zotero，省去手动复制链接。

最终生成结果在 Obsidian 里大概会长这样：

```text
ObsidianVault/
├── DailyPapers/YYYY-MM-DD-论文推荐.md
├── 论文笔记/.../*.md
└── 论文笔记/_概念/.../*.md
```

可直接看模板：

- [Obsidian 模板](obsidian-templates/论文笔记模板.md)

## 🐕 怎么用

基本就 2 句：

```text
今日论文推荐
读一下这篇论文 https://arxiv.org/abs/2509.24527
```

其他常见说法：

```text
过去3天论文推荐
过去一周论文推荐

读一下这篇论文 ~/Downloads/paper.pdf
快速看一下这篇论文 https://arxiv.org/abs/2509.24527
批判性分析这篇论文 ~/Downloads/paper.pdf

读一下 Zotero 里的 Diffusion Policy
```

`今日论文推荐` 会跑完整流程，`读一下这篇论文 ...` 用来读单篇。

目录页一般会自动更新；如果你手动改过结构，或者怀疑没同步，再补一句：

```text
更新索引
```

## 🏡 安装

前置环境：

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code)
- [Obsidian](https://obsidian.md/)
- [Python 3.8+](https://www.python.org/)
- [`poppler-utils`](https://poppler.freedesktop.org/)（`apt install poppler-utils` / `brew install poppler`）
- [Zotero](https://www.zotero.org/)（可选）

建议给 Obsidian 库加上 git 版本管理。笔记多了以后有个版本历史会安心很多，也方便多设备同步。

如果你是在自己的本地机器上日常使用，通常直接用 `claude --dangerously-skip-permissions` 会省很多权限确认；前提是你清楚这会跳过权限检查，所以更适合个人环境，不建议在不熟悉的机器上直接这么跑。

在仓库根目录运行：

```bash
mkdir -p ~/.claude/skills
cp -r ./skills/* ~/.claude/skills/

# 改成你自己的 Obsidian 库路径，要跟配置文件里的 paths.obsidian_vault 一致
VAULT=~/ObsidianVault
mkdir -p "$VAULT/DailyPapers" \
  "$VAULT/论文笔记/_概念/0-待分类" \
  "$VAULT/论文笔记/_待整理"
```

## ⚙️ 配置

安装完之后需要改一下配置。配置文件是 `~/.claude/skills/_shared/user-config.json`，可以自己改，也可以直接告诉 Claude 你的需求让它帮你改。

里面主要改这几项：

| 配置项 | 说明 |
| --- | --- |
| `paths.obsidian_vault` | 你的 Obsidian 库在哪 |
| `paths.zotero_db` | Zotero 数据库路径（不用 Zotero 可以不填） |
| `paths.zotero_storage` | Zotero 附件存储路径 |
| `active_domain` | 当前激活的领域 profile 名称 |
| `domain_profiles.<name>.queries` | 该领域的检索查询词列表 |
| `domain_profiles.<name>.positive_keywords` | 正向关键词，用来给论文加分 |
| `domain_profiles.<name>.negative_keywords` | 负向关键词，命中直接排除 |
| `domain_profiles.<name>.boost_keywords` | 额外加分的领域特征词 |

`读一下 Zotero 里的 XXX` 不需要额外的映射文件；只要 `paths.zotero_db` 和 `paths.zotero_storage` 配对，脚本会直接从你的 Zotero 分类树里查。

## 🦮 默认行为

默认 Obsidian 库管理不会自动commit、push：

- `auto_refresh_indexes = true`
- `git_commit = false`
- `git_push = false`

也就是默认会自动刷新目录页，但不会动你的 git。如果你的 Obsidian 库已经用 git 管理，希望跑完流程后自动提交，把 `git_commit` 打开就行。

## 🆕 v2 双通道

当前主线升级为双通道论文发现：

1. **Published 通道**：`paper-fetcher` 多源 metadata 召回（默认 200）-> metadata-first 评分 -> top50 lite -> top20 PDF 候选 -> （暂停，等待 Zotero 手动拿 PDF）-> PDF enrich -> rich review。
2. **Preprint 通道**：`arXiv / bioRxiv / adaptive` 抓取 -> enrich -> rich review（默认 top20）。
3. **汇合层**：两个 rich reviewed pool 合并成 `/tmp/daily_review_merged.json`，再给 notes / reader / MOC 使用。

关键中间文件：

```text
/tmp/published_raw_200.json
/tmp/published_lite_50.json
/tmp/published_pdf_candidates_20.json
/tmp/published_enriched_20.json
/tmp/published_review_rich_20.json

/tmp/preprint_raw.json
/tmp/preprint_enriched.json
/tmp/preprint_review_rich_20.json

/tmp/daily_review_merged.json
```

**读单篇**仍走 paper-reader：支持 arXiv、本地 PDF、Zotero。

更多实现细节见 [ARCHITECTURE.md](ARCHITECTURE.md)。

## 🏠 仓库里有什么

3 个面向用户的 skill：

- `daily-papers`：每日推荐全流程（内含 review-lite / review-rich / 笔记生成等内部阶段）
- `paper-reader`：读单篇论文
- `generate-mocs`：手动补刷目录页

另外 `_shared/` 存放共享配置和 MOC 生成脚本。

> 以前拆分的 `daily-papers-fetch`、`daily-papers-review`、`daily-papers-notes`、`published-review-lite`、`review-rich` 已在 v2 整合中被删除或内部化，不再作为独立 skill 暴露。相关模板和参考文档已移入 `daily-papers/templates/` 和 `daily-papers/references/`。

## 🧪 最小可运行 Demo

```bash
# 第一次运行（会停在 Published PDF 检查点）
python skills/daily-papers/orchestration/run_daily_pipeline.py

# 导入并下载 PDF 后恢复
python skills/daily-papers/state/resume_published.py
```

首次暂停时会生成 Zotero handoff 文件：

```text
/tmp/published_top20.ris
/tmp/published_top20.bib
/tmp/published_top20_doi.txt
```

可选全自动（不等 PDF，低置信继续）：

```bash
# 在 user-config.json 打开 published_channel.auto_continue_without_pdf=true
python skills/daily-papers/orchestration/run_daily_pipeline.py
```

## 🎾 进阶用法

日常使用只需 `今日论文推荐` 一句话即可触发完整流水线。流水线内部各阶段（抓取 → 点评 → 笔记）由 `daily-papers` 自动编排，不需要手动分步执行。

如果你想做本地定时任务（比如每天早上6点自动运行），可以直接让 Claude 按你的系统环境帮你配置。

## 🐶 FAQ

**可以一步跑完整流程吗？**

默认会在 Published PDF 检查点暂停（这是设计行为）。先导入 Zotero 并手动下载 PDF，再执行 `resume_published.py` 继续。
如果你明确要强制全自动，可将 `published_channel.auto_continue_without_pdf=true`，但 Published rich 会带低置信度标记。

**目录页会自动刷新吗？**

默认会。读单篇论文和跑完整的每日推荐流程时，结束后通常都会自动刷新一次。`更新索引` 更像是手动补刷入口。

**不用 Zotero 可以吗？**

可以。每日推荐不依赖 Zotero，单篇阅读也支持直接输入 arXiv 链接或本地 PDF。Zotero 主要用于已有文献库的搜索和归类。

**不用 Obsidian 可以吗？**

可以。输出本质上是 Markdown 文件，不强绑 Obsidian；只是如果你希望使用 `[[双向链接]]`、图谱和目录页索引，Obsidian 会更顺手。

**可以用来辅助论文写作吗？**

可以，比较适合用来整理 related work、维护笔记库和生成阅读提纲。AI 生成的内容建议自己核验后再使用。

**默认会动我的 git 仓库吗？**

不会。`commit / push` 默认关闭，只有你自己打开配置后才会执行。

## ⚠️ 免责声明

这是我个人研究工作流的开源整理。AI 生成的推荐、点评和笔记可能有事实错误或遗漏，所以更适合作为辅助工具，而不是直接替代你的研究判断。

另外，这套东西难免会有 bug，平台和环境适配问题也很正常；如果你遇到小问题，最省事的办法通常就是直接让 AI 帮你一起改。

## ⭐ 支持这个项目

如果这套 workflow 对你有帮助，欢迎提 PR、开 issue，或者顺手点个 Star。像 [`codex+humanoid`](https://github.com/huangkiki/dailypaper-skills/tree/codex%2Bhumanoid) 这种兼容性适配也很欢迎，一起补会比我一个人慢慢填坑快很多。

[![Star History Chart](https://api.star-history.com/svg?repos=huangkiki/dailypaper-skills&type=Date)](https://www.star-history.com/#huangkiki/dailypaper-skills&Date)

## License

Apache-2.0. See `LICENSE`.
