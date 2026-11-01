import sys
import unittest
from unittest.mock import patch
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from cat_arena.cat_ranking.model import fit_bradley_terry
from cat_arena.model_comparison.analysis import metrics
from cat_arena.model_comparison.design import fit
from cat_arena.model_comparison import design


COLUMNS = ['a_cat', 'b_cat', 'a_image', 'b_image', 'choice', 'comparison_type', 'pet_history']


def frame(rows):
    return pd.DataFrame(rows, columns=COLUMNS)


def between(a, b, choice):
    return (a, b, f'{a}/1.jpg', f'{b}/1.jpg', choice, 'between_cats', 'never')


def two_cat():
    """Four comparisons of cat_a against cat_b, with three A wins."""
    return frame([between('cat_a', 'cat_b', c) for c in 'AAAB'])


def position_bias():
    """Both orientations appear ten times and A is chosen in seven of each."""
    rows = []
    for i in range(10):
        rows.append(('cat_a', 'cat_b', 'cat_a/1.jpg', 'cat_b/1.jpg',
                     'A' if i < 7 else 'B', 'between_cats', 'never'))
        rows.append(('cat_b', 'cat_a', 'cat_b/1.jpg', 'cat_a/1.jpg',
                     'A' if i < 7 else 'B', 'between_cats', 'never'))
    return frame(rows)


class PairwiseDesignTests(unittest.TestCase):
    def test_exhausted_budget_continues_to_analytic_solution(self):
        with patch.dict(design.CONFIG['cat_ranking'], maxiter=1):
            model = fit(two_cat(), ['cat'])
        self.assertTrue(model.diagnostics['restarted_after_budget'])
        self.assertTrue(model.diagnostics['converged'])
        np.testing.assert_allclose(model.predict_proba(two_cat()), .75, atol=1e-7)

    def test_cat_block_reproduces_bradley_terry(self):
        data = two_cat()
        ours = fit(data, ['cat']).cat_scores().set_index('cat_id').score
        theirs = fit_bradley_terry(data).scores.set_index('cat_id').bt_score
        np.testing.assert_allclose(ours.loc[theirs.index], theirs, atol=1e-8)

    def test_cat_effects_are_centred(self):
        effects = fit(two_cat(), ['cat']).effects('cat')
        self.assertAlmostEqual(float(effects.effect.sum()), 0., places=10)

    def test_position_block_recovers_side_bias_without_cat_difference(self):
        data = position_bias()
        model = fit(data, ['cat', 'side'])
        scores = model.cat_scores().set_index('cat_id').score
        self.assertLess(abs(float(scores.loc['cat_a']-scores.loc['cat_b'])), .02)
        self.assertGreater(float(model.effects('side').effect.iloc[0]), .3)
        self.assertGreater(float(model.predict_proba(data).mean()), .6)

    def test_large_image_penalty_shrinks_image_effects(self):
        rows = [between('cat_a', 'cat_b', c) for c in 'AAAB']
        rows += [('cat_a', 'cat_a', 'cat_a/1.jpg', 'cat_a/2.jpg', 'A', 'within_cat', 'never')]*4
        model = fit(frame(rows), ['cat', 'image'], {'image': 1e6})
        self.assertLess(float(model.effects('image').effect.abs().max()), 1e-3)

    def test_image_effects_favour_the_winning_image(self):
        rows = [('cat_a', 'cat_a', 'cat_a/1.jpg', 'cat_a/2.jpg',
                 'A' if i < 7 else 'B', 'within_cat', 'never') for i in range(10)]
        rows += [between('cat_a', 'cat_b', c) for c in 'AAAB']
        effects = fit(frame(rows), ['cat', 'image']).effects('image').set_index('level').effect
        self.assertGreater(float(effects.loc['cat_a/1.jpg']), float(effects.loc['cat_a/2.jpg']))

    def test_unseen_levels_fall_back_to_zero(self):
        model = fit(two_cat(), ['cat'])
        unseen = frame([between('cat_new', 'cat_other', 'A')])
        self.assertEqual(float(model.unseen_coverage(unseen)), 0.)
        self.assertEqual(float(model.predict_proba(unseen)[0]), .5)

    def test_group_cat_requires_the_group_block(self):
        with self.assertRaisesRegex(ValueError, 'requires the group block'):
            fit(two_cat(), ['cat', 'group_cat'])

    def test_penalty_for_unused_block_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'unused blocks'):
            fit(two_cat(), ['cat'], {'image': 1.0})

    def test_metrics_match_manual_values(self):
        data = frame([between('cat_a', 'cat_b', c) for c in 'AB'])
        result = metrics(data, np.array([.8, .8]))
        self.assertAlmostEqual(result['accuracy'], .5)
        self.assertAlmostEqual(result['brier'], float(np.mean([(.8-1)**2, (.8-0)**2])))
        self.assertAlmostEqual(result['log_loss'], float(-np.mean([np.log(.8), np.log(.2)])))


if __name__ == '__main__':
    unittest.main()
