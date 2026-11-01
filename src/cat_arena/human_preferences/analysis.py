"""Descriptive pet-history/contact/care differences in cat choices."""
from __future__ import annotations

import hashlib
import json
from itertools import combinations
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import chi2, spearmanr

from cat_arena.common.data import load_training
from cat_arena.common.paths import PROJECT_ROOT, module_output, project_path, write_text
from cat_arena.cat_ranking.model import fit_bradley_terry

PRIMARY = 'pet_history'
GROUPS = ('pet_history', 'pet_contact', 'pet_care', 'gender', 'future_pet', 'mbti_ie')
BLUE, ORANGE = '#377EB8', '#F0A44B'


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _prepare(data):
    required = {'a_cat', 'b_cat', 'choice', 'comparison_type', *GROUPS}
    missing = required - set(data.columns)
    if missing:
        raise ValueError(f'Missing required fields: {sorted(missing)}')
    d = data.loc[data.comparison_type.eq('between_cats')].copy()
    if d.empty:
        raise ValueError('No between_cats records available')
    d['cat_1'] = d[['a_cat', 'b_cat']].min(axis=1)
    d['cat_2'] = d[['a_cat', 'b_cat']].max(axis=1)
    d['cat_pair_id'] = d.cat_1 + '||' + d.cat_2
    d['choice_cat_1'] = np.where(d.a_cat.eq(d.cat_1), d.choice.eq('A'), d.choice.eq('B')).astype(int)
    return d


def _stratified_score_test(data, group_col):
    """Pearson score test for group/choice association conditional on unordered cat pair.

    The covariance is the fixed-margin randomization covariance within each cat-pair
    stratum. This controls pair composition and yields a chi-square approximation.
    """
    d = data.loc[data[group_col].notna(), ['cat_pair_id', 'choice_cat_1', group_col]]
    levels = sorted(d[group_col].unique())
    if len(levels) < 2:
        raise ValueError(f'{group_col} has fewer than two observed groups')
    level_idx = {level: i for i, level in enumerate(levels)}
    score = np.zeros(len(levels), dtype=float)
    covariance = np.zeros((len(levels), len(levels)), dtype=float)
    informative_strata = 0
    for _, stratum in d.groupby('cat_pair_id', sort=False, observed=True):
        y = stratum.choice_cat_1.to_numpy(dtype=float)
        m = len(y)
        if m < 2 or y.min() == y.max():
            continue
        z = y-y.mean()
        s2 = float(z @ z)
        codes = stratum[group_col].map(level_idx).to_numpy()
        counts = np.bincount(codes, minlength=len(levels))
        if np.count_nonzero(counts) < 2:
            continue
        informative_strata += 1
        for i in range(len(levels)):
            score[i] += z[codes == i].sum()
            for j in range(len(levels)):
                covariance[i, j] += s2/(m-1)*(counts[i]*(i == j)-counts[i]*counts[j]/m)
    rank = len(levels)-1
    reduced_covariance = covariance[:-1, :-1]
    reduced_score = score[:-1]
    if np.linalg.matrix_rank(reduced_covariance) < rank:
        return dict(group_variable=group_col, test='cat-pair-stratified score chi-square',
                    statistic=np.nan, df=rank, p_value=np.nan, informative_cat_pairs=informative_strata,
                    n_records=len(d), groups=';'.join(levels))
    statistic = float(reduced_score @ np.linalg.solve(reduced_covariance, reduced_score))
    return dict(group_variable=group_col, test='cat-pair-stratified score chi-square',
                statistic=statistic, df=rank, p_value=float(chi2.sf(statistic, rank)),
                informative_cat_pairs=informative_strata, n_records=len(d), groups=';'.join(levels))


