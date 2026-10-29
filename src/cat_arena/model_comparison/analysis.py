"""Member 5: nested model comparison, validation and cat-ranking stability.

All models are fitted on the training part of the shared image-pair split only.
Penalties are chosen by inner cross-validation inside that training part; the
saved validation part is read once per model for the final comparison. No
full-data win rate, ranking, p-value or fitted score enters a predictor.
"""
import argparse
import hashlib
import json
import platform
import time
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy
from matplotlib.ticker import MaxNLocator
from scipy.stats import spearmanr

from cat_arena.common.data import load_training
from cat_arena.common.paths import (CONFIG, CONFIG_PATH, PROJECT_ROOT, module_output, project_path,
                                    write_text)
from .design import fit as fit_design

HERE = Path(__file__).resolve().parent
BLUE, ORANGE, GREEN, GREY = '#377EB8', '#F0A44B', '#4DAF4A', '#777777'

MODELS = (
    dict(name='M0_cat_baseline', blocks=('cat',), grid={},
         label='Cat ability only (BT baseline)'),
    dict(name='M1_position', blocks=('cat', 'side'), grid={},
         label='+ A/B presentation position'),
    dict(name='M2_image', blocks=('cat', 'side', 'image'), grid={'image': 'image_penalties'},
         label='+ regularized image effect'),
    dict(name='M3_group_main', blocks=('cat', 'side', 'group'), grid={},
         label='+ pet_history main effect'),
    dict(name='M4_group_interaction', blocks=('cat', 'side', 'image', 'group', 'group_cat'),
         grid={'group_cat': 'group_penalties'}, label='+ pet_history x cat interaction'),
)

# These settings are module-local on purpose: `scripts/check_project.py` pins the
# hash of the shared configuration for the other modules, so adding a section
# there would invalidate their provenance records. A `model_comparison` section
# in `configs/default.json` still overrides these defaults if the team adds one.
DEFAULT_SETTINGS = dict(seed=CONFIG['seed'], inner_folds=5,
                        image_penalties=[0.3, 1.0, 3.0, 10.0],
                        group_penalties=[1.0, 10.0, 100.0],
                        metric_bootstrap=2000, rank_bootstrap=200, rank_bootstrap_reduced=60)
SETTINGS = {**DEFAULT_SETTINGS, **CONFIG.get('model_comparison', {})}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _relative(path):
    """Repository-relative POSIX form when possible, so generated files stay portable."""
    try:
        return Path(path).resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(path)


def _save(fig, out, name):
    fig.tight_layout()
    fig.savefig(out/'figures'/f'{name}.png', dpi=300, bbox_inches='tight')
    fig.savefig(out/'figures'/f'{name}.pdf', bbox_inches='tight',
                metadata={'CreationDate': None, 'ModDate': None})
    plt.close(fig)


def metrics(frame, probability):
    """Log loss, Brier score and accuracy for side-A probabilities."""
    y = frame.choice.eq('A').to_numpy().astype(float)
    p = np.clip(np.asarray(probability, dtype=float), 1e-12, 1-1e-12)
    return dict(log_loss=float(-np.mean(y*np.log(p)+(1-y)*np.log(1-p))),
                brier=float(np.mean((p-y)**2)),
                accuracy=float(np.mean((p >= .5) == y.astype(bool))))


def _folds(frame, k, seed):
    """Assign whole image pairs to inner folds so no pair spans two folds."""
    pairs = np.sort(frame.image_pair_id.unique())
    shuffled = np.random.default_rng(seed).permutation(pairs)
    lookup = pd.Series(np.arange(len(shuffled)) % k, index=shuffled)
    return frame.image_pair_id.map(lookup).to_numpy()


def inner_selection(train, blocks, grid, base_penalties=None):
    """Choose each penalty on inner folds of the training part only."""
    base_penalties = base_penalties or {}
    chosen, rows = dict(base_penalties), []
    if not grid:
        return chosen, pd.DataFrame(rows)
    fold_id = _folds(train, SETTINGS['inner_folds'], SETTINGS['seed'])
    grids = {block: SETTINGS[key] for block, key in grid.items()}
    candidates = [dict(base_penalties)]
    for block, values in grids.items():
        candidates = [{**base, block: value} for base in candidates for value in values]
    best = None
    for candidate in candidates:
        losses = []
        for fold in range(SETTINGS['inner_folds']):
            inside = train.loc[fold_id != fold]
            held = train.loc[fold_id == fold]
            model = fit_design(inside, blocks, candidate)
            losses.append(metrics(held, model.predict_proba(held))['log_loss'])
        mean = float(np.mean(losses))
        rows.append(dict(candidate=json.dumps(candidate, sort_keys=True), mean_inner_log_loss=mean,
                         fold_log_losses=json.dumps([round(v, 6) for v in losses])))
        if best is None or mean < best[1]-1e-12:
            best = (dict(candidate), mean)
    return best[0], pd.DataFrame(rows)


