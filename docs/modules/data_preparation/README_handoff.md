# 数据准备与总体探索 · 成员1

成员1原分析贡献：梁桂荣。目录迁移保留现有数据、清洗规则和基础结果。

## 下游读取

- data/processed/train_clean.csv：24896条训练回答，未删行、未填补属性。
- data/processed/test_features_clean.csv：6224条测试特征，真实选择未给出。
- data/processed/image_pair_summary.csv：8049个无序图片对的全数据汇总，仅作描述。
- data/splits/validation_split.csv：全组共同图片对划分。

字段含义见本目录data_dictionary.md，清洗规则和验证边界见cleaning_rules.md。全组使用公共数据，不再复制到个人目录。

## 完整重建

把课程train.csv、test.csv、test_example.csv和全部images/放入data/raw/，安装根目录依赖后运行：

```powershell
python scripts/run_data_preparation.py
python scripts/audit_data_preparation.py --rerun
```

路径读取configs/default.json，与工作目录无关。完整准备保留原有强校验：引用图片必须存在、通过Pillow验证及完整解码。缺少CSV或图片时明确报错，不生成假装通过图片检查的数据。

清洗表写data/processed/，划分写data/splits/，表图与新运行/审计记录写outputs/data_preparation/，完整审计更新本目录quality_review.md。清洗与随机划分算法未改变，种子仍为2026。

## 本次验证边界

迁移时核对公共数据与原交接字节一致，用构造图片测试方向、缺失保留和原表不变性。本地缺少完整课程图片，未重跑1558张图片解码。历史metadata与审计在docs/provenance/data_preparation/，不能当作重构后的新审核证据。

报告章节为reports/sections/data_preparation.md。仅供教育与研究。