def _holm(p_values):
    values = np.asarray(p_values, dtype=float)
    out = np.full(values.shape, np.nan)
    valid = np.flatnonzero(np.isfinite(values))
    if not len(valid):
        return out
    order = valid[np.argsort(values[valid])]
    adjusted = np.maximum.accumulate([(len(order)-i)*values[index] for i, index in enumerate(order)])
    for index, value in zip(order, adjusted):
        out[index] = min(float(value), 1.)
    return out


def _wilson(successes, n, z=1.959963984540054):
    """Wilson interval for a descriptive response-record proportion."""
    if n == 0:
        return np.nan, np.nan
    p = successes/n
    den = 1+z*z/n
    center = (p+z*z/(2*n))/den
    half = z*np.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return float(center-half), float(center+half)


def _position_choices(data):
    rows = []
    for variable in GROUPS:
        for group, subset in data.loc[data[variable].notna()].groupby(variable, sort=True, observed=True):
            n = len(subset)
            n_a = int(subset.choice.eq('A').sum())
            low, high = _wilson(n_a, n)
            rows.append(dict(group_variable=variable, group=group, n_responses=n,
                             choose_a=n_a, choose_b=n-n_a, proportion_choose_a=n_a/n,
                             choose_a_ci95_low=low, choose_a_ci95_high=high))
    return pd.DataFrame(rows)


def _group_distribution(data):
    """Category counts and shares; missing is shown as its own category."""
    rows = []
    for variable in GROUPS:
        values = data[variable].astype('object').where(data[variable].notna(), 'Missing')
        counts = values.value_counts(dropna=False, sort=False)
        for group, n in counts.items():
            rows.append(dict(group_variable=variable, group=str(group), n_responses=int(n),
                             proportion=float(n/len(data)), n_total=int(len(data))))
    return pd.DataFrame(rows)


def _group_bradley_terry(data):
    """Fit separate, unregularized BT models for pet-history groups when identifiable."""
    rows, diagnostics = [], []
    for group, subset in data.loc[data.pet_history.notna()].groupby('pet_history', sort=True, observed=True):
        try:
            fit = fit_bradley_terry(subset)
        except (ValueError, RuntimeError) as exc:
            diagnostics.append(dict(group=group, n_responses=len(subset), identified=False,
                                    reason=str(exc), strong_components=np.nan))
            continue
        diagnostics.append(dict(group=group, n_responses=len(subset), identified=True,
                                reason='', strong_components=fit.diagnostics['strong_components']))
        for row in fit.scores.itertuples(index=False):
            rows.append(dict(group=group, cat_id=row.cat_id, bt_score=row.bt_score, bt_rank=row.bt_rank))
    return pd.DataFrame(rows), pd.DataFrame(diagnostics)


def _rank_table(data, group_col):
    rows = []
    valid = data.loc[data[group_col].notna()]
    for group, subset in valid.groupby(group_col, sort=True, observed=True):
        wins = pd.Series(np.where(subset.choice_cat_1.eq(1), subset.cat_1, subset.cat_2)).value_counts()
        appearances = pd.concat([subset.cat_1.value_counts(), subset.cat_2.value_counts()], axis=1).fillna(0).sum(axis=1)
        win_rate = wins.reindex(appearances.index, fill_value=0).div(appearances)
        rank = win_rate.rank(method='min', ascending=False).astype(int)
        for cat, comparisons in appearances.items():
            low, high = _wilson(int(wins.get(cat, 0)), int(comparisons))
            rows.append(dict(group_variable=group_col, group=group, cat_id=cat,
                             comparisons=int(comparisons), wins=int(wins.get(cat, 0)),
                             win_rate=float(win_rate[cat]), win_rate_ci95_low=low,
                             win_rate_ci95_high=high, rank=int(rank[cat])))
    return pd.DataFrame(rows).sort_values(['group_variable', 'group', 'rank', 'cat_id']).reset_index(drop=True)


