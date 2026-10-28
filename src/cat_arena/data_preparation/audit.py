"""Independent audit of member 1 outputs, using csv/Counter instead of pandas.

Run after scripts/run_data_preparation.py. Writes audit_report.json and quality_review.md.
This verifies data preparation; it does not fit or evaluate preference models.
"""
from collections import Counter, defaultdict
import argparse
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import subprocess
import sys

from cat_arena.common.paths import PROJECT_ROOT, project_path, module_output
ROOT = PROJECT_ROOT
RAW = project_path('raw')
IMAGES = project_path('images')
OUT = module_output('data_preparation')
DATA = project_path('processed')
SPLITS = project_path('splits')
MODULE_DOCS = ROOT/'docs/modules/data_preparation'
HUMAN = ['gender', 'pet_history', 'pet_care', 'pet_contact', 'future_pet', 'mbti_ie']
RESULTS = []


def read(relative):
    if relative in ['train.csv', 'test.csv', 'test_example.csv']:
        path = RAW/relative
    elif relative == 'data/splits/validation_split.csv':
        path = SPLITS/'validation_split.csv'
    elif relative.startswith('data/processed/'):
        path = DATA/Path(relative).name
    elif relative.startswith('outputs/'):
        path = OUT/relative[len('outputs/'):]
    else:
        path = ROOT/relative
    with path.open(encoding='utf-8-sig', newline='') as handle:
        reader = csv.DictReader(handle)
        return reader.fieldnames, list(reader)


def check(name, condition, detail):
    RESULTS.append(dict(check=name, passed=bool(condition), detail=detail))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def close(actual, expected):
    return abs(float(actual)-expected) < 1e-9


def check_dataset(name):
    fields, raw = read(name+'.csv')
    clean_name = 'train_clean.csv' if name=='train' else 'test_features_clean.csv'
    _, clean = read('data/processed/'+clean_name)
    idcol = name+'_row_id'
    check(name+'_row_count_and_order', len(raw)==len(clean) and
          [r[idcol] for r in raw]==[r[idcol] for r in clean], f'{len(raw)} source rows; {len(clean)} output rows')
    # Independent comparison of every original cell, allowing only documented whitespace normalization.
    differing_cells = sum(r[c].strip()!=s[c] for r,s in zip(raw,clean) for c in fields)
    normalized_cells = sum(r[c]!=r[c].strip() for r in raw for c in fields)
    check(name+'_original_cells_preserved', differing_cells==0,
          f'{differing_cells} unexplained differences; {normalized_cells} whitespace normalizations')
    content_fields = [c for c in fields if c!=idcol]
    counts = Counter(tuple(r[c].strip() for c in content_fields) for r in raw)
    failures = Counter()
    pairs = defaultdict(list)
    for r,s in zip(raw,clean):
        r={k:v.strip() for k,v in r.items()}
        first,second=sorted([r['a_image'],r['b_image']])
        pair=first+'||'+second
        pairs[pair].append(r)
        if (s['canonical_image_1'],s['canonical_image_2'],s['image_pair_id'])!=(first,second,pair):
            failures['canonical_image_pair']+=1
        if s['cat_pair_id']!='||'.join(sorted([r['a_cat'],r['b_cat']])):
            failures['canonical_cat_pair']+=1
        if s['content_duplicate_flag']!=str(counts[tuple(r[c] for c in content_fields)]>1):
            failures['duplicate_flags']+=1
        missing=[r[c]=='' for c in HUMAN]
        if s['human_info_missing']!=str(any(missing)) or s['human_info_all_missing']!=str(all(missing)):
            failures['human_missing_flags']+=1
        if any(s[c+'_missing']!=str(r[c]=='') for c in HUMAN):
            failures['individual_missing_flags']+=1
        if name=='train':
            chosen=r['a_image'] if r['choice']=='A' else r['b_image']
            unchosen=r['b_image'] if r['choice']=='A' else r['a_image']
            expected={'choice_a':str(int(r['choice']=='A')),
                      'choice_canonical_1':str(int(chosen==first)),
                      'winner_image':chosen,'loser_image':unchosen,
                      'winner_cat':chosen.split('/')[0],'loser_cat':unchosen.split('/')[0]}
            if any(s[c]!=v for c,v in expected.items()): failures['outcome_fields']+=1
        elif any(s[c]!='' for c in ['choice','prob_a','choice_a','choice_canonical_1','winner_cat','loser_cat','winner_image','loser_image']):
            failures['withheld_test_outcomes']+=1
    for item in ['canonical_image_pair','canonical_cat_pair','duplicate_flags','human_missing_flags','individual_missing_flags',
                 'outcome_fields' if name=='train' else 'withheld_test_outcomes']:
        check(name+'_'+item, failures[item]==0, f'{failures[item]} mismatched rows')
    return raw, clean, pairs


