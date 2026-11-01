"""Verify an untouched submission archive and reproduce its analyses in this Python environment."""
import argparse
import hashlib
from importlib.metadata import version
import json
import math
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compare(actual, expected, location='', differences=None):
    differences = [] if differences is None else differences
    if isinstance(expected, dict):
        if not isinstance(actual, dict) or actual.keys() != expected.keys():
            differences.append(location+': different keys')
        else:
            for key in expected:
                compare(actual[key], expected[key], f'{location}/{key}', differences)
    elif isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            differences.append(location+': different list length/type')
        else:
            for i, item in enumerate(expected):
                compare(actual[i], item, f'{location}/{i}', differences)
    elif isinstance(expected, bool) or expected is None or isinstance(expected, str):
        if actual != expected:
            differences.append(location+': different value')
    elif isinstance(expected, int):
        if actual != expected:
            differences.append(location+': different integer count')
    elif not isinstance(actual, (int, float)) or not math.isclose(actual, expected, rel_tol=0, abs_tol=1e-5):
        differences.append(location+': numerical difference > 1e-5')
    return differences


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    started = time.perf_counter()
    manifest_file = ROOT/'SUBMISSION_MANIFEST.json'
    if not manifest_file.is_file():
        raise SystemExit('This validator is for an extracted submission ZIP. In a Git checkout use scripts/check_project.py --rerun.')
    manifest = json.loads(manifest_file.read_text(encoding='utf-8'))
    bad = [name for name, info in manifest['files'].items()
           if not (ROOT/name).is_file() or digest(ROOT/name) != info['sha256']]
    if bad:
        raise SystemExit('Manifest mismatch; use a newly extracted copy: '+', '.join(bad))
    if sys.version_info[:2] != (3, 12):
        raise SystemExit('Use Python 3.12 as documented in README.md.')
    installed = {}
    for line in (ROOT/'requirements.lock.txt').read_text(encoding='utf-8').splitlines():
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        package, required = line.strip().split('==')
        installed[package] = version(package)
        if installed[package] != required:
            raise SystemExit(f'Version mismatch for {package}: need {required}, found {installed[package]}')
    modules = ('cat_ranking', 'image_analysis', 'human_preferences', 'model_comparison')
    reference = {name: json.loads((ROOT/'outputs'/name/'summary.json').read_text(encoding='utf-8'))
                 for name in modules}
    output = ROOT/'outputs/project_checks'
    output.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, str(ROOT/'scripts/check_project.py'), '--rerun']
    print('Manifest and locked environment verified. Rerunning analyses and checks...', flush=True)
    print('Progress log: '+str(output/'submission_validation.log'), flush=True)
    # A separate working directory verifies that entry points use project-relative paths.
    with (output/'submission_validation.log').open('w', encoding='utf-8', newline='\n') as log:
        result = subprocess.run(command, cwd=ROOT.parent, stdout=log, stderr=subprocess.STDOUT,
                                env={**os.environ, 'PYTHONIOENCODING': 'utf-8', 'MPLBACKEND': 'Agg'})
    comparisons = {}
    for name in modules:
        actual = json.loads((ROOT/'outputs'/name/'summary.json').read_text(encoding='utf-8'))
        differences = (compare(actual, reference[name]) if result.returncode == 0
                       else ['Pipeline failed; reproduction is not confirmed. See the log.'])
        comparisons[name] = dict(passed=not differences, differences=differences)
    fingerprints = {name: info['sha256'] for name, info in manifest['files'].items()
                    if name.startswith(('src/', 'scripts/', 'tests/', 'configs/', 'data/'))
                    or name in ('requirements.txt', 'requirements.lock.txt', 'pyproject.toml')}
    report = dict(passed=result.returncode == 0 and all(c['passed'] for c in comparisons.values()),
                  source_commit=manifest['source_commit'],
                  archive_manifest_verified=True, fresh_virtual_environment=(sys.prefix != sys.base_prefix),
                  summary_numeric_absolute_tolerance=1e-5,
                  command=['python', 'scripts/check_project.py', '--rerun'],
                  executed_from_project_parent=True, pipeline_exit_code=result.returncode,
                  summaries=comparisons, python=platform.python_version(), platform=platform.platform(),
                  processor=platform.processor(), logical_cpu_count=os.cpu_count(), versions=installed,
                  runtime_seconds=round(time.perf_counter()-started, 3),
                  full_source_image_audit_rerun=False,
                  reproduction_inputs_sha256=fingerprints)
    (output/'submission_validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n',
                                                    encoding='utf-8', newline='\n')
    print(json.dumps({key: value for key, value in report.items() if key != 'reproduction_inputs_sha256'},
                     ensure_ascii=False, indent=2))
    if not report['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
