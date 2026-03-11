# dailypaper-skills

面向 Obsidian 的紧凑论文流水线仓库：发现论文、生成研究笔记、刷新索引。

对最终用户，公开入口只有 3 个：`daily-papers`、`paper-reader`、`generate-mocs`。其余抓取、排序、PDF enrich、合并、笔记回填都属于内部实现模块，不单独触发。

## 这套东西做什么

- 生成每日论文推荐，输出到 `DailyPapers/`
- 读取单篇论文或一个 Zotero 分类，先输出统一格式的研究笔记，再按可用性补充轻量图像增强
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
- `skills/paper-reader`：读取单篇论文，或按同一模板批量读取一个 Zotero 分类；默认先完成文本研究笔记，再按需补充图像增强
- `skills/generate-mocs`：手动刷新论文目录页和概念目录页

## 论文推荐的运行方式

说 `今日论文推荐` 后，系统自动完成以下工作：

1. **发现论文**：从已发表期刊和 arXiv 预印本两个方向同时搜索
2. **筛选排序**：按你的领域偏好打分、去重、排序
3. **生成推荐页**：输出一份当日推荐 Markdown 到 `DailyPapers/`
4. **生成笔记**（最佳努力）：对标记为 must_read 的论文调用 paper-reader 生成研究笔记

### 如果有些论文缺少本地 PDF

当已发表渠道的候选论文需要完整 PDF 才能做深度评审，但本地尚未导入时：

- 系统**不会停下来等你**
- 而是先用已有数据（预印本 + 已有 PDF 的论文）生成**临时推荐页**
- 同时给你一份**待补 PDF 清单**（论文标题 + DOI）
- 你把 PDF 补进 Zotero 或本地路径后，**重新说一次** `今日论文推荐` 即可——系统会自动检测到 PDF 已就位并继续完成剩余评审

### 笔记生成是最佳努力

- 单篇笔记生成失败不会阻断其他论文的笔记，也不会影响推荐页
- 失败的论文在推荐页里标注为"笔记待生成"
- 你随时可以单独用 `读一下这篇论文 ...` 补生成

## 配置方式

共享配置仍采用单一路径策略：提交 `user-config.example.json`，本机只改 `user-config.local.json`。

共享配置加载顺序：`DEFAULT_CONFIG` -> `skills/_shared/user-config.local.json`

`skills/_shared/user-config.example.json` 只用于示例，不再被运行时当作真实配置覆盖默认值。

`paper-reader` 自己额外维护：

- `skills/paper-reader/paper-reader.config.example.json`：字段示例
- `skills/paper-reader/paper-reader.local.json`：本地真实输出路径和图像增强偏好
- `skills/paper-reader/paper-reader.state.json`：初始化缓存和后端状态

如果 `paper-reader.local.json` 不存在，`paper-reader` 会自动进入临时模式，继续完成文本研究笔记。

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
- `全部候选图 (All Candidate Figures)`：面向归档；无图时会写简洁占位状态

如果你想改输出结构，只改 `obsidian-templates/论文笔记模板.md`。

## 输出到 Obsidian 的结果

- 推荐页：`{vault}/DailyPapers/YYYY-MM-DD-论文推荐.md`
- 论文笔记：`{vault}/论文笔记/.../*.md`
- 概念笔记：`{vault}/论文笔记/_概念/.../*.md`
- 论文图片：`{output_root}/assets/papers/<paper_id>/figures/*.png`
- 图像 manifest：`{output_root}/assets/papers/<paper_id>/figures/figure_manifest.json`
- 目录页：由 `generate-mocs` 或自动刷新生成

## 安装

前置环境：

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code)
- [Obsidian](https://obsidian.md/)
- [Python 3.8+](https://www.python.org/)
- [Zotero](https://www.zotero.org/)（已发表论文的 PDF 补齐和 Zotero 读取会用到）

可选图像增强：

- 优先推荐 [PyMuPDF](https://pymupdf.readthedocs.io/)
- `poppler-utils` 仅作为可选增强后端，不再是主流程必需依赖

在仓库根目录运行：

```bash
mkdir -p ~/.claude/skills
cp -r ./skills/* ~/.claude/skills/
cp -r ./obsidian-templates ~/.claude/skills/obsidian-templates
cp ~/.claude/skills/_shared/user-config.example.json ~/.claude/skills/_shared/user-config.local.json
```

然后把 `~/.claude/skills/_shared/user-config.local.json` 改成你的本机配置。

如果你想让 `paper-reader` 直接写入自己的 Obsidian 路径，再额外复制：

```bash
cp ~/.claude/skills/paper-reader/paper-reader.config.example.json ~/.claude/skills/paper-reader/paper-reader.local.json
```

不复制也可以；此时 `paper-reader` 会进入临时模式，但仍能正常生成文本研究笔记。

直接跑单篇文本优先阅读时，建议使用：

```bash
python skills/paper-reader/scripts/run_paper_reader.py /path/to/paper.pdf
```

## FAQ

**一句话能让它做什么？**

可以。最常见就是 `今日论文推荐`、`读一下这篇论文 ...`、`更新索引`。

**有些论文缺 PDF 怎么办？**

系统会先用已有数据生成临时推荐页，并给出待补 PDF 清单（标题 + DOI）。补好后重新说 `今日论文推荐`，系统自动检测并继续。

**笔记生成失败了怎么办？**

单篇失败不影响其他笔记和推荐页。推荐页里会标注"笔记待生成"，你随时可以用 `读一下这篇论文 ...` 单独补生成。

**Zotero 在流程里做什么？**

它主要承担已发表论文的 PDF 补齐，以及 `paper-reader` 的条目检索、附件定位、分类批读。

**`paper-reader` 现在会不会因为图像环境没配好而卡住？**

不会。文本研究笔记永远先完成；图像增强只在已初始化且后端可用时自动执行，否则会直接降级到 text-only。

**首次使用图像增强会发生什么？**

首次读论文时，如果状态还是 `unknown`，会只问一次你是否要做图像增强初始化，并明确说明不配置也不会影响本次研究笔记输出。你的选择会缓存到 `skills/paper-reader/paper-reader.state.json`。

**Obsidian 里的图片放哪里？**

已配置时统一落在 `assets/papers/<paper_id>/figures/`；未配置时写入 `skills/paper-reader/.temp-output/assets/papers/<paper_id>/figures/`。笔记里统一用相对 `![[assets/papers/<paper_id>/figures/<filename>.png]]`。

**Obsidian 在流程里做什么？**

它是最终输出仓库：推荐页、论文笔记、概念笔记、MOC 都直接写进去。

**目录页会自动刷新吗？**

默认会；也可以手动说 `更新索引`。

**默认会提交我的个人路径吗？**

不会。示例配置和本地配置已经拆开。

## License

Apache-2.0. See `LICENSE`.
