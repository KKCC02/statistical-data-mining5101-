# Image-Level Analysis: Modest Shared Preference Amid Substantial Disagreement

## Research question and scope

When cat identity is held fixed, do repeated comparisons of the same two photos show more shared preference than an exchangeable A/B-choice reference? Is the evidence and comparison coverage sufficient to motivate a separate image effect?

We use only **within_cat** records for the main analysis: **3,003 responses, 1,132 unordered image pairs, 1,251 images and 237 cats**. Holding cat identity fixed removes differences between cats from each contrast. It does not isolate lighting, pose, composition or any other visual cause. Images are identified by file paths; no image pixels, external images or pretrained models are used. Participant identifiers are unavailable, so responses must not be described as independent people. The withheld test set and example labels are unused.

## Preparation and measures

We retain member 1's records, including missing human attributes and content duplicates. Sort the two image paths and recode the outcome as selection of canonical image 1; **888** within-cat pairs appear in both A/B orientations. Never aggregate raw A choices across swapped image directions.

For pair j with n_j responses and k_j choices of canonical image 1:

- Image-1 selection proportion: k_j/n_j; an arbitrary path order, not an attractiveness order.
- Mixed choices: 0 < k_j < n_j. Unanimous choices: k_j = 0 or n_j.
- Agreement among unordered response dyads: a_j = [C(k_j,2) + C(n_j-k_j,2)] / C(n_j,2), defined only for n_j >= 2.
- Primary pooled agreement: T = sum_j agreeing_dyads_j / sum_j response_dyads_j. Pairs receive weight C(n_j,2); these dyads overlap and are **not independent trials**. Equal-pair agreement is also reported.

Unanimity and entropy are descriptive and strongly affected by n. In particular, singletons always look unanimous, and under independent 50/50 choices, P(unanimous | n) = 2^(1-n). This fair-choice reference is explanatory; the main inferential reference below preserves the observed A count.

## Results 1: Disagreement is common

There are **1,016 repeated pairs** and **116 singletons**. Of the repeated pairs, **656 (64.57%)** have mixed choices and **360** are unanimous. Each pair has only 1-4 responses. At n=4, 38/190 pairs (20.00%) are unanimous; the independent fair-choice reference is 12.50%. Across all repeated pairs the observed unanimous count is 360, compared with an expectation of 318 under independent fair choices.

Use **Figure 1**, `../figures/01_pair_coverage_and_unanimity.png`. The left panel counts image pairs, not participants. The right panel compares unanimity within response-count strata, excluding singletons.

## Results 2: A modest aggregate consistency signal

The pooled agreement is **1,547/2,916 = 53.05%**. Equal-pair agreement is **52.89%**. A **10,000-replicate percentile bootstrap resampling whole cats** gives a 95% interval of **[51.03%, 55.20%]** for pooled agreement. This preserves within-cat dependence but cannot capture unknown cross-cat dependence from the same participants.

The primary one-sided test asks whether agreement exceeds the no-image-specific-preference reference. We shuffle the A/B choices over within-cat response slots, preserving their overall A count, all image pairs, orientations and response counts. Each permutation is then recoded to canonical image identity before T is computed. With **19,999** permutations, the null mean is **50.00%**, observed excess **3.05 percentage points**, and Monte Carlo **p = 0.0008** (15 permutations at least as extreme; p=(b+1)/(B+1), MC standard error approximately 0.00020).

An additional **9,999** permutations shuffle A/B choices **within each cat**, preserving each cat's A count. The reference mean is **50.19%**, with **p = 0.0013** (MC standard error approximately 0.00036). Both tests rely on exchangeable responses under their respective nulls. They are conditional association diagnostics, not randomized experiments or proof of a visual cause. Unobserved repeated participants could make the p-values optimistic.

Use **Figure 2**, `../figures/02_agreement_and_pair_uncertainty.png`. Its left panel is the global-permutation reference. The right panel illustrates the uncertainty of all possible four-answer outcomes; it is not a collection of selected winning images.

## Results 3: No individual pair can be established at 5%

We compute two-sided exact binomial tests against p=0.5 and 95% exact (Clopper-Pearson) intervals for every within-cat pair. **0/1,132** have unadjusted p<0.05; the minimum possible/observed p with this dataset's n<=4 is **0.125**. None survive BY or BH adjustment. BY is supplied as the conservative dependency-robust adjustment; neither method repairs invalid marginal p-values from dependent responses.

