# 笔记质量规则

`paper-reader` 的目标不是生成最长的笔记，而是生成可信、可复用的单篇研究笔记。

## 基本原则

1. 先保证问题、方法、主要发现、局限写清楚
2. figure / formula / table 能提取就保留，提不到就诚实记录
3. 不确定的内容降级表述，不要补写成确定事实

## 公式

- 只保留真正支撑理解的方法公式
- 写公式时同时写用途和符号含义
- 变量名必须与原文一致
- `$$` 前后保留空行，避免 Obsidian 渲染失败

## 图片

- 优先保留方法总览图、实验主图、关键结果图
- 图片来源优先：arXiv HTML -> 项目主页 -> PDF 提取
- 图片缺失时在 `Missing Field Report` 里说明原因

## 表格

- 优先保留最关键的结果表
- 表太长时允许摘录核心列，但要在缺失字段报告中说明是 partial

## 最低自检

- [ ] `Research Problem` 已写
- [ ] `Method Summary` 已写
- [ ] `Main Findings` 已写
- [ ] `Limitations` 已写
- [ ] `Inspiration for My Research` 已写
- [ ] 图片/公式/表格的缺失已记录
- [ ] `extraction_confidence` 已填写