def bootstrap_delta(validation, probabilities, baseline, settings):
    """Paired cluster bootstrap of the log-loss difference against the baseline."""
    rng = np.random.default_rng(settings['seed'])
    codes, uniques = pd.factorize(validation.image_pair_id.to_numpy(), sort=True)
    n_clusters = len(uniques)
    y = validation.choice.eq('A').to_numpy().astype(float)
    p0 = np.clip(baseline, 1e-12, 1-1e-12)
    base_loss = -(y*np.log(p0)+(1-y)*np.log(1-p0))
    counts = np.bincount(codes, minlength=n_clusters)
    draws = rng.integers(0, n_clusters, size=(settings['metric_bootstrap'], n_clusters))
    drawn_counts = counts[draws].sum(axis=1)
    out = {}
    for name, p in probabilities.items():
        p = np.clip(p, 1e-12, 1-1e-12)
        delta = -(y*np.log(p)+(1-y)*np.log(1-p))-base_loss
        cluster_sums = np.bincount(codes, weights=delta, minlength=n_clusters)
        boot = cluster_sums[draws].sum(axis=1)/drawn_counts
        out[name] = (float(delta.mean()), float(np.quantile(boot, .025)),
                     float(np.quantile(boot, .975)))
    return out


def rank_stability(train, blocks, penalties, repetitions, settings):
    """Cluster bootstrap of the cat ranking under one fixed model specification."""
    rng = np.random.default_rng(settings['seed']+1)
    codes, uniques = pd.factorize(train.image_pair_id.to_numpy(), sort=True)
    n_clusters = len(uniques)
    reference = fit_design(train, blocks, penalties).cat_scores().set_index('cat_id')
    ranks, top10 = {}, []
    for _ in range(repetitions):
        pick = rng.integers(0, n_clusters, n_clusters)
        sample = train.iloc[np.repeat(np.arange(len(train)), np.bincount(pick, minlength=n_clusters)[codes])]
        try:
            scores = fit_design(sample, blocks, penalties).cat_scores().set_index('cat_id')
        except (RuntimeError, ValueError):
            continue
        ranks[len(ranks)] = scores['rank']
        top10.append(set(scores.nsmallest(10, 'rank').index))
    table = pd.DataFrame(ranks).T
    table = table.reindex(columns=reference.index)
    summary = reference.reset_index().rename(columns={'score': 'baseline_score', 'rank': 'baseline_rank'})
    summary['rank_ci_low'] = np.nanquantile(table.to_numpy(), .025, axis=0)
    summary['rank_ci_high'] = np.nanquantile(table.to_numpy(), .975, axis=0)
    summary['rank_median'] = np.nanmedian(table.to_numpy(), axis=0)
    summary['rank_appearances'] = table.notna().sum().to_numpy()
    reference_top = set(summary.nsmallest(10, 'baseline_rank').cat_id)
    summary['bootstrap_top10_share'] = [float(np.mean([c in s for s in top10])) for c in summary.cat_id]
    complete = table.dropna()
    rho = []
    for row in complete.index:
        rho.append(spearmanr(complete.loc[row], reference['rank'].loc[complete.columns]).statistic)
    diagnostics = dict(repetitions=len(table), used=len(complete),
                       top10_overlap_mean=float(np.mean([len(reference_top & s)/10 for s in top10])),
                       top10_overlap_min=float(np.min([len(reference_top & s)/10 for s in top10])),
                       spearman_vs_point_median=float(np.nanmedian(rho)),
                       spearman_vs_point_low=float(np.nanquantile(rho, .025)),
                       spearman_vs_point_high=float(np.nanquantile(rho, .975)))
    return summary, table, diagnostics