Even four unanimous choices give a two-sided exact p=0.125 and a 95% interval approximately [0.398, 1.000] for the chosen image (assuming independent identically distributed answers). Thus **absence of pair-level significance reflects limited resolution, not proof that images are equivalent**. All intervals are marginal, not simultaneous. Pair estimates do not establish a common transitive score for each image.

## Sensitivity analyses

| Scenario | Response records | Pooled agreement | Cat-bootstrap 95% interval |
|---|---:|---:|---:|
| all_records | 3,003 | 53.05% | [51.03%, 55.20%] |
| drop_extra_identical_contents | 2,998 | 53.00% | [50.97%, 55.16%] |
| complete_human_information | 2,954 | 52.88% | [50.81%, 55.06%] |
| pairs_with_both_orientations | 2,631 | 52.76% | [50.63%, 54.98%] |

Dropping extra identical-content records is a sensitivity scenario only; it is not evidence of duplicate entry. The complete-human-information scenario checks the effect of excluding missing records without modeling human-group differences. Restricting to pairs shown in both directions does not randomize presentation order. These are descriptive checks, not additional independent confirmatory tests.

For context, between-cat dyad agreement is 55.74%, versus within-cat 53.05% in this data version. Different pair compositions, response counts and participant mixtures prevent a causal or matched interpretation of this difference. See `comparison_type_summary.csv` and response-count-stratified results.

## Image-model readiness and handoff to member 5

Within-cat comparison graphs have **200/237** cats with connected undirected image networks, and **74/237** with strongly connected directed win networks. A finite unique unpenalized image BT fit, after fixing a location per cat, is not supported by the win graph for most cats. For disconnected graphs, centering alone cannot identify contrasts across components. Across these graphs, there are 291 components and 960 linearly identifiable within-component score contrasts. Median image exposure is **5 responses**; **366/1,251** images have only one distinct within-cat opponent. These are full-data diagnostics, not training-split model validation.

In member 1's saved pair-held-out split, within-cat fitting uses **2,396** records and evaluation contains **607**. With image exposure defined only using the **within-cat fitting subset**, both images are seen for **300/607 (49.42%)** validation records; 238 have one unseen image and 69 have two unseen images. If fitting on all training comparison types, all images in the saved validation set are seen. Coverage therefore depends on the actual fitting scope.

Use **Figure 3**, `../figures/03_image_model_readiness.png`.

The modest pooled signal supports **trying a regularized/partially pooled image effect**, subject to validation; it does not establish a predictive improvement. A candidate is logit P(A) = u_catA - u_catB + v_imageA - v_imageB (+ optional A-side intercept). Cat terms cancel in within-cat records. Member 5 should fit using training records only, constrain/shrink image effects within cats, choose penalty strength using an inner split, and compare on the untouched common outer validation split. Explicitly report unseen-image/cat handling and evaluate calibration/log loss as well as accuracy. Do not use the full-data pair rates, winner flags, p-values or image summaries here as validation features. Report-level exploration used all supplied training responses, so any adaptive model selection also needs nested/independent confirmation.

## Conclusion and contribution

**Different photos of the same cat show a small aggregate consistency signal, while disagreement remains common and individual pair evidence is weak. Sparse comparison networks motivate cautious shrinkage rather than unrestricted image rankings.** This analysis does not infer image-quality causes, participant-level reliability, population unanimity or human-subgroup differences. Member 3's contribution is canonicalized image-pair analysis, agreement and uncertainty measures, conditional permutation tests, sensitivity and network diagnostics, reproducible code, figures and report text. The member's name should be added by the group.

## References and reproducibility

1. Course-provided *Cat Image Arena Dataset*, README and *Midterm Report Guidelines 2026*; member 1's cleaning rules and data dictionary in `交接1/docs/`.
2. [SciPy: exact binomial test and proportion intervals](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.binomtest.html).
3. [SciPy: BH and BY false discovery adjustments](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.false_discovery_control.html); Benjamini & Hochberg (1995), Benjamini & Yekutieli (2001), as cited there.
4. [SciPy: permutation tests](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.permutation_test.html), especially the add-one convention for Monte Carlo p-values. Our permutations use a custom batched NumPy implementation to retain A/B orientation and, in a sensitivity analysis, each cat's A count.
5. [SciPy: connected components](https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.csgraph.connected_components.html).
6. Software: Python, NumPy, pandas, SciPy and Matplotlib; exact versions, seeds and hashes in `../run_metadata.json`. Analysis code and report drafting were assisted by OpenAI Codex; computed outputs were checked against source choices and by rerunning the scripts.
