"""Generate member 2's full-data descriptive rankings and figures."""
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
from scipy.stats import spearmanr

from cat_arena.common.data import load_training
from cat_arena.common.paths import CONFIG_PATH, module_output, project_path, write_text
from .model import fit_bradley_terry, win_rate_ranking


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _save(fig, out, name):
    fig.tight_layout()
    fig.savefig(out/'figures'/f'{name}.png', dpi=300, bbox_inches='tight')
    fig.savefig(out/'figures'/f'{name}.pdf', bbox_inches='tight', metadata={'CreationDate': None, 'ModDate': None})
    plt.close(fig)


def run_analysis(input_path=None, output_path=None):
    started = time.perf_counter()
    source = Path(input_path) if input_path is not None else project_path('processed')/'train_clean.csv'
    out = Path(output_path) if output_path is not None else module_output('cat_ranking')
    fingerprint = digest(source)
    data = load_training(source)
    between = data.loc[data.comparison_type.eq('between_cats')]
    ranking = win_rate_ranking(between)
    fit = fit_bradley_terry(between)
    comparison = ranking.merge(fit.scores, on='cat_id', validate='one_to_one')
    comparison['rank_change'] = comparison.win_rate_rank-comparison.bt_rank
    comparison = comparison.sort_values(['bt_rank', 'cat_id']).reset_index(drop=True)
    rho = float(spearmanr(comparison.win_rate, comparison.bt_score).statistic)
    top_overlap = len(set(ranking.head(10).cat_id) & set(comparison.head(10).cat_id))
    for name in ['tables', 'figures']: (out/name).mkdir(parents=True, exist_ok=True)
    for name, table in [('cat_win_rate_ranking', ranking), ('cat_ranking_comparison', comparison)]:
        table.to_csv(out/'tables'/f'{name}.csv', index=False, encoding='utf-8-sig', lineterminator='\n')
    summary = dict(**fit.diagnostics, spearman_rho=rho, top10_overlap=top_overlap,
                   analysis_scope='all supplied between-cat training records; descriptive, not validation')
    write_text(out/'summary.json', json.dumps(summary, indent=2)+'\n')
    n_cats = len(comparison)
    fig, ax = plt.subplots(figsize=(7, 7))
    ax.scatter(comparison.win_rate_rank, comparison.bt_rank, color='#377EB8', alpha=.65, s=28)
    ax.plot([1, n_cats], [1, n_cats], linestyle='--', color='gray', linewidth=1)
    changes = comparison.assign(absolute_change=comparison.rank_change.abs()).sort_values(
        ['absolute_change', 'cat_id'], ascending=[False, True])
    for row in changes.head(2).itertuples():
        ax.annotate(row.cat_id, (row.win_rate_rank, row.bt_rank), xytext=(8, 8),
                    textcoords='offset points', fontsize=9)
    ax.set(xlabel='Win-rate rank (1 = highest)', ylabel='Bradley-Terry rank (1 = highest)',
           title=f'Win-rate vs Bradley-Terry ranking\nSpearman correlation = {rho:.4f}',
           xlim=(0, n_cats+5), ylim=(0, n_cats+5))
    ax.set_aspect('equal', adjustable='box'); ax.grid(alpha=.2)
    _save(fig, out, '01_rank_comparison')
    fig, axes = plt.subplots(1, 2, figsize=(13, 6))
    for ax, subset, title, color in [
        (axes[0], comparison.nlargest(10, 'bt_score'), 'Top 10 cats', '#377EB8'),
        (axes[1], comparison.nsmallest(10, 'bt_score'), 'Bottom 10 cats', '#F0A44B')]:
        labels = [f'{r.cat_id} (n={r.comparisons})' for r in subset.itertuples()]
        ax.barh(labels, subset.bt_score, color=color); ax.invert_yaxis()
        ax.axvline(0, color='gray', linewidth=1)
        ax.set(title=title, xlabel='Centered BT score')
        ax.grid(axis='x', alpha=.2); ax.set_axisbelow(True)
        limit = comparison.bt_score.abs().max()*1.15
        ax.set_xlim(-limit, limit)
    fig.suptitle('Cat preference ranking: Bradley-Terry model', fontsize=15)
    _save(fig, out, '02_bt_top_bottom')
    if digest(source) != fingerprint: raise RuntimeError('Input changed during analysis')
    meta = dict(python=platform.python_version(), platform=platform.platform(),
                versions={name: mod.__version__ for name, mod in [('numpy', np), ('pandas', pd),
                                                               ('scipy', scipy), ('matplotlib', matplotlib)]},
                source_sha256=fingerprint, analysis_sha256=digest(__file__),
                model_sha256=digest(Path(__file__).with_name('model.py')), config_sha256=digest(CONFIG_PATH),
                runtime_seconds=round(time.perf_counter()-started, 3))
    write_text(out/'run_metadata.json', json.dumps(meta, indent=2)+'\n')
    return ranking, comparison, summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    _, _, summary = run_analysis(args.input, args.output)
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