def _rank_comparisons(ranks):
    rows = []
    for variable, subset in ranks.groupby('group_variable', sort=False):
        groups = sorted(subset.group.unique())
        rank_pivot = subset.pivot(index='cat_id', columns='group', values='rank')
        for left, right in combinations(groups, 2):
            rho = float(spearmanr(rank_pivot[left], rank_pivot[right]).statistic)
            top_left = set(subset.loc[subset.group.eq(left)].nsmallest(10, 'rank').cat_id)
            top_right = set(subset.loc[subset.group.eq(right)].nsmallest(10, 'rank').cat_id)
            rows.append(dict(group_variable=variable, group_1=left, group_2=right,
                             cats_ranked=len(rank_pivot), spearman_rank_correlation=rho,
                             top_10_overlap=len(top_left & top_right)))
    return pd.DataFrame(rows)


def _coverage(data):
    rows = []
    for variable in GROUPS:
        nonmissing = data.loc[data[variable].notna()]
        for group, subset in nonmissing.groupby(variable, sort=True, observed=True):
            rows.append(dict(group_variable=variable, group=group,
                             n_responses=int(len(subset)), n_image_pairs=int(subset.image_pair_id.nunique())
                             if 'image_pair_id' in subset else np.nan,
                             n_cat_pairs=int(subset.cat_pair_id.nunique()),
                             n_cats=int(pd.concat([subset.cat_1, subset.cat_2]).nunique())))
    return pd.DataFrame(rows)


def _pet_history_pair_standardized_differences(data, ranks, top_n=5):
    """Compare cat choice rates across history groups over their common cat pairs.

    The risk difference is standardized over shared opponent-pair strata, weighted
    by pooled records. Its approximate interval assumes independent records and
    cannot adjust for unobserved participant clustering.
    """
    history_ranks = ranks.loc[ranks.group_variable.eq('pet_history')]
    cats = []
    for group in sorted(history_ranks.group.unique()):
        cats.extend(history_ranks.loc[history_ranks.group.eq(group)].nsmallest(top_n, 'rank').cat_id.tolist())
    cats = list(dict.fromkeys(cats))
    groups = sorted(data.pet_history.dropna().unique())
    rows = []
    for cat in cats:
        d = data.loc[data.pet_history.notna() & (data.cat_1.eq(cat) | data.cat_2.eq(cat))].copy()
        d['focal_win'] = np.where(d.cat_1.eq(cat), d.choice_cat_1, 1-d.choice_cat_1)
        summary = d.groupby(['cat_pair_id', 'pet_history'], observed=True).focal_win.agg(['sum', 'count'])
        counts = summary['count'].unstack('pet_history').reindex(columns=groups)
        wins = summary['sum'].unstack('pet_history').reindex(columns=groups)
        for group_1, group_2 in combinations(groups, 2):
            n1, n2 = counts[group_1], counts[group_2]
            common = n1.notna() & n2.notna()
            n1, n2 = n1[common].astype(float), n2[common].astype(float)
            w1, w2 = wins.loc[common, group_1].astype(float), wins.loc[common, group_2].astype(float)
            if len(n1) == 0:
                continue
            p1, p2 = w1/n1, w2/n2
            pooled_n = n1+n2
            weights = pooled_n/pooled_n.sum()
            difference = float((weights*(p1-p2)).sum())
            variance = float((weights.pow(2)*(p1*(1-p1)/n1+p2*(1-p2)/n2)).sum())
            se = np.sqrt(variance)
            rows.append(dict(cat_id=cat, group_1=group_1, group_2=group_2,
                             group_1_minus_group_2=difference,
                             ci95_low=difference-1.959963984540054*se,
                             ci95_high=difference+1.959963984540054*se,
                             common_cat_pairs=int(len(n1)), n_group_1=int(n1.sum()),
                             n_group_2=int(n2.sum())))
    return pd.DataFrame(rows)


