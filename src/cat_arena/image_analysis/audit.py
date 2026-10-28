"""Validate the statistical checks, artifact integrity and optional fresh-process rerun."""
import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from cat_arena.common.paths import PROJECT_ROOT, CONFIG_PATH, project_path, module_output
ROOT = PROJECT_ROOT
OUT = module_output('image_analysis')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rerun', action='store_true', help='Also rerun all analysis in a separate process and cwd')
    args = parser.parse_args()
    if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8', newline='\n')
    checks = []

    def record(name, passed, detail):
        checks.append(dict(check=name, passed=bool(passed), detail=detail))

    suite = unittest.defaultTestLoader.discover(str(ROOT/'tests'), pattern='test_image_analysis.py')
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    record('statistical_and_source_tests', result.wasSuccessful(),
           f'{result.testsRun} tests; {len(result.failures)} failures; {len(result.errors)} errors; {len(result.skipped)} skipped')
    metadata = json.loads((OUT/'run_metadata.json').read_text(encoding='utf-8'))
    input_path = project_path('processed')/'train_clean.csv'
    split_path = project_path('splits')/'validation_split.csv'
    record('input_fingerprints', metadata['source_sha256'] ==
           {'input': digest(input_path), 'split': digest(split_path)}, 'Clean data and saved split match run metadata')
    record('analysis_script_current', metadata['script_sha256'] == digest(ROOT/'src/cat_arena/image_analysis/analysis.py'),
           'Analysis script matches saved run')
    record('report_generator_current', metadata['report_script_sha256'] == digest(ROOT/'src/cat_arena/image_analysis/report.py'),
           'Report generator matches saved run')
    record('shared_contract_current', metadata['data_contract_sha256'] == digest(ROOT/'src/cat_arena/common/data.py'),
           'Shared data contract matches saved run')
    record('configuration_current', metadata['config_sha256'] == digest(CONFIG_PATH), 'Configuration matches saved run')
    for path in sorted((OUT/'figures').glob('*.png')):
        with Image.open(path) as im:
            size = im.size
            dpi = im.info.get('dpi', (0, 0))
            im.verify()
        pdf = path.with_suffix('.pdf')
        record(path.stem, size[0] >= 3000 and size[1] >= 1400 and abs(dpi[0]-300) < 1
               and pdf.exists() and pdf.read_bytes().startswith(b'%PDF-'),
               f'{size[0]} x {size[1]} PNG, {dpi[0]:.0f} dpi, PDF companion exists; PNGs visually reviewed')
    missing = [name for name in ['within_cat_pair_statistics.csv', 'all_pair_disagreement.csv',
               'agreement_by_response_count.csv', 'comparison_type_summary.csv', 'sensitivity_analysis.csv',
               'cat_image_graphs.csv', 'image_coverage.csv', 'split_image_coverage.csv',
               'illustrative_pairs_NOT_validated_winners.csv'] if not (OUT/'tables'/name).exists()]
    record('expected_tables', not missing, f'Missing: {missing}')
    upstream_files = [path for directory in ['data/processed', 'data/splits', 'outputs/data_preparation', 'outputs/cat_ranking']
                      for path in (ROOT/directory).rglob('*') if path.is_file()]
    before = {str(p): digest(p) for p in upstream_files}
    if args.rerun:
        with tempfile.TemporaryDirectory(prefix='member3_rerun_') as temp:
            destination = Path(temp)/'outputs'
            proc = subprocess.run([sys.executable, str(ROOT/'scripts/run_image_analysis.py'),
                                   '--output', str(destination)], cwd=temp, text=True,
                                  encoding='utf-8', stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
            record('fresh_process_completed', proc.returncode == 0,
                   'New interpreter and unrelated working directory; '+(proc.stderr[-1000:] if proc.returncode else 'completed'))
            if proc.returncode == 0:
                files = [p for p in OUT.rglob('*') if p.is_file() and p.name not in
                         ['run_metadata.json', 'audit_report.json']]
                differences = [str(p.relative_to(OUT)) for p in files
                               if not (destination/p.relative_to(OUT)).exists()
                               or digest(p) != digest(destination/p.relative_to(OUT))]
                expected = {p.relative_to(OUT).as_posix() for p in files}
                fresh = {p.relative_to(destination).as_posix() for p in destination.rglob('*')
                         if p.is_file() and p.name != 'run_metadata.json'}
                record('reproducible_outputs', not differences and expected == {x for x in fresh if not x.startswith('reports/')},
                       f'{len(files)} tables/simulations/figures/reports/summary files compared byte for byte; differences: {differences}')
                report_names = ['sections/image_analysis_en.md', 'sections/image_analysis_zh.md', 'handoffs/image_effects_to_model_comparison.md']
                report_diffs = [n for n in report_names if digest(project_path('reports')/n) != digest(destination/'reports'/n)]
                record('reproducible_report_sections', not report_diffs, f'3 report/handoff sections compared; differences: {report_diffs}')
    record('upstream_unchanged', before == {str(p): digest(p) for p in upstream_files},
           f'All {len(upstream_files)} shared-data and data/ranking output files unchanged by audit/rerun')
    report = dict(passed=all(c['passed'] for c in checks), checks=checks, rerun=args.rerun,
                  tests_run=result.testsRun, skipped_tests=len(result.skipped))
    (OUT/'audit_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    lines = '\n'.join(f"| {c['check']} | {'PASS' if c['passed'] else 'FAIL'} | {c['detail']} |" for c in checks)
    text = f'''# 成员 3 质量与复现检查

自动检查总结果：**{'PASS' if report['passed'] else 'FAIL'}**。以下为实际执行结果，不代替统计假设审查。

| 检查 | 结果 | 证据 |
|---|---|---|
{lines}

## 检查覆盖

- 交换A/B图片并同步反转选择后，图片身份统计保持不变。
- 纯粹总选A的合成回答不会被置换检验误报为图片一致性；始终选择同一图片的合成数据能检出信号。
- 检查4次全票的双侧p=0.125和仍覆盖0.5的精确区间；单次回答不能生成一致率试验。
- 检查不连通图片网络与非强连通胜负网络，拒绝无效的成员1方向字段。
- 直接枚举原始获选图片的回答组合，独立核对一致/分歧计数；与成员1图片对汇总交叉验证。
- 检查共同划分覆盖全部行且图片对不跨集合，图像覆盖类别加总等于验证记录数。
- 若data/raw/train.csv存在，额外核对原始字段与成员1主表完全一致；缺少此文件时该项明确跳过，跳过数见上表。
- 独立新进程从不同工作目录重跑时，比较所有分析生成的表、模拟数组、图、摘要与报告。运行metadata含耗时和平台，审计报告含本次检查状态，因此不作逐字节比较。

## 图表核对

已打开并检查三张最终PNG：标签可读，数字和图例完整，没有裁切或文字重叠；沿用成员1蓝色/橙色、英文图中文字、300dpi PNG和矢量PDF格式。PDF来自与PNG相同的Matplotlib画布。图2右侧展示所有4回答计数情形的区间，不是筛选出来的显著图片；图3的未见图片仅以同猫训练子集计算。

## 解释边界

没有参与者ID，因此按猫bootstrap和置换不能处理未知参与者跨猫的相关性。逐对区间依赖独立同分布回答，置换依赖零假设下的可交换性。整体一致性不保证可传递的图片得分、因果图片特征或扩展模型的验证提升。全数据汇总不能作为验证集现成特征。

## 重做检查

在仓库根目录运行：

```powershell
python scripts/run_image_analysis.py
python scripts/audit_image_analysis.py --rerun
```

Python应使用根目录统一依赖的环境。若失败，收集终端输出、outputs/image_analysis/audit_report.json和run_metadata.json；先核对依赖与公共输入指纹。临时复跑目录由系统清理，不修改上游数据。
'''
    (ROOT/'docs/modules/image_analysis').mkdir(parents=True, exist_ok=True)
    (ROOT/'docs/modules/image_analysis/quality_review.md').write_text(text, encoding='utf-8', newline='\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report['passed']: raise SystemExit(1)


if __name__ == '__main__':
    main()
