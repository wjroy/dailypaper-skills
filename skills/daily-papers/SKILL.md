---
name: daily-papers
description: |
  每日论文推荐主入口。用户说“今日论文推荐”“过去3天论文推荐”
  “过去一周论文推荐”“看看这周有啥论文”时使用。
---

# daily-papers

对用户，这就是一个稳定的科研工具，不是内部流水线调试入口。

## 公开语义

发现论文 -> 排序 -> 生成每日推荐页 -> 尽可能生成 must_read 笔记

## 必须遵守的规则

1. 每日推荐页必须优先产出，任何单个子流程失败都不能阻断主结果。
2. 缺少 published PDF 时，推荐页仍然生成，并把对应论文标记为 `PDF pending`。
3. 用户只需要补充 PDF 后重新运行 `daily-papers`。
4. 调用 `paper-reader` 生成 must_read 笔记时，单篇失败只标记 `note pending`。
5. 如果 `paper-reader` 回退到纯文本笔记，仍视为成功并添加笔记链接。
6. 不向用户暴露 checkpoint、resume、tmp 文件、状态文件或内部脚本名。

## 用户输出

只汇报：

- 推荐页位置
- 推荐数量
- 哪些论文已有笔记
- 哪些论文是 `PDF pending`
- 哪些论文是 `note pending`
