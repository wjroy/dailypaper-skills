# 图片排错

## 首选顺序

1. `extract_arxiv_figures.py`
2. `https://arxiv.org/html/{arxiv_id}`
3. 项目主页
4. `pdfimages -png`

## 常见问题

- arXiv HTML 里有 icon / logo，容易误当成 Figure
- 相对路径拼接时可能把 `arxiv_id` 重复一遍
- 某些论文只有 PDF 里有完整图片

## 快速检查

- 图片 URL 是否能直接打开
- 文件是否明显不是正文 figure
- 文件过小（如 `<10KB`）时是否提到了错误资源

## 本地化兜底

笔记保存后可运行：

```bash
python3 ../daily-papers/download_note_images.py "{笔记路径}"
```

不可访问的外链会下载到本地并替换为 wikilink。
