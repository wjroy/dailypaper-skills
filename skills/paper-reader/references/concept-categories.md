# 概念自动归类规则

概念库位置：`{CONCEPTS_PATH}`

先用 `ls {CONCEPTS_PATH}` 查看已有子目录，再按当前研究领域的规则分类。

## 归类原则

1. **按 `active_domain` 选择对应的分类表**（见下方各领域子目录定义）
2. 如果概念不属于任何已定义类别，归入 `0-待分类`（应尽量避免）
3. 跨领域的通用概念（如 Transformer、GNN）归入各领域的"基础方法"类别

---

## geo_timeseries_fm / intelligent_construction 领域

| 子目录 | 归类标准 | 示例 |
|--------|----------|------|
| `1-时序预测` | 时间序列预测方法、模型 | LSTM, Transformer-TS, Informer, PatchTST |
| `2-岩土工程` | 岩土力学、基坑、隧道、边坡相关 | FEM, Mohr-Coulomb, SPT, CPT |
| `3-不确定性量化` | 概率预测、置信区间、贝叶斯方法 | Conformal Prediction, BNN, GP |
| `4-基础模型` | 预训练大模型、迁移学习 | Foundation Model, LoRA, Prompt Tuning |
| `5-时空建模` | 时空联合建模、图网络 | GNN, ST-GCN, Spatial Attention |
| `6-数字孪生` | BIM、仿真、有限元 | Digital Twin, FEM, OpenSees |
| `7-传感与物联网` | 传感器、边缘计算、实时监测 | MEMS, LoRa, Edge AI |
| `8-深度学习基础` | 通用 DL 技术、架构组件 | Transformer, CNN, Attention, Dropout |
| `9-数据集` | 数据集、benchmark | SHM Benchmark, PLAXIS Dataset |
| `0-待分类` | **仅在完全无法判断时**才用 | — |

## biology 领域

| 子目录 | 归类标准 | 示例 |
|--------|----------|------|
| `1-免疫学` | 免疫应答、T/B 细胞、抗体 | TCR, MHC, Cytokine Storm |
| `2-单细胞组学` | scRNA-seq、空间转录组、多组学 | Seurat, Scanpy, UMAP |
| `3-蛋白质与结构` | 蛋白质结构预测、分子动力学 | AlphaFold, Rosetta, MD |
| `4-基因调控` | 转录因子、表观遗传、CRISPR | Enhancer, Methylation, sgRNA |
| `5-生物信息学` | 序列比对、系统发育、基因组 | BLAST, Phylogenetics, BWA |
| `6-药物发现` | 虚拟筛选、分子生成 | SMILES, Docking, ADMET |
| `7-临床与流行病学` | 临床队列、生物标志物 | Biomarker, Hazard Ratio, ROC |
| `8-计算方法` | 深度学习与机器学习通用方法 | Transformer, GNN, VAE |
| `9-数据集` | 生物数据集、benchmark | TCGA, GEO, UniProt |
| `0-待分类` | **仅在完全无法判断时**才用 | — |

---

## 概念笔记模板

```markdown
---
type: concept
aliases: [中文别名, 英文别名]
domain: {active_domain}
---

# 概念名称

## 定义
{一句话定义}

## 数学形式
$$公式$$

## 核心要点
1. ...
2. ...

## 代表工作
- [[Paper1]]: ...
- [[Paper2]]: ...

## 相关概念
- [[相关概念1]]
- [[相关概念2]]
```
