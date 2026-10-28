# 从成员交接目录迁移为团队项目

## 组织和协作

旧交接版本为提交b09be57，保存为Git标签`v0.1-handoff`。本次直接在main整理，不创建分支或PR。由于数据与路径是所有模块的共同依赖，首次目录迁移作为一个完整的`project:`提交；后续改动按功能模块分别提交。

| 原位置 | 当前位置 |
|---|---|
| 交接1/data/processed中的主表与汇总 | data/processed/ |
| 交接1/data/processed/validation_split.csv | data/splits/validation_split.csv |
| 交接1/scripts | src/cat_arena/data_preparation/ |
| 交接2的BT实现 | src/cat_arena/cat_ranking/，Notebook调用相同实现 |
| 交接3/scripts | src/cat_arena/image_analysis/ |
| 各成员outputs | outputs/data_preparation、cat_ranking、image_analysis |
| 报告章节与成员间交接 | reports/sections、reports/handoffs |
| 原依赖与历史运行记录 | docs/provenance/ |

逐文件映射为`docs/migration_map.json`。旧代码可从标签中恢复，不保留第二套活动代码。成员4/5仅预留模块和接入文档，没有虚构分析结果。

## 方法保持与接口变化

保留成员1的清洗、方向编码、重复/缺失规则和图片对划分。成员2的目标函数、参考猫、优化设置和中心化保持，新增可调用拟合/预测接口及明确的连通性、未知猫错误处理。成员3的计数、置换、bootstrap与网络算法保持，输入检查提取成公共数据契约。

路径/参数集中至configs/default.json，核心依赖只维护根目录requirements.txt。已使用统一Python3.12环境实际重跑BT和图片分析。原成员1/2环境仍保留作追溯，不能与当前安装说明混用。生成文本使用LF，数据和结果文件保留字节，避免Git行尾转换破坏指纹。

## 验证与局限

运行`python scripts/check_project.py --rerun`重新生成已交付的猫咪/图片分析，执行团队测试，并核对：公共数据和划分字节保持；成员1描述表图保持；逐猫名次一致且BT分数差异在1e-8内；成员3数值摘要与迁移前一致。实际结果在`outputs/project_checks/migration_report.json`。

`python scripts/audit_image_analysis.py --rerun`另外从无关工作目录以独立进程重跑图片分析，比较结果与中英文报告。原始数据和图片不随本次目录整理新增上传。

本地缺少1558张课程图片，未完整重跑成员1图片验证与解码；原审核归档为历史资料，当前仅核对现有数据和描述结果保持，并用构造图片测试清洗核心行为。完整重建需要把CSV及images放入data/raw，再运行数据准备及审计。

迁移回归用于证明当前版本的结果保持。未来有意改变方法、数据或参数时，应记录新研究决策和结果差异，再更新相应回归基准；不能为了让检查变绿而无说明地改基准。
