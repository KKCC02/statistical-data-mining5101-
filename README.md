# Cat Image Arena · DSAI5101 Statistical Data Mining

五人团队的猫咪图片偏好分析项目。统一数据、验证划分、环境和运行入口；按功能模块协作，**直接在 main 上按模块提交，不建功能分支、不提 PR**。

## 快速开始

使用 Python **3.12**。以下命令在仓库根目录运行；macOS/Linux将解释器路径改为`.venv/bin/python`。

```powershell
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.lock.txt
.venv/Scripts/python scripts/run_all.py
.venv/Scripts/python scripts/check_project.py
```

默认使用已有清洗数据，运行猫咪排名、图片分歧分析、人群偏好分析和扩展模型比较，无需图片、GPU或外部模型下载。核心依赖在`requirements.txt`，完整已验证环境在`requirements.lock.txt`。需要导入包的Notebook环境可额外执行`python -m pip install -e . --no-deps`。

提交代码包的运行说明见 [README_SUBMISSION.md](README_SUBMISSION.md)。打包入口为 `scripts/build_submission.py --output <ZIP路径>`；它仅收集 Git 已跟踪文件及三份指定的课程 CSV，不包含 Git 历史、虚拟环境、缓存和原始图片。

## 模块与负责人

| 功能 | 负责人 | 代码目录（src/cat_arena下） | 运行入口（scripts下） | 状态 |
|---|---|---|---|---|
| 数据准备与总体探索 | 成员1 | `data_preparation/` | `run_data_preparation.py` | 已交付；完整重建需课程CSV和图片 |
| 猫咪排名与BT基础模型 | 成员2 | `cat_ranking/` | `run_cat_ranking.py` | 已接入可复用拟合函数 |
| 图片差异与偏好分歧 | 成员3 | `image_analysis/` | `run_image_analysis.py` | 已交付并完成迁移复现 |
| 人群差异 | 成员4 | `human_preferences/` | `run_human_preferences.py` | 已交付；按人群比较猫咪经验胜率 |
| 扩展模型与报告整合 | 成员5 | `model_comparison/` | `run_model_comparison.py` | 已交付；扩展模型比较、验证与排名稳健性 |

`run_all.py`运行已实现、可凭清洗数据执行的成员2/3/4/5模块，不代表成员1的完整重建已完成。加`--prepare-data`会先重建并审计成员1数据，要求原始CSV及全部引用图片已放入`data/raw/`。

## 目录与数据流

```text
configs/default.json          路径、随机种子、分析参数
data/raw/                    本地原始CSV与images，不提交Git
data/processed/              全组唯一清洗数据来源
data/splits/                 全组共同图片对划分
src/cat_arena/               按功能划分的实现与公共数据契约
scripts/                    命令行入口，与当前工作目录无关
notebooks/                  演示与探索，调用src方法
tests/                      方向编码、拟合、数据与迁移检查
outputs/<模块>/             表格、图、摘要及运行记录
reports/sections/           报告章节
reports/handoffs/           跨模块交接
reports/slides/             最终PPT/PDF归档位置
docs/modules/               方法、接口与使用说明
docs/provenance/            原环境记录与迁移基准
```

原始数据 → 数据准备 → 统一清洗数据和共同划分 → 各分析模块 → 模型比较 → 最终报告。成员间读取公共数据或约定输出，不再依赖个人交接文件夹。

## 团队入口

- [直接提交main的协作约定](CONTRIBUTING.md)
- [数据字典](docs/modules/data_preparation/data_dictionary.md)与[数据准备](docs/modules/data_preparation/README_handoff.md)
- [猫咪排名与可复用BT接口](docs/modules/cat_ranking.md)
- [图片差异分析](docs/modules/image_analysis/README.md)
- [人群差异说明](docs/modules/human_preferences.md)、[成员5人群交接](docs/modules/human_preferences_handoff.md)与[模型比较接入](docs/modules/model_comparison.md)
- [成员贡献](docs/contributions.md)与[迁移验证](docs/migration.md)

## 数据与推断边界

每行是一次选择回答，没有参与者ID，记录数不等于独立人数。沿用成员1清洗规则，保留重复回答与缺失属性。划分按无序图片对分组，允许图片和猫跨集合，不能证明新图片、新猫或新参与者泛化。拟合和结果派生特征只使用相应训练子集；`test_example.csv`示例值不是真实标签。

数据及衍生材料仅用于教育和研究。课程截止要求和署名以课程指南、小组最终确认信息为准。