def audit_synthetic_cases():
    """Exercise all four order/choice combinations and invalid-input rejection."""
    from cat_arena.data_preparation import prepare as module
    pd=module.pd
    _,rows=read('train.csv')
    base=next(r for r in rows if r['comparison_type']=='between_cats')
    fixtures=[]
    for swapped in [False,True]:
        for choice in ['A','B']:
            r=base.copy()
            if swapped:
                for entity in ['cat','image']:
                    r['a_'+entity],r['b_'+entity]=r['b_'+entity],r['a_'+entity]
            r['choice']=choice; r['train_row_id']=f'fixture_{len(fixtures)}'
            fixtures.append(r)
    frame=pd.DataFrame(fixtures,dtype='string')
    with tempfile.TemporaryDirectory() as directory:
        module.OUT=Path(directory); (module.OUT/'tables').mkdir()
        result=module.prepare(frame,'train',[])
        expected=[int((r['a_image'] if r['choice']=='A' else r['b_image'])==min(r['a_image'],r['b_image'])) for r in fixtures]
        check('four_order_choice_combinations',result.choice_canonical_1.tolist()==expected and result.image_pair_id.nunique()==1,
              'A/B choices tested with both image orientations')
        blank=frame.iloc[[0]].copy()
        blank.loc[0,'pet_history']='  '; blank.loc[0,'mbti_ie']='unknown'
        blank.loc[0,'gender']=pd.NA
        checks=[]; normalized=module.prepare(blank,'train',checks)
        check('blank_unknown_and_partial_missing',pd.isna(normalized.loc[0,'pet_history']) and
              normalized.loc[0,'mbti_ie']=='unknown' and bool(normalized.loc[0,'human_info_missing']) and
              not bool(normalized.loc[0,'human_info_all_missing']) and checks[0]['count']==1,
              'Blank normalized; unknown preserved; partial missingness handled')
        for label, col, value in [('invalid_choice','choice','C'),('invalid_category','pet_history','NA'),
                                  ('inconsistent_type','comparison_type','within_cat')]:
            damaged=frame.iloc[[0]].copy(); damaged.loc[0,col]=value
            rejected=False
            try: module.prepare(damaged,'train',[])
            except ValueError: rejected=True
            check('reject_'+label,rejected,'Must stop rather than silently alter/drop the record')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rerun',action='store_true',help='Also rerun preparation from another working directory and compare output hashes')
    args=parser.parse_args()
    if args.rerun:
        paths=sorted(DATA.glob('*.csv'))+sorted((OUT/'tables').glob('*'))+sorted((OUT/'figures').glob('*'))
        paths += list(SPLITS.glob('*.csv'))
        before={str(p.relative_to(ROOT)):digest(p) for p in paths if p.is_file()}
        source_before={name:digest(RAW/name) for name in ['train.csv','test.csv','test_example.csv']}
        with tempfile.TemporaryDirectory() as working_directory:
            completed=subprocess.run([sys.executable,str(ROOT/'scripts/run_data_preparation.py')],cwd=working_directory,capture_output=True,text=True)
        if completed.returncode:
            raise RuntimeError(completed.stdout+'\n'+completed.stderr)
        changed=[name for name,value in before.items() if digest(RAW/name)!=value]
        check('reproducible_from_other_working_directory',not changed,f'{len(before)} data/table/figure files compared; changed: {changed}')
        check('source_files_unchanged_by_rerun',all(digest(RAW/name)==value for name,value in source_before.items()),
              'train.csv, test.csv, test_example.csv unchanged')
    raw,clean,pairs=check_dataset('train')
    raw_test,_,test_pairs=check_dataset('test')
    _,summaries=read('data/processed/image_pair_summary.csv')
    check('pair_summary_identity',len(summaries)==len(pairs) and {s['image_pair_id'] for s in summaries}==set(pairs),
          f'{len(pairs)} unique source image pairs')
    good=True
    for s in summaries:
        group=pairs[s['image_pair_id']]
        first=s['image_pair_id'].split('||')[0]
        winners=[r['a_image'] if r['choice']=='A' else r['b_image'] for r in group]
        a=winners.count(first); b=len(group)-a
        good &= (int(s['n_responses'])==len(group) and int(s['n_choose_image_1'])==a and int(s['n_choose_image_2'])==b
                 and close(s['proportion_choose_image_1'],a/len(group)) and close(s['majority_share'],max(a,b)/len(group))
                 and s['comparison_type']==group[0]['comparison_type'])
    check('all_pair_summary_counts_and_proportions',good,'Recomputed directly from source choices, not derived choice codes')
    _,category=read('outputs/tables/category_distribution.csv')
    category_ok=True
    for field in ['choice','comparison_type',*HUMAN]:
        expected=Counter(r[field] or '[missing]' for r in raw)
        observed={r['level']:int(r['n']) for r in category if r['field']==field}
        category_ok &= dict(expected)==observed
    category_ok &= all(close(r['pct'],int(r['n'])/len(raw)*100) for r in category)
    check('category_counts_and_denominators',category_ok,'Each field sums to all training responses; missing included')
    _,missing=read('outputs/tables/missingness.csv')
    check('missingness_table',all(int(s['missing_n'])==sum(r[s['field']]=='' for r in raw) and
          close(s['missing_pct'],int(s['missing_n'])/len(raw)*100) for s in missing),'Original training fields checked')
    _,choice=read('outputs/tables/choice_by_comparison_type.csv')
    check('choice_by_type_table',all(int(s[c])==sum(r['choice']==c and r['comparison_type']==s['comparison_type'] for r in raw)
          for s in choice for c in ['A','B']) and all(int(s['n'])==int(s['A'])+int(s['B']) and close(s['proportion_A'],int(s['A'])/int(s['n'])) for s in choice),
          'A/B numerators and comparison-type denominators verified')
    between=Counter(); within=Counter()
    for r in raw:
        if r['comparison_type']=='between_cats': between.update([r['a_cat'],r['b_cat']])
        else: within.update([r['a_cat']])
    _,coverage=read('outputs/tables/cat_coverage.csv')
    check('cat_coverage_counts',len(coverage)==len(set(between)|set(within)) and
          all(int(r['between_cats_appearances'])==between[r['cat_id']] and int(r['within_cat_records'])==within[r['cat_id']] for r in coverage),
          'Between-cat: two cats per record; within-cat: one record per cat')
    _,pair_dist=read('outputs/tables/pair_response_distribution.csv')
    expected=Counter((group[0]['comparison_type'],len(group)) for group in pairs.values())
    check('pair_response_distribution',expected==Counter({(s['comparison_type'],int(s['n_responses'])):int(s['n_image_pairs']) for s in pair_dist}),
          'Distribution matches source pair groups')
    _,split=read('data/splits/validation_split.csv')
    split_groups=defaultdict(set); record_groups={r['train_row_id']:'||'.join(sorted([r['a_image'],r['b_image']])) for r in raw}
    for r in split: split_groups[r['image_pair_id']].add(r['split'])
    check('split_record_coverage',len(split)==len(raw) and len({r['train_row_id'] for r in split})==len(raw) and
          all(r['train_row_id'] in record_groups and record_groups[r['train_row_id']]==r['image_pair_id'] for r in split),
          'Every source training row appears exactly once')
    check('split_pair_separation',all(len(values)==1 and values<= {'train','validation'} for values in split_groups.values()),
          'No unordered image pair crosses the saved split')
    image_paths={r[c] for r in raw+raw_test for c in ['a_image','b_image']}
    _,images=read('outputs/tables/image_file_check.csv')
    check('image_inventory_and_decoding',len(images)==len(image_paths) and {r['image'] for r in images}==image_paths and
          all(r['error']=='' and int(r['width'])>0 and int(r['height'])>0 for r in images),
          f'{len(image_paths)} referenced images verified and fully decoded by preparation script')
    check('image_hashes_current',all(digest(IMAGES/r['image'])==r['sha256'] for r in images),'Inventory fingerprints match current image files')
    train_cats={r[c] for r in raw for c in ['a_cat','b_cat']}
    train_images={r[c] for r in raw for c in ['a_image','b_image']}
    test_cats={r[c] for r in raw_test for c in ['a_cat','b_cat']}
    test_images={r[c] for r in raw_test for c in ['a_image','b_image']}
    content=Counter(tuple(value for key,value in r.items() if key!='train_row_id') for r in raw)
    summary_expected={
        'train_rows':len(raw),'test_rows':len(raw_test),'rows_removed':len(raw)-len(clean),
        'normalized_train_cells':sum(value!=value.strip() for r in raw for value in r.values()),
        'choice_A':sum(r['choice']=='A' for r in raw),'choice_B':sum(r['choice']=='B' for r in raw),
        'between_cats_rows':sum(r['comparison_type']=='between_cats' for r in raw),
        'within_cat_rows':sum(r['comparison_type']=='within_cat' for r in raw),
        'train_cats':len(train_cats),'train_images':len(train_images),
        'unique_train_image_pairs':len(pairs),'repeated_train_image_pairs':sum(len(g)>1 for g in pairs.values()),
        'human_all_missing':sum(all(r[c]=='' for c in HUMAN) for r in raw),
        'extra_content_duplicate_rows':sum(n-1 for n in content.values()),
        'rows_in_content_duplicate_groups':sum(n for n in content.values() if n>1),
        'pairs_with_both_orientations':sum(len({r['a_image'] for r in g})==2 for g in pairs.values()),
        'referenced_images_decoded':len(image_paths),'extra_byte_identical_image_files':len(images)-len({r['sha256'] for r in images}),
        'train_test_image_pair_overlap':len(set(pairs)&set(test_pairs)),
        'test_unseen_cats':len(test_cats-train_cats),'test_unseen_images':len(test_images-train_images),
        'validation_rows':sum(r['split']=='validation' for r in split),'seed':2026,
    }
    summary=json.loads((OUT/'tables/dataset_summary.json').read_text(encoding='utf-8'))
    check('all_dataset_summary_values',summary==summary_expected,'Every dataset_summary.json entry recomputed or checked against the declared seed')
    _,overview=read('outputs/tables/dataset_overview.csv')
    check('overview_matches_summary',{r['metric']:int(r['value']) for r in overview}==summary_expected,'CSV overview and JSON agree')
    metadata=json.loads((OUT/'run_metadata.json').read_text(encoding='utf-8'))
    check('source_hashes_current',all(digest(RAW/name)==value for name,value in metadata['source_sha256'].items()),'Source fingerprints match the preparation run')
    check('script_hash_current',digest(Path(__file__).with_name('prepare.py'))==metadata['script_sha256'],'Outputs were produced by the current preparation script')
    for name in ['01_comparisons_and_choices','02_data_coverage','03_human_information']:
        from PIL import Image
        with Image.open(OUT/'figures'/(name+'.png')) as image:
            image.load()
            check('figure_'+name,image.width>=2500 and image.height>=1000 and (OUT/'figures'/(name+'.pdf')).is_file(),
                  f'{image.width} x {image.height} PNG and PDF available')
    audit_synthetic_cases()
    passed=all(r['passed'] for r in RESULTS)
    result={'passed':passed,'n_checks':len(RESULTS),'n_passed':sum(r['passed'] for r in RESULTS),'checks':RESULTS}
    (OUT/'audit_report.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8', newline='\n')
    table='\n'.join('| '+r['check']+' | '+('PASS' if r['passed'] else 'FAIL')+' | '+r['detail']+' |' for r in RESULTS)
    report=f'''# 成员 1 数据复查记录

自动检查结果：{'通过' if passed else '未通过'}，{result['n_passed']}/{len(RESULTS)} 项通过。

运行 `python scripts/audit_data_preparation.py --rerun` 可重建包括复跑验证在内的完整记录；不加 --rerun 时跳过两项复跑检查。逐行复核使用 Python csv/Counter 独立读取原始文件，不直接复用清洗脚本的选择方向计算。另用构造记录检查 A/B 互换、缺失处理和非法输入拒绝。

这说明输出符合约定的处理规则；不能据此证明原始问卷无测量误差、回答独立、抽样有代表性，或内容重复一定不是重复录入。图片解码通过不代表已人工审核图片内容。

| 检查 | 结果 | 证据 |
|---|---|---|
{table}
'''
    MODULE_DOCS.mkdir(parents=True, exist_ok=True)
    (MODULE_DOCS/'quality_review.md').write_text(report,encoding='utf-8',newline='\n')
    print(f'Audit: {result["n_passed"]}/{len(RESULTS)} passed. See docs/quality_review.md')
    if not passed:
        raise SystemExit(1)


if __name__=='__main__':
    main()
