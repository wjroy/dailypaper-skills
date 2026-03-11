---
name: daily-papers
description: |
  每日论文推荐的一句话总入口（v2 双通道 + pause/resume）。用户说"今日论文推荐""过去3天论文推荐""过去一周论文推荐"
  "最近3天论文""看看这周有啥论文"时使用。

  默认会在 Published PDF 检查点暂停，待用户 Zotero 手动下载 PDF 后再恢复继续。
---

# 每日论文推荐

这是面向用户的一句话入口。对用户来说，正常只需要说一次：

- `今日论文推荐`
- `过去3天论文推荐`
- `过去一周论文推荐`

## 执行原则

1. 先识别时间范围：
   - `今日论文推荐`、`每日推荐`、`今日论文` -> 当天
   - `过去3天论文推荐`、`最近3天论文` -> 3 天
   - `过去一周论文推荐`、`看看这周有啥论文` -> 7 天
2. 首次运行调用 `skills/daily-papers/orchestration/run_daily_pipeline.py`。
3. 如果返回 `awaiting_published_pdf_import`：
   - 明确告诉用户已暂停（这是预期行为）
   - 告知 Zotero 导入文件路径（RIS/Bib/DOI）
   - 告知恢复命令：`python skills/daily-papers/state/resume_published.py`
4. 用户完成 PDF 下载后，调用 `resume_published.py` 继续。
5. 恢复完成后执行笔记生成阶段（参见 `references/notes-stage-guide.md`，默认只处理"必读"）。
6. 全部完成后，用一句话告诉用户：
   - final 推荐文件已生成
   - 重点论文笔记已生成多少篇
   - 目录页是否已自动刷新

## 内部资源

本 skill 包含以下内部阶段资源（非独立 skill，由流水线自动调度）：

- `references/notes-stage-guide.md` — 笔记生成阶段详细指南
- `templates/lite_review_template.md` — Published 通道 metadata-first 轻点评模板
- `templates/rich_review_template.md` — Rich review 评审模板

## 重要约束

- 不要先要求用户手动跑 `跑一下论文抓取 / 点评 / 笔记`。
- 这些命令是内部流水线和调试入口，不是首页主交互。
- 如果用户明确只想跑其中一步，参照内部阶段资源处理。
- 只有在 `published_channel.auto_continue_without_pdf=true` 时，才允许跳过人工 PDF 检查点自动继续。

## 自动化

- 本 skill 本身就是"一步跑完整流水线"的入口。
- 如果用户想做本地定时任务，默认也应该触发这一句，而不是写死三条内部命令。
