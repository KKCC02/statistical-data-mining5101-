"""Reusable form of member 2's unregularized Bradley-Terry baseline."""
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.special import expit

from cat_arena.common.paths import CONFIG


@dataclass
class BradleyTerryFit:
    scores: pd.DataFrame
    diagnostics: dict

    def predict_probability(self, a_cats, b_cats, unseen='raise'):
        """Return P(A). Unknown cats raise unless caller explicitly requests zero-score fallback."""
        if unseen not in ['raise', 'zero']:
            raise ValueError("unseen must be 'raise' or 'zero'")
        a, b = pd.Series(a_cats).reset_index(drop=True), pd.Series(b_cats).reset_index(drop=True)
        if len(a) != len(b) or a.isna().any() or b.isna().any():
            raise ValueError('A and B identifiers must be nonmissing and equally sized')
        mapping = self.scores.set_index('cat_id').bt_score
        sa, sb = a.map(mapping), b.map(mapping)
        if unseen == 'raise' and (sa.isna().any() or sb.isna().any()):
            raise ValueError('Unseen cat: supply a documented fallback explicitly')
        return expit(sa.fillna(0).to_numpy()-sb.fillna(0).to_numpy())


def _between(data):
    required = ['a_cat', 'b_cat', 'choice', 'comparison_type']
    if not set(required).issubset(data.columns) or data[required].isna().any().any():
        raise ValueError('Required between-cat fields are missing')
    if data.empty or not data.comparison_type.eq('between_cats').all():
        raise ValueError('Fit/ranking requires a nonempty between_cats subset')
    if data.a_cat.eq(data.b_cat).any() or not data.choice.isin(['A', 'B']).all():
        raise ValueError('Invalid between-cat comparison or choice')
    winners = data.a_cat.where(data.choice.eq('A'), data.b_cat)
    losers = data.b_cat.where(data.choice.eq('A'), data.a_cat)
    return winners, losers


def win_rate_ranking(data):
    winners, losers = _between(data)
    ranking = pd.concat([winners.value_counts().rename('wins'),
                         losers.value_counts().rename('losses')], axis=1).fillna(0).astype(int)
    ranking.index.name = 'cat_id'
    ranking = ranking.reset_index()
    ranking['comparisons'] = ranking.wins+ranking.losses
    ranking['win_rate'] = ranking.wins/ranking.comparisons
    ranking['win_rate_rank'] = ranking.win_rate.rank(method='min', ascending=False).astype(int)
    ranking = ranking.sort_values(['win_rate', 'cat_id'], ascending=[False, True]).reset_index(drop=True)
    if ranking.wins.sum() != len(data) or ranking.comparisons.sum() != 2*len(data):
        raise RuntimeError('Win/loss accounting failed')
    return ranking[['win_rate_rank', 'cat_id', 'comparisons', 'wins', 'losses', 'win_rate']]


def fit_bradley_terry(data):
    """Fit only the records provided by the caller; no saved full-data scores are read."""
    winners, losers = _between(data)
    cats = sorted(set(data.a_cat) | set(data.b_cat))
    index = {cat: i for i, cat in enumerate(cats)}
    wi, li = winners.map(index).to_numpy(), losers.map(index).to_numpy()
    graph = coo_matrix((np.ones(len(data)), (wi, li)), shape=(len(cats), len(cats))).tocsr()
    components, _ = connected_components(graph, directed=True, connection='strong')
    if components != 1:
        raise ValueError('Unregularized BT needs a strongly connected win graph; change the model or split')

    def objective(free_scores):
        scores = np.r_[0., free_scores]
        difference = scores[wi]-scores[li]
        loss = np.logaddexp(0, -difference).mean()
        q = expit(-difference)
        gradient = (np.bincount(li, weights=q, minlength=len(cats))
                    - np.bincount(wi, weights=q, minlength=len(cats)))/len(data)
        return loss, gradient[1:]

    result = minimize(objective, np.zeros(len(cats)-1), jac=True, method='L-BFGS-B',
                      options=CONFIG['cat_ranking'])
    if not result.success or not np.isfinite(result.x).all():
        raise RuntimeError(f'BT optimization failed: {result.message}')
    scores = np.r_[0., result.x]
    scores -= scores.mean()
    table = pd.DataFrame({'cat_id': cats, 'bt_score': scores})
    table['bt_rank'] = table.bt_score.rank(method='min', ascending=False).astype(int)
    return BradleyTerryFit(table, dict(strong_components=int(components), converged=True,
                           optimizer_message=str(result.message), mean_negative_log_likelihood=float(result.fun),
                           max_abs_free_gradient=float(np.abs(result.jac).max()), records=len(data), cats=len(cats)))
