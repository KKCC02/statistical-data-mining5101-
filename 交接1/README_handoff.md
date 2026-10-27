# 成员 1 交接包：文件用途与使用方法

成员 1：梁桂荣。直接交付整个 `交接1` 文件夹，保持内部文件夹结构，先阅读本文件，再看字段说明和清洗规则。

## 先用哪些文件

1. 后续逐行分析统一读取 `data/processed/train_clean.csv`，不需要先运行清洗代码。
2. 先看 `docs/data_dictionary.md` 确认字段含义，再看 `docs/cleaning_rules.md` 了解缺失与重复处理。
3. 基础表格、图和报告文字已提供，可用于全组报告的数据部分。
4. 如果需要重新生成结果，把课程原始 `train.csv`、`test.csv`、`test_example.csv` 和 `images/` 放到 `交接1` 根目录，按本文的运行步骤执行。

## 数据文件

| 文件 | 是什么、用于什么 |
|---|---|
| `data/processed/train_clean.csv` | 统一训练主表，24,896 条记录，保留全部原字段、记录和行顺序，增加选择编码、无序图片对 ID、胜负字段、缺失和重复标记。供各成员继续分析。 |
| `data/processed/test_features_clean.csv` | 6,224 条测试记录及辅助字段；选择结果和依赖结果的字段保持为空。不是带真实标签的验证数据。 |
| `data/processed/image_pair_summary.csv` | 每个无序图片对一行，包含回答数、两张图各自获选次数和比例。用于查看图片对回答构成；不能替代逐行主表做人群分析。 |
| `data/processed/validation_split.csv` | 在原训练集内部按图片对分组的可选划分。用 train_row_id 与主表连接；不改变主表，也不强制组员使用。 |

## 文档

| 文件 | 是什么、用于什么 |
|---|---|
| `README_handoff.md` | 本文件：完整交接清单与快速使用说明。 |
| `README_analysis.md` | 准备和复核脚本的运行顺序、环境、输出位置和可复现性说明。 |
| `README.md` | 课程提供的原始数据集说明，保留作为来源说明。 |
| `docs/data_dictionary.md` | 原始和新增字段的含义、编码、缺失表示及辅助表的列说明。 |
| `docs/cleaning_rules.md` | 实际采用的清洗规则、保留缺失/重复的依据、图表规范和已有划分说明。 |
| `docs/member1_report_notes.md` | Data Description、Data Quality、局限性、三张图的图注及梁桂荣的贡献说明，可并入小组报告；组号待小组补充。 |
| `docs/quality_review.md` | 自动质量复核的逐项结果，包括原值保留、字段正确性、统计一致性和复跑检查。 |
| `docs/review_notes.md` | 本次复查改进、图表审阅说明与成员 1 交付清单。 |

## 代码和环境

| 文件 | 是什么、用于什么 |
|---|---|
| `scripts/member1_prepare.py` | 从原始数据进行检查、添加字段、生成清洗数据、统计表、三张图和已有验证划分。 |
| `scripts/member1_audit.py` | 独立读取源 CSV，核对清洗结果、汇总统计和标记；可额外复跑检查输出一致性。 |
| `requirements.txt` | 本次已验证的 pandas、NumPy、Matplotlib、Pillow 版本。Python 使用 3.11.8。 |

## 描述统计与检查表

| 文件（位于 outputs/tables/） | 是什么、用于什么 |
|---|---|
| `dataset_overview.csv` | 数据整体规模、比较类型、选择数量、清洗变动和覆盖情况，便于直接查看。 |
| `dataset_summary.json` | 与概况 CSV 对应的机器可读版本。 |
| `quality_check_summary.csv` | 逐项输入检查、计数和处理方式；缺失/重复非零不一定是错误。 |
| `missingness.csv` | 原训练集各字段的缺失数量与比例。 |
| `category_distribution.csv` | 选择、比较类型和六个人群字段的类别数量/比例，分母为全部训练记录并包含缺失类别。 |
| `choice_by_comparison_type.csv` | 两种比较类型内部的 A/B 数量和 A 选择比例。 |
| `cat_coverage.csv` | 每只猫的不同猫比较出场次数和同猫比较记录数，不是偏好排名。 |
| `pair_response_distribution.csv` | 两类比较中，每对有多少条回答、对应多少个图片对。 |
| `image_file_check.csv` | 全部引用图片的路径、大小、SHA-256、尺寸、格式和解码结果。 |

## 三张基础图

每张图均有 300 dpi PNG 和矢量 PDF，两种格式内容相同，按需要选用。

| 文件名（位于 outputs/figures/） | 内容 |
|---|---|
| `01_comparisons_and_choices.png` / `.pdf` | 两类比较的数量占比，以及各类型内 A/B 选择比例。 |
| `02_data_coverage.png` / `.pdf` | 不同猫比较中的猫咪出场次数分布，以及每个图片对的回答数分布。 |
| `03_human_information.png` / `.pdf` | pet_history 类别分布，以及六个人群字段的缺失率。 |

## 运行与审计记录

| 文件 | 内容 |
|---|---|
| `outputs/run_metadata.json` | 准备运行时的依赖版本、平台、处理器、耗时、随机种子、输入和脚本指纹。 |
| `outputs/audit_report.json` | 机器可读的质量审计结果，与 quality_review.md 对应。 |

## 使用时必须理解的口径

- 没有参与者 ID，记录数不等于独立人数。
- 训练数据未删行、未填补人群属性、未删除内容重复，也未改写有效原值；主要是质量核验与添加辅助字段。
- 508 条人群信息缺失记录保留；MBTI 的 unknown 是有效类别，与缺失分开。
- 46 个内容重复组共 92 条标记记录，相当于 46 条额外重复。不能据此确认重复录入。
- 同一图片对的多条回答全部保留，A/B 方向通过统一图片对和选择编码处理。
- 猫咪偏好排名使用 between_cats；within_cat 的胜负猫咪相同，不应计入猫咪胜率。
- choice_a、choice_canonical_1、winner_*、loser_*、训练集 content_duplicate_flag 依赖选择结果，不能作为预测输入。全数据图片对汇总也含结果信息。
- 每个图片对仅有 1–4 条回答，表面全票不能直接解释为可靠总体共识。

## 需要复现时

交接包不重复收录原始 CSV、图片或课程 PDF，组员使用课程已有数据。根目录应为：

```text
交接1/
  train.csv                 # 放入课程原始文件
  test.csv                  # 放入课程原始文件
  test_example.csv          # 完整复跑审计时需要
  images/                   # 放入课程图片，保留猫咪子目录
  scripts/
  data/processed/
  outputs/
  docs/
  requirements.txt
  README_handoff.md
  README_analysis.md
  README.md
```

```powershell
python -m pip install -r requirements.txt
python scripts/member1_prepare.py
python scripts/member1_audit.py --rerun
```

最后一条会额外再运行一次准备脚本，并比较生成文件；若只需普通审计，可去掉 --rerun。只查看或使用已生成的数据不需要运行这些命令。重新运行会覆盖生成文件，不改写原始 CSV 和图片。

本交付完成成员 1 的数据准备与总体探索；小组其他研究问题的模型、统计检验和结论由后续分析产生。数据及衍生材料仅用于教育与研究。