def _plot_ranks(ranks, out):
    fig, axes = plt.subplots(2, 3, figsize=(21, 12), sharex=False)
    for ax, variable in zip(axes.flat, GROUPS):
        subset = ranks.loc[ranks.group_variable.eq(variable)]
        groups = sorted(subset.group.unique())
        cat_union = []
        for group in groups:
            cat_union.extend(subset.loc[subset.group.eq(group)].nsmallest(5, 'rank').cat_id.tolist())
        cats = list(dict.fromkeys(cat_union))
        matrix = subset[subset.cat_id.isin(cats)].pivot(index='cat_id', columns='group', values='win_rate')
        matrix = matrix.reindex(index=cats, columns=groups)
        x = np.arange(len(cats))
        width = .82/len(groups)
        colors = [plt.get_cmap('tab10')(i) for i in range(len(groups))]
        for i, (group, color) in enumerate(zip(groups, colors)):
            ax.bar(x+(i-(len(groups)-1)/2)*width, matrix[group], width, color=color, label=group)
        ax.set_title(variable.replace('_', ' '))
        ax.set_ylabel('Win rate within group')
        ax.set_xticks(x, cats, rotation=65, ha='right', fontsize=7)
        ax.set_ylim(0, 1)
        ax.legend(fontsize=7, frameon=False)
        ax.spines[['top', 'right']].set_visible(False)
    fig.suptitle('Top five cats per group by empirical win rate')
    fig.tight_layout()
    fig.savefig(out/'figures/group_cat_rankings.png', dpi=300, bbox_inches='tight')
    fig.savefig(out/'figures/group_cat_rankings.pdf', bbox_inches='tight')
    plt.close(fig)


def _save_png_pdf(fig, out, name):
    fig.savefig(out/'figures'/f'{name}.png', dpi=300, bbox_inches='tight')
    fig.savefig(out/'figures'/f'{name}.pdf', bbox_inches='tight')
    plt.close(fig)


def _plot_group_distribution(distribution, out):
    fig, axes = plt.subplots(2, 3, figsize=(17, 10))
    palette = plt.get_cmap('tab10')
    for ax, variable in zip(axes.flat, GROUPS):
        subset = distribution.loc[distribution.group_variable.eq(variable)].sort_values('n_responses')
        colors = [palette(i % 10) for i in range(len(subset))]
        bars = ax.barh(subset.group, subset.proportion, color=colors)
        for bar, row in zip(bars, subset.itertuples(index=False)):
            ax.text(bar.get_width()+.006, bar.get_y()+bar.get_height()/2,
                    f'{row.n_responses:,} ({row.proportion:.1%})', va='center', fontsize=8)
        ax.set_title(variable.replace('_', ' '))
        ax.set_xlabel('Share of between-cat response records')
        ax.set_xlim(0, max(.5, float(subset.proportion.max())*1.55))
        ax.spines[['top', 'right']].set_visible(False)
    fig.suptitle('Group sample sizes and category distributions (missing shown separately)')
    fig.tight_layout()
    _save_png_pdf(fig, out, 'group_sample_and_category_distribution')


def _plot_position_intervals(position_choices, out):
    fig, axes = plt.subplots(2, 3, figsize=(17, 11))
    for ax, variable in zip(axes.flat, GROUPS):
        subset = position_choices.loc[position_choices.group_variable.eq(variable)].sort_values('group')
        y = np.arange(len(subset))
        p = subset.proportion_choose_a.to_numpy()
        low = subset.choose_a_ci95_low.to_numpy()
        high = subset.choose_a_ci95_high.to_numpy()
        ax.errorbar(p, y, xerr=np.vstack([p-low, high-p]), fmt='o', color=BLUE,
                    ecolor=BLUE, capsize=3)
        ax.axvline(.5, color='#777777', linestyle='--', linewidth=1)
        ax.set_yticks(y, subset.group)
        ax.set_xlim(0.35, 0.65)
        ax.set_xlabel('Proportion choosing A (Wilson 95% CI)')
        ax.set_title(variable.replace('_', ' '))
        ax.spines[['top', 'right']].set_visible(False)
    fig.suptitle('A/B position choice by group — between-cat comparisons')
    fig.tight_layout()
    _save_png_pdf(fig, out, 'group_ab_choice_intervals')


