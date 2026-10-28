# 数据准备运行说明

当前入口和输入摆放见同目录README_handoff.md。实现为src/cat_arena/data_preparation/prepare.py，独立审计为audit.py，对外通过scripts/run_data_preparation.py和scripts/audit_data_preparation.py执行。

安装以根目录requirements.txt/requirements.lock.txt为准。原版本及完整图片检查记录在docs/provenance/data_preparation/；缺少课程图片时不能宣称已完整重跑。

python scripts/check_project.py验证公共主表、划分、迁移基准和核心测试，不替代具备原始CSV及图片时的完整准备与审计。
