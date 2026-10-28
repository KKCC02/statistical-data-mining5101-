# 成员4 → 成员5：人群偏好分析交接

## 主要发现

- 主表有 24,896 条训练回答，其中 21,893 条为猫与猫比较；六个人群变量均缺失 508 条全表记录，猫与猫比较中 21,434 条人群属性完整。没有参与者 ID，任何计数均是回答记录，不是独立人数。
- `pet_history` 三组的猫比较回答数为 current 7,512、never 8,259、past 5,663；各组均覆盖 237 只猫及 4,156–5,236 个无序猫对。`pet_contact`、`pet_care` 也有较好的覆盖，详见 `outputs/human_preferences/tables/group_coverage.csv`。
- 六个变量的各组猫咪经验胜率排序都覆盖 237 只猫。组间排名、Spearman 相关和 top-10 重合见 `rank_comparisons.csv`；各猫胜率/出场数见 `cat_rankings_by_group.csv`。这些是描述性排序，不能单独证明组间猫咪交互差异。
- `pet_history` 的猫与猫比较 A 侧选择比例为 current 49.3% [95% Wilson CI 48.2%, 50.5%]、never 53.1% [52.0%, 54.2%]、past 53.2% [51.9%, 54.4%]。所有变量按组的 A/B 计数及区间在 `position_choices.csv`。A/B 是位置选择，不能替代猫身份偏好。
- 对 `pet_history` 各组拟合的基础 BT 胜负图均强连通（237只猫；current 7,512、never 8,259、past 5,663 条），分数/排名及连通诊断见 `pet_history_group_bt_scores.csv` 和 `pet_history_group_bt_diagnostics.csv`。分组 BT 是探索性组内排名，不是有统计检验的交互模型；current/past 组经验 BT 第一名分别为 cat_000024、cat_000013，never 为 cat_001013，不能单凭排名差异推断显著偏好交互。
- 按无序猫对分层后，群体与选择首只（字典序较小）猫的关联检验：`pet_history` χ²(2)=1.339, p=.512；`pet_contact` χ²(4)=0.850, p=.932；`pet_care` χ²(3)=4.503, p=.212；`gender` χ²(1)=0.758, p=.384；`future_pet` χ²(2)=0.647, p=.724；`mbti_ie` χ²(2)=4.589, p=.101。六项 Holm 校正后均未达到 .05（最低调整 p=.605）。不显著不等于偏好相同。
- 这是记录级渐近检验，无法处理未知参与者聚类；重复回答、图片与猫咪共享也可能造成依赖。因此这些 p 值和 Wilson 区间仅供探索，不能宣称独立参与者推断。

## 可复用文件

- `outputs/human_preferences/tables/position_choices.csv`：各人群组 A/B 选择计数、A 侧比例和 Wilson 区间。
- `outputs/human_preferences/tables/group_category_distribution.csv`：各群体类别样本量和占比，含缺失类别。
- `outputs/human_preferences/tables/pet_history_cat_group_differences.csv`：同一猫咪在共同对手猫对中的 pet-history 组间标准化选择率差异及近似区间。
- `outputs/human_preferences/tables/pet_history_group_bt_scores.csv`、`pet_history_group_bt_diagnostics.csv`：pet_history 各组基础 BT 分数和可识别性诊断。
- `outputs/human_preferences/tables/group_coverage.csv`、`missingness.csv`、`field_audit.csv`：样本量、类别覆盖、缺失与必要字段检查。
- `outputs/human_preferences/tables/cat_rankings_by_group.csv`、`rank_comparisons.csv`：各组猫咪经验胜率排序和排序相似度。
- `outputs/human_preferences/tables/stratified_tests.csv`：猫对分层 score 检验及 Holm 校正。
- `outputs/human_preferences/figures/group_cat_rankings.png`（另有 PDF）及 `reports/sections/human_preferences.md`：图和完整解释。
- `group_sample_and_category_distribution.png`、`group_ab_choice_intervals.png`、`pet_history_cat_choice_rates.png`、`pet_history_group_preference_differences.png`（均有 PDF 版）：群体样本/类别、A/B 比例区间、猫咪选择率区间和共同猫对标准化差异图。

## 后续模型建议

- `pet_history` 是优先候选分组变量，可在训练折评估 `pet_history × cat identity`；图表/结果不证明该交互能提高预测。拟合前需检查各组猫对胜负图连通性，并为稀疏交互使用正则化或分层收缩。
- `pet_contact` 与 `pet_care` 可作为次级探索候选。`gender`、`future_pet`、`mbti_ie` 暂无这份探索分析提供的强依据；如有理论理由再单独检验，避免一次加入相关的人群主效应和交互。
- 主效应描述群体整体选择倾向；只有群体 × 猫身份项才直接表示不同群体对特定猫的相对偏好改变。不要从 A/B 比例或单独猫咪胜率推出该交互。
- 任何变换或估计出的猫分数/群体效应均在 `validation_split.csv` 的训练部分内拟合；验证只用于预先定义的模型比较。不得使用本模块全训练集胜率、排名、检验统计量作验证特征、调参信号或标签代理。
- 当前无参与者 ID，无法使用参与者聚类稳健标准误、参与者随机效应或参与者条件似然。不要把回答记录当作独立参与者数，也不要宣称解决了重复作答依赖。
