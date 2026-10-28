> 历史交接记录：以下内容产生于目录迁移前。当前路径和验证范围见同目录README_handoff.md及docs/migration.md；历史图片审核不是本次重新运行的结果。

# 成员 1 数据复查记录

自动检查结果：通过，41/41 项通过。

运行 `python scripts/member1_audit.py --rerun` 可重建包括复跑验证在内的完整记录；不加 --rerun 时跳过两项复跑检查。逐行复核使用 Python csv/Counter 独立读取原始文件，不直接复用清洗脚本的选择方向计算。另用构造记录检查 A/B 互换、缺失处理和非法输入拒绝。

这说明输出符合约定的处理规则；不能据此证明原始问卷无测量误差、回答独立、抽样有代表性，或内容重复一定不是重复录入。图片解码通过不代表已人工审核图片内容。

| 检查 | 结果 | 证据 |
|---|---|---|
| reproducible_from_other_working_directory | PASS | 19 data/table/figure files compared; changed: [] |
| source_files_unchanged_by_rerun | PASS | train.csv, test.csv, test_example.csv unchanged |
| train_row_count_and_order | PASS | 24896 source rows; 24896 output rows |
| train_original_cells_preserved | PASS | 0 unexplained differences; 0 whitespace normalizations |
| train_canonical_image_pair | PASS | 0 mismatched rows |
| train_canonical_cat_pair | PASS | 0 mismatched rows |
| train_duplicate_flags | PASS | 0 mismatched rows |
| train_human_missing_flags | PASS | 0 mismatched rows |
| train_individual_missing_flags | PASS | 0 mismatched rows |
| train_outcome_fields | PASS | 0 mismatched rows |
| test_row_count_and_order | PASS | 6224 source rows; 6224 output rows |
| test_original_cells_preserved | PASS | 0 unexplained differences; 0 whitespace normalizations |
| test_canonical_image_pair | PASS | 0 mismatched rows |
| test_canonical_cat_pair | PASS | 0 mismatched rows |
| test_duplicate_flags | PASS | 0 mismatched rows |
| test_human_missing_flags | PASS | 0 mismatched rows |
| test_individual_missing_flags | PASS | 0 mismatched rows |
| test_withheld_test_outcomes | PASS | 0 mismatched rows |
| pair_summary_identity | PASS | 8049 unique source image pairs |
| all_pair_summary_counts_and_proportions | PASS | Recomputed directly from source choices, not derived choice codes |
| category_counts_and_denominators | PASS | Each field sums to all training responses; missing included |
| missingness_table | PASS | Original training fields checked |
| choice_by_type_table | PASS | A/B numerators and comparison-type denominators verified |
| cat_coverage_counts | PASS | Between-cat: two cats per record; within-cat: one record per cat |
| pair_response_distribution | PASS | Distribution matches source pair groups |
| split_record_coverage | PASS | Every source training row appears exactly once |
| split_pair_separation | PASS | No unordered image pair crosses the saved split |
| image_inventory_and_decoding | PASS | 1558 referenced images verified and fully decoded by preparation script |
| image_hashes_current | PASS | Inventory fingerprints match current image files |
| all_dataset_summary_values | PASS | Every dataset_summary.json entry recomputed or checked against the declared seed |
| overview_matches_summary | PASS | CSV overview and JSON agree |
| source_hashes_current | PASS | Source fingerprints match the preparation run |
| script_hash_current | PASS | Outputs were produced by the current preparation script |
| figure_01_comparisons_and_choices | PASS | 3000 x 1200 PNG and PDF available |
| figure_02_data_coverage | PASS | 3000 x 1200 PNG and PDF available |
| figure_03_human_information | PASS | 3000 x 1200 PNG and PDF available |
| four_order_choice_combinations | PASS | A/B choices tested with both image orientations |
| blank_unknown_and_partial_missing | PASS | Blank normalized; unknown preserved; partial missingness handled |
| reject_invalid_choice | PASS | Must stop rather than silently alter/drop the record |
| reject_invalid_category | PASS | Must stop rather than silently alter/drop the record |
| reject_inconsistent_type | PASS | Must stop rather than silently alter/drop the record |