def _plot_pet_history_cat_rates(ranks, out, top_n=5):
    subset = ranks.loc[ranks.group_variable.eq('pet_history')]
    groups = sorted(subset.group.unique())
    cats = []
    for group in groups:
        cats.extend(subset.loc[subset.group.eq(group)].nsmallest(top_n, 'rank').cat_id.tolist())
    cats = list(dict.fromkeys(cats))
    width = .8/len(groups)
    fig, ax = plt.subplots(figsize=(max(12, .8*len(cats)), 7))
    palette = plt.get_cmap('tab10')
    for i, group in enumerate(groups):
        values = subset.loc[subset.group.eq(group)].set_index('cat_id').reindex(cats)
        x = np.arange(len(cats))+(i-(len(groups)-1)/2)*width
        rate = values.win_rate.to_numpy()
        low, high = values.win_rate_ci95_low.to_numpy(), values.win_rate_ci95_high.to_numpy()
        ax.errorbar(x, rate, yerr=np.vstack([rate-low, high-rate]), fmt='o', capsize=3,
                    label=group, color=palette(i))
    ax.set_xticks(np.arange(len(cats)), cats, rotation=65, ha='right')
    ax.set_ylim(0, 1)
    ax.set_ylabel('Empirical cat win rate (Wilson 95% CI)')
    ax.set_title('Cat choice rates by pet history (union of each group’s top five cats)')
    ax.legend(title='pet_history', frameon=False)
    ax.spines[['top', 'right']].set_visible(False)
    fig.tight_layout()
    _save_png_pdf(fig, out, 'pet_history_cat_choice_rates')


def _plot_pet_history_differences(differences, out):
    groups = sorted(set(differences.group_1) | set(differences.group_2))
    contrasts = list(combinations(groups, 2))
    fig, axes = plt.subplots(1, len(contrasts), figsize=(18, 7), sharey=True)
    for ax, (group_1, group_2) in zip(axes, contrasts):
        subset = differences.loc[differences.group_1.eq(group_1) & differences.group_2.eq(group_2)].sort_values('cat_id')
        y = np.arange(len(subset))
        effect = subset.group_1_minus_group_2.to_numpy()
        low, high = subset.ci95_low.to_numpy(), subset.ci95_high.to_numpy()
        ax.errorbar(effect, y, xerr=np.vstack([effect-low, high-effect]), fmt='o', capsize=3,
                    color=BLUE)
        ax.axvline(0, color='#777777', linestyle='--', linewidth=1)
        ax.set_yticks(y, subset.cat_id)
        ax.set_title(f'{group_1} − {group_2}')
        ax.set_xlabel('Difference in choice rate\n(approx. 95% CI)')
        ax.spines[['top', 'right']].set_visible(False)
    fig.suptitle('Pet-history differences in cat choice, standardized over shared opponents')
    fig.tight_layout()
    _save_png_pdf(fig, out, 'pet_history_group_preference_differences')


