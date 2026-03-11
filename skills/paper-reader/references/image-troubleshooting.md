# 图片排错

`paper-reader` 现在采用文本优先、图像增强可选的策略。默认顺序是：

1. 先完成全文文本解析与研究笔记主内容
2. 如果图像增强已初始化且后端可用，再调用 `skills/paper-reader/scripts/run_figure_pipeline.py`
3. `run_figure_pipeline.py` 内部按需执行：
   - `extract_embedded_figures.py`
   - `render_figure_pages.py`
   - `build_figure_manifest.py`
   - `link_figures_to_note.py`

## 为什么要这样做

- 文本研究笔记必须永远先完成
- 图像增强只作为补充视觉锚点，不能阻断阅读
- 如果 clean crop 做不到，保留 full-page rendered fallback 也比整篇失败更好

## 自动 fallback 触发条件

满足任一条件就会自动触发轻量页级 fallback：

- embedded figure count 偏少
- 方法图 / 框架图缺失
- 结果图缺失
- figure-like 页面明显多于 embedded 图数量

## 常见问题

- 优先尝试 PyMuPDF；只有可用时才用 `pdfimages` / `pdftoppm`
- PDF 里很多是矢量图，embedded extraction 抽不出完整结果时会回退到 full-page render
- 某些页面会同时包含 caption、表格、结果图，manifest 会优先保留，不轻易丢弃
- 如果 caption 提取不到，会退回页面文本关键词做角色判断
- 如果图片文件没成功写进输出目录，笔记不会插入坏 wiki-link，而是写入占位状态

## 最小检查项

- 文本研究笔记已生成
- 图像模式：`full` / `page_fallback` / `text_only`
- 图像增强是否补充成功
- 若失败，是否已自动降级到文本模式

## Obsidian 落盘规则

- 图片目录：`assets/papers/<paper_id>/figures/`（无本地配置时写到临时输出目录）
- manifest：`assets/papers/<paper_id>/figures/figure_manifest.json`
- 笔记引用：`![[assets/papers/<paper_id>/figures/<filename>.png]]`
- 禁止写本机绝对路径

## 仍然可能不完美的情况

- 一个整页里有多个复杂子图时，当前 fallback 先保留 full-page render，不强制做脆弱裁剪
- 某些 PDF 页面文字层很差时，caption 和角色判断会降级到 `unknown`
- 无图模式下会保留 `图像覆盖：未提取` 和建议关注图，不让笔记空段落
