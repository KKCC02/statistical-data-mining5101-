"""Checks for direction errors, false side-bias signals and source-count consistency."""
import itertools
import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from member3_analysis import (ORIGINAL, load_data, pair_table, agreement_summary,
                              permutation_agreement, graph_tables, split_diagnostic)


def records(pairs=20, all_side_a=False):
    rows = []
    for i in range(pairs):
        cat = f'cat_{i:06d}'
        first, second = f'{cat}/1.jpg', f'{cat}/2.jpg'
        for j in range(4):
            a, b = (first, second) if j % 2 == 0 else (second, first)
            rows.append(dict(train_row_id=f'{i}-{j}', a_cat=cat, b_cat=cat,
                             a_image=a, b_image=b, choice='A' if all_side_a or a == first else 'B',
                             comparison_type='within_cat', gender='woman', pet_history='current',
                             pet_care='occasionally', pet_contact='often', future_pet='yes', mbti_ie='I'))
    return pd.DataFrame(rows)


def prepare(data):
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp)/'source.csv'
        data.to_csv(path, index=False)
        return load_data(path)


class StatisticalCorrectness(unittest.TestCase):
    def test_swap_sides_and_labels_keeps_image_preferences(self):
        original = records()
        swapped = original.copy()
        mask = np.arange(len(swapped)) % 3 == 0
        swapped.loc[mask, ['a_image', 'b_image']] = swapped.loc[mask, ['b_image', 'a_image']].to_numpy()
        swapped.loc[mask, 'choice'] = swapped.loc[mask, 'choice'].map({'A': 'B', 'B': 'A'})
        a, b = pair_table(prepare(original)), pair_table(prepare(swapped))
        cols = ['image_pair_id', 'n_responses', 'n_choose_image_1', 'agreeing_dyads', 'dyad_agreement']
        pd.testing.assert_frame_equal(a[cols], b[cols])

    def test_four_unanimous_answers_do_not_establish_pair(self):
        table = pair_table(prepare(records(pairs=1)), inference=True)
        self.assertAlmostEqual(table.p_exact_two_sided.iloc[0], .125)
        self.assertLess(table.ci95_low.iloc[0], .5)
        self.assertAlmostEqual(table.ci95_high.iloc[0], 1.)

    def test_no_false_image_signal_for_always_choosing_a(self):
        d = prepare(records(all_side_a=True))
        result, null = permutation_agreement(d, n_resamples=199, seed=8)
        self.assertEqual(result['p_one_sided'], 1.)
        self.assertTrue(np.all(null == result['observed_agreement']))

    def test_detects_shared_image_choices_despite_ab_swapping(self):
        d = prepare(records())
        result, _ = permutation_agreement(d, n_resamples=999, seed=8)
        self.assertEqual(result['observed_agreement'], 1.)
        self.assertLess(result['p_one_sided'], .01)

    def test_cat_conditioning_is_not_global_shuffle(self):
        raw = records(pairs=2)
        raw['choice'] = np.where(raw.a_cat.eq('cat_000000'), 'A', 'B')
        d = prepare(raw)
        result, conditional_null = permutation_agreement(d, n_resamples=199, seed=7, within_cat=True)
        _, global_null = permutation_agreement(d, n_resamples=199, seed=7)
        self.assertEqual(result['p_one_sided'], 1.)
        self.assertAlmostEqual(float(conditional_null.var()), 0.)
        self.assertGreater(float(global_null.var()), 0.)

    def test_singletons_do_not_supply_agreement_trials(self):
        d = prepare(records(pairs=1).iloc[:1])
        table = pair_table(d)
        self.assertTrue(np.isnan(table.dyad_agreement.iloc[0]))
        with self.assertRaisesRegex(ValueError, 'No repeated pairs'):
            agreement_summary(table)
        with self.assertRaisesRegex(ValueError, 'requires repeated'):
            permutation_agreement(d, n_resamples=10)

    def test_disconnected_and_separated_networks(self):
        d = records(pairs=2)
        d['a_cat'] = 'cat_000000'; d['b_cat'] = 'cat_000000'
        for col in ['a_image', 'b_image']:
            d[col] = d[col].str.replace('cat_000001/1', 'cat_000000/3').str.replace('cat_000001/2', 'cat_000000/4')
        cats, images = graph_tables(prepare(d))
        self.assertEqual(cats.n_components.iloc[0], 2)
        self.assertFalse(cats.finite_unpenalized_bt.iloc[0])
        self.assertTrue(images.n_distinct_opponents.eq(1).all())
        self.assertEqual(cats.identifiable_score_contrasts.iloc[0], 2)

    def test_malformed_orientation_field_rejected(self):
        d = prepare(records(pairs=1))
        d.loc[0, 'choice_canonical_1'] = 0
        with self.assertRaisesRegex(ValueError, 'Member 1 field mismatch'):
            prepare(d)


class RealDataAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = load_data(ROOT.parent/'交接1/data/processed/train_clean.csv')
        cls.w = cls.d[cls.d.comparison_type.eq('within_cat')]

    def test_independent_record_combinations_match_summary(self):
        # Enumerate original choices rather than reusing canonical counts or formula.
        total, agree, mixed = 0, 0, 0
        for _, group in self.w.groupby('image_pair_id'):
            selected = [r.a_image if r.choice == 'A' else r.b_image for r in group.itertuples()]
            if len(selected) >= 2:
                mixed += len(set(selected)) > 1
            for left, right in itertools.combinations(selected, 2):
                total += 1
                agree += left == right
        summary = json.loads((ROOT/'outputs/summary.json').read_text(encoding='utf-8'))
        self.assertEqual(total, summary['response_dyads'])
        self.assertEqual(agree, summary['agreeing_dyads'])
        self.assertEqual(mixed, summary['mixed_repeated_pairs'])
        self.assertEqual(summary['response_records'], len(self.w))

    def test_agrees_with_member1_pair_summary(self):
        reference = pd.read_csv(ROOT.parent/'交接1/data/processed/image_pair_summary.csv')
        actual = pair_table(self.d)
        cols = ['image_pair_id', 'n_responses', 'n_choose_image_1', 'n_choose_image_2']
        pd.testing.assert_frame_equal(actual[cols].reset_index(drop=True),
                                      reference[cols].reset_index(drop=True))

    def test_split_integrity_and_denominators(self):
        split_path = ROOT.parent/'交接1/data/processed/validation_split.csv'
        coverage = split_diagnostic(self.d, split_path)
        counts = coverage[['validation_both_images_seen', 'validation_one_image_seen',
                           'validation_neither_image_seen']].sum(axis=1)
        self.assertTrue(counts.eq(coverage.validation_records).all())
        split = pd.read_csv(split_path)
        split.loc[0, 'split'] = 'validation' if split.loc[0, 'split'] == 'train' else 'train'
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'split.csv'; split.to_csv(path, index=False)
            with self.assertRaisesRegex(ValueError, 'Pair leakage'):
                split_diagnostic(self.d, path)

    def test_upstream_original_data_still_matches_course_file_when_available(self):
        source = ROOT.parent.parent/'course_files_export/Midterm/Dataset/train.csv'
        if not source.exists():
            self.skipTest('Course original file is not included in repository')
        original = pd.read_csv(source, keep_default_na=False, na_values=[''])
        cols = ['train_row_id', *ORIGINAL]
        pd.testing.assert_frame_equal(self.d[cols], original[cols])


if __name__ == '__main__':
    unittest.main(verbosity=2)
