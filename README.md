# dailypaper-skills

面向 Obsidian 的紧凑论文流水线仓库：发现论文、生成研究笔记、刷新索引。

对最终用户，公开入口只有 3 个：`daily-papers`、`paper-reader`、`generate-mocs`。其余抓取、排序、PDF enrich、合并、笔记回填都属于内部实现模块，不单独触发。

## 这套东西做什么

- 生成每日论文推荐，输出到 `DailyPapers/`
- 读取单篇论文或一个 Zotero 分类，先强制提图，再输出统一格式的研究笔记
- 维护 Obsidian 里的论文目录页和概念目录页

最终产物通常落在你的 Obsidian 库里：

```text
ObsidianVault/
├── DailyPapers/YYYY-MM-DD-论文推荐.md
├── 论文笔记/.../*.md
└── 论文笔记/_概念/.../*.md
```

## 最小用法

平时只需要 3 句话：

```text
今日论文推荐
读一下这篇论文 https://arxiv.org/abs/2509.24527
更新索引
```

其他公开说法只保留这些：

```text
过去3天论文推荐
过去一周论文推荐
读一下这篇论文 https://arxiv.org/abs/2509.24527
快速看一下这篇论文 https://arxiv.org/abs/2509.24527
批判性分析这篇论文 https://arxiv.org/abs/2509.24527
读一下 Zotero 里的 Diffusion Policy
批量读一下 Zotero 里 机器人 这个分类下的论文
更新索引
```

## 3 个公开 skill

- `skills/daily-papers`：每日推荐总入口，负责整条推荐流水线
- `skills/paper-reader`：读取单篇论文，或按同一模板批量读取一个 Zotero 分类；默认先跑 recall-first 图像提取与 Obsidian 落盘
- `skills/generate-mocs`：手动刷新论文目录页和概念目录页

## Published / Preprint 双通道

- Published 通道：先做多源 metadata 召回和分诊，再停在 PDF 检查点，等你把需要的 PDF 补进 Zotero 或本地路径
- Preprint 通道：直接从 arXiv 拉取并 enrich
- Merge：两路 rich review 合并后渲染推荐页，再把 `must_read` 论文送进笔记生成

如果 Published 通道返回 `awaiting_published_pdf_import`，这是正常检查点，不是失败。补好 PDF 后继续运行：`python skills/daily-papers/state/resume_published.py`。

## 配置方式

本仓库采用单一路径策略：提交 `user-config.example.json`，本机只改 `user-config.local.json`。

加载顺序：`DEFAULT_CONFIG` -> `skills/_shared/user-config.example.json` -> `skills/_shared/user-config.local.json`

第一次安装后：

1. 复制 `skills/_shared/user-config.example.json`
2. 重命名为 `skills/_shared/user-config.local.json`
3. 只修改你的本机路径和领域配置

需要先改的通常只有：

- `paths.obsidian_vault`
- `paths.zotero_db`
- `paths.zotero_storage`
- `active_domain`
- `domain_profiles.<name>.queries`

仓库不会提交你的个人路径；`.gitignore` 已忽略 `skills/_shared/user-config.local.json`。

当前主线领域是智能建造 / 岩土监测 / 时序预测 / foundation model，内置 profile 保留：

- `intelligent_construction`
- `geo_timeseries_fm`

## 单一笔记模板

论文笔记只遵循一个 canonical template：`obsidian-templates/论文笔记模板.md`

- `paper-reader` 按这个模板生成
- `daily-papers` 的 notes stage 按这个模板做最低质量检查
- README 展示的也是这个模板

图像章节也统一收在这个模板里：

- `关键图示 (Key Figures)`：面向阅读，优先展示方法/框架图和核心结果图
- `全部候选图 (All Candidate Figures)`：面向完整保留，尽量展示所有候选图

如果你想改输出结构，只改 `obsidian-templates/论文笔记模板.md`。

## 输出到 Obsidian 的结果

- 推荐页：`{vault}/DailyPapers/YYYY-MM-DD-论文推荐.md`
- 论文笔记：`{vault}/论文笔记/.../*.md`
- 概念笔记：`{vault}/论文笔记/_概念/.../*.md`
- 论文图片：`{vault}/assets/papers/<paper_id>/figures/*.png`
- 图像 manifest：`{vault}/assets/papers/<paper_id>/figures/figure_manifest.json`
- 目录页：由 `generate-mocs` 或自动刷新生成

## 安装

前置环境：

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code)
- [Obsidian](https://obsidian.md/)
- [Python 3.8+](https://www.python.org/)
- [`poppler-utils`](https://poppler.freedesktop.org/)
- [Zotero](https://www.zotero.org/)（Published PDF 检查点和 Zotero 读取会用到）

在仓库根目录运行：

```bash
mkdir -p ~/.claude/skills
cp -r ./skills/* ~/.claude/skills/
cp -r ./obsidian-templates ~/.claude/skills/obsidian-templates
cp ~/.claude/skills/_shared/user-config.example.json ~/.claude/skills/_shared/user-config.local.json
```

然后把 `~/.claude/skills/_shared/user-config.local.json` 改成你的本机配置。

## FAQ

**一句话能让它做什么？**

可以。最常见就是 `今日论文推荐`、`读一下这篇论文 ...`、`更新索引`。

**什么时候会停在 Published PDF 检查点？**

当 Published 候选论文需要本地 PDF 做 rich review，但 `published_pdf_inputs.json` 还没补齐时就会暂停。

**如何继续？**

补好 PDF 后运行 `python skills/daily-papers/state/resume_published.py`。

**Zotero 在流程里做什么？**

它主要承担 Published 通道的 PDF 补齐，以及 `paper-reader` 的条目检索、附件定位、分类批读。

**为什么 `paper-reader` 现在默认会提很多图？**

因为这里采用 recall-first 策略：优先减少漏图和返工，而不是只挑最少几张图。关键方法图、框架图、结果图如果 embedded extraction 不完整，会自动触发 full-page rendered fallback。

**Obsidian 里的图片放哪里？**

统一落在 `assets/papers/<paper_id>/figures/`，笔记里统一用 `![[assets/papers/<paper_id>/figures/<filename>.png]]`。

**Obsidian 在流程里做什么？**

它是最终输出仓库：推荐页、论文笔记、概念笔记、MOC 都直接写进去。

**目录页会自动刷新吗？**

默认会；也可以手动说 `更新索引`。

**默认会提交我的个人路径吗？**

不会。示例配置和本地配置已经拆开。

## License

Apache-2.0. See `LICENSE`.
