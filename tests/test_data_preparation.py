import sys
import tempfile
import unittest
import json
import io
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from cat_arena.common.paths import PROJECT_ROOT, project_path
from cat_arena.data_preparation import prepare, audit


class DataPreparationTests(unittest.TestCase):
    def test_configured_paths_are_repository_relative(self):
        self.assertEqual(project_path('processed'), PROJECT_ROOT/'data/processed')
        self.assertEqual(project_path('splits'), PROJECT_ROOT/'data/splits')

    def test_canonical_choices_missing_values_and_source_preservation(self):
        first = 'cat_000001/cat_000001_0001.jpg'
        second = 'cat_000002/cat_000002_0001.jpg'
        rows = []
        for i, (a, b, choice) in enumerate([(first, second, 'A'), (first, second, 'B'),
                                          (second, first, 'A'), (second, first, 'B')]):
            rows.append(dict(train_row_id=f'TR{i}', a_cat=a.split('/')[0], b_cat=b.split('/')[0],
                             a_image=a, b_image=b, choice=choice, comparison_type='between_cats',
                             gender='woman', pet_history=pd.NA, pet_care='never', pet_contact='daily',
                             future_pet='yes', mbti_ie='unknown'))
        raw = pd.DataFrame(rows, dtype='string')
        original = raw.copy(deep=True)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name in [first, second]:
                path = root/'images'/name; path.parent.mkdir(parents=True, exist_ok=True)
                Image.new('RGB', (3, 3), 'white').save(path)
            (root/'out/tables').mkdir(parents=True)
            with patch.object(prepare, 'IMAGES', root/'images'), patch.object(prepare, 'OUT', root/'out'):
                clean = prepare.prepare(raw, 'train', [])
        pd.testing.assert_frame_equal(raw, original)
        self.assertEqual(clean.choice_canonical_1.tolist(), [1, 0, 0, 1])
        self.assertEqual(clean.image_pair_id.nunique(), 1)
        self.assertTrue(clean.pet_history.isna().all())
        self.assertTrue(clean.mbti_ie.eq('unknown').all())
        self.assertTrue(clean.human_info_missing.all())

    def test_complete_preparation_and_independent_audit_on_small_image_fixture(self):
        # Exercise relocated paths, real image decoding, shared split and metadata together.
        first = 'cat_000001/cat_000001_0001.jpg'
        second = 'cat_000002/cat_000002_0001.jpg'
        third = 'cat_000001/cat_000001_0002.jpg'
        rows = []
        for i, (a, b, choice) in enumerate([(first, second, 'A'), (second, first, 'A'),
                                          (first, third, 'A'), (third, first, 'A')]):
            rows.append(dict(train_row_id=f'TR{i}', a_cat=a.split('/')[0], b_cat=b.split('/')[0],
                             a_image=a, b_image=b, choice=choice,
                             comparison_type='within_cat' if a.split('/')[0] == b.split('/')[0] else 'between_cats',
                             gender='woman', pet_history='current', pet_care='never', pet_contact='daily',
                             future_pet='yes', mbti_ie='unknown'))
        raw = pd.DataFrame(rows)
        test = raw.iloc[:2].rename(columns={'train_row_id': 'test_row_id'}).copy()
        test['choice'] = ''; test['prob_a'] = ''
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            folders = dict(ROOT=root, RAW=root/'data/raw', IMAGES=root/'data/raw/images',
                           OUT=root/'outputs/data_preparation', DATA=root/'data/processed', SPLITS=root/'data/splits')
            folders['RAW'].mkdir(parents=True)
            for name in [first, second, third]:
                path = folders['IMAGES']/name; path.parent.mkdir(parents=True, exist_ok=True)
                Image.new('RGB', (3, 3), 'white').save(path)
            raw.to_csv(folders['RAW']/'train.csv', index=False)
            test.to_csv(folders['RAW']/'test.csv', index=False)
            test.to_csv(folders['RAW']/'test_example.csv', index=False)
            with patch.multiple(prepare, **folders), patch.multiple(audit, **folders), \
                 patch.object(audit, 'MODULE_DOCS', root/'docs/modules/data_preparation'), \
                 patch.object(audit, 'RESULTS', []), patch.object(sys, 'argv', ['fixture']), redirect_stdout(io.StringIO()):
                prepare.main()
                audit.main()
            result = json.loads((folders['OUT']/'audit_report.json').read_text(encoding='utf-8'))
            self.assertTrue(result['passed'], result)
            self.assertGreater(result['n_checks'], 30)
            self.assertTrue((folders['SPLITS']/'validation_split.csv').exists())


if __name__ == '__main__': unittest.main()
