"""Run team tests and verify preserved data plus migrated analysis results."""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import _bootstrap
import numpy as np
import pandas as pd

ROOT = _bootstrap.ROOT


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rerun', action='store_true', help='Regenerate delivered analyses before checking')
    args = parser.parse_args()
    if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
    if args.rerun:
        subprocess.run([sys.executable, str(ROOT/'scripts/run_all.py')], check=True)
    completed = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', str(ROOT/'tests'), '-v'])
    checks = [dict(check='team_unit_and_source_tests', passed=completed.returncode == 0)]
    baseline = json.loads((ROOT/'docs/provenance/migration_baseline.json').read_text(encoding='utf-8'))
    mapping = json.loads((ROOT/'docs/migration_map.json').read_text(encoding='utf-8'))
    data_names = [name for name in mapping if name.startswith('交接1/data/processed/')]
    data_changed = [mapping[name] for name in data_names
                    if digest(ROOT/mapping[name]) != baseline['hashes'][name]]
    checks.append(dict(check='shared_data_and_split_preserved', passed=not data_changed,
                       files_checked=len(data_names), differences=data_changed))
    # Original descriptive member-1 outputs have been moved, not recomputed without images.
    retained = [name for name in mapping if name.startswith(('交接1/outputs/tables/', '交接1/outputs/figures/'))]
    changed = [mapping[name] for name in retained if digest(ROOT/mapping[name]) != baseline['hashes'][name]]
    checks.append(dict(check='data_description_outputs_preserved', passed=not changed,
                       files_checked=len(retained), differences=changed))
    old = pd.read_csv(ROOT/'docs/provenance/cat_ranking/baseline_ranking.csv').sort_values('cat_id').reset_index(drop=True)
    new = pd.read_csv(ROOT/'outputs/cat_ranking/tables/cat_ranking_comparison.csv').sort_values('cat_id').reset_index(drop=True)
    same_cats = old.cat_id.equals(new.cat_id)
    exact_cols = ['comparisons', 'wins', 'losses', 'win_rate_rank', 'bt_rank', 'rank_change']
    exact = same_cats and old[exact_cols].equals(new[exact_cols])
    max_diff = float(np.max(np.abs(old.bt_score.to_numpy()-new.bt_score.to_numpy()))) if same_cats else float('inf')
    checks.append(dict(check='cat_ranking_unchanged', passed=exact and max_diff < 1e-8,
                       max_abs_score_difference=max_diff, same_cats_and_ranks=exact))
    actual = json.loads((ROOT/'outputs/image_analysis/summary.json').read_text(encoding='utf-8'))
    checks.append(dict(check='image_analysis_numbers_unchanged', passed=actual == baseline['member3_summary']))
    meta = json.loads((ROOT/'outputs/image_analysis/run_metadata.json').read_text(encoding='utf-8'))
    current = (meta['script_sha256'] == digest(ROOT/'src/cat_arena/image_analysis/analysis.py')
               and meta['report_script_sha256'] == digest(ROOT/'src/cat_arena/image_analysis/report.py')
               and meta['data_contract_sha256'] == digest(ROOT/'src/cat_arena/common/data.py')
               and meta['config_sha256'] == digest(ROOT/'configs/default.json'))
    checks.append(dict(check='image_analysis_implementation_current', passed=current))
    sources = (meta['source_sha256'] == {
        'input': digest(ROOT/'data/processed/train_clean.csv'),
        'split': digest(ROOT/'data/splits/validation_split.csv')})
    checks.append(dict(check='image_analysis_sources_current', passed=sources))
    cat_meta = json.loads((ROOT/'outputs/cat_ranking/run_metadata.json').read_text(encoding='utf-8'))
    cat_current = (cat_meta['analysis_sha256'] == digest(ROOT/'src/cat_arena/cat_ranking/analysis.py')
                   and cat_meta['model_sha256'] == digest(ROOT/'src/cat_arena/cat_ranking/model.py')
                   and cat_meta['config_sha256'] == digest(ROOT/'configs/default.json')
                   and cat_meta['source_sha256'] == digest(ROOT/'data/processed/train_clean.csv'))
    checks.append(dict(check='cat_ranking_implementation_and_sources_current', passed=cat_current))
    model_meta = json.loads((ROOT/'outputs/model_comparison/run_metadata.json').read_text(encoding='utf-8'))
    model_current = (model_meta['analysis_sha256'] == digest(ROOT/'src/cat_arena/model_comparison/analysis.py')
                     and model_meta['design_sha256'] == digest(ROOT/'src/cat_arena/model_comparison/design.py')
                     and model_meta['config_sha256'] == digest(ROOT/'configs/default.json'))
    checks.append(dict(check='model_comparison_implementation_current', passed=model_current))
    model_sources = (model_meta['source_sha256'] == digest(ROOT/'data/processed/train_clean.csv')
                     and model_meta['split_sha256'] == digest(ROOT/'data/splits/validation_split.csv'))
    checks.append(dict(check='model_comparison_sources_current', passed=model_sources))
    checks.append(dict(check='model_comparison_validation_not_used_for_fitting',
                       passed=model_meta.get('validation_data_used_for_fitting') is False))
    report = dict(passed=all(c['passed'] for c in checks), baseline_commit=baseline['commit'],
                  checks=checks, full_source_image_audit_rerun=False,
                  limitation='This check does not execute the full raw-image audit. Run source preparation/audit separately when course images are available.')
    destination = ROOT/'outputs/project_checks/migration_report.json'
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report['passed']: raise SystemExit(1)


if __name__ == '__main__':
    main()
