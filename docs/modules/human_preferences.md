# 人群偏好差异 · 成员4

运行 `python scripts/run_human_preferences.py`，输入仅为 `data/processed/train_clean.csv`，结果写入 `outputs/human_preferences/`，章节写入 `reports/sections/human_preferences.md`。模块已接入 `scripts/run_all.py`。分析不读取验证集，也不将全数据统计用作验证特征。

主分析使用 `between_cats` 记录：分别检查 `pet_history`、`pet_contact`、`pet_care`、`gender`、`future_pet` 和 `mbti_ie`。输出包含缺失与字段审计、群体样本/类别分布、A 侧选择比例及 Wilson 区间、逐猫经验胜率区间、按共同猫对标准化的 `pet_history` 组间差异、排名相关和按无序猫对分层的群体关联检验。图表为样本分布、A/B 不确定性、猫咪选择率与组间差异。`pet_history` 三个分组比较图均强连通，因此另拟合分组 BT 分数作为探索性对比；这不是交互项检验或验证性能评估。`mbti_ie=unknown` 是有效类别。全体回答记录数不是参与者人数。

猫对分层 score 检验控制各组接触到的猫对差异，但假定记录层面的独立性；由于没有参与者 ID，统计量和比例区间都不能校正同一参与者重复作答。猫咪组间差异图仅作按共同对手标准化的描述性比较，区间未作多重比较校正，也不是交互模型检验。结果仅为探索性关联，不作因果解释。按猫身份分组的胜率和排名是描述结果，不等同于交互模型推断。

方法评估和建议见报告及 [成员5交接](human_preferences_handoff.md)。任何人群变量进入扩展模型前都须在训练折拟合，使用共同验证划分作评估；不得将全训练集排名、p 值或获胜派生字段当作验证特征。建议优先评估 `pet_history × cat`，但需先检查各子集比较图连通性，并采用有约束/正则化的交互模型。模块不替成员5决定最终模型。
