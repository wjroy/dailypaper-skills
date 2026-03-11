# 概念归类规则

概念库位置：`{CONCEPTS_PATH}`

按 `active_domain` 选择分类。优先少而稳定，不追求过细目录树。

## geo_timeseries_fm

| 子目录 | 说明 | 示例 |
| --- | --- | --- |
| `1-岩土监测与预测` | 基坑、隧道、沉降、变形预测 | settlement, deformation, foundation pit |
| `2-时空与不确定性` | 时空建模、概率预测、区间估计 | spatiotemporal, quantile, conformal |
| `3-基础模型与机器学习` | 预训练、迁移学习、通用建模方法 | foundation model, transformer, LoRA |
| `4-工程应用与数据` | 监测系统、现场数据、数字孪生 | field monitoring, digital twin |
| `5-Survey` | 综述和 benchmark | survey, benchmark |
| `0-待分类` | 无法判断时使用 | - |

## intelligent_construction

| 子目录 | 说明 | 示例 |
| --- | --- | --- |
| `1-施工机器人与自动化` | 施工机器人、自主作业、机器人平台 | construction robot, autonomous excavation |
| `2-岩土与安全监测` | 岩土场景、安全监测、预警 | geotechnical, safety monitoring |
| `3-数字孪生与感知控制` | BIM/CIM、感知、定位、控制 | digital twin, LiDAR, MPC |
| `4-基础模型与机器学习` | 通用机器学习方法 | transformer, foundation model |
| `5-Survey` | 综述和 benchmark | survey, benchmark |
| `0-待分类` | 无法判断时使用 | - |

## 概念笔记模板

```markdown
---
type: concept
domain: {active_domain}
aliases: []
---

# 概念名称

## 定义

## 为什么重要

## 代表工作
- [[Paper1]]

## 相关概念
- [[Related Concept]]
```
