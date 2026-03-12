# Architecture

> 本文件面向维护者。最终用户只应感知 3 个公开入口：`daily-papers`、`paper-reader`、`generate-mocs`。

## Product Contract

仓库对外统一为 3 个稳定科研工具，而不是内部流水线节点：

- `daily-papers`：每日论文发现与推荐
- `paper-reader`：单篇论文阅读与研究笔记生成
- `generate-mocs`：索引刷新

维护规则：

- 公开输出不暴露 checkpoint、resume 脚本、tmp 文件、状态文件、内部脚本名、图像流水线阶段名
- 所有入口以“主任务永不阻断”为优先原则
- 文档、配置和运行时语义必须保持一致

## Unified Config Model

共享配置只保留 3 层，顺序固定：

1. `skills/_shared/user_config.py` 中的 `DEFAULT_CONFIG`
2. `skills/_shared/user-config.example.json`
3. `skills/_shared/user-config.local.json`

约束：

- `DEFAULT_CONFIG` 提供所有字段默认值，保证零配置可运行
- `user-config.example.json` 是已提交的基础配置层，运行时必须读取
- `user-config.local.json` 是用户本机覆盖层，不提交
- example 或 local 缺失都不应阻断公开 skill
- 旧的 `user-config.json` 已废弃，不再进入加载链

## daily-papers

公开语义：

发现论文 -> 排序 -> 生成每日推荐页 -> 尽可能生成 must_read 笔记

实现约束：

- Published 与 Preprint 两个来源独立运行
- 单个来源失败不阻断推荐页渲染
- Published 缺 PDF 时不暂停主流程，推荐页照常产出，并将对应论文标记为 `PDF pending`
- 用户只需补充 PDF 后重新运行 `daily-papers`
- must_read 笔记阶段为 best-effort，单篇失败只标记 `note pending`
- `paper-reader` 的异常、超时、图像失败都不得传播为 `daily-papers` 整体失败

内部主文件：

- `skills/daily-papers/orchestration/run_daily_pipeline.py`
- `skills/daily-papers/orchestration/run_published_channel.py`
- `skills/daily-papers/orchestration/run_published_rich_channel.py`
- `skills/daily-papers/orchestration/run_preprint_channel.py`
- `skills/daily-papers/merge/merge_reviewed_papers.py`
- `skills/daily-papers/render/render_daily_recommendation.py`

内部状态与中间文件允许存在，但只能留在开发层，不进入用户话术。

## paper-reader

公开语义：

读取论文 -> 提取文本 -> 尝试图像提取 -> 生成研究笔记

图像增强规则：

- 图像增强默认尝试，但不是写笔记前置条件
- 图像失败时必须自动回退，仍生成完整研究笔记
- 三种输出模式：
  - `full`：方法图和结果图都覆盖
  - `partial`：只覆盖部分关键图，并标记缺失图像
  - `none`：无图回退模式，写明 `图像覆盖：未提取`

图像依赖顺序：

1. PyMuPDF
2. poppler（`pdfimages` / `pdftoppm`）
3. 页截图
4. 无图回退

依赖缺失规则：

- 任一依赖缺失都不能阻断文本阅读
- 初始化失败不能阻断当前任务
- 首次运行只允许询问一次是否启用图像增强初始化
- 初始化状态缓存到内部状态文件 `skills/paper-reader/image_pipeline_state.json`

内部主文件：

- `skills/paper-reader/scripts/run_paper_reader.py`
- `skills/paper-reader/scripts/run_figure_pipeline.py`
- `skills/paper-reader/scripts/manage_image_enhancement.py`

## daily-papers 与 paper-reader 边界

- `daily-papers` 只把 `paper-reader` 视为可降级的公开阅读能力
- `paper-reader` 成功：推荐页回填笔记链接
- `paper-reader` 回退到无图：推荐页仍视为文本笔记成功
- `paper-reader` 完全失败：推荐页标记 `note pending`

## generate-mocs

公开语义：刷新所有索引。

内部行为是分别刷新概念索引与论文索引，但对外不暴露内部脚本名。

实现约束：

- 概念索引失败不阻断论文索引
- 论文索引失败不阻断概念索引
- 对外统一结果消息：`MOCs refreshed`

公开编排入口：

- `skills/generate-mocs/scripts/run_generate_mocs.py`

## User-Facing Output Rules

禁止进入用户输出的内容：

- checkpoint 名称
- resume 机制
- tmp 文件路径
- 状态文件路径
- 内部脚本名
- 图像流水线阶段名

这些内容只允许存在于开发文档、内部日志和维护排障流程中。
