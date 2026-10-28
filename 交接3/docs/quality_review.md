# 成员 3 质量与复现检查

自动检查总结果：**PASS**。以下为实际执行结果，不代替统计假设审查。

| 检查 | 结果 | 证据 |
|---|---|---|
| statistical_and_source_tests | PASS | 12 tests; 0 failures; 0 errors; 0 skipped |
| input_fingerprints | PASS | Clean data and saved split match run metadata |
| analysis_script_current | PASS | Analysis script matches saved run |
| report_generator_current | PASS | Report generator matches saved run |
| 01_pair_coverage_and_unanimity | PASS | 3450 x 1440 PNG, 300 dpi, PDF companion exists; PNGs visually reviewed |
| 02_agreement_and_pair_uncertainty | PASS | 3450 x 1470 PNG, 300 dpi, PDF companion exists; PNGs visually reviewed |
| 03_image_model_readiness | PASS | 3450 x 1470 PNG, 300 dpi, PDF companion exists; PNGs visually reviewed |
| expected_tables | PASS | Missing: [] |
| fresh_process_completed | PASS | New interpreter and unrelated working directory; completed |
| reproducible_outputs | PASS | 21 tables/simulations/figures/reports/summary files compared byte for byte; differences: [] |
| upstream_unchanged | PASS | All 43 files in member 1 and member 2 handoffs unchanged by audit/rerun |

## 检查覆盖

- 交换A/B图片并同步反转选择后，图片身份统计保持不变。
- 纯粹总选A的合成回答不会被置换检验误报为图片一致性；始终选择同一图片的合成数据能检出信号。
- 检查4次全票的双侧p=0.125和仍覆盖0.5的精确区间；单次回答不能生成一致率试验。
- 检查不连通图片网络与非强连通胜负网络，拒绝无效的成员1方向字段。
- 直接枚举原始获选图片的回答组合，独立核对一致/分歧计数；与成员1图片对汇总交叉验证。
- 检查共同划分覆盖全部行且图片对不跨集合，图像覆盖类别加总等于验证记录数。
- 当前机器上存在课程原始train.csv，额外核对原始字段与成员1主表完全一致；其他机器缺少此原文件时该项明确跳过。
- 独立新进程从不同工作目录重跑时，比较所有分析生成的表、模拟数组、图、摘要与报告。运行metadata含耗时和平台，审计报告含本次检查状态，因此不作逐字节比较。

## 图表核对

已打开并检查三张最终PNG：标签可读，数字和图例完整，没有裁切或文字重叠；沿用成员1蓝色/橙色、英文图中文字、300dpi PNG和矢量PDF格式。PDF来自与PNG相同的Matplotlib画布。图2右侧展示所有4回答计数情形的区间，不是筛选出来的显著图片；图3的未见图片仅以同猫训练子集计算。

## 解释边界

没有参与者ID，因此按猫bootstrap和置换不能处理未知参与者跨猫的相关性。逐对区间依赖独立同分布回答，置换依赖零假设下的可交换性。整体一致性不保证可传递的图片得分、因果图片特征或扩展模型的验证提升。全数据汇总不能作为验证集现成特征。

## 重做检查

在仓库根目录运行：

```powershell
python 交接3/scripts/member3_analysis.py
python 交接3/scripts/member3_audit.py --rerun
```

Python应使用已安装本交接依赖的环境。若失败，收集终端输出、outputs/audit_report.json和run_metadata.json；先核对依赖版本和成员1输入指纹。审计的临时复跑目录由系统清理，不修改上游数据。
