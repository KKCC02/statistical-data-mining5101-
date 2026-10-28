# 猫咪排名与Bradley-Terry基础模型 · 成员2

运行`python scripts/run_cat_ranking.py`，读取`data/processed/train_clean.csv`，仅用21893条between_cats回答、237只猫。排名表、两张300dpi PNG/矢量PDF、摘要和metadata写入`outputs/cat_ranking/`。Notebook为`notebooks/cat_ranking.ipynb`。

## 可复用接口

```python
from cat_arena.cat_ranking.model import fit_bradley_terry, win_rate_ranking
fit = fit_bradley_terry(training_between)
prob_a = fit.predict_probability(validation_between.a_cat, validation_between.b_cat)
```

`fit.scores`包含cat_id、bt_score、bt_rank，`fit.diagnostics`记录强连通性、收敛、梯度和样本量。函数只拟合传入子集，不读取保存的全数据分数。非强连通胜负图明确报错。未见猫默认报错，调用方可显式选择`unseen='zero'`以0分回退，并报告该假设和覆盖。

包导入可先执行`pip install -e . --no-deps`，或使用入口脚本/Notebook提供的src路径设置。成员5按train_row_id连接`data/splits/validation_split.csv`，只传训练between_cats子集拟合，重新检查网络和未知猫情况。

## 方法和结果

与原成员2分析一致：经验胜率为wins/comparisons；普通无正则BT使用猫分数差的logistic概率；首猫固定0，平均负对数似然，L-BFGS-B，maxiter=5000、gtol=1e-8、ftol=1e-12，展示分数中心化。设置集中在`configs/default.json`。

全数据排名Spearman约0.9730，前十名单重合10/10；cat_000024第一，cat_003674最后。分数和名次与迁移前基准逐猫比较。Notebook现在调用同一实现，不再自动安装或覆盖依赖。

原中文方法在`reports/sections/cat_ranking_zh.md`。全数据排名仅用于描述，没有验证性能或置信区间；Spearman不是准确率，分数不代表固有吸引力。没有参与者ID，不能保证回答独立。

原Notebook可在Git标签v0.1-handoff查阅，原环境保存在`docs/provenance/cat_ranking/`。当前安装以根目录依赖为准，接口提取不改写成员2原分析署名。
