"""Within-cat image preferences and repeated-pair disagreement. No test labels used."""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
import time
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.stats import binomtest, false_discovery_control
from .report import write_reports
from cat_arena.common.paths import PROJECT_ROOT, CONFIG, CONFIG_PATH, project_path, module_output

ROOT = PROJECT_ROOT
SEED = CONFIG['seed']
from cat_arena.common.data import ORIGINAL, load_training as load_data
BLUE, ORANGE, GRAY = '#377EB8', '#F0A44B', '#687787'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def pair_table(d, inference=False):
    p = d.groupby(['image_pair_id', 'comparison_type', 'canonical_image_1',
                   'canonical_image_2'], sort=True, as_index=False).agg(
        n_responses=('choice_canonical_1', 'size'),
        n_choose_image_1=('choice_canonical_1', 'sum')
    )
    # Compute orientation counts separately; group key is the pair, not a row's A side.
    orientation = d.assign(on_a=d.a_image.eq(d.canonical_image_1)).groupby('image_pair_id').on_a.sum()
    p['n_canonical_1_on_A'] = p.image_pair_id.map(orientation).astype(int)
    n, k = p.n_responses.to_numpy(), p.n_choose_image_1.to_numpy()
    p['n_choose_image_2'] = n - k
    p['proportion_choose_image_1'] = k / n
    p['majority_share'] = np.maximum(k, n-k) / n
    p['unanimous'] = (k == 0) | (k == n)
    p['mixed_choices'] = ~p.unanimous
    p['response_dyads'] = n * (n-1) // 2
    p['agreeing_dyads'] = (k * (k-1) + (n-k) * (n-k-1)) // 2
    p['dyad_agreement'] = p.agreeing_dyads.div(p.response_dyads.replace(0, np.nan))
    prob = k / n
    terms = np.zeros(len(p))
    interior = (k > 0) & (k < n)
    terms[interior] = -(prob[interior]*np.log2(prob[interior])
                        + (1-prob[interior])*np.log2(1-prob[interior]))
    p['observed_entropy_bits'] = terms  # Downward biased at small n; descriptive only.
    p['cat_id_1'] = p.canonical_image_1.str.split('/').str[0]
    p['cat_id_2'] = p.canonical_image_2.str.split('/').str[0]
    if inference:
        results = [binomtest(int(ki), int(ni), p=0.5) for ki, ni in zip(k, n)]
        intervals = [r.proportion_ci(method='exact') for r in results]
        p['ci95_low'] = [ci.low for ci in intervals]
        p['ci95_high'] = [ci.high for ci in intervals]
        p['p_exact_two_sided'] = [r.pvalue for r in results]
        p['p_bh'] = false_discovery_control(p.p_exact_two_sided, method='bh')
        p['p_by'] = false_discovery_control(p.p_exact_two_sided, method='by')
    return p


def agreement_summary(p):
    r = p[p.n_responses >= 2]
    if r.empty:
        raise ValueError('No repeated pairs: agreement cannot be estimated')
    return {
        'response_records': int(p.n_responses.sum()), 'image_pairs': len(p),
        'repeated_pairs': len(r), 'singleton_pairs': int((p.n_responses == 1).sum()),
        'mixed_repeated_pairs': int(r.mixed_choices.sum()),
        'unanimous_repeated_pairs': int(r.unanimous.sum()),
        'mixed_repeated_fraction': float(r.mixed_choices.mean()),
        'response_dyads': int(r.response_dyads.sum()),
        'agreeing_dyads': int(r.agreeing_dyads.sum()),
        'dyad_weighted_agreement': float(r.agreeing_dyads.sum()/r.response_dyads.sum()),
        'equal_pair_agreement': float(r.dyad_agreement.mean()),
        'fair_coin_expected_unanimous': float(np.power(2., 1-r.n_responses).sum()),
    }


