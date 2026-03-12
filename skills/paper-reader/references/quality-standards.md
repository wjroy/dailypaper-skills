# 笔记质量规则

`paper-reader` 的目标不是生成最长的笔记，而是生成可信、可复用的单篇研究笔记。

## 基本原则

1. 先保证问题、方法、主要发现、局限写清楚
2. 文本研究笔记是主流程，图像增强只做补充
3. 不确定的内容降级表述，不要补写成确定事实

## 公式

- 只保留真正支撑理解的方法公式
- 写公式时同时写用途和符号含义
- 变量名必须与原文一致
- 写进 `Key Formula` section；提不到就在 `Missing Field Report` 里说明

## 图片

- 优先保留对理解最关键的方法图和结果图
- 使用统一的 `Figures` 区块表达图像覆盖状态
- embedded extraction 不稳定时，自动降级到部分图像模式或无图回退模式
- 无法干净裁剪时保留 full-page render，而不是跳过
- 图片必须保存到输出根目录下的 `assets/papers/<paper_id>/figures/`
- 笔记里统一使用相对 wiki-link，不能写本机绝对路径
- 图片缺失时在 `Missing Field Report` 和 `Source Notes` 里说明原因

## 表格

- 优先保留最关键的结果表
- 表太长时允许摘录核心列，但要在缺失字段报告中说明是 partial

## 最低自检

- [ ] `Research Problem` 已写
- [ ] `Method Summary` 已写
- [ ] `Figures` 已写或已记录缺失
- [ ] `Key Formula` 已写或已记录缺失
- [ ] `Main Findings` 已写
- [ ] `Limitations` 已写
- [ ] `Inspiration for My Research` 已写
- [ ] `Source Notes` 已写
- [ ] 若启用了图像增强，`figure_manifest.json` 已生成；否则已写明无图回退状态
- [ ] 图片/公式/表格的缺失已记录
- [ ] `extraction_confidence` 已填写
