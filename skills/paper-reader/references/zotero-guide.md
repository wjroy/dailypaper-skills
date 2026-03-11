# Zotero 读取指南

`paper-reader` 通过 Zotero 做两件事：条目检索，以及分类批量读取。

## 常用命令

```bash
python skills/paper-reader/assets/zotero_helper.py search "paper title"
python skills/paper-reader/assets/zotero_helper.py info {item_id}
python skills/paper-reader/assets/zotero_helper.py pdf {item_id}
python skills/paper-reader/assets/zotero_helper.py collections
python skills/paper-reader/assets/zotero_helper.py find-collection "机器人"
python skills/paper-reader/assets/zotero_helper.py papers {collection_id} --recursive
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

## 分类批读流程

1. 用 `find-collection` 或 `collections` 定位分类
2. 用 `papers {collection_id} --recursive` 列出候选论文
3. 对目标论文逐篇读取并按同一模板输出

`zotero_helper.py` 只提供只读查询，不修改 Zotero 分类结构。
