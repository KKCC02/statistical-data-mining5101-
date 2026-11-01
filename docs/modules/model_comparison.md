# 扩展模型、验证与排名稳健性 · 成员5接入约定

状态：已交付。实现 `src/cat_arena/model_comparison/`，入口 `scripts/run_model_comparison.py`，
结果 `outputs/model_comparison/`，章节 `reports/sections/model_comparison.md`，已接入 `scripts/run_all.py`。

## 输入

`data/processed/train_clean.csv`（经 `cat_arena.common.data.load_training` 校验）与共同划分
`data/splits/validation_split.csv`。按 `train_row_id` 一对一合并，并检查每个无序图片对只属于一侧。

## 模型阶梯

`design.fit(frame, blocks, penalties)` 用同一套成对 logistic 设计拟合，`blocks` 的子集就是模型限制：

| 模型 | blocks | 含义 |
|---|---|---|
| M0 | `cat` | 猫效应差值，等价于成员2的无正则 Bradley–Terry |
| M1 | `cat, side` | 加 A 侧展示位置截距 |
| M2 | `cat, side, image` | 加猫内收缩的图片效应 |
| M3 | `cat, side, group` | 加 `pet_history` 主效应（整体 A 侧倾向） |
| M4 | `cat, side, image, group, group_cat` | 加 `pet_history × 猫身份` 交互 |

`cat` 块与成员2的 `fit_bradley_terry` 数值一致（差异 < 1e-13，单元测试覆盖）。差值型块只识别到
常数平移，实现中丢弃参考水平并对估计效应做中心化；`group_cat` 在每个组内丢弃一个参考猫。

跨平台复现时，大 L2 惩罚的内层拟合可能耗尽基础 BT 的 5000 次迭代预算。仅在优化器明确报告预算耗尽时，
从已有系数继续同一目标，追加最多 20000 次迭代、100000 次函数计算并使用 50 对 L-BFGS 历史向量；
保持原 `ftol=1e-12`、`gtol=1e-8`。仍不收敛则报错，不把未收敛结果当作成功。

## 防泄漏

- 所有水平映射、猫分数、图片效应和交互项只用训练部分建立；验证集只读一次用于最终比较。
- 收缩强度用训练部分内部、以图片对分组的 5 折交叉验证选择，验证集不参与选参。
- 全数据胜率、排名、检验统计量和已拟合全数据的分数都不作为特征；`cat_ranking`、`image_analysis`、
  `human_preferences` 的全量汇总表只用于描述和对照。
- 没有参与者 ID：计数单位是回答记录，不是人数。区间按图片对整簇 bootstrap，只部分吸收重复回答的依赖。

## 输出

- `tables/model_comparison.csv`：log loss、Brier、准确率、相对 M0 的 Δ 与 95% 区间。
- `tables/metrics_by_comparison_type.csv`：按 `between_cats` / `within_cat` 拆分。
- `tables/inner_selection.csv`：内层交叉验证的惩罚候选与平均 log loss。
- `tables/cat_rank_stability.csv`：名次点估计、bootstrap 名次区间、前十命中率、比较数。
- `tables/rank_specification_agreement.csv`：各模型设定与基础模型的排名相关、前十重合、最大名次变化。
- `figures/01_validation_metrics.png`、`02_by_comparison_type.png`、`03_rank_stability.png`（均含 PDF）。
- `summary.json`、`run_metadata.json`（含实现、配置与数据哈希，供 `scripts/check_project.py` 校验）。

## 结论与边界

验证集上没有任何扩展模型显著优于基础模型，最终模型保留基础 Bradley–Terry；扩展项作为稳健性检验保留。
排名稳健性用三种方式给出：图片对整簇 bootstrap 的名次区间、训练图片对随机分半的 Spearman–Brown 校正，
以及不同模型设定之间的排名相关。三者都指向“整体排序稳定、相邻名次的差异不可靠”这一点。

`model_comparison` 的选择偏差需要注意：五个候选都在同一份验证集上比较，没有做多重比较校正，
“最好模型”的区间是单次比较的区间，不是“五选一”的区间。训练集覆盖了验证集的全部图片与猫，
因此本模块不提供新图片、新猫或新参与者的泛化证据。
