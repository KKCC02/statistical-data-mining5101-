"""Run delivered analyses; optionally rebuild inputs when course images are available."""
import argparse
import subprocess
import sys
import _bootstrap


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare-data', action='store_true', help='First rebuild and audit data; requires course images')
    args = parser.parse_args()
    scripts = ['run_cat_ranking.py', 'run_image_analysis.py', 'run_human_preferences.py']
    if args.prepare_data: scripts = ['run_data_preparation.py', 'audit_data_preparation.py', *scripts]
    for name in scripts:
        print(f'Running {name}', flush=True)
        subprocess.run([sys.executable, str(_bootstrap.ROOT/'scripts'/name)], check=True)


if __name__ == '__main__':
    main()
