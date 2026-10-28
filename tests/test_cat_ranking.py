import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from cat_arena.cat_ranking.model import fit_bradley_terry, win_rate_ranking


def sample(choices):
    return pd.DataFrame({'a_cat': ['cat_a']*len(choices), 'b_cat': ['cat_b']*len(choices),
                         'choice': list(choices), 'comparison_type': ['between_cats']*len(choices)})


class CatRankingTests(unittest.TestCase):
    def test_two_cat_fit_matches_analytic_odds(self):
        d = sample('AAAB')
        fit = fit_bradley_terry(d)
        self.assertAlmostEqual(fit.predict_probability(['cat_a'], ['cat_b'])[0], .75, places=6)
        scores = fit.scores.set_index('cat_id').bt_score
        self.assertAlmostEqual(scores.cat_a-scores.cat_b, np.log(3), places=6)
        self.assertAlmostEqual(scores.mean(), 0.)

    def test_fit_uses_only_the_passed_records(self):
        high = fit_bradley_terry(sample('AAAB'))
        low = fit_bradley_terry(sample('ABBB'))
        self.assertGreater(high.predict_probability(['cat_a'], ['cat_b'])[0], .5)
        self.assertLess(low.predict_probability(['cat_a'], ['cat_b'])[0], .5)

    def test_reversed_sides_preserve_cat_scores(self):
        d = sample('AAAB')
        reverse = d.rename(columns={'a_cat': 'b_cat', 'b_cat': 'a_cat'}).copy()
        reverse['choice'] = reverse.choice.map({'A': 'B', 'B': 'A'})
        np.testing.assert_allclose(fit_bradley_terry(d).scores.bt_score,
                                   fit_bradley_terry(reverse).scores.bt_score)

    def test_rejects_separated_graph(self):
        with self.assertRaisesRegex(ValueError, 'strongly connected'):
            fit_bradley_terry(sample('AAAA'))

    def test_unseen_cats_need_explicit_fallback(self):
        fit = fit_bradley_terry(sample('AB'))
        with self.assertRaisesRegex(ValueError, 'Unseen cat'):
            fit.predict_probability(['new_a'], ['new_b'])
        self.assertEqual(fit.predict_probability(['new_a'], ['new_b'], unseen='zero')[0], .5)

    def test_rejects_within_cat_inputs(self):
        d = sample('AB'); d['comparison_type'] = 'within_cat'
        with self.assertRaisesRegex(ValueError, 'between_cats'):
            fit_bradley_terry(d)

    def test_win_accounting_and_ties(self):
        ranks = win_rate_ranking(sample('AB'))
        self.assertEqual(ranks.wins.sum(), 2)
        self.assertEqual(ranks.comparisons.sum(), 4)
        self.assertEqual(ranks.win_rate_rank.tolist(), [1, 1])


if __name__ == '__main__': unittest.main()
