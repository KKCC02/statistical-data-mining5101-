"""Shared cleaned-training-data contract, checked before any analysis."""
from pathlib import Path
import numpy as np
import pandas as pd

ORIGINAL = ['a_cat', 'b_cat', 'a_image', 'b_image', 'choice', 'comparison_type',
            'gender', 'pet_history', 'pet_care', 'pet_contact', 'future_pet', 'mbti_ie']

def load_training(path):
    d = pd.read_csv(path, keep_default_na=False, na_values=[''])
    if not set(['train_row_id', *ORIGINAL]).issubset(d.columns):
        raise ValueError('Required source fields are missing')
    if d.train_row_id.isna().any() or d.train_row_id.duplicated().any():
        raise ValueError('Training row identifiers must be unique and nonmissing')
    if d[ORIGINAL[:6]].isna().any().any() or not d.choice.isin(['A', 'B']).all():
        raise ValueError('Missing core fields or invalid choices')
    same = d.a_cat.eq(d.b_cat)
    if not d.comparison_type.eq(np.where(same, 'within_cat', 'between_cats')).all():
        raise ValueError('Comparison type inconsistent with cat identifiers')
    if d.a_image.eq(d.b_image).any():
        raise ValueError('An image cannot be compared with itself')
    for side in ['a', 'b']:
        if not d[f'{side}_image'].str.split('/').str[0].eq(d[f'{side}_cat']).all():
            raise ValueError('Image directory inconsistent with cat identifier')
    first = np.minimum(d.a_image.to_numpy(), d.b_image.to_numpy())
    second = np.maximum(d.a_image.to_numpy(), d.b_image.to_numpy())
    canonical = (np.where(d.choice.eq('A'), d.a_image, d.b_image) == first).astype(int)
    expected = {'canonical_image_1': first, 'canonical_image_2': second,
                'image_pair_id': first + '||' + second,
                'choice_a': d.choice.eq('A').astype(int), 'choice_canonical_1': canonical}
    for col, values in expected.items():
        if col in d and not np.array_equal(d[col].to_numpy(), np.asarray(values)):
            raise ValueError(f'Member 1 field mismatch: {col}')
        d[col] = values
    # Never remove these in the primary analysis: same contents do not identify a person.
    d['content_duplicate_extra'] = d.duplicated(ORIGINAL, keep='first')
    return d
