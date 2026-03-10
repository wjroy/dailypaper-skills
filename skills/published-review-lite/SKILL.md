---
name: published-review-lite
description: |
  Published 通道 metadata-first 轻点评。读取 /tmp/published_lite_50.json，
  只基于 metadata/abstract 做筛选与排序，不依赖 PDF，不假装看过全文。
---

# Published Review Lite

你是 Published 通道的 `review-lite` 分诊器。

目标：
- 读取 `/tmp/published_lite_50.json`
- 对 50 篇 metadata-first 候选做轻点评
- 明确每篇是否值得获取 PDF
- 输出 markdown 报告 + JSON 决策结果

## 输入与边界

- 输入文件：`/tmp/published_lite_50.json`
- 允许证据：`title`、`abstract`、`authors`、`venue`、`publication_type`、`source_providers`、评分分解字段
- 禁止行为：
  - 禁止写“通读全文后”
  - 禁止虚构实验细节/图表结果
  - 禁止把 review-lite 写成 review-rich

## 执行步骤

1. 读取 `/tmp/published_lite_50.json`，若不存在则提示先运行 Published 通道前半段。
2. 使用 `templates/lite_review_template.md` 的结构输出 `markdown` 报告。
3. 对每篇给出：
   - `decision`: `fetch_pdf | hold | skip`
   - `confidence`: 0~1
   - `reason`: 1~2 句，必须是 metadata/abstract 证据
4. 生成两个输出：
   - `/tmp/published_lite_review_report.md`
   - `/tmp/published_lite_reviewed_50.json`

## 决策规则

- `fetch_pdf`：
  - 与 active_domain 高相关，且 `final_meta_score` 较高；或
  - 尽管新颖性不确定，但方法价值明显、值得全文确认。
- `hold`：
  - 有一定相关性，但创新点/证据强度不足。
- `skip`：
  - 低相关，或负面关键词/主题偏离明显。

必须明确写出：
- “该判断仅基于 metadata 与 abstract，不代表全文结论”。

## 输出要求

- `markdown` 报告中按三组汇总：
  - `A. 建议立即获取 PDF (fetch_pdf)`
  - `B. 观察池 (hold)`
  - `C. 暂不跟进 (skip)`
- 每条建议包含：
  - 论文标题
  - metadata 证据要点
  - 是否建议获取 PDF

## 真实性要求

- 对缺失字段要诚实写 `metadata 未提供`。
- 不允许把未验证信息写成既定事实。
