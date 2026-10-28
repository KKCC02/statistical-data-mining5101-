"""Run from any directory: python scripts/run_data_preparation.py."""
from pathlib import Path
import argparse
from cat_arena.common.paths import PROJECT_ROOT, CONFIG, project_path, module_output
import csv
import hashlib
import json
import platform
import time

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image

ROOT = PROJECT_ROOT
RAW = project_path('raw')
IMAGES = project_path('images')
OUT = module_output('data_preparation')
DATA = project_path('processed')
SPLITS = project_path('splits')
SEED = CONFIG['seed']
HUMAN = ['gender', 'pet_history', 'pet_care', 'pet_contact', 'future_pet', 'mbti_ie']
ALLOWED = {
    'choice': ['A', 'B'], 'comparison_type': ['within_cat', 'between_cats'],
    'gender': ['man', 'woman'], 'pet_history': ['current', 'past', 'never'],
    'pet_care': ['never', 'occasionally', 'past_regular', 'current_regular'],
    'pet_contact': ['never', 'rarely', 'sometimes', 'often', 'daily'],
    'future_pet': ['yes', 'no', 'unsure'], 'mbti_ie': ['I', 'E', 'unknown'],
}
BASE_COLUMNS = ['a_cat', 'b_cat', 'a_image', 'b_image', 'choice',
                'comparison_type', *HUMAN]


def read_source(name):
    """Preserve identifiers and unknown/NA-like literal categories for validation."""
    path = RAW / (name + '.csv')
    expected = [name + '_row_id', *BASE_COLUMNS]
    if name == 'test':
        expected.append('prob_a')
    with path.open(encoding='utf-8-sig', newline='') as handle:
        reader = csv.reader(handle)
        header = next(reader)
        if len(header) != len(set(header)) or set(header) != set(expected):
            raise ValueError(f'{name}: unexpected or duplicate columns: {header}')
        if any(len(row) != len(header) for row in reader):
            raise ValueError(f'{name}: malformed CSV row width')
    return pd.read_csv(path, dtype='string', keep_default_na=False, na_values=[''])


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(df, path):
    df.to_csv(path, index=False, encoding='utf-8-sig', lineterminator='\n')


