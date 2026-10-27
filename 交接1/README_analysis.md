# 成员 1：清洗与总体探索

成员姓名：梁桂荣。

## 运行

在项目根目录保留原始 train.csv、test.csv、README.md 和 images/。已使用 Python 3.11.8 验证，依赖版本见 requirements.txt。无需下载外部数据或模型；不需要 GPU。

```powershell
python -m pip install -r requirements.txt
python scripts/member1_prepare.py
python scripts/member1_audit.py
```

脚本也可以从其他工作目录用绝对路径运行；数据路径以脚本位置为基准。第一条脚本命令重新生成全部数据、表、图和运行元数据，包含 1,558 张图片的完整解码检查，本机此次两次运行约 8–17 秒；第二条执行独立审计，约数秒。实际平台、版本、处理器和准备耗时见 outputs/run_metadata.json。再次运行会覆盖生成文件，不修改原始文件。请在准备脚本成功退出后运行审计；遇到异常应先查明原因，不把旧输出当成新运行成功的结果。

如需同时验证重复运行及工作目录可移植性：

```powershell
python scripts/member1_audit.py --rerun
```

该命令会从另一个工作目录调用准备脚本，逐个比较数据、表格和图文件的 SHA-256，再执行独立检查。准备脚本的致命输入错误会终止运行；具体记录见质量检查表或错误信息。审计失败返回非零退出码。

## 阅读顺序

1. docs/cleaning_rules.md：清洗、重复记录处理与验证口径。
2. docs/data_dictionary.md：原始及新增字段、汇总表说明。
3. outputs/tables/：质量检查、缺失、类别分布、猫咪覆盖与总体统计。
4. outputs/figures/：三张图的 PNG 和 PDF；图中文字为英文以避免跨平台中文字体缺失。
5. docs/member1_report_notes.md：已核对的数据描述、质量说明与图注，含梁桂荣的贡献说明，可并入全组报告；组号待补充。
6. docs/quality_review.md：最近一次审计记录；机器可读版本为 outputs/audit_report.json。
7. docs/review_notes.md：本次复查改进、图表审阅与交付清单。

## 输出数据

- data/processed/train_clean.csv：全体训练记录，保留原字段并增加公共字段。
- data/processed/test_features_clean.csv：测试记录，结果相关字段保持缺失。
- data/processed/image_pair_summary.csv：训练集图片对汇总。
- data/processed/validation_split.csv：按图片对分组的固定划分，按 train_row_id 与主表连接。

统计图表使用全训练集，仅用于描述。已保留的划分作为可选统一方案；清洗主表不依赖它，也不强制其他成员采用该方案。标签衍生字段及训练内容重复标记仅用于分析/质检，不作预测输入。此步骤不拟合预测模型、不生成测试预测、不验证小组其他成员的研究假设。

固定种子：2026。表格在相同输入和依赖版本下应可复现；不同字体与 Matplotlib 版本可能产生细微绘图外观差异。runtime_seconds 随机器变化。

提交前可在全新 Python 会话按以上命令运行，检查输出，并把小组编号补入最终报告；成员 1 姓名已填写为梁桂荣。保留课程数据的教育研究用途限制。代码已在独立 Python 进程中运行；未另建完全隔离的依赖安装环境。审计验证的是准备结果与规则的一致性，不能证明问卷回答独立或数据代表所有人类偏好。
