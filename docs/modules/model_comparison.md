# 扩展模型、稳健性与整合 · 成员5接入约定

状态：尚未交付实际比较，`src/cat_arena/model_comparison/`仅预留模块边界。

输入：公共主表、共同划分、成员2 BT接口、成员3/4探索发现。先读`reports/handoffs/image_effects_to_model_comparison.md`，不把全数据图片选择率直接作为验证特征。

调用`cat_arena.cat_ranking.model.fit_bradley_terry(training_between)`仅拟合传入子集，默认拒绝未见猫预测与非强连通胜负图。依据发现尝试有约束/收缩的图片效应或有证据的人群交互，不机械加入所有变量。

只用训练部分估计参数，内层选参数，共同外层验证比较log loss、Brier score和准确率。说明未见图片/猫的回退和覆盖，检查排名稳定性。反复据同一外层结果挑模型时需明确选择偏差并独立确认。

实现放本模块，入口拟定`scripts/run_model_comparison.py`，结果写`outputs/model_comparison/`，章节写`reports/sections/model_comparison.md`；实现和验证后再加入总入口。最终PPT/PDF放`reports/slides/`。
