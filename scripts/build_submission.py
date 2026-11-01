"""Build a standalone Group_17_Code.zip from tracked files and course CSVs.

Builder only: requires Git. Running the delivered analyses does not require Git.
Untracked files are excluded except the three explicitly named source CSVs.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
RAW_FILES = ('train.csv', 'test.csv', 'test_example.csv')
EXCLUDED = {'.gitattributes', '.gitignore', 'AGENTS.md',
            'outputs/project_checks/clean_checkout_report.json'}


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def is_reproduction_input(name):
    return (name.startswith(('src/', 'scripts/', 'tests/', 'configs/', 'data/'))
            or name in ('requirements.txt', 'requirements.lock.txt', 'pyproject.toml'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--validation-report', type=Path,
                        help='Include evidence from validate_submission.py in an extracted candidate')
    args = parser.parse_args()
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    names = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode('utf-8').split('\0')
    files = {}
    for name in filter(None, names):
        if name in EXCLUDED:
            continue
        if any(part in ('.git', '__pycache__', '.venv', 'node_modules') for part in Path(name).parts):
            raise ValueError(f'Unexpected development file tracked: {name}')
        destination = 'README_TEAM.md' if name == 'README.md' else name
        files[destination] = (ROOT/name).read_bytes()
    files['README.md'] = (ROOT/'README_SUBMISSION.md').read_bytes()
    for name in RAW_FILES:
        files['data/raw/'+name] = (ROOT/'data/raw'/name).read_bytes()
    fingerprints = {name: sha256(content) for name, content in sorted(files.items())}
    if args.validation_report:
        report = json.loads(args.validation_report.read_text(encoding='utf-8'))
        expected = {name: value for name, value in fingerprints.items() if is_reproduction_input(name)}
        if not report.get('passed') or report.get('reproduction_inputs_sha256') != expected:
            raise ValueError('Validation evidence failed or does not match current code/config/data/environment files')
        files['SUBMISSION_VALIDATION.json'] = args.validation_report.read_bytes()
        files['SUBMISSION_VALIDATION.log'] = args.validation_report.with_suffix('.log').read_bytes()
    manifest = dict(group=17, source_repository='https://github.com/KKCC02/statistical-data-mining5101-',
                    source_commit=revision,
                    working_tree_status=subprocess.check_output(
                        ['git', 'status', '--porcelain'], cwd=ROOT, text=True).splitlines(),
                    source_images_included=False,
                    full_source_image_audit_rerun=False,
                    files={name: dict(bytes=len(content), sha256=sha256(content))
                           for name, content in sorted(files.items())})
    files['SUBMISSION_MANIFEST.json'] = (json.dumps(manifest, ensure_ascii=False, indent=2)+'\n').encode('utf-8')
    destination = args.output.resolve()
    if destination.suffix.lower() != '.zip':
        raise ValueError('--output must name a ZIP file')
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Mode x prevents accidental replacement of an existing deliverable.
    with zipfile.ZipFile(destination, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, content in sorted(files.items()):
            info = zipfile.ZipInfo('Group_17_Code/'+name, date_time=(2026, 11, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, content, compresslevel=9)
    print(json.dumps(dict(zip=str(destination), files=len(files), bytes=destination.stat().st_size,
                          sha256=sha256(destination.read_bytes()), source_commit=revision), indent=2))


if __name__ == '__main__':
    main()
