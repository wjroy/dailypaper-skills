# 图片排错

`paper-reader` 现在把图像提取当成标准流程，而不是可选补丁。默认顺序是：

0. `skills/paper-reader/scripts/run_figure_pipeline.py`
1. `skills/paper-reader/scripts/extract_embedded_figures.py`
2. `skills/paper-reader/scripts/render_figure_pages.py`
3. `skills/paper-reader/scripts/build_figure_manifest.py`
4. `skills/paper-reader/scripts/link_figures_to_note.py`

## 为什么要这样做

- 单一 embedded extraction 容易漏掉 vector / composite figure
- recall-first 的目标是减少返工，而不是最小化插图数量
- 如果 clean crop 做不到，保留 full-page rendered fallback 也比漏图更好

## 自动 fallback 触发条件

满足任一条件就会自动触发 rendered fallback：

- embedded figure count 偏少
- 方法图 / 框架图缺失
- 结果图缺失
- figure-like 页面明显多于 embedded 图数量

## 常见问题

- PDF 里很多是矢量图，`pdfimages` 抽不出完整结果，这时会保留 full-page render
- 某些页面会同时包含 caption、表格、结果图，manifest 会优先保留，不轻易丢弃
- 如果 caption 提取不到，会退回页面文本关键词做角色判断
- 如果图片文件没成功写进 vault，笔记不会插入坏 wiki-link

## 最小检查项

- `embedded figures extracted: X`
- `rendered fallback pages: Y`
- `total candidate figures: Z`
- `key method/framework figures: A`
- `key result figures: B`
- `figure manifest saved to: ...`
- `note linked with figures: yes/no`

## Obsidian 落盘规则

- 图片目录：`assets/papers/<paper_id>/figures/`
- manifest：`assets/papers/<paper_id>/figures/figure_manifest.json`
- 笔记引用：`![[assets/papers/<paper_id>/figures/<filename>.png]]`
- 禁止写本机绝对路径

## 仍然可能不完美的情况

- 一个整页里有多个复杂子图时，当前 fallback 先保留 full-page render，不强制做脆弱裁剪
- 某些 PDF 页面文字层很差时，caption 和角色判断会降级到 `unknown`
- 图片数量很多时，`全部候选图` 会比较长，但这是 recall-first 的有意选择
