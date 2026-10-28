# 成员 3 交接包：图片差异与群体偏好分歧

本部分承接成员1的统一数据，仅以 `within_cat` 为主要研究对象。直接查看已有结果无需重跑、下载图片或重新执行清洗。`交接1` 与 `交接3` 应保留在同一仓库根目录。

## 先看什么

1. [中文方法、结果与建议的三页PPT内容](outputs/reports/方法与结果_中文版.md)。
2. [可并入报告的英文 Image-Level Analysis](outputs/reports/Image_Level_Analysis_EN.md)。
3. [给成员5的图片效应交接](outputs/reports/Member5_图片效应交接.md)。
4. [质量与复现检查](docs/quality_review.md)。

主要发现：3003条同猫回答、1132个图片对；1016个重复图片对中64.57%有分歧。回答组合一致率53.05%，保留A总数置换参照约50%，单侧p=0.0008。每对仅1-4条回答，没有单对达到双侧p<0.05。该结果支持谨慎试验收缩图片效应，不能当作模型已经改善或图片存在确定赢家的证据。没有参与者ID，推断依赖可交换性/独立性假设。

## 文件用途

| 文件 | 用途 |
|---|---|
| `scripts/member3_analysis.py` | 检查输入、统一方向、逐对统计、置换、按猫bootstrap、敏感性检查、网络/划分诊断、作图的主入口 |
| `scripts/member3_report.py` | 将本次运行数字写入中英文报告和成员5交接文字，由主入口自动调用 |
| `scripts/member3_audit.py` | 执行统计/源数据检查，核对文件指纹、图表和独立新进程复现，生成质量说明 |
| `tests/test_member3.py` | A/B互换、位置偏差、单对分辨率、图结构、源数据组合计数、成员1汇总和划分完整性检查 |
| `outputs/summary.json` | 核心统计、检验、网络和敏感性结果 |
| `outputs/tables/within_cat_pair_statistics.csv` | 全部1132对同猫图片的逐对计数、选择率、精确区间、BH/BY p值 |
| `outputs/tables/all_pair_disagreement.csv` | 两种比较类型的描述性逐对指标；不同猫数据仅作分歧背景对照 |
| `outputs/tables/agreement_by_response_count.csv` | 按比较类型及每对回答数分层的全票/分歧比例 |
| `outputs/tables/comparison_type_summary.csv` | 两种比较类型的描述性概况；不对差值做因果解释 |
| `outputs/tables/sensitivity_analysis.csv` | 保留全部、删除额外相同内容、完整人群记录、双朝向图片对子集的对照 |
| `outputs/tables/cat_image_graphs.csv` | 每只猫的同猫图片网络连通性和有向胜负强连通性 |
| `outputs/tables/image_coverage.csv` | 每张图片的回答曝光数、不同对手数、连通分量 |
| `outputs/tables/split_image_coverage.csv` | 共同图片对划分中，按实际训练范围计算图片覆盖 |
| `outputs/tables/illustrative_pairs_NOT_validated_winners.csv` | 按回答数、观察多数比例、图片对ID排序的12个示例，**不是可靠赢家或显著优胜列表** |
| `outputs/data/*_permutation_null.csv` | 两种置换检验的完整模拟一致率，可复核尾概率 |
| `outputs/run_metadata.json` | 输入/脚本SHA-256、种子、环境版本、平台和运行时间 |
| `outputs/reports/` | 自动生成的报告与成员5交接 |
| `requirements.txt` / `environment_lock.txt` | 核心依赖锁定 / 已验证环境完整包版本 |

三张图均在 `outputs/figures/`，同时提供300dpi PNG和矢量PDF：

1. `01_pair_coverage_and_unanimity`：每对回答数及全票率的有限样本参照。
2. `02_agreement_and_pair_uncertainty`：整体置换检验与单对精确区间示意。
3. `03_image_model_readiness`：同猫图片网络与同猫训练范围下的验证图片覆盖。

## 安装和复现

已验证 Python **3.12.14**，Windows x86-64 CPU，单进程，无GPU。使用标准虚拟环境；macOS/Linux将`.venv/Scripts/python`替换为`.venv/bin/python`。如果已有兼容环境，可省略建环境步骤。

在**仓库根目录**执行：

```powershell
python -m venv .venv
.venv/Scripts/python -m pip install -r 交接3/requirements.txt
.venv/Scripts/python 交接3/scripts/member3_analysis.py
.venv/Scripts/python 交接3/scripts/member3_audit.py --rerun
```

若需要尽量匹配全部传递依赖，将安装文件换成`交接3/environment_lock.txt`。不需要 Jupyter；不读取测试集标签，不需要训练图像或外部模型下载。首次安装需要互联网，分析本身离线执行。

默认输入是脚本位置相对解析的：

```text
仓库根目录/
  交接1/data/processed/train_clean.csv
  交接1/data/processed/validation_split.csv
  交接1/data/processed/image_pair_summary.csv   # 测试中交叉核对
  交接3/
    scripts/
    tests/
    outputs/
    requirements.txt
```

主脚本可从任意工作目录运行；如移动数据，可使用`--input`与`--split`指定路径，用`--output`指定输出。重跑会覆盖所指定输出目录中同名文件，不修改成员1/2的文件。默认19999次全局置换、9999次按猫分层置换、10000次按猫bootstrap；随机种子分别2026、2027、2026。具体耗时见metadata，当前CPU为十秒量级，首次字体缓存可能更慢。

同一版本环境和默认参数下，数据表、模拟数组、报告文字应完全一致；跨依赖版本的尾部分位数/字体和渲染可能有微小变化。Monte Carlo不确定性已在报告中列明；更换种子得到不同p值不意味着可挑选最小值。完整新进程复跑及图表视觉核对见质量说明。

本目录的`.gitattributes`保留文件原始字节，避免Git自动转换行尾影响脚本指纹或逐字节复现检查。

## 指标解释与禁止误用

- 无序图片对由排序后图片路径定义，`choice_canonical_1=1`表示选规范第一图，不等于选A。
- 单次回答无可比的回答组合，其`dyad_agreement`为空；不能当作100%真实一致性。
- `response_dyads`是同一图片对的不同回答记录组合数；同一回答可以出现在多个组合中，不是独立观测数。
- `ci95_low/high`是规范第一图概率的逐对95%精确二项区间，依赖独立同分布假设，不是多数图概率的区间，也不是同时覆盖区间。
- `p_exact_two_sided`检验规范第一图选择概率=0.5；`p_bh`与`p_by`分别是对全部同猫图片对调整后的p值。未显著不表示等效。
- `observed_entropy_bits`是未经小样本修正的二元选择熵，仅用于描述。`majority_share`同样不能证明共识。
- `cat_id_1/2`来自规范图片路径，同猫对相同。`n_canonical_1_on_A`用于核查展示方向。
- 图结构按全部同猫记录计算。`finite_unpenalized_bt`只说明相应网络满足普通图片BT有限估计的强连通条件，未拟合任何图片模型；不能把它当模型收敛或验证性能。
- 主表和人群缺失/重复记录沿用成员1规则；敏感性分析不改写主数据。具体字段见成员1数据字典。
- 全数据统计含选择结果，只作报告和建模诊断，不能作为验证/测试预测输入。成员5必须在每个拟合子集重新学习相关量。
- “群体分歧”在此指不同回答记录间的选择差异；特定养宠群体的差异由成员4负责。本部分不能估计个人可靠性或确认不同记录来自不同人。

数据与衍生材料仅用于教育和研究。姓名/组号由小组在最终贡献页补充。
