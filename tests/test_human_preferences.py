import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from cat_arena.human_preferences.analysis import _holm, _position_choices, _prepare, _rank_table, _stratified_score_test, _wilson


def sample():
    rows = []
    for a, b, history, chosen in [
        ('cat_000001', 'cat_000002', 'current', 1),
        ('cat_000001', 'cat_000002', 'current', 1),
        ('cat_000001', 'cat_000002', 'past', 0),
        ('cat_000001', 'cat_000002', 'past', 0),
        ('cat_000001', 'cat_000003', 'current', 1),
        ('cat_000001', 'cat_000003', 'current', 1),
        ('cat_000001', 'cat_000003', 'past', 0),
        ('cat_000001', 'cat_000003', 'past', 0),
    ]:
        rows.append(dict(a_cat=a, b_cat=b, choice='A' if chosen else 'B',
                         comparison_type='between_cats', pet_history=history,
                         pet_contact='daily', pet_care='never', gender='woman',
                         future_pet='yes', mbti_ie='unknown'))
    return pd.DataFrame(rows)


class HumanPreferenceTests(unittest.TestCase):
    def test_prepare_canonicalizes_cat_pair_choice(self):
        data = sample()
        reversed_row = data.iloc[[0]].copy()
        reversed_row['a_cat'], reversed_row['b_cat'] = 'cat_000002', 'cat_000001'
        reversed_row['choice'] = 'B'
        prepared = _prepare(pd.concat([data, reversed_row], ignore_index=True))
        self.assertEqual(prepared.cat_pair_id.nunique(), 2)
        self.assertEqual(prepared.choice_cat_1.iloc[0], prepared.choice_cat_1.iloc[-1])

    def test_cat_pair_stratified_test_detects_synthetic_group_difference(self):
        result = _stratified_score_test(_prepare(sample()), 'pet_history')
        self.assertEqual(result['df'], 1)
        self.assertEqual(result['informative_cat_pairs'], 2)
        self.assertLess(result['p_value'], .05)

    def test_group_rankings_use_cat_wins_over_appearances(self):
        ranks = _rank_table(_prepare(sample()), 'pet_history')
        current = ranks[ranks.group.eq('current')].set_index('cat_id')
        past = ranks[ranks.group.eq('past')].set_index('cat_id')
        self.assertEqual(current.loc['cat_000001', 'rank'], 1)
        self.assertEqual(past.loc['cat_000002', 'rank'], 1)

    def test_holm_adjustment_is_monotone_and_bounded(self):
        adjusted = _holm([.01, .04, .03])
        np.testing.assert_allclose(adjusted, [.03, .06, .06])
        self.assertTrue(np.all(adjusted <= 1))

    def test_wilson_interval_and_a_b_counts(self):
        low, high = _wilson(5, 10)
        self.assertLess(low, .5)
        self.assertGreater(high, .5)
        choices = _position_choices(_prepare(sample()))
        row = choices[(choices.group_variable == 'pet_history') & (choices.group == 'current')].iloc[0]
        self.assertEqual(row.choose_a + row.choose_b, row.n_responses)
        self.assertEqual(row.proportion_choose_a, row.choose_a/row.n_responses)


if __name__ == '__main__':
    unittest.main()