def prepare(raw, name, checks):
    df = raw.copy()
    row_id = 'train_row_id' if name == 'train' else 'test_row_id'
    changes = 0
    for col in df.select_dtypes(include=['object', 'string']):
        cleaned = df[col].str.strip().replace('', pd.NA)
        same_value = (df[col].eq(cleaned).fillna(False)
                      | (df[col].isna() & cleaned.isna()))
        changes += int((~same_value).sum())
        df[col] = cleaned
    def check(label, count, action, fatal=False):
        checks.append(dict(dataset=name, check=label, count=int(count), action=action))
        if fatal and count:
            save(pd.DataFrame(checks), OUT/'tables'/'quality_check_summary.csv')
            raise ValueError(f'{name}: {label}: {count}; resolve before continuing')
    check('trimmed_or_blank_normalized_cells', changes, 'normalize whitespace; blanks become missing')
    check('missing_row_id', df[row_id].isna().sum(), 'fail if present', True)
    check('duplicate_row_id', df[row_id].duplicated().sum(), 'fail if present', True)
    for col in ['a_cat', 'b_cat', 'a_image', 'b_image', 'comparison_type']:
        check('missing_' + col, df[col].isna().sum(), 'fail if present', True)
    for col, allowed in ALLOWED.items():
        check('invalid_' + col, (df[col].notna() & ~df[col].isin(allowed)).sum(), 'fail if present', True)
    if name == 'train':
        check('missing_choice', df.choice.isna().sum(), 'fail if present', True)
    else:
        check('unexpected_test_outcomes', df[['choice', 'prob_a']].notna().sum().sum(),
              'fail if present; test outcomes must remain withheld', True)
    same_cat = df.a_cat.eq(df.b_cat)
    check('comparison_type_mismatch', (same_cat != df.comparison_type.eq('within_cat')).sum(), 'fail if present', True)
    check('same_image', df.a_image.eq(df.b_image).sum(), 'fail if present', True)
    for side in ['a', 'b']:
        check(side + '_invalid_cat_id', (~df[side+'_cat'].str.fullmatch(r'cat_\d{6}')).sum(), 'fail if present', True)
        check(side + '_invalid_image_path', (~df[side+'_image'].str.fullmatch(r'cat_\d{6}/cat_\d{6}_\d{4}\.jpg')).sum(), 'fail if present', True)
        check(side + '_path_cat_mismatch', (df[side+'_image'].str.split('/').str[0] != df[side+'_cat']).sum(), 'fail if present', True)
        check(side + '_filename_cat_mismatch', (df[side+'_image'].str.split('/').str[-1].str[:10] != df[side+'_cat']).sum(), 'fail if present', True)
    paths = set(df.a_image) | set(df.b_image)
    check('missing_unique_image_files', sum(not (IMAGES/p).is_file() for p in paths), 'fail if present', True)
    content = [c for c in raw.columns if c != row_id]
    check('extra_content_duplicate_rows', df.duplicated(subset=content).sum(), 'retain; identity of respondents is unavailable')
    df['content_duplicate_flag'] = df.duplicated(subset=content, keep=False)
    check('rows_in_content_duplicate_groups', df.content_duplicate_flag.sum(), 'retain; includes the first row in each group')
    df['human_info_missing'] = df[HUMAN].isna().any(axis=1)
    df['human_info_all_missing'] = df[HUMAN].isna().all(axis=1)
    for col in HUMAN:
        df[col+'_missing'] = df[col].isna()
        check('missing_' + col, df[col].isna().sum(), 'retain and flag; no imputation')
    check('all_human_fields_missing', df.human_info_all_missing.sum(), 'retain and flag')
    check('partially_missing_human_fields', (df.human_info_missing & ~df.human_info_all_missing).sum(), 'retain and flag')
    first = df.a_image < df.b_image
    df['canonical_image_1'] = df.a_image.where(first, df.b_image)
    df['canonical_image_2'] = df.b_image.where(first, df.a_image)
    df['image_pair_id'] = df.canonical_image_1 + '||' + df.canonical_image_2
    catfirst = df.a_cat <= df.b_cat
    df['cat_pair_id'] = df.a_cat.where(catfirst, df.b_cat) + '||' + df.b_cat.where(catfirst, df.a_cat)
    # Outcome-derived fields must never be predictors. Test outcomes remain missing.
    valid = df.choice.isin(['A', 'B'])
    a_wins = df.choice.eq('A')
    df['choice_a'] = a_wins.astype('Int64').where(valid)
    df['choice_canonical_1'] = a_wins.eq(first).astype('Int64').where(valid)
    for entity in ['cat', 'image']:
        df['winner_'+entity] = df['a_'+entity].where(a_wins, df['b_'+entity]).where(valid)
        df['loser_'+entity] = df['b_'+entity].where(a_wins, df['a_'+entity]).where(valid)
    return df


