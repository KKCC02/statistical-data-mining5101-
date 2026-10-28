# 人群偏好差异 · 成员4接入约定

状态：尚未交付实际分析，`src/cat_arena/human_preferences/`仅预留模块边界。

输入为`data/processed/train_clean.csv`，字段沿用成员1数据字典。优先`pet_history`，视证据考虑`pet_contact`/`pet_care`。使用逐行主表，不用缺少人群字段的图片对汇总代替。记录数不等于人数，缺失应明确排除或单列。

实现放本模块，入口拟定`scripts/run_human_preferences.py`，结果写`outputs/human_preferences/`，报告写`reports/sections/human_preferences.md`。实现和验证之前不加入`run_all.py`。

向成员5交付群体样本量、比较对象覆盖、群体偏好排名或条件选择差异、统计不确定性与候选交互项依据。只比总体A/B比例不能直接说明更喜欢哪些猫，应考虑比较对象构成。复用BT时重新检查各群体训练子集强连通性，不盲目对小群体拟合无正则模型。
