"""Generate report text from computed results so numbers stay synchronized."""
from pathlib import Path


def write_reports(s, reports):
    reports = Path(reports)
    for subdir in ['sections', 'handoffs']:
        (reports/subdir).mkdir(parents=True, exist_ok=True)
    p, c, g = s['primary_permutation'], s['within_cat_conditional_permutation'], s['graph']
    low, high = s['cat_cluster_ci95']
    v = next(x for x in s['split_coverage'] if x['training_scope'] == 'within_cat')
    sensitivity_en = '\n'.join(
        f"| {r['scenario']} | {r['response_records']:,} | {r['dyad_weighted_agreement']:.2%} | "
        f"[{r['ci95_low']:.2%}, {r['ci95_high']:.2%}] |" for r in s['sensitivity'])
    refs = '''1. Course-provided *Cat Image Arena Dataset*, README and *Midterm Report Guidelines 2026*; member 1's cleaning rules and data dictionary in `docs/modules/data_preparation/`.
2. [SciPy: exact binomial test and proportion intervals](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.binomtest.html).
3. [SciPy: BH and BY false discovery adjustments](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.false_discovery_control.html); Benjamini & Hochberg (1995), Benjamini & Yekutieli (2001), as cited there.
4. [SciPy: permutation tests](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.permutation_test.html), especially the add-one convention for Monte Carlo p-values. Our permutations use a custom batched NumPy implementation to retain A/B orientation and, in a sensitivity analysis, each cat's A count.
5. [SciPy: connected components](https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.csgraph.connected_components.html).
6. Software: Python, NumPy, pandas, SciPy and Matplotlib; exact versions, seeds and hashes in `../../outputs/image_analysis/run_metadata.json`. Analysis code and report drafting were assisted by OpenAI Codex; computed outputs were checked against source choices and by rerunning the scripts.'''
    en = f'''# Image-Level Analysis: Modest Shared Preference Amid Substantial Disagreement

## Research question and scope

When cat identity is held fixed, do repeated comparisons of the same two photos show more shared preference than an exchangeable A/B-choice reference? Is the evidence and comparison coverage sufficient to motivate a separate image effect?

We use only **within_cat** records for the main analysis: **{s['response_records']:,} responses, {s['image_pairs']:,} unordered image pairs, {s['images']:,} images and {s['cats']} cats**. Holding cat identity fixed removes differences between cats from each contrast. It does not isolate lighting, pose, composition or any other visual cause. Images are identified by file paths; no image pixels, external images or pretrained models are used. Participant identifiers are unavailable, so responses must not be described as independent people. The withheld test set and example labels are unused.

## Preparation and measures

We retain member 1's records, including missing human attributes and content duplicates. Sort the two image paths and recode the outcome as selection of canonical image 1; **{s['pairs_with_both_orientations']:,}** within-cat pairs appear in both A/B orientations. Never aggregate raw A choices across swapped image directions.

For pair j with n_j responses and k_j choices of canonical image 1:

- Image-1 selection proportion: k_j/n_j; an arbitrary path order, not an attractiveness order.
- Mixed choices: 0 < k_j < n_j. Unanimous choices: k_j = 0 or n_j.
- Agreement among unordered response dyads: a_j = [C(k_j,2) + C(n_j-k_j,2)] / C(n_j,2), defined only for n_j >= 2.
- Primary pooled agreement: T = sum_j agreeing_dyads_j / sum_j response_dyads_j. Pairs receive weight C(n_j,2); these dyads overlap and are **not independent trials**. Equal-pair agreement is also reported.

Unanimity and entropy are descriptive and strongly affected by n. In particular, singletons always look unanimous, and under independent 50/50 choices, P(unanimous | n) = 2^(1-n). This fair-choice reference is explanatory; the main inferential reference below preserves the observed A count.

## Results 1: Disagreement is common

There are **{s['repeated_pairs']:,} repeated pairs** and **{s['singleton_pairs']} singletons**. Of the repeated pairs, **{s['mixed_repeated_pairs']} ({s['mixed_repeated_fraction']:.2%})** have mixed choices and **{s['unanimous_repeated_pairs']}** are unanimous. Each pair has only 1-4 responses. At n=4, 38/190 pairs (20.00%) are unanimous; the independent fair-choice reference is 12.50%. Across all repeated pairs the observed unanimous count is {s['unanimous_repeated_pairs']}, compared with an expectation of {s['fair_coin_expected_unanimous']:.0f} under independent fair choices.

Use **Figure 1**, `../../outputs/image_analysis/figures/01_pair_coverage_and_unanimity.png`. The left panel counts image pairs, not participants. The right panel compares unanimity within response-count strata, excluding singletons.

## Results 2: A modest aggregate consistency signal

The pooled agreement is **{s['agreeing_dyads']:,}/{s['response_dyads']:,} = {s['dyad_weighted_agreement']:.2%}**. Equal-pair agreement is **{s['equal_pair_agreement']:.2%}**. A **{s['n_bootstrap']:,}-replicate percentile bootstrap resampling whole cats** gives a 95% interval of **[{low:.2%}, {high:.2%}]** for pooled agreement. This preserves within-cat dependence but cannot capture unknown cross-cat dependence from the same participants.

The primary one-sided test asks whether agreement exceeds the no-image-specific-preference reference. We shuffle the A/B choices over within-cat response slots, preserving their overall A count, all image pairs, orientations and response counts. Each permutation is then recoded to canonical image identity before T is computed. With **{p['n_permutations']:,}** permutations, the null mean is **{p['null_mean']:.2%}**, observed excess **{p['excess_agreement']*100:.2f} percentage points**, and Monte Carlo **p = {p['p_one_sided']:.4f}** ({p['extreme_permutations']} permutations at least as extreme; p=(b+1)/(B+1), MC standard error approximately {p['monte_carlo_se']:.5f}).

An additional **{c['n_permutations']:,}** permutations shuffle A/B choices **within each cat**, preserving each cat's A count. The reference mean is **{c['null_mean']:.2%}**, with **p = {c['p_one_sided']:.4f}** (MC standard error approximately {c['monte_carlo_se']:.5f}). Both tests rely on exchangeable responses under their respective nulls. They are conditional association diagnostics, not randomized experiments or proof of a visual cause. Unobserved repeated participants could make the p-values optimistic.

Use **Figure 2**, `../../outputs/image_analysis/figures/02_agreement_and_pair_uncertainty.png`. Its left panel is the global-permutation reference. The right panel illustrates the uncertainty of all possible four-answer outcomes; it is not a collection of selected winning images.

## Results 3: No individual pair can be established at 5%

We compute two-sided exact binomial tests against p=0.5 and 95% exact (Clopper-Pearson) intervals for every within-cat pair. **{s['exact_p_below_005']}/{s['image_pairs']:,}** have unadjusted p<0.05; the minimum possible/observed p with this dataset's n<=4 is **{s['min_exact_p']:.3f}**. None survive BY or BH adjustment. BY is supplied as the conservative dependency-robust adjustment; neither method repairs invalid marginal p-values from dependent responses.

Even four unanimous choices give a two-sided exact p=0.125 and a 95% interval approximately [0.398, 1.000] for the chosen image (assuming independent identically distributed answers). Thus **absence of pair-level significance reflects limited resolution, not proof that images are equivalent**. All intervals are marginal, not simultaneous. Pair estimates do not establish a common transitive score for each image.

## Sensitivity analyses

| Scenario | Response records | Pooled agreement | Cat-bootstrap 95% interval |
|---|---:|---:|---:|
{sensitivity_en}

Dropping extra identical-content records is a sensitivity scenario only; it is not evidence of duplicate entry. The complete-human-information scenario checks the effect of excluding missing records without modeling human-group differences. Restricting to pairs shown in both directions does not randomize presentation order. These are descriptive checks, not additional independent confirmatory tests.

For context, between-cat dyad agreement is 55.74%, versus within-cat 53.05% in this data version. Different pair compositions, response counts and participant mixtures prevent a causal or matched interpretation of this difference. See `comparison_type_summary.csv` and response-count-stratified results.

## Image-model readiness and handoff to member 5

Within-cat comparison graphs have **{g['connected_cats']}/{s['cats']}** cats with connected undirected image networks, and **{g['finite_unpenalized_bt_cats']}/{s['cats']}** with strongly connected directed win networks. A finite unique unpenalized image BT fit, after fixing a location per cat, is not supported by the win graph for most cats. For disconnected graphs, centering alone cannot identify contrasts across components. Across these graphs, there are {g['total_components']} components and {g['within_only_identifiable_contrasts']} linearly identifiable within-component score contrasts. Median image exposure is **{g['median_image_appearances']:.0f} responses**; **{g['images_with_one_opponent']}/{s['images']:,}** images have only one distinct within-cat opponent. These are full-data diagnostics, not training-split model validation.

In member 1's saved pair-held-out split, within-cat fitting uses **{v['train_records']:,}** records and evaluation contains **{v['validation_records']}**. With image exposure defined only using the **within-cat fitting subset**, both images are seen for **{v['validation_both_images_seen']}/{v['validation_records']} ({v['validation_both_images_seen']/v['validation_records']:.2%})** validation records; {v['validation_one_image_seen']} have one unseen image and {v['validation_neither_image_seen']} have two unseen images. If fitting on all training comparison types, all images in the saved validation set are seen. Coverage therefore depends on the actual fitting scope.

Use **Figure 3**, `../../outputs/image_analysis/figures/03_image_model_readiness.png`.

The modest pooled signal supports **trying a regularized/partially pooled image effect**, subject to validation; it does not establish a predictive improvement. A candidate is logit P(A) = u_catA - u_catB + v_imageA - v_imageB (+ optional A-side intercept). Cat terms cancel in within-cat records. Member 5 should fit using training records only, constrain/shrink image effects within cats, choose penalty strength using an inner split, and compare on the untouched common outer validation split. Explicitly report unseen-image/cat handling and evaluate calibration/log loss as well as accuracy. Do not use the full-data pair rates, winner flags, p-values or image summaries here as validation features. Report-level exploration used all supplied training responses, so any adaptive model selection also needs nested/independent confirmation.

## Conclusion and contribution

**Different photos of the same cat show a small aggregate consistency signal, while disagreement remains common and individual pair evidence is weak. Sparse comparison networks motivate cautious shrinkage rather than unrestricted image rankings.** This analysis does not infer image-quality causes, participant-level reliability, population unanimity or human-subgroup differences. Member 3's contribution is canonicalized image-pair analysis, agreement and uncertainty measures, conditional permutation tests, sensitivity and network diagnostics, reproducible code, figures and report text. The member's name should be added by the group.

## References and reproducibility

{refs}
'''
    zh = f'''# 成员 3：同一只猫的图片差异与偏好分歧

## 核心结论

同一只猫的不同照片存在**较小的整体偏好一致性信号**，但重复图片对中分歧普遍存在，单个图片对的回答不足以确认稳定赢家。因此，可以建议成员 5 尝试带收缩的图片效应，再通过独立验证判断是否有用；不能直接宣称扩展模型会更好。

## 研究问题与数据

研究问题：控制猫咪身份后，对相同两张照片的重复选择，是否比保留 A/B 选择倾向的置换参照更一致？当前覆盖是否足以支持独立图片效应？

主分析统一读取成员 1 的 `train_clean.csv`，使用 **{s['response_records']:,} 条 within_cat 记录、{s['image_pairs']:,} 个无序图片对、{s['images']:,} 张图片、{s['cats']} 只猫**。每只猫有 {g['min_cat_records']}-{g['max_cat_records']} 条同猫比较。每行是一次回答，不是一个可识别的独立参与者。没有使用测试标签、示例标签、图片像素、外部图片或预训练模型。

同猫比较中两侧猫咪身份相同，因此猫咪层面的效应在比较中抵消；但拍照条件、姿态、画面内容等仍可能同时变化，不能据此确定具体视觉原因。

## 处理规则和指标

保留成员 1 的缺失信息记录及内容重复记录。图片路径按字典序固定为 image 1 和 image 2，重新编码选择方向；{s['pairs_with_both_orientations']} 对同时出现过两种 A/B 朝向，不能直接混加原始 A 选择。

对第 j 对图片，回答数 n_j、选择规范第一图的次数 k_j：

- 第一图选择率为 k_j/n_j，第一图仅由路径排序确定。
- 0 < k_j < n_j 表示观察到分歧；k_j=0 或 n_j 表示观察到全票。
- 从同一图片对的回答中抽取两个不同记录，比较它们是否选择同一图片。可形成的回答组合为 C(n_j,2)，其中相同选择组合为 C(k_j,2)+C(n_j-k_j,2)。
- 主指标 T 为所有图片对的相同选择组合数之和，除以全部可比较组合数之和。一个回答会出现在多个组合里，因此这些组合不独立，不能直接把它们当二项试验计算标准误。
- 每对等权的一致率也单独报告；单次回答不参与一致率。熵和多数比例仅作描述，小样本下存在明显偏差。

公平独立选择下全票概率为 2^(1-n)：n=2、3、4 时分别为 50%、25%、12.5%。这个公式用于解释样本量影响，主检验使用下面保留实际 A 总数的置换参照。

## 结果一：分歧普遍存在

共 **{s['repeated_pairs']:,} 个重复图片对**，另有 {s['singleton_pairs']} 对只有一次回答。重复图片对中 **{s['mixed_repeated_pairs']} 对（{s['mixed_repeated_fraction']:.2%}）**出现两种选择，{s['unanimous_repeated_pairs']} 对全票。n=4 的190对中仅38对全票（20.00%），公平独立选择参照为12.50%。对全部重复图片对，公平独立参照下预期全票为318对，实际为360对。

图 1：`../../outputs/image_analysis/figures/01_pair_coverage_and_unanimity.png`。左侧展示每对回答数的分布，右侧按相同回答数比较全票比例。单次回答必然全票，不作为可靠共识。

## 结果二：整体一致率略高于置换参照

相同选择的回答组合数为 **{s['agreeing_dyads']:,}**，全部组合数 **{s['response_dyads']:,}**，主指标为 **{s['dyad_weighted_agreement']:.2%}**；每个图片对等权得到 **{s['equal_pair_agreement']:.2%}**。

以猫为整簇重采样 {s['n_bootstrap']:,} 次，主指标的百分位95%区间为 **[{low:.2%}, {high:.2%}]**。整簇保留同一猫内部的依赖，但无法处理同一未知参与者跨猫回答造成的相关性。

主检验将全部同猫回答的原始 A/B 选择在固定记录位置间打乱，保留 A 总数、图片对、方向和每对回答数，再转换为图片身份并计算一致率。备择方向预设为“高于无图片特异偏好的参照”。**{p['n_permutations']:,} 次置换**的均值为 **{p['null_mean']:.2%}**，观察值高 **{p['excess_agreement']*100:.2f} 个百分点**，单侧 Monte Carlo **p={p['p_one_sided']:.4f}**，近似模拟标准误为 {p['monte_carlo_se']:.5f}。采用 p=(极端次数+1)/(置换次数+1)，不报告 p=0。

额外按猫分层置换，每只猫的 A 选择总数保持不变。**{c['n_permutations']:,} 次**的参照均值为 **{c['null_mean']:.2%}**，**p={c['p_one_sided']:.4f}**，近似模拟标准误为 {c['monte_carlo_se']:.5f}。这降低了猫间 A 倾向差异的影响，但两项检验都要求其零假设下回答可交换。没有参与者 ID，不能核实这一假设，p 值可能偏乐观；不能当作随机实验或视觉原因的因果证据。

图 2：`../../outputs/image_analysis/figures/02_agreement_and_pair_uncertainty.png`。左侧为整体置换参照，右侧说明即使有4个回答，不确定性仍很大。

## 结果三：没有足够证据确认某一图片对的赢家

逐对计算 p=0.5 的双侧精确二项检验和 Clopper-Pearson 95%区间，提供 BY 与 BH 调整值。**{s['exact_p_below_005']}/{s['image_pairs']:,}** 对达到未校正 p<0.05，校正后同样为0。每对最多4条回答，即使4:0全票，双侧 p 也为0.125；对获选图的概率区间约为 [0.398, 1.000]，仍包含0.5。

因此，“没有逐对显著结果”主要说明数据分辨率不足，不能证明图片完全没有差异。区间是逐对区间，不是同时覆盖区间；检验和区间依赖独立同分布回答假设。BY 对多重检验间依赖较保守，但不能修复单个检验本身因回答依赖而失效的问题。整体一致性也不保证图片偏好能由一套具有传递性的图片分数完整解释。

## 敏感性检查

| 场景 | 回答记录数 | 整体一致率 | 按猫 bootstrap 95%区间 |
|---|---:|---:|---:|
{sensitivity_en}

删除额外相同内容记录只作为敏感性分析：同样的回答可能来自不同人。排除人群信息缺失只是检查缺失记录影响，不分析人群差异。只保留两种 A/B 方向都出现的图片对也不等于展示顺序随机化。以上检查不视为新的独立确认性研究。

补充描述：between_cats 的整体一致率为55.74%，within_cat为53.05%。两类图片对构成、回答数和参与者组合不同，不能把差值解释为猫身份的因果贡献。细分回答数的结果见 `agreement_by_response_count.csv`。

## 是否支持建立图片效应模型

**支持进一步试验，不支持直接认定有效。** 同猫比较能够提供区别图片的信号，但覆盖稀疏：

- {g['connected_cats']}/{s['cats']} 只猫的无向图片比较网络连通；{s['cats']-g['connected_cats']}只存在多个互不连接的部分，部分之间的图片分数不能仅靠同猫数据识别。
- 仅 {g['finite_unpenalized_bt_cats']}/{s['cats']} 只猫的有向胜负网络强连通。对多数猫，无正则图片 BT 的有限唯一极大似然估计条件不满足。连通性按全部同猫记录诊断，不是训练子集的模型检查。
- 图片出现次数中位数为{g['median_image_appearances']:.0f}，{g['images_with_one_opponent']}/{s['images']:,}张图片仅与一个不同图片对手比较。
- 若仅用共同划分中的同猫训练部分拟合：训练{v['train_records']:,}条、验证{v['validation_records']}条。验证中两图均在同猫训练里出现的只有{v['validation_both_images_seen']}条（{v['validation_both_images_seen']/v['validation_records']:.2%}）；{v['validation_one_image_seen']}条有一张未见，{v['validation_neither_image_seen']}条两张均未见。若训练时使用全部比较类型，当前共同验证集图片均在相应训练部分出现，必须明确覆盖计算的范围。

图 3：`../../outputs/image_analysis/figures/03_image_model_readiness.png`。

给成员5的候选：logit P(A)=u_catA-u_catB+v_imageA-v_imageB，可另检验 A 侧截距。同猫比较中的猫效应抵消。建议约束图片效应在猫内中心化并使用正则化或部分汇聚；对于不连通网络，中心化本身不能补足跨分量信息，正则化只是施加额外假设。成员5需要在训练部分拟合、内层划分选收缩强度、共同外层验证集比较log loss、Brier score和准确率，并说明未见图片或猫的处理。

全数据图片对选择率、获胜字段、显著性与图片统计表不能作为验证集的现成预测特征。本部分属于全训练集探索；若由探索结果反复选模型，还需要内层或独立确认，不能把同一验证集用于不断挑选最终结论。

## 建议放入PPT的三页

1. **Same cat, different photos: disagreement is common.** 用图1；说明3003条记录、1132对、64.57%重复对存在分歧。
2. **A modest pooled signal, weak pair-level evidence.** 用图2；53.05%一致率、置换p=0.0008，但单对样本量太少，不能建立可靠赢家。
3. **Image effects merit a regularized validation trial.** 用图3；网络稀疏、仅74只猫满足强连通胜负网络条件；说明验证覆盖、未见图片和收缩要求。

## 局限与贡献

没有参与者ID，不能估计个人内可靠性、按参与者聚类、保证回答独立或代表总体人群。分歧不等于标注错误；未检查图片像素，不能归因于姿态或清晰度；有限配对覆盖、曝光不均、小样本和潜在展示偏差限制推广。未做成员4的人群差异检验，也未替代成员5的模型比较。

成员3贡献：统一方向后的图片对分析、分歧与不确定性指标、两种条件置换、敏感性检查、图片网络与验证覆盖诊断、复现代码、三张图和中英文报告内容。姓名由小组补充，不能自动推断。

## 参考与复现

{refs}
'''
    handoff = f'''# 给成员 5：图片效应候选与接入边界

## 可引用的发现

- 同猫图片重复回答的一致率{s['dyad_weighted_agreement']:.2%}，高于保留A总数的置换均值{p['null_mean']:.2%}（单侧p={p['p_one_sided']:.4f}；按猫分层置换p={c['p_one_sided']:.4f}）。这是需要回答可交换假设的探索性证据，不是预测表现。
- {s['mixed_repeated_fraction']:.2%}重复对存在分歧；每对1-4个回答，没有单对达到双侧p<0.05。不要选择“显著最优图片”，也不要解释为图片没有差异。
- {g['finite_unpenalized_bt_cats']}/{s['cats']}强连通胜负网络，说明无正则图片BT对多数猫不稳妥。全数据网络不能替代训练子集检查。

## 最小候选模型

在成员2的猫效应差值上加图片效应差值：`logit P(A) = u_catA-u_catB+v_imageA-v_imageB`。可把A侧截距作为单独候选。图片效应需要明确猫内约束和正则化；不连通分量之间的比较靠假设而非同猫数据识别。不机械加入人群变量，成员4需另提供依据。

本交接不拟合候选扩展模型，也没有验证准确率、log loss提升或排名稳定性结论。

## 正确的数据接入

1. 读取 `data/processed/train_clean.csv`，按`train_row_id`一对一连接共同`validation_split.csv`，检查所有行及无序图片对不跨集合。
2. 所有猫/图片索引、模型参数和需要学习的特征只使用实际训练部分建立；内层划分选择收缩强度，外层验证仅作比较。
3. 如只用同猫训练记录估计图片效应，当前验证607条中仅{v['validation_both_images_seen']}条两图均见过。需要对其余{v['validation_records']-v['validation_both_images_seen']}条制定回退，例如未知图片效应置0并报告适用范围；不能用全数据分数补值。
4. 如果使用全部比较类型的训练记录，当前全部4915条外层验证记录的图片均已在训练部分出现；这是不同的拟合范围。需要重新计算对应图片网络、猫效应及图片效应的可识别性。
5. 比较同一评估集合的log loss、Brier score和准确率，说明未见图片/猫覆盖。图片对分组划分不证明新图片、新猫或新参与者泛化。
6. 本目录全数据汇总表只用于描述与诊断，不能作为带结果的验证特征；所需胜率等必须在各训练折内重算。探索后的模型比较需注意数据适应性。

## 表与图

- `../../outputs/image_analysis/tables/within_cat_pair_statistics.csv`：逐对计数、规范第一图选择率、精确区间、原始/BH/BY p值。区间是逐对区间，依赖独立同分布回答。
- `../../outputs/image_analysis/tables/cat_image_graphs.csv`：全部同猫数据的网络结构，不是可直接用的拟合分数。
- `../../outputs/image_analysis/tables/image_coverage.csv`：曝光数和对手数。
- `../../outputs/image_analysis/tables/split_image_coverage.csv`：按两种实际拟合范围分别统计共同划分覆盖。
- `../../outputs/image_analysis/tables/sensitivity_analysis.csv`：保留/删除额外相同内容记录、完整人群记录及双向展示子集的描述性对照。
- `../../outputs/image_analysis/figures/01_pair_coverage_and_unanimity.png`、`02_agreement_and_pair_uncertainty.png`、`03_image_model_readiness.png`：均提供300dpi PNG和矢量PDF。

仅为教育与研究使用；不把观察到的分歧称为错误标签或个人不可靠。
'''
    for name, content in [('sections/image_analysis_en.md', en), ('sections/image_analysis_zh.md', zh),
                          ('handoffs/image_effects_to_model_comparison.md', handoff)]:
        (reports/name).write_text(content, encoding='utf-8', newline='\n')
