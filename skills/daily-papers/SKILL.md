---
name: daily-papers
description: |
  每日论文推荐的总入口。用户说“今日论文推荐”“过去3天论文推荐”
  “过去一周论文推荐”“最近3天论文”“看看这周有啥论文”时使用。

  这是唯一公开的推荐 skill。抓取、rich review、notes 等都是内部阶段，
  不再作为独立 skill 暴露。
---

# 每日论文推荐

对用户来说，正常只需要一句：

- `今日论文推荐`
- `过去3天论文推荐`
- `过去一周论文推荐`

## 执行原则

1. 先识别时间范围。
2. 调用 `skills/daily-papers/orchestration/run_daily_pipeline.py`。
3. 如果返回 `awaiting_published_pdf_import`：
   - 明确告诉用户这是预期暂停点
   - 告知 Zotero 导入文件路径
   - 告知恢复命令：`python skills/daily-papers/state/resume_published.py`
4. 用户完成 PDF 下载后，调用 `resume_published.py` 继续。
5. 完成后汇报：
   - 推荐文件位置
   - 生成了多少篇 must-read 笔记
   - 目录页是否已刷新

## 内部资源

以下内容都属于 `daily-papers` 内部阶段资源：

- `references/notes-stage-guide.md`
- `templates/lite_review_template.md`
- `templates/rich_review_template.md`

## 重要约束

- 不要让用户手动分步跑“抓取 / 点评 / 笔记”。
- 这些都是内部流程，不是首页主交互。
- 只有在 `published_channel.auto_continue_without_pdf=true` 时，才允许跳过人工 PDF 检查点。
- `daily-papers` 负责统一编排，`paper-reader` 只负责单篇阅读。