def run(data_path=None, output_dir=None):
    data_path = project_path('processed')/'train_clean.csv' if data_path is None else data_path
    out = module_output('human_preferences') if output_dir is None else output_dir
    out = out if hasattr(out, 'mkdir') else project_path('outputs')/out
    out.mkdir(parents=True, exist_ok=True)
    (out/'tables').mkdir(exist_ok=True)
    (out/'figures').mkdir(exist_ok=True)
    full = load_training(data_path)
    data = _prepare(full)
    coverage = _coverage(data)
    ranks = pd.concat([_rank_table(data, variable) for variable in GROUPS], ignore_index=True)
    tests = pd.DataFrame([_stratified_score_test(data, variable) for variable in GROUPS])
    tests['p_holm'] = _holm(tests.p_value)
    # A/B position is summarized on between-cat rows to align with identity analysis.
    position_choices = _position_choices(data)
    group_distribution = _group_distribution(data)
    group_bt, group_bt_diagnostics = _group_bradley_terry(data)
    rank_comparisons = _rank_comparisons(ranks)
    pet_history_differences = _pet_history_pair_standardized_differences(data, ranks)
    coverage.to_csv(out/'tables/group_coverage.csv', index=False, lineterminator='\n')
    ranks.to_csv(out/'tables/cat_rankings_by_group.csv', index=False, lineterminator='\n')
    tests.to_csv(out/'tables/stratified_tests.csv', index=False, lineterminator='\n')
    rank_comparisons.to_csv(out/'tables/rank_comparisons.csv', index=False, lineterminator='\n')
    position_choices.to_csv(out/'tables/position_choices.csv', index=False, lineterminator='\n')
    group_distribution.to_csv(out/'tables/group_category_distribution.csv', index=False, lineterminator='\n')
    pet_history_differences.to_csv(out/'tables/pet_history_cat_group_differences.csv', index=False, lineterminator='\n')
    group_bt.to_csv(out/'tables/pet_history_group_bt_scores.csv', index=False, lineterminator='\n')
    group_bt_diagnostics.to_csv(out/'tables/pet_history_group_bt_diagnostics.csv', index=False, lineterminator='\n')
    _plot_ranks(ranks, out)
    _plot_group_distribution(group_distribution, out)
    _plot_position_intervals(position_choices, out)
    _plot_pet_history_cat_rates(ranks, out)
    _plot_pet_history_differences(pet_history_differences, out)
    missingness = pd.DataFrame([dict(group_variable=v, n_missing=int(full[v].isna().sum()),
                                     n_total=len(full), n_between_cats=int(full.comparison_type.eq('between_cats').sum()),
                                     n_between_nonmissing=int(data[v].notna().sum())) for v in GROUPS])
    missingness.to_csv(out/'tables/missingness.csv', index=False, lineterminator='\n')
    audited_fields = ['train_row_id', 'a_cat', 'b_cat', 'a_image', 'b_image', 'choice', 'comparison_type', *GROUPS]
    field_audit = pd.DataFrame([dict(field=field, present=field in full.columns,
                                     n_nonmissing=int(full[field].notna().sum()) if field in full else 0,
                                     n_levels=int(full[field].nunique(dropna=True)) if field in full else 0)
                                for field in audited_fields])
    field_audit.to_csv(out/'tables/field_audit.csv', index=False, lineterminator='\n')
    try:
        input_label = Path(data_path).resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        input_label = Path(data_path).as_posix()
    summary = dict(input_file=input_label, n_train_records=len(full), n_between_cat_responses=len(data),
                   primary_variable=PRIMARY, group_variables=list(GROUPS),
                   missingness=missingness.to_dict(orient='records'),
                   tests=tests.to_dict(orient='records'),
                   position_choices=position_choices.to_dict(orient='records'),
                   pet_history_group_bt_diagnostics=group_bt_diagnostics.to_dict(orient='records'),
                   field_audit=field_audit.to_dict(orient='records'), participant_id_available=False,
                   interpretation='Rows are response records, not identified people. Group differences are descriptive associations.')
    write_text(out/'summary.json', json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
    meta = dict(input_sha256=_sha256(data_path),
                primary_source='data/processed/train_clean.csv', validation_data_used=False)
    from cat_arena.human_preferences import __file__ as package_init
    meta['implementation_sha256'] = _sha256(Path(package_init).with_name('analysis.py'))
    write_text(out/'run_metadata.json', json.dumps(meta, ensure_ascii=False, indent=2)+'\n')
    return dict(coverage=coverage, rankings=ranks, tests=tests, rank_comparisons=rank_comparisons,
                position_choices=position_choices, field_audit=field_audit,
                group_distribution=group_distribution,
                pet_history_differences=pet_history_differences,
                group_bt=group_bt, group_bt_diagnostics=group_bt_diagnostics,
                missingness=missingness, summary=summary)


def write_report(result, output_path=None):
    tests = result['tests'].set_index('group_variable')
    coverage = result['coverage']
    miss = result['missingness'].set_index('group_variable')
    lines = [
        '# Human Preference Differences', '',
        '## Data and coverage', '',
        f"The analysis uses {result['summary']['n_between_cat_responses']:,} between-cat response records from `data/processed/train_clean.csv`. `pet_history` is the primary grouping variable; `pet_contact` and `pet_care` are analyzed next, followed by `gender`, `future_pet`, and `mbti_ie`. The dictionary’s `unknown` value for `mbti_ie` is retained as an observed category. Missing values are excluded only from the corresponding grouped analysis. No participant identifier is available, so counts are response records, not people.", '',
        '| Variable | Group | Response records | Cat pairs | Cats |', '|---|---|---:|---:|---:|']
    for row in coverage.itertuples(index=False):
        lines.append(f'| {row.group_variable} | {row.group} | {row.n_responses:,} | {row.n_cat_pairs:,} | {row.n_cats} |')
    lines += ['', '## Marginal A/B position choices', '',
        'This table shows the A-side share and a 95% Wilson interval. These marginal side shares are distinct from preference for particular cat identities. The intervals assume independent response records and do not account for unobserved participant clustering.', '',
        '| Variable | Group | Responses | Choose A | Choose B | A share | Wilson 95% CI |', '|---|---|---:|---:|---:|---:|---:|']
    for row in result['position_choices'].itertuples(index=False):
        lines.append(f'| {row.group_variable} | {row.group} | {row.n_responses:,} | {row.choose_a:,} | {row.choose_b:,} | {row.proportion_choose_a:.3f} | [{row.choose_a_ci95_low:.3f}, {row.choose_a_ci95_high:.3f}] |')
    lines += ['', 'Missing values in the full training table: ' + '; '.join(
        f"`{v}` {int(miss.loc[v, 'n_missing']):,}/{int(miss.loc[v, 'n_total']):,}"
        for v in GROUPS) + '.', '', '## Cat preference rankings', '',
        'For each group, cats are ranked by empirical win rate over between-cat response records. This compares the cats chosen within each group and goes beyond the overall A/B position share. All observed groups cover the same 237 cats. The chart shows each group’s top five (the union of these cats per panel); complete rankings are in `outputs/human_preferences/tables/cat_rankings_by_group.csv`.', '',
        '![Group-specific cat rankings](../../outputs/human_preferences/figures/group_cat_rankings.png)', '',
        '| Variable | Group 1 | Group 2 | Cats ranked | Spearman rank correlation | Top-10 overlap |', '|---|---|---|---:|---:|---:|']
    for row in result['rank_comparisons'].itertuples(index=False):
        lines.append(f'| {row.group_variable} | {row.group_1} | {row.group_2} | {row.cats_ranked} | {row.spearman_rank_correlation:.3f} | {row.top_10_overlap}/10 |')
    lines += ['', '## Sample size and category distribution', '',
        '![Group sample size and category distribution](../../outputs/human_preferences/figures/group_sample_and_category_distribution.png)', '',
        'Counts and shares, with missing values shown separately, are in `outputs/human_preferences/tables/group_category_distribution.csv`.', '',
        '![A/B choice proportions with Wilson intervals](../../outputs/human_preferences/figures/group_ab_choice_intervals.png)', '',
        'The displayed A/B intervals are descriptive record-level Wilson intervals; they do not account for participant clustering.', '',
        '## Cat-specific choices and group contrasts', '',
        '![Pet-history cat win rates](../../outputs/human_preferences/figures/pet_history_cat_choice_rates.png)', '',
        'The plot shows each pet-history group’s empirical win rate for the union of that group’s top five cats, with record-level Wilson intervals. Exact cat/group counts are in `cat_rankings_by_group.csv`.', '',
        '![Pet-history group differences in cat choice](../../outputs/human_preferences/figures/pet_history_group_preference_differences.png)', '',
        'The contrast plot compares pet-history groups on shared unordered cat-pair strata, weighted by pooled response records. It shows exploratory risk differences and approximate intervals, not a fitted interaction model; participant-level dependence remains unadjusted.', '',
        '## Statistical tests', '',
        'A cat-pair-stratified score chi-square test checks whether the probability of choosing the lexicographically first cat varies across groups, conditioning on unordered cat identity pair. This controls for different cat-pair exposure across groups and answers a different question from the marginal A/B position shares. P-values are asymptotic and Holm-adjusted across all six group variables. The data include cat IDs, image IDs, A/B side, choice, comparison type, and unique response-row IDs, but no participant ID; this record-level test cannot correct within-participant dependence, so p-values are exploratory rather than cluster-valid inference.', '',
        '| Variable | Response records | Informative cat pairs | χ² | df | p | Holm-adjusted p |', '|---|---:|---:|---:|---:|---:|---:|']
    for row in result['tests'].itertuples(index=False):
        lines.append(f'| {row.group_variable} | {row.n_records:,} | {row.informative_cat_pairs:,} | {row.statistic:.2f} | {row.df} | {row.p_value:.3g} | {row.p_holm:.3g} |')
    lines += ['', '## Method assessment', '',
        'The primary sample is 21,893 between-cat response records (21,434 with observed group attributes). Each observed group spans all 237 cats; pet-history groups contain 5,663–8,259 responses and 4,156–5,236 distinct cat pairs. A/B share alone cannot establish cat-identity preference differences. The stratified score test is an omnibus identity-sensitive association check, while per-cat win rates and rank correlations are descriptive. A basic Bradley–Terry model is suitable for overall ranking and is implemented in the companion module. We additionally fit separate pet-history BT models: all three group-specific directed win graphs are strongly connected (237 cats each), so the unregularized fits are identifiable. Scores are saved in `pet_history_group_bt_scores.csv`; these in-sample fits are exploratory and do not constitute a formal interaction test or validation. A joint pet-history × cat BT extension would need explicit regularization and nested evaluation. Participant-clustered logistic or conditional-logistic models are not supportable because participant IDs are absent. A multi-factor regression could confound correlated self-reported attributes. Test interactions one at a time with training-fold-only estimation and use the saved validation split only for evaluation; do not use full-data summaries as validation features.', '',
        '## Interpretation and limits', '',
        'The conditional tests assess within-cat-pair group association; the empirical rankings describe each group’s observed wins and remain sensitive to sampling noise and unequal comparison counts. None of the six tests provides evidence of a group difference after Holm adjustment in this dataset; this is not proof that preferences are identical. Treat the p-values as exploratory: participant IDs are absent, repeated responses and shared images/cats may be dependent, and the test cannot account for participant-level clustering. The analysis is observational and does not support causal claims. Do not interpret response records as independent people.', '',
        '## Recommendation for member 5', '',
        'The available analysis does not establish that any human variable improves prediction. Do not add variables to the final model based on full-data results alone. If member 5 evaluates a nested extension, `pet_history` is the best-supported first candidate for a pre-specified `pet_history × cat` term because it is the priority variable and has broad support. `pet_contact` and `pet_care` are secondary candidates with broad support; other variables need a specific rationale. Test extensions separately or with suitable regularization, fit derived features within training folds, and retain a term only if validation performance improves against the no-group baseline. Do not use these full-data rankings or p-values as validation features or tuning evidence. Preference ranks and winner-derived quantities must not enter as predictors.', '']
    content = '\n'.join(lines)
    if output_path is None:
        output_path = project_path('reports')/'sections/human_preferences.md'
    write_text(output_path, content)
    return content


def main():
    result = run()
    write_report(result)
    print(json.dumps(result['summary'], ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