def cluster_bootstrap(p, n_resamples=10000, seed=SEED):
    """Resample whole cats; does not account for unknown participant clustering."""
    totals = p.groupby('cat_id_1')[['agreeing_dyads', 'response_dyads']].sum().to_numpy()
    rng = np.random.default_rng(seed)
    estimates = []
    for start in range(0, n_resamples, 256):
        ids = rng.integers(0, len(totals), size=(min(256, n_resamples-start), len(totals)))
        sums = totals[ids].sum(axis=1)
        estimates.extend((sums[:, 0]/sums[:, 1]).tolist())
    return np.quantile(estimates, [.025, .975]).tolist()


def permutation_agreement(d, n_resamples=19999, seed=SEED, within_cat=False):
    """Shuffle A/B choices, then reorient to image identity. One-sided excess agreement.

    Global permutation conditions on the total A count. Optional within-cat permutation
    additionally conditions on each cat's A count. Both require exchangeable answers.
    """
    d = d.sort_values('image_pair_id').reset_index(drop=True)
    codes, _ = pd.factorize(d.image_pair_id, sort=False)
    starts = np.r_[0, np.flatnonzero(np.diff(codes)) + 1]
    n = np.diff(np.r_[starts, len(d)])
    denominator = int((n*(n-1)//2).sum())
    if denominator == 0:
        raise ValueError('Permutation statistic requires repeated image pairs')
    y = d.choice_a.to_numpy(dtype=int)
    orientation = d.a_image.eq(d.canonical_image_1).to_numpy()

    def statistic(labels):
        canonical = np.where(orientation, labels, 1-labels)
        k = np.add.reduceat(canonical, starts, axis=-1)
        agreements = (k*(k-1)+(n-k)*(n-k-1))//2
        return agreements.sum(axis=-1)  # Integer comparisons avoid float tie errors.

    observed = int(statistic(y))
    rng = np.random.default_rng(seed)
    null = np.empty(n_resamples, dtype=int)
    groups = list(d.groupby('a_cat', sort=True).indices.values()) if within_cat else None
    for start in range(0, n_resamples, 128):
        batch = min(128, n_resamples-start)
        if within_cat:
            shuffled = np.empty((batch, len(d)), dtype=int)
            for idx in groups:
                shuffled[:, idx] = rng.permuted(np.broadcast_to(y[idx], (batch, len(idx))), axis=1)
        else:
            shuffled = rng.permuted(np.broadcast_to(y, (batch, len(y))), axis=1)
        null[start:start+batch] = statistic(shuffled)
    extreme = int((null >= observed).sum())
    pv = (extreme+1)/(n_resamples+1)
    return {'observed_agreement': observed/denominator,
            'null_mean': float(null.mean()/denominator),
            'excess_agreement': float((observed-null.mean())/denominator),
            'p_one_sided': pv, 'monte_carlo_se': float(np.sqrt(pv*(1-pv)/(n_resamples+1))),
            'n_permutations': n_resamples, 'extreme_permutations': extreme,
            'condition': 'A count within each cat' if within_cat else 'global A count',
            'seed': seed}, null/denominator


def graph_tables(w):
    cats, images = [], []
    for cat, d in w.groupby('a_cat', sort=True):
        names = sorted(set(d.a_image) | set(d.b_image))
        mapping = {name: i for i, name in enumerate(names)}
        edges = d.drop_duplicates('image_pair_id')
        i = edges.canonical_image_1.map(mapping).to_numpy()
        j = edges.canonical_image_2.map(mapping).to_numpy()
        graph = coo_matrix((np.ones(len(i)), (i, j)), shape=(len(names), len(names))).tocsr()
        n_components, labels = connected_components(graph, directed=False)
        # A finite unpenalized BT estimate needs a strongly connected win graph.
        win = np.where(d.choice.eq('A'), d.a_image, d.b_image)
        lose = np.where(d.choice.eq('A'), d.b_image, d.a_image)
        wins = coo_matrix((np.ones(len(d)),
                           ([mapping[x] for x in win], [mapping[x] for x in lose])),
                          shape=(len(names), len(names))).tocsr()
        n_strong, _ = connected_components(wins, directed=True, connection='strong')
        counts = pd.concat([d.a_image, d.b_image]).value_counts()
        degree = (graph + graph.T).astype(bool).sum(axis=1).A1
        cats.append(dict(cat_id=cat, n_responses=len(d), n_images=len(names),
                         n_image_pairs=len(edges), n_components=int(n_components),
                         connected=bool(n_components == 1), n_strong_components=int(n_strong),
                         finite_unpenalized_bt=bool(n_strong == 1),
                         identifiable_score_contrasts=len(names)-int(n_components)))
        for pos, name in enumerate(names):
            images.append(dict(cat_id=cat, image=name, n_appearances=int(counts[name]),
                               n_distinct_opponents=int(degree[pos]),
                               component_id=f'{cat}:{labels[pos]}'))
    return pd.DataFrame(cats), pd.DataFrame(images)


def split_diagnostic(d, split_path):
    split = pd.read_csv(split_path)
    if split.train_row_id.duplicated().any() or set(split.train_row_id) != set(d.train_row_id):
        raise ValueError('Split identifiers must exactly cover the training data')
    merged = d.merge(split, on='train_row_id', validate='one_to_one', suffixes=('', '_split'))
    if not merged.image_pair_id.eq(merged.image_pair_id_split).all():
        raise ValueError('Saved split pair identifiers differ from source data')
    if not merged.split.isin(['train', 'validation']).all():
        raise ValueError('Invalid split label')
    if merged.groupby('image_pair_id').split.nunique().max() != 1:
        raise ValueError('Pair leakage across the saved split')
    records = []
    for scope in ['within_cat', 'all_comparisons']:
        source = merged[merged.comparison_type.eq('within_cat')] if scope == 'within_cat' else merged
        tr, va = source[source.split.eq('train')], source[source.split.eq('validation')]
        known_images = set(tr.a_image) | set(tr.b_image)
        known_cats = set(tr.a_cat) | set(tr.b_cat)
        seen_a, seen_b = va.a_image.isin(known_images), va.b_image.isin(known_images)
        records.append(dict(training_scope=scope, train_records=len(tr), validation_records=len(va),
                            train_images=len(known_images), validation_unique_images=len(set(va.a_image)|set(va.b_image)),
                            validation_both_images_seen=int((seen_a & seen_b).sum()),
                            validation_one_image_seen=int((seen_a ^ seen_b).sum()),
                            validation_neither_image_seen=int((~seen_a & ~seen_b).sum()),
                            validation_both_cats_seen=int((va.a_cat.isin(known_cats)&va.b_cat.isin(known_cats)).sum())))
    return pd.DataFrame(records)


def save_csv(df, path):
    df.to_csv(path, index=False, encoding='utf-8-sig', float_format='%.12g', lineterminator='\n')


def save_figure(fig, out, name):
    fig.savefig(out/'figures'/f'{name}.png', dpi=300, facecolor='white')
    fig.savefig(out/'figures'/f'{name}.pdf', metadata={'CreationDate': None, 'ModDate': None})
    plt.close(fig)


def figures(pairs, within, by_n, null, summary, cats, coverage, out):
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10,
                         'axes.spines.top': False, 'axes.spines.right': False,
                         'axes.titlesize': 12, 'pdf.fonttype': 42})
    fig, ax = plt.subplots(1, 2, figsize=(11.5, 4.8), layout='constrained')
    counts = within.groupby('n_responses').size().reindex(range(1, 5), fill_value=0)
    ax[0].bar(counts.index, counts, color=BLUE)
    for n, v in counts.items(): ax[0].text(n, v+7, f'{v:,}', ha='center')
    ax[0].set(title='Within-cat comparison coverage', xlabel='Response records per image pair',
              ylabel='Image pairs', xticks=[1, 2, 3, 4], ylim=(0, counts.max()*1.2))
    sub = by_n[by_n.comparison_type.eq('within_cat') & by_n.n_responses.ge(2)]
    x = np.arange(len(sub)); width = .34
    ax[1].bar(x-width/2, sub.unanimous_fraction, width, color=BLUE, label='Observed unanimity')
    ax[1].bar(x+width/2, sub.fair_coin_unanimous_probability, width,
              color=ORANGE, label='Independent fair-choice reference')
    for idx, row in enumerate(sub.itertuples()):
        ax[1].text(idx-width/2, row.unanimous_fraction+.02,
                   f'{row.n_unanimous}/{row.n_pairs}', ha='center', fontsize=9)
    ax[1].set(title='Unanimity depends on sample size', xlabel='Response records per image pair',
              ylabel='Fraction of image pairs', xticks=x,
              xticklabels=[str(n) for n in sub.n_responses], ylim=(0, .76))
    ax[1].legend(fontsize=8, loc='upper right')
    fig.suptitle('Repeated choices of different photos of the same cat', fontsize=14)
    save_figure(fig, out, '01_pair_coverage_and_unanimity')

    fig, ax = plt.subplots(1, 2, figsize=(11.5, 4.9), layout='constrained')
    heights, _, _ = ax[0].hist(null, bins=32, color=BLUE, edgecolor='white')
    ax[0].set_ylim(0, heights.max()*1.30)
    obs = summary['primary_permutation']['observed_agreement']
    ax[0].axvline(obs, color=ORANGE, linewidth=2.5, label=f'Observed: {obs:.2%}')
    ax[0].set(title='Pooled agreement under shuffled A/B choices', xlabel='Agreeing response dyads / all response dyads',
              ylabel='Permutations')
    ax[0].legend(fontsize=9)
    ax[0].text(.03, .96, f"One-sided p = {summary['primary_permutation']['p_one_sided']:.4f}\n"
                f"{len(null):,} permutations; total A count preserved",
                transform=ax[0].transAxes, va='top', fontsize=9)
    templates = []
    for k in range(5):
        r = binomtest(k, 4); ci = r.proportion_ci(method='exact')
        templates.append((k/4, ci.low, ci.high))
    for k, (point, low, high) in enumerate(templates):
        ax[1].errorbar(point, k, xerr=[[point-low], [high-point]], fmt='o',
                       color=BLUE, capsize=4, markersize=7)
    ax[1].axvline(.5, color=GRAY, linestyle='--', linewidth=1)
    ax[1].set(title='Even four answers give wide uncertainty', xlabel='P(choose canonical image 1)',
              yticks=range(5), yticklabels=[f'{k} of 4 choices' for k in range(5)],
              xlim=(-.03, 1.03), ylim=(-.6, 4.6))
    ax[1].text(.02, .03, '95% exact binomial intervals; independent-answer assumption',
                transform=ax[1].transAxes, fontsize=8)
    fig.suptitle('An aggregate signal does not identify a reliable winning photo', fontsize=14)
    save_figure(fig, out, '02_agreement_and_pair_uncertainty')

    fig, ax = plt.subplots(1, 2, figsize=(11.5, 4.9), layout='constrained')
    comp = cats.groupby('n_components').size()
    ax[0].bar(comp.index, comp, color=BLUE)
    for k, v in comp.items(): ax[0].text(k, v+3, str(v), ha='center')
    ax[0].set(title='Within-cat image comparison networks', xlabel='Connected components per cat',
              ylabel='Cats', xticks=comp.index, ylim=(0, comp.max()*1.2))
    ax[0].text(.97, .95, f"{int(cats.connected.sum())}/{len(cats)} connected\n"
               f"{int(cats.finite_unpenalized_bt.sum())}/{len(cats)} strongly connected win graphs",
               transform=ax[0].transAxes, ha='right', va='top', fontsize=9)
    c = coverage[coverage.training_scope.eq('within_cat')].iloc[0]
    vals = [c.validation_both_images_seen, c.validation_one_image_seen, c.validation_neither_image_seen]
    ax[1].bar(range(3), vals, color=[BLUE, ORANGE, GRAY])
    for i, v in enumerate(vals):
        ax[1].text(i, v+4, f'{v:,}\n({v/c.validation_records:.2%})', ha='center')
    ax[1].set(title='Pair-held-out validation: within-cat data only',
              xlabel='Image coverage in the fitting subset', ylabel='Validation response records',
              xticks=range(3), xticklabels=['Both seen', 'One seen', 'Neither seen'],
              ylim=(0, max(vals)*1.25))
    fig.suptitle('Sparse coverage favors partial pooling and explicit unseen-image handling', fontsize=14)
    save_figure(fig, out, '03_image_model_readiness')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=project_path('processed')/'train_clean.csv')
    parser.add_argument('--split', type=Path, default=project_path('splits')/'validation_split.csv')
    parser.add_argument('--output', type=Path, default=module_output('image_analysis'))
    parser.add_argument('--permutations', type=int, default=CONFIG['image_analysis']['permutations'])
    parser.add_argument('--conditional-permutations', type=int, default=CONFIG['image_analysis']['conditional_permutations'])
    parser.add_argument('--bootstrap', type=int, default=CONFIG['image_analysis']['bootstrap'])
    args = parser.parse_args()
    if min(args.permutations, args.conditional_permutations, args.bootstrap) < 100:
        parser.error('Use at least 100 resamples for each procedure')
    begin = time.perf_counter()
    hashes = {'input': digest(args.input), 'split': digest(args.split)}
    out = args.output.resolve()
    for folder in ['tables', 'figures', 'data']: (out/folder).mkdir(parents=True, exist_ok=True)
    d = load_data(args.input)
    w = d[d.comparison_type.eq('within_cat')].copy()
    if w.empty: raise ValueError('No within-cat records')
    pairs = pair_table(d)
    within = pair_table(w, inference=True)
    summary = agreement_summary(within)
    summary.update(seed=SEED, cats=int(w.a_cat.nunique()), images=len(set(w.a_image)|set(w.b_image)),
                   choice_a_fraction=float(w.choice_a.mean()),
                   pairs_with_both_orientations=int(w.groupby('image_pair_id').a_image.nunique().eq(2).sum()),
                   exact_p_below_005=int((within.p_exact_two_sided < .05).sum()),
                   by_p_below_005=int((within.p_by < .05).sum()),
                   min_exact_p=float(within.p_exact_two_sided.min()),
                   cat_cluster_ci95=cluster_bootstrap(within, args.bootstrap),
                   n_bootstrap=args.bootstrap)
    summary['primary_permutation'], null = permutation_agreement(w, args.permutations)
    summary['within_cat_conditional_permutation'], null_cat = permutation_agreement(
        w, args.conditional_permutations, SEED+1, within_cat=True)
    save_csv(pd.DataFrame({'agreement': null}), out/'data/global_permutation_null.csv')
    save_csv(pd.DataFrame({'agreement': null_cat}), out/'data/cat_conditional_permutation_null.csv')
    by_n = []
    for (kind, n), sub in pairs.groupby(['comparison_type', 'n_responses'], sort=True):
        by_n.append(dict(comparison_type=kind, n_responses=int(n), n_pairs=len(sub),
                         n_unanimous=int(sub.unanimous.sum()), n_mixed=int(sub.mixed_choices.sum()),
                         unanimous_fraction=float(sub.unanimous.mean()),
                         fair_coin_unanimous_probability=float(2.**(1-n)),
                         dyad_weighted_agreement=(float(sub.agreeing_dyads.sum()/sub.response_dyads.sum())
                                                  if n > 1 else np.nan)))
    by_n = pd.DataFrame(by_n)
    compare = pd.DataFrame([dict(comparison_type=kind, **agreement_summary(sub))
                            for kind, sub in pairs.groupby('comparison_type', sort=True)])
    sensitivity = []
    for name, data in [('all_records', w),
                       ('drop_extra_identical_contents', w[~w.content_duplicate_extra]),
                       ('complete_human_information', w[w[ORIGINAL[6:]].notna().all(axis=1)]),
                       ('pairs_with_both_orientations', w[w.image_pair_id.isin(
                           w.groupby('image_pair_id').a_image.nunique().loc[lambda s: s == 2].index)])]:
        p = pair_table(data)
        low, high = cluster_bootstrap(p, args.bootstrap)
        sensitivity.append(dict(scenario=name, **agreement_summary(p), ci95_low=low, ci95_high=high))
    sensitivity = pd.DataFrame(sensitivity)
    cats, images = graph_tables(w)
    coverage = split_diagnostic(d, args.split)
    summary['graph'] = dict(connected_cats=int(cats.connected.sum()),
                           finite_unpenalized_bt_cats=int(cats.finite_unpenalized_bt.sum()),
                           total_components=int(cats.n_components.sum()),
                           within_only_identifiable_contrasts=int(cats.identifiable_score_contrasts.sum()),
                           images_with_one_opponent=int(images.n_distinct_opponents.eq(1).sum()),
                           median_image_appearances=float(images.n_appearances.median()),
                           min_cat_records=int(cats.n_responses.min()), max_cat_records=int(cats.n_responses.max()))
    summary['sensitivity'] = sensitivity.to_dict(orient='records')
    summary['split_coverage'] = coverage.to_dict(orient='records')
    save_csv(within, out/'tables/within_cat_pair_statistics.csv')
    save_csv(pairs, out/'tables/all_pair_disagreement.csv')
    save_csv(by_n, out/'tables/agreement_by_response_count.csv')
    save_csv(compare, out/'tables/comparison_type_summary.csv')
    save_csv(sensitivity, out/'tables/sensitivity_analysis.csv')
    save_csv(cats, out/'tables/cat_image_graphs.csv')
    save_csv(images, out/'tables/image_coverage.csv')
    save_csv(coverage, out/'tables/split_image_coverage.csv')
    # Aggregate descriptive candidates only: not row-level features for validation.
    candidates = within.sort_values(['n_responses', 'majority_share', 'image_pair_id'],
                                    ascending=[False, False, True]).head(12).copy()
    candidates['selection_rule'] = 'n descending; observed majority descending; pair ID ascending'
    save_csv(candidates, out/'tables/illustrative_pairs_NOT_validated_winners.csv')
    (out/'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    figures(pairs, within, by_n, null, summary, cats, coverage, out)
    write_reports(summary, project_path('reports') if out == module_output('image_analysis').resolve() else out/'reports')
    if hashes != {'input': digest(args.input), 'split': digest(args.split)}:
        raise RuntimeError('Upstream source changed during analysis')
    metadata = dict(python=platform.python_version(), platform=platform.platform(),
                    processor=platform.processor(), versions={name: mod.__version__ for name, mod in
                    [('numpy', np), ('pandas', pd), ('scipy', scipy), ('matplotlib', matplotlib)]},
                    seed=SEED, source_sha256=hashes, script_sha256=digest(__file__),
                    report_script_sha256=digest(Path(__file__).with_name('report.py')),
                    data_contract_sha256=digest(ROOT/'src/cat_arena/common/data.py'),
                    config_sha256=digest(CONFIG_PATH),
                    runtime_seconds=round(time.perf_counter()-begin, 3),
                    parameters=dict(permutations=args.permutations,
                                    conditional_permutations=args.conditional_permutations, bootstrap=args.bootstrap))
    (out/'run_metadata.json').write_text(json.dumps(metadata, indent=2)+'\n', encoding='utf-8', newline='\n')
    if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8', newline='\n')
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f'Completed in {metadata["runtime_seconds"]:.1f}s: {out}')


if __name__ == '__main__':
    main()