def inspect_images(train, test):
    """Check file decoding, not subjective photo quality; never modify an image."""
    paths = sorted(set(train.a_image) | set(train.b_image) | set(test.a_image) | set(test.b_image))
    rows = []
    for rel in paths:
        path = IMAGES / rel
        row = dict(image=rel, bytes=path.stat().st_size, sha256=file_hash(path),
                   width=None, height=None, format=None, error='')
        try:
            with Image.open(path) as im:
                im.verify()
            with Image.open(path) as im:
                im.load()
                row.update(width=im.width, height=im.height, format=im.format)
        except Exception as exc:
            row['error'] = f'{type(exc).__name__}: {exc}'
        rows.append(row)
    result = pd.DataFrame(rows)
    save(result, OUT/'tables'/'image_file_check.csv')
    if result.error.ne('').any():
        raise ValueError('Image decoding failed; see image_file_check.csv')
    return result


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    required = [RAW/'train.csv', RAW/'test.csv', IMAGES]
    missing = [str(p) for p in required if not p.exists()]
    if missing:
        raise FileNotFoundError('Full preparation requires course CSV files and images. See data/raw/README.md. Missing: ' + ', '.join(missing))
    start = time.perf_counter()
    for p in [DATA, SPLITS, OUT/'tables', OUT/'figures']:
        p.mkdir(parents=True, exist_ok=True)
    source_hashes = {s+'.csv': file_hash(RAW/(s+'.csv')) for s in ['train', 'test']}
    raw = {s: read_source(s) for s in ['train', 'test']}
    checks = []
    train, test = [prepare(raw[s], s, checks) for s in ['train', 'test']]
    image_checks = inspect_images(train, test)
    save(train, DATA/'train_clean.csv')
    save(test, DATA/'test_features_clean.csv')
    save(pd.DataFrame(checks), OUT/'tables'/'quality_check_summary.csv')

    pairs = train.groupby(['image_pair_id', 'comparison_type', 'canonical_image_1', 'canonical_image_2'], as_index=False).agg(
        n_responses=('choice_canonical_1', 'size'), n_choose_image_1=('choice_canonical_1', 'sum'))
    pairs['n_choose_image_2'] = pairs.n_responses - pairs.n_choose_image_1
    pairs['proportion_choose_image_1'] = pairs.n_choose_image_1 / pairs.n_responses
    # Descriptive only: 100% agreement with 1-4 answers is not proof of population consensus.
    pairs['majority_share'] = pairs[['n_choose_image_1', 'n_choose_image_2']].max(axis=1) / pairs.n_responses
    save(pairs, DATA/'image_pair_summary.csv')
    pair_counts = pairs.groupby(['comparison_type', 'n_responses']).size().rename('n_image_pairs').reset_index()
    save(pair_counts, OUT/'tables'/'pair_response_distribution.csv')
    ids = np.array(sorted(train.image_pair_id.unique()))
    np.random.default_rng(SEED).shuffle(ids)
    val_ids = set(ids[:int(np.ceil(0.2*len(ids)))])
    split = train[['train_row_id', 'image_pair_id']].copy()
    split['split'] = np.where(split.image_pair_id.isin(val_ids), 'validation', 'train')
    assert not set(split.loc[split.split.eq('train'), 'image_pair_id']) & set(split.loc[split.split.eq('validation'), 'image_pair_id'])
    save(split, SPLITS/'validation_split.csv')

    missing = pd.DataFrame({'field': raw['train'].columns, 'missing_n': raw['train'].isna().sum().values})
    missing['missing_pct'] = 100*missing.missing_n/len(train)
    save(missing, OUT/'tables'/'missingness.csv')
    levels = []
    for col in ALLOWED:
        for level, n in train[col].fillna('[missing]').value_counts(dropna=False).items():
            levels.append(dict(field=col, level=level, n=n, pct=100*n/len(train)))
    save(pd.DataFrame(levels), OUT/'tables'/'category_distribution.csv')
    choices = pd.crosstab(train.comparison_type, train.choice).reindex(columns=['A','B'], fill_value=0)
    choices['n'] = choices.A + choices.B
    choices['proportion_A'] = choices.A / choices.n
    save(choices.reset_index(), OUT/'tables'/'choice_by_comparison_type.csv')
    exposures = pd.concat([train[['a_cat','comparison_type']].rename(columns={'a_cat':'cat_id'}), train[['b_cat','comparison_type']].rename(columns={'b_cat':'cat_id'})])
    exposure = exposures.groupby(['cat_id','comparison_type']).size().unstack(fill_value=0).reset_index()
    # within_cat rows contribute two appearances of the same cat; report records instead.
    exposure['within_cat'] = exposure.within_cat // 2
    exposure = exposure.rename(columns={'within_cat':'within_cat_records', 'between_cats':'between_cats_appearances'})
    save(exposure, OUT/'tables'/'cat_coverage.csv')
    summary = {
        'train_rows': len(train), 'test_rows': len(test),
        'rows_removed': len(raw['train']) - len(train),
        'normalized_train_cells': next(c['count'] for c in checks if c['dataset']=='train' and c['check']=='trimmed_or_blank_normalized_cells'),
        'choice_A': int(train.choice.eq('A').sum()), 'choice_B': int(train.choice.eq('B').sum()),
        'between_cats_rows': int(train.comparison_type.eq('between_cats').sum()),
        'within_cat_rows': int(train.comparison_type.eq('within_cat').sum()),
        'train_cats': len(set(train.a_cat)|set(train.b_cat)),
        'train_images': len(set(train.a_image)|set(train.b_image)),
        'unique_train_image_pairs': len(pairs), 'repeated_train_image_pairs': int((pairs.n_responses>1).sum()),
        'human_all_missing': int(train.human_info_all_missing.sum()),
        'extra_content_duplicate_rows': next(c['count'] for c in checks if c['dataset']=='train' and c['check']=='extra_content_duplicate_rows'),
        'rows_in_content_duplicate_groups': int(train.content_duplicate_flag.sum()),
        'pairs_with_both_orientations': int(train.groupby('image_pair_id').a_image.nunique().eq(2).sum()),
        'referenced_images_decoded': len(image_checks),
        'extra_byte_identical_image_files': int(image_checks.sha256.duplicated().sum()),
        'train_test_image_pair_overlap': len(set(train.image_pair_id)&set(test.image_pair_id)),
        'test_unseen_cats': len((set(test.a_cat)|set(test.b_cat))-(set(train.a_cat)|set(train.b_cat))),
        'test_unseen_images': len((set(test.a_image)|set(test.b_image))-(set(train.a_image)|set(train.b_image))),
        'validation_rows': int(split.split.eq('validation').sum()), 'seed': SEED,
    }
    (OUT/'tables'/'dataset_summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8', newline='\n')
    save(pd.DataFrame([{'metric': key, 'value': value} for key, value in summary.items()]), OUT/'tables'/'dataset_overview.csv')

    plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False, 'figure.dpi': 140})
    colors = ['#377EB8', '#F0A44B']
    fig, ax = plt.subplots(1,2,figsize=(10,4))
    choices['n'].plot.bar(ax=ax[0], color=colors, rot=0)
    ax[0].set(title='Comparison types', ylabel='Response records', xlabel='')
    ax[0].set_ylim(0, choices.n.max()*1.22)
    for i,n in enumerate(choices.n): ax[0].text(i,n,f'{n:,}\n({n/len(train):.2%})',ha='center',va='bottom')
    choices[['A','B']].div(choices.n, axis=0).plot.bar(stacked=True,ax=ax[1],color=colors,rot=0)
    ax[1].set(title='Observed choices by comparison type',ylabel='Proportion',xlabel='',ylim=(0,1))
    ax[1].get_legend().remove()
    for i,p in enumerate(choices.proportion_A):
        ax[1].text(i,p/2,f'A: {p:.2%}',ha='center',color='white')
        ax[1].text(i,p+(1-p)/2,f'B: {1-p:.2%}',ha='center',color='black')
    save_figure(fig, '01_comparisons_and_choices')
    fig,ax=plt.subplots(1,2,figsize=(10,4))
    ax[0].hist(exposure.between_cats_appearances,bins=15,color=colors[0],edgecolor='white')
    ax[0].set(title='Between-cat coverage',xlabel='Appearances per cat',ylabel='Number of cats')
    counts=pd.crosstab(pairs.n_responses,pairs.comparison_type).reindex(range(1,int(pairs.n_responses.max())+1),fill_value=0)
    counts.plot.bar(ax=ax[1],color=colors,rot=0)
    ax[1].set(title='Responses per unordered image pair',xlabel='Response records per pair',ylabel='Number of image pairs')
    ax[1].legend(fontsize=8)
    save_figure(fig, '02_data_coverage')
    fig,ax=plt.subplots(1,2,figsize=(10,4))
    history=train.pet_history.fillna('[missing]').value_counts().reindex(['never','past','current','[missing]'],fill_value=0)
    history.plot.bar(ax=ax[0],color=colors[0],rot=0)
    ax[0].set(title='Pet history',ylabel='Response records',xlabel='')
    ax[0].set_ylim(0,history.max()*1.22)
    for i,n in enumerate(history): ax[0].text(i,n,f'{n:,}\n({n/len(train):.2%})',ha='center',va='bottom',fontsize=9)
    miss_pct=train[HUMAN].isna().mean()*100
    miss_pct.plot.barh(ax=ax[1],color=colors[1])
    ax[1].set(title='Missing human information',xlabel='Missing records (%)',xlim=(0,max(3,float(miss_pct.max())*1.6)))
    for i,col in enumerate(HUMAN): ax[1].text(miss_pct[col]+0.04,i,f'{train[col].isna().sum():,} ({miss_pct[col]:.2f}%)',va='center',fontsize=9)
    save_figure(fig, '03_human_information')
    versions = {'python':platform.python_version(),'pandas':pd.__version__,'numpy':np.__version__,'matplotlib':matplotlib.__version__, 'Pillow':Image.__version__}
    if any(file_hash(RAW/name) != value for name,value in source_hashes.items()):
        raise RuntimeError('Source data changed during execution')
    (OUT/'run_metadata.json').write_text(json.dumps({'versions':versions,'platform':platform.platform(),'processor':platform.processor(),'runtime_seconds':round(time.perf_counter()-start,2),'seed':SEED,'source_sha256':source_hashes,'script_sha256':file_hash(Path(__file__))},indent=2),encoding='utf-8', newline='\n')
    print(json.dumps(summary,indent=2))
    print('Completed. Tables: outputs/tables; figures: outputs/figures; data: data/processed')


def save_figure(fig, name):
    fig.tight_layout()
    fig.savefig(OUT/'figures'/(name+'.png'), dpi=300)
    fig.savefig(OUT/'figures'/(name+'.pdf'), metadata={'CreationDate': None, 'ModDate': None})
    plt.close(fig)


if __name__ == '__main__':
    main()
