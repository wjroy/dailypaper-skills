# Zotero 单篇读取指南

`paper-reader` 只依赖 Zotero 的单篇检索和附件定位，不再承担批量阅读入口。

## 常用命令

```bash
python3 assets/zotero_helper.py search "paper title"
python3 assets/zotero_helper.py info {item_id}
python3 assets/zotero_helper.py pdf {item_id}
python3 assets/zotero_helper.py collections
```

## 单篇读取流程

1. 用标题或关键词搜索条目
2. 用 `info` 确认标题、作者、DOI、当前分类
3. 用 `pdf` 拿附件路径
4. 如果没有 PDF，再回退 arXiv / DOI / URL

## 读取决策

优先级：

1. 本地 PDF
2. arXiv HTML
3. PDF URL
4. DOI / 期刊页

## 什么时候更新分类

只有在你明确要整理笔记库时，才需要再单独调用分类脚本。

`paper-reader` 默认关注单篇阅读，不要求每次都改 Zotero 分类结构。
