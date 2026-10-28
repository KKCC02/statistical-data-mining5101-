# 团队协作：直接在main按模块提交

## 日常步骤

```powershell
git pull --ff-only origin main
# 修改负责模块及相关测试、结果和文档
python scripts/check_project.py
git add <本次模块涉及的具体路径>
git commit -m "image_analysis: describe the concrete change"
git push origin main
```

不创建功能分支，不提PR。一次提交围绕一个可独立核对的模块变更；公共目录调整用`project:`前缀并说明影响。提交前查看`git diff --cached --stat`，避免加入虚拟环境、原始图片、缓存或其他成员未完成的内容。

若远程已更新，先`git pull --rebase origin main`，解决冲突、重跑受影响检查，再普通推送。不要强推共享历史，也不要用自己的文件直接覆盖别人的工作。

## 模块边界

成员1负责统一数据及字段；成员2负责猫咪排名/BT；成员3负责图片分析；成员4负责人群差异；成员5负责扩展模型、验证和最终报告。每人同步维护自己模块的代码、输出和报告章节。

多人需要改同一公共文件时，先在小组明确由谁处理。更改清洗规则、共同划分、核心依赖或字段含义时，记录影响并通知相关成员，不能只改自己的读取代码。

## 文件与命名

- Python与字段用英文`snake_case`；文档可用中英文，代码不写个人电脑绝对路径。
- 依赖只在根目录`requirements.txt`统一维护，同步`requirements.lock.txt`与运行记录；脚本/Notebook不自动安装或改写依赖。
- 路径/参数读取`configs/default.json`。共享工具需确有多个模块使用，不把业务方法堆入`common/`。
- 各模块只写自己的`outputs/<模块>/`及报告章节；多次实验使用明确的自定义输出目录。
- 默认提交小型结果表与报告图供组员查看；原始图片、虚拟环境、缓存不提交。
- Notebook调用`src/`实现，可复用拟合函数不能依赖隐藏全局状态。

## 验证

使用同一清洗主表与保存的图片对划分。全数据描述统计与子集拟合严格区分，不能用全数据胜率或已拟合全数据的分数评估验证集。

模块改动运行相关测试和入口。公共路径/数据改动运行`python scripts/check_project.py --rerun`。完整源数据和图片审计需要全部课程图片，未执行时明确记录，不将历史审核当作当前通过。

提交前缀：`data_preparation:`、`cat_ranking:`、`image_analysis:`、`human_preferences:`、`model_comparison:`、`reports:`、`project:`。
