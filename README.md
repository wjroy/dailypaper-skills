# dailypaper-skills

面向 Obsidian 研究工作流的 3 个紧凑 skill：

- `daily-papers`：每日论文推荐总入口
- `paper-reader`：单篇论文阅读 -> 研究笔记输出
- `generate-mocs`：手动刷新论文/概念目录页

这套仓库现在只保留这 3 个公开入口。抓取、rich review、笔记回填等都已经收进 `daily-papers` 内部，不再作为独立 skill 暴露。

## 这套东西做什么

- 跑每日论文推荐，输出 `DailyPapers/YYYY-MM-DD-论文推荐.md`
- 读取单篇 arXiv / 本地 PDF / Zotero 条目，生成结构化研究笔记
- 自动维护 Obsidian 里的论文目录页和概念目录页

最终产物通常长这样：

```text
ObsidianVault/
├── DailyPapers/YYYY-MM-DD-论文推荐.md
├── 论文笔记/.../*.md
└── 论文笔记/_概念/.../*.md
```

模板见 `obsidian-templates/论文笔记模板.md`。

## 怎么用

最常用的 3 句话：

```text
今日论文推荐
读一下这篇论文 https://arxiv.org/abs/2509.24527
更新索引
```

其他常见说法：

```text
过去3天论文推荐
过去一周论文推荐
读一下这篇论文 ~/Downloads/paper.pdf
快速看一下这篇论文 https://arxiv.org/abs/2509.24527
读一下 Zotero 里的 Diffusion Policy
```

`daily-papers` 负责完整推荐流水线，`paper-reader` 只负责单篇阅读，`generate-mocs` 只负责补刷目录。

## 安装

前置环境：

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code)
- [Obsidian](https://obsidian.md/)
- [Python 3.8+](https://www.python.org/)
- [`poppler-utils`](https://poppler.freedesktop.org/)（`apt install poppler-utils` / `brew install poppler`）
- [Zotero](https://www.zotero.org/)（可选）

在仓库根目录运行：

```bash
mkdir -p ~/.claude/skills
cp -r ./skills/* ~/.claude/skills/

VAULT=~/ObsidianVault
mkdir -p "$VAULT/DailyPapers" \
  "$VAULT/论文笔记/_概念/0-待分类" \
  "$VAULT/论文笔记/_待整理"
```

## 配置

主配置文件：`~/.claude/skills/_shared/user-config.json`

当前配置心智只围绕 4 组：

- `active_domain`
- `domain_profiles`
- `published_channel`
- `preprint_channel`

常改的项：

| 配置项 | 说明 |
| --- | --- |
| `paths.obsidian_vault` | Obsidian 库路径 |
| `paths.zotero_db` | Zotero 数据库路径 |
| `paths.zotero_storage` | Zotero 附件路径 |
| `active_domain` | 当前激活的领域 |
| `domain_profiles.<name>.queries` | 领域检索 query |
| `domain_profiles.<name>.positive_keywords` | 领域正向关键词 |
| `domain_profiles.<name>.negative_keywords` | 领域排除词 |
| `domain_profiles.<name>.boost_keywords` | 领域加分词 |

内置 profile：

- `geo_timeseries_fm`
- `intelligent_construction`
- `biology`

默认行为：

- `auto_refresh_indexes = true`
- `git_commit = false`
- `git_push = false`

## v2 流水线

`daily-papers` 当前是双通道发现 + 内部汇合：

1. Published 通道：`paper-fetcher` 多源 metadata 召回 -> lite 分诊 -> Zotero/PDF 检查点 -> PDF enrich -> rich review
2. Preprint 通道：`arXiv / bioRxiv` 抓取 -> enrich -> rich review
3. 汇合层：输出 `/tmp/daily_review_merged.json`
4. 内部 notes stage：只给 must-read 论文生成笔记并回填推荐页

主入口仍然只有一句：`今日论文推荐`。

更多实现细节见 `ARCHITECTURE.md`。

## 仓库结构

```text
skills/
├── _shared/
├── daily-papers/
├── generate-mocs/
└── paper-reader/
```

只有 3 个公开 skill：

- `daily-papers`
- `paper-reader`
- `generate-mocs`

`_shared/` 只放配置和共享脚本，不算公开 skill。

## 最小可运行 Demo

```bash
python skills/daily-papers/orchestration/run_daily_pipeline.py
python skills/daily-papers/state/resume_published.py
```

首次运行默认会在 Published PDF 检查点暂停。下载好 PDF 后再恢复继续。

## FAQ

**可以一步跑完整流程吗？**

可以。用户入口就是 `今日论文推荐`。默认只在 Published PDF 检查点暂停一次。

**paper-reader 现在负责什么？**

只负责单篇论文阅读和研究笔记生成，支持 arXiv、本地 PDF、Zotero 单条目和结构化 payload。

**不用 Zotero 可以吗？**

可以。每日推荐不依赖 Zotero；单篇阅读也支持直接输入 arXiv 链接或本地 PDF。

**目录页会自动刷新吗？**

默认会。`更新索引` 是手动补刷入口。

**默认会动我的 git 仓库吗？**

不会。只有你自己打开 `git_commit` / `git_push` 才会执行。

## License

Apache-2.0. See `LICENSE`.