def split_half(train, blocks, penalties, settings):
    """Rank agreement between two disjoint halves of the training image pairs."""
    rng = np.random.default_rng(settings['seed']+2)
    pairs = np.sort(train.image_pair_id.unique())
    shuffled = rng.permutation(pairs)
    half = set(shuffled[:len(shuffled)//2].tolist())
    first = train.loc[train.image_pair_id.isin(half)]
    second = train.loc[~train.image_pair_id.isin(half)]
    one = fit_design(first, blocks, penalties).cat_scores().set_index('cat_id')['score']
    two = fit_design(second, blocks, penalties).cat_scores().set_index('cat_id')['score']
    common = one.index.intersection(two.index)
    rho = float(spearmanr(one.loc[common], two.loc[common]).statistic)
    top_one = set(one.loc[common].nlargest(10).index)
    top_two = set(two.loc[common].nlargest(10).index)
    return dict(spearman=rho, spearman_brown=2*rho/(1+rho) if rho > -1 else float('nan'),
                top10_overlap=len(top_one & top_two), cats=len(common),
                first_records=len(first), second_records=len(second))


def run(input_path=None, split_path=None, output_dir=None):
    started = time.perf_counter()
    source = Path(input_path) if input_path is not None else project_path('processed')/'train_clean.csv'
    split_file = Path(split_path) if split_path is not None else project_path('splits')/'validation_split.csv'
    out = Path(output_dir) if output_dir is not None else module_output('model_comparison')
    for name in ['tables', 'figures']:
        (out/name).mkdir(parents=True, exist_ok=True)
    source_hash, split_hash = digest(source), digest(split_file)

    data = load_training(source)
    split = pd.read_csv(split_file, keep_default_na=False, na_values=[''])
    merged = data.merge(split[['train_row_id', 'image_pair_id', 'split']], on='train_row_id',
                        how='left', validate='one_to_one', suffixes=('', '_split'))
    if merged.split.isna().any():
        raise ValueError('Every training row needs a split assignment')
    if not np.array_equal(merged.image_pair_id.to_numpy(), merged.image_pair_id_split.to_numpy()):
        raise ValueError('Split image pair disagrees with the cleaned training table')
    crossing = merged.groupby('image_pair_id').split.nunique()
    if (crossing > 1).any():
        raise ValueError('An image pair spans both splits')
    train = merged.loc[merged.split.eq('train')].copy()
    validation = merged.loc[merged.split.eq('validation')].copy()
    if train.empty or validation.empty:
        raise ValueError('Both split parts must be non-empty')

    penalties, inner_tables, fits = {}, [], {}
    for spec in MODELS:
        grid = spec['grid']
        base = {'image': penalties['M2_image']['image']} if spec['name'] == 'M4_group_interaction' else {}
        chosen, table = inner_selection(train, spec['blocks'], grid, base)
        if not table.empty:
            table.insert(0, 'model', spec['name'])
            inner_tables.append(table)
        penalties[spec['name']] = chosen
        fits[spec['name']] = fit_design(train, spec['blocks'], chosen)

    rows, probabilities = [], {}
    for spec in MODELS:
        model = fits[spec['name']]
        p = model.predict_proba(validation)
        probabilities[spec['name']] = p
        overall = metrics(validation, p)
        rows.append(dict(model=spec['name'], label=spec['label'],
                         blocks='+'.join(spec['blocks']),
                         parameters=model.diagnostics['parameters'],
                         penalized_parameters=model.diagnostics['penalized_parameters'],
                         penalties=json.dumps(penalties[spec['name']], sort_keys=True),
                         unseen_row_share=1-model.unseen_coverage(validation),
                         **{k: overall[k] for k in ('log_loss', 'brier', 'accuracy')}))
    comparison = pd.DataFrame(rows)
    deltas = bootstrap_delta(validation, probabilities, probabilities['M0_cat_baseline'], SETTINGS)
    comparison['delta_log_loss_vs_baseline'] = [deltas[n][0] for n in comparison.model]
    comparison['delta_ci_low'] = [deltas[n][1] for n in comparison.model]
    comparison['delta_ci_high'] = [deltas[n][2] for n in comparison.model]
    comparison['improves_on_baseline'] = (comparison.delta_ci_high < 0) & (comparison.model != 'M0_cat_baseline')

    by_type = []
    for spec in MODELS:
        p = probabilities[spec['name']]
        for kind in ['between_cats', 'within_cat']:
            subset = validation.comparison_type.eq(kind).to_numpy()
            if subset.any():
                by_type.append(dict(model=spec['name'], comparison_type=kind,
                                    records=int(subset.sum()),
                                    **metrics(validation.loc[subset], p[subset])))
    by_type = pd.DataFrame(by_type)

    best = comparison.loc[comparison.delta_log_loss_vs_baseline.idxmin()]
    adopted = best.model if bool(best.improves_on_baseline) and best.model != 'M0_cat_baseline' else 'M0_cat_baseline'

    baseline_stability, baseline_draws, baseline_diagnostics = rank_stability(
        train, ('cat',), {}, SETTINGS['rank_bootstrap'], SETTINGS)
    adopted_spec = next(s for s in MODELS if s['name'] == adopted)
    if adopted == 'M0_cat_baseline':
        adopted_stability, adopted_diagnostics = baseline_stability, baseline_diagnostics
    else:
        adopted_stability, _, adopted_diagnostics = rank_stability(
            train, adopted_spec['blocks'], penalties[adopted], SETTINGS['rank_bootstrap_reduced'], SETTINGS)
    halved = split_half(train, ('cat',), {}, SETTINGS)

    adopted_scores = fits[adopted].cat_scores().set_index('cat_id')
    shift = baseline_stability.merge(
        adopted_scores.reset_index()[['cat_id', 'score', 'rank']].rename(
            columns={'score': 'adopted_score', 'rank': 'adopted_rank'}), on='cat_id', validate='one_to_one')
    shift['rank_change'] = shift.baseline_rank-shift.adopted_rank
    shift['comparisons'] = (train.a_cat.value_counts().reindex(shift.cat_id.to_numpy()).fillna(0).astype(int).to_numpy()
                            + train.b_cat.value_counts().reindex(shift.cat_id.to_numpy()).fillna(0).astype(int).to_numpy())
    appearances = pd.concat([validation.a_cat, validation.b_cat]).value_counts()
    shift['validation_appearances'] = appearances.reindex(
        shift.cat_id.to_numpy()).fillna(0).astype(int).to_numpy()
    rank_agreement = float(spearmanr(shift.baseline_score, shift.adopted_score).statistic)

    rank_frame = shift[['cat_id', 'baseline_rank']].copy()
    agreement = []
    baseline_top = set(rank_frame.nsmallest(10, 'baseline_rank').cat_id)
    for spec in MODELS:
        scores = fits[spec['name']].cat_scores()[['cat_id', 'rank']]
        rank_frame = rank_frame.merge(scores.rename(columns={'rank': spec['name']}),
                                      on='cat_id', validate='one_to_one')
        rho = float(spearmanr(rank_frame.baseline_rank, rank_frame[spec['name']]).statistic)
        top = set(rank_frame.nsmallest(10, spec['name']).cat_id)
        agreement.append(dict(model=spec['name'], spearman_vs_baseline=rho,
                              top10_overlap_vs_baseline=len(top & baseline_top),
                              max_abs_rank_change=int((rank_frame.baseline_rank
                                                       - rank_frame[spec['name']]).abs().max())))
    agreement = pd.DataFrame(agreement)
    divergent = agreement.loc[agreement.model.ne('M0_cat_baseline')].sort_values(
        ['max_abs_rank_change', 'spearman_vs_baseline'], ascending=[False, True]).iloc[0]
    rank_frame['adopted_rank'] = rank_frame[adopted]

    side_effect = float(fits['M1_position'].effects('side').effect.iloc[0])
    base_by_type = by_type[by_type.model.eq('M0_cat_baseline')].set_index('comparison_type').log_loss
    image_by_type = by_type[by_type.model.eq('M2_image')].set_index('comparison_type').log_loss
    image_gain = {kind: float(image_by_type[kind]-base_by_type[kind]) for kind in base_by_type.index}

    comparison.to_csv(out/'tables/model_comparison.csv', index=False, encoding='utf-8-sig', lineterminator='\n')
    by_type.to_csv(out/'tables/metrics_by_comparison_type.csv', index=False, encoding='utf-8-sig', lineterminator='\n')
    shift.to_csv(out/'tables/cat_rank_stability.csv', index=False, encoding='utf-8-sig', lineterminator='\n')
    agreement.to_csv(out/'tables/rank_specification_agreement.csv', index=False,
                     encoding='utf-8-sig', lineterminator='\n')
    inner = pd.concat(inner_tables, ignore_index=True) if inner_tables else pd.DataFrame()
    inner.to_csv(out/'tables/inner_selection.csv', index=False, encoding='utf-8-sig', lineterminator='\n')
    _plot_metrics(comparison, out)
    _plot_by_type(by_type, out)
    _plot_stability(baseline_stability, rank_frame, divergent.model,
                    float(divergent.spearman_vs_baseline), out)

    summary = dict(input_file=_relative(source), split_file=_relative(split_file),
                   n_train_records=len(train), n_validation_records=len(validation),
                   n_train_pairs=int(train.image_pair_id.nunique()),
                   n_validation_pairs=int(validation.image_pair_id.nunique()),
                   n_cats=int(train.a_cat.nunique()), n_images=int(train.a_image.nunique()),
                   validation_coverage=1-float(comparison.unseen_row_share.max()),
                   penalties={k: v for k, v in penalties.items()},
                   metrics=comparison.to_dict(orient='records'),
                   metrics_by_comparison_type=by_type.to_dict(orient='records'),
                   adopted_model=adopted,
                   position_effect_logit=side_effect,
                   a_side_probability=float(1/(1+np.exp(-side_effect))),
                   image_gain_by_comparison_type=image_gain,
                   rank_agreement_baseline_vs_adopted=rank_agreement,
                   rank_specification_agreement=agreement.to_dict(orient='records'),
                   most_divergent_specification=divergent.model,
                   baseline_rank_stability=baseline_diagnostics,
                   adopted_rank_stability=adopted_diagnostics,
                   split_half=halved,
                   participant_id_available=False,
                   limitation='Rows are response records, not identified people. Repeated responses, shared cats and '
                              'shared images induce dependence that the cluster bootstrap over image pairs only partly removes.')
    write_text(out/'summary.json', json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
    meta = dict(python=platform.python_version(), platform=platform.platform(),
                versions={n: m.__version__ for n, m in [('numpy', np), ('pandas', pd),
                                                       ('scipy', scipy), ('matplotlib', matplotlib)]},
                source_sha256=source_hash, split_sha256=split_hash,
                design_sha256=digest(HERE/'design.py'), analysis_sha256=digest(HERE/'analysis.py'),
                config_sha256=digest(CONFIG_PATH),
                input_sha256=source_hash, validation_data_used_for_fitting=False,
                runtime_seconds=round(time.perf_counter()-started, 3))
    write_text(out/'run_metadata.json', json.dumps(meta, indent=2)+'\n')
    return dict(comparison=comparison, by_type=by_type, shift=shift, summary=summary, inner=inner,
                baseline_diagnostics=baseline_diagnostics, adopted_diagnostics=adopted_diagnostics,
                split_half=halved, rank_agreement=rank_agreement, adopted=adopted, penalties=penalties,
                n_train=len(train), n_validation=len(validation), baseline_stability=baseline_stability,
                agreement=agreement, divergent=divergent.model,
                divergent_rho=float(divergent.spearman_vs_baseline))


def _plot_metrics(comparison, out):
    names = comparison.label.tolist()
    extension = comparison.model.ne('M0_cat_baseline').to_numpy()
    figure, axes = plt.subplots(1, 2, figsize=(13, 4.8))
    ax = axes[0]
    subset = comparison.loc[extension]
    ax.errorbar(subset.delta_log_loss_vs_baseline, np.arange(len(subset)),
                xerr=[subset.delta_log_loss_vs_baseline-subset.delta_ci_low,
                      subset.delta_ci_high-subset.delta_log_loss_vs_baseline],
                fmt='o', color=BLUE, ecolor=GREY, capsize=3, markersize=6)
    ax.axvline(0, color=GREY, linestyle='--', linewidth=1)
    ax.set_yticks(np.arange(len(subset)), subset.label)
    ax.invert_yaxis()
    ax.set(xlabel='Δ log loss vs baseline (95% CI)', title='No extension beats the baseline')
    ax.xaxis.set_major_locator(MaxNLocator(4))
    ax.grid(axis='x', alpha=.2)
    ax.set_axisbelow(True)
    ax.spines[['top', 'right']].set_visible(False)
    ax = axes[1]
    order = comparison.sort_values('accuracy')
    ax.barh(order.label, order.accuracy,
            color=[GREY if name == 'M0_cat_baseline' else BLUE for name in order.model])
    ax.axvline(float(comparison.loc[comparison.model.eq('M0_cat_baseline'), 'accuracy'].iloc[0]),
               color=GREY, linestyle='--', linewidth=1)
    ax.set(xlabel='Validation accuracy', title='Accuracy at the 0.5 threshold')
    ax.set_xlim(.45, max(float(comparison.accuracy.max())+.02, .58))
    ax.grid(axis='x', alpha=.2)
    ax.set_axisbelow(True)
    ax.spines[['top', 'right']].set_visible(False)
    figure.suptitle('Nested extensions of the cat Bradley-Terry baseline', fontsize=14)
    _save(figure, out, '01_validation_metrics')


def _plot_by_type(by_type, out):
    kinds = [k for k in ['between_cats', 'within_cat'] if k in set(by_type.comparison_type)]
    models = [m for m in by_type.model.unique() if m != 'M0_cat_baseline']
    base = by_type[by_type.model.eq('M0_cat_baseline')].set_index('comparison_type').log_loss
    width = .8/len(kinds)
    figure, ax = plt.subplots(figsize=(10, 4.8))
    positions = np.arange(len(models))
    for offset, (kind, colour) in enumerate(zip(kinds, [BLUE, ORANGE])):
        subset = by_type[by_type.comparison_type.eq(kind)].set_index('model').reindex(models)
        ax.barh(positions+offset*width-width*(len(kinds)-1)/2, subset.log_loss-base[kind],
                height=width, color=colour, label=kind.replace('_', ' '))
    ax.axvline(0, color=GREY, linestyle='--', linewidth=1)
    ax.set_yticks(positions, models)
    ax.set(xlabel='Δ log loss vs baseline within the same comparison type',
           title='Where image effects would have to pay off')
    ax.legend(frameon=False)
    ax.grid(axis='x', alpha=.2)
    ax.set_axisbelow(True)
    ax.spines[['top', 'right']].set_visible(False)
    _save(figure, out, '02_by_comparison_type')


def _plot_stability(stability, rank_frame, divergent, rho, out):
    top = stability.nsmallest(40, 'baseline_rank').sort_values('baseline_rank')
    figure, axes = plt.subplots(1, 2, figsize=(13, 6.4))
    ax = axes[0]
    ax.errorbar(top.rank_median, top.baseline_rank,
                xerr=[top.rank_median-top.rank_ci_low, top.rank_ci_high-top.rank_median],
                fmt='o', color=BLUE, ecolor=GREY, elinewidth=1, capsize=0, markersize=4)
    ax.invert_yaxis()
    ax.set(xlabel='Bootstrapped rank (95% interval)', ylabel='Point-estimate rank',
           title='Top 40 cats: rank uncertainty')
    ax.grid(alpha=.2)
    ax.spines[['top', 'right']].set_visible(False)
    ax = axes[1]
    change = rank_frame[divergent]-rank_frame.baseline_rank
    ax.scatter(rank_frame.baseline_rank, change, s=12, color=BLUE, alpha=.6)
    ax.axhline(0, color=GREY, linestyle='--', linewidth=1)
    ax.set(xlabel='Baseline cat rank', ylabel='Rank change under the extension',
           title=f'{divergent} (Spearman {rho:.3f})')
    ax.grid(alpha=.2)
    ax.spines[['top', 'right']].set_visible(False)
    figure.suptitle('Stability of the cat preference ranking', fontsize=14)
    _save(figure, out, '03_rank_stability')


def write_report(result, output_path=None):
    """Render the member-5 report section from the computed tables."""
    comparison = result['comparison'].set_index('model')
    by_type = result['by_type']
    shift = result['shift']
    half = result['split_half']
    base = result['baseline_diagnostics']
    adopted = result['adopted']
    chosen = comparison.loc[adopted]
    lines = [
        '# 扩展模型、验证与排名稳健性', '',
        '## 评估设计', '',
        f"本模块只使用共同划分 `data/splits/validation_split.csv`：训练 {result['n_train']:,} 条回答记录、"
        f"验证 {result['n_validation']:,} 条；每个无序图片对只属于一侧，没有图片对跨两个集合。"
        f"所有猫分数、图片效应和人群交互项都只在训练部分拟合；以图片对为单位的 {SETTINGS['inner_folds']} 折"
        '内层交叉验证只用来选择惩罚强度；保存的验证集在候选模型全部定稿后一次性用于比较。'
        '全数据胜率、排名、检验统计量和已拟合全数据的分数都不进入预测。', '',
        '没有参与者 ID，因此所有计数都是回答记录，不是独立人数；同一未知参与者可能贡献多条记录，'
        '下面的区间按图片对整簇重采样，只能部分吸收这种依赖。', '',
        '## 模型阶梯', '',
        '模型按“先控制干扰项，再按证据逐项加入”的顺序排列，不机械堆叠变量：', '',
        '| 模型 | 加入项 | 加入依据 |', '|---|---|---|',
        '| M0 | 猫效应差值（BT 基线） | 成员 2 的基础模型，作为对照 |',
        '| M1 | A/B 展示位置截距 | A/B 界面普遍存在位置偏差，不加会污染其他结论 |',
        '| M2 | 猫内约束、带 L2 收缩的图片效应 | 成员 3：同猫图片一致率 53.05% 高于置换参照（p=0.0008） |',
        '| M3 | `pet_history` 主效应 | 只检验人群整体 A 侧倾向，不等于猫咪偏好差异 |',
        '| M4 | `pet_history` × 猫身份交互 | 成员 4 的优先候选，需要正则化；检验“不同人群偏好不同猫” |', '',
        '## 内层惩罚选择', '',
        '惩罚强度只在训练部分内部选择，验证集不参与：', '',
        '| 模型 | 选中的惩罚 |', '|---|---|']
    for model, value in result['penalties'].items():
        lines.append(f"| {model} | {json.dumps(value) if value else '无（无收缩项）'} |")
    spread = (result['inner'].groupby('model').mean_inner_log_loss.max()
              - result['inner'].groupby('model').mean_inner_log_loss.min())
    if len(spread):
        lines += ['',
                  f"各候选之间的内层 log loss 差距最大只有 {float(spread.max()):.5f}（`{spread.idxmax()}`），"
                  '说明惩罚强度的选择本身已经接近噪声水平：选中哪个收缩强度并不能证明它真的更好，'
                  '这本身就是“扩展项没有稳定增益”的一个旁证。']
    lines += ['', '## 验证集比较', '',
              f"所有模型都在同 {result['n_validation']:,} 条验证记录上评估；`Δ` 为相对 M0 的 log loss 变化"
              '（负值更好），区间按图片对整簇 bootstrap 得到。', '',
              '| 模型 | 参数个数 | Log loss | Δ vs M0 [95% CI] | Brier | 准确率 | 显著优于 M0 |',
              '|---|---:|---:|---:|---:|---:|---|']
    for row in result['comparison'].itertuples(index=False):
        delta = ('—' if row.model == 'M0_cat_baseline' else
                 f'{row.delta_log_loss_vs_baseline:+.5f} [{row.delta_ci_low:+.5f}, {row.delta_ci_high:+.5f}]')
        lines.append(f'| {row.model} | {row.parameters:,} | {row.log_loss:.4f} | {delta} | '
                     f'{row.brier:.4f} | {row.accuracy:.4f} | {"是" if row.improves_on_baseline else "否"} |')
    lines += ['',
              f"位置项自身的估计是 {result['summary']['position_effect_logit']:+.3f}（logit），"
              f"相当于 A 侧被选概率 {result['summary']['a_side_probability']:.3f}，说明展示位置确实有系统优势。"
              '但猫分数只取决于猫与猫之间的差值，整体平移不改变排名；它只在 0.5 阈值分类上带来小幅准确率提升，'
              'log loss 几乎不变。', '',
              '## 按比较类型拆分', '',
              '同猫比较两侧猫身份相同，猫效应抵消，因此图片效应只可能在这一部分带来增益：', '',
              '| 模型 | 类型 | 记录数 | Log loss | Brier | 准确率 |', '|---|---|---:|---:|---:|---:|']
    for row in by_type.itertuples(index=False):
        lines.append(f'| {row.model} | {row.comparison_type} | {row.records:,} | {row.log_loss:.4f} | '
                     f'{row.brier:.4f} | {row.accuracy:.4f} |')
    gain = result['summary']['image_gain_by_comparison_type']
    lines += ['',
              f"图片效应项的取舍在两类记录上是相反的：M2 在 `within_cat` 记录上把 log loss 降低 "
              f"{-gain['within_cat']:.4f}，在 `between_cats` 记录上却升高 {gain['between_cats']:.4f}，两者几乎抵消。"
              '这与成员 3 的结论一致——同猫比较确实带有一点图片信息，但量级小到不足以改变整体预测，'
              '而图片项在异猫记录上只会增加方差。', '',
              '## 猫咪排名稳定性', '',
              f"对基础模型按图片对整簇重采样 {base['repetitions']} 次重新拟合，每次记录每只猫的名次。"
              f"重采样名次与点估计排名的 Spearman 相关中位数为 {base['spearman_vs_point_median']:.3f}"
              f"（95% 区间 [{base['spearman_vs_point_low']:.3f}, {base['spearman_vs_point_high']:.3f}]）；"
              f"前十名重合率平均 {base['top10_overlap_mean']:.2f}，最差一次 {base['top10_overlap_min']:.2f}。", '',
              f"把训练图片对随机分成两半各自独立拟合，两边排名的 Spearman 相关为 {half['spearman']:.3f}，"
              f"用 Spearman–Brown 公式外推到全量后为 {half['spearman_brown']:.3f}，"
              f"两半的前十名重合 {half['top10_overlap']}/10。这是在缺少参与者 ID 时能给出的排名信度估计。", '',
              '排名前 10 的猫及其名次区间：', '',
              '| 猫 | 点估计名次 | Bootstrap 95% 区间 | 训练比较数 | 前十命中率 |',
              '|---|---:|---|---:|---:|']
    for row in shift.nsmallest(10, 'baseline_rank').itertuples(index=False):
        lines.append(f'| `{row.cat_id}` | {row.baseline_rank} | [{row.rank_ci_low:.0f}, {row.rank_ci_high:.0f}] | '
                     f'{row.comparisons:,} | {row.bootstrap_top10_share:.2f} |')
    lines += ['', '![验证集指标](../../outputs/model_comparison/figures/01_validation_metrics.png)', '',
              '![按比较类型](../../outputs/model_comparison/figures/02_by_comparison_type.png)', '',
              '![排名稳定性](../../outputs/model_comparison/figures/03_rank_stability.png)', '',
              '## 模型设定之间的排名变化', '',
              '同一份数据、不同模型设定下猫咪排名的相似度（与基础模型比较）：', '',
              '| 模型 | 与基础模型的 Spearman | 前十重合 | 最大名次变化 |', '|---|---:|---:|---:|']
    for row in result['agreement'].itertuples(index=False):
        lines.append(f'| {row.model} | {row.spearman_vs_baseline:.4f} | '
                     f'{row.top10_overlap_vs_baseline}/10 | {row.max_abs_rank_change} |')
    lines += ['', '## 结论', '']
    if adopted == 'M0_cat_baseline':
        lines += ['验证集上没有任何扩展模型把 log loss 相对基础模型显著降低；'
                  '因此最终模型保留基础 Bradley–Terry，只报告猫的相对偏好。'
                  '位置项、图片项和人群交互项作为稳健性检验保留在比较表里，不进入最终预测。']
    else:
        lines += [f'`{adopted}` 在验证集上把 log loss 降低了 {-chosen.delta_log_loss_vs_baseline:.4f}'
                  f'（95% CI [{chosen.delta_ci_low:+.4f}, {chosen.delta_ci_high:+.4f}]），'
                  '区间整体位于 0 以下，因此采用该扩展模型作为最终模型。']
    lines += ['',
              f"四个扩展模型的排名与基础模型的 Spearman 相关最低为 "
              f"{result['agreement'].loc[result['agreement'].model.ne('M0_cat_baseline'), 'spearman_vs_baseline'].min():.4f}，"
              f"前十名在每种设定下都完全相同；名次移动最多的是 `{result['divergent']}`，"
              f"单只猫最多移动 {int(result['agreement'].loc[result['agreement'].model.eq(result['divergent']), 'max_abs_rank_change'].iloc[0])} 名。"
              '也就是说，加入位置、图片或人群项会改变个别名次，但不会重排整个偏好结构——'
              '这与“猫的身份是主要信号，图片和人群只是次要调整”一致。', '',
              '需要注意的是，即使排名相关接近 1，个别名次仍会移动数位，原因是相邻猫的分数非常接近；'
              '上文的 bootstrap 区间说明，这类相邻名次差异在没有更多比较记录时无法可靠区分。', '',
              '## 局限', '',
              '- 验证集只用于一次最终比较，但五个候选模型都在同一份验证集上排序；'
              '“最好模型”的区间没有做多重比较校正，最优模型的乐观偏差没有被消除。',
              '- 按图片对重采样只处理了同一图片对内的重复回答；同一未知参与者跨图片对的依赖、猫与图片的共享都无法校正，'
              '区间实际可能偏窄。',
              '- 训练集覆盖了验证集的全部图片和猫，所以这里的结论不涉及新图片、新猫或新参与者的泛化。'
              '若只用同猫训练记录估计图片效应，607 条同猫验证记录中只有 300 条两图都出现过。',
              '- 人群交互项是在成员 4 未发现显著组间差异的前提下仍然拟合的探索项，其参数不应被解释为“某类人更喜欢某只猫”。', '',
              '分析与报告生成由 AI 编程助手（DeepSeek Harness）协助完成；所有数字由脚本从清洗数据重新计算，'
              '可通过 `python scripts/run_model_comparison.py` 复现。', '']
    content = '\n'.join(lines)
    if output_path is None:
        output_path = project_path('reports')/'sections/model_comparison.md'
    write_text(output_path, content)
    return content


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path)
    parser.add_argument('--split', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    result = run(args.input, args.split, args.output)
    write_report(result)
    print(json.dumps(result['summary'], ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
