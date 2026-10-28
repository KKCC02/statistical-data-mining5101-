# 图片差异与偏好分歧 · 成员3

## 运行

```powershell
python scripts/run_image_analysis.py
python scripts/audit_image_analysis.py --rerun
```

统一读取`data/processed/train_clean.csv`及`data/splits/validation_split.csv`。无需原始图片或测试标签。默认参数在configs/default.json。支持--input、--split、--output和重采样次数选项；自定义输出时报告写该目录的reports/，不覆盖正式章节。

## 位置与接口

| 内容 | 项目根目录相对路径 |
|---|---|
| 分析/报告/审核实现 | src/cat_arena/image_analysis/analysis.py、report.py、audit.py |
| 共用清洗主表契约 | src/cat_arena/common/data.py |
| 表格、3张图、模拟数组、摘要、metadata | outputs/image_analysis/ |
| 中英文报告 | reports/sections/image_analysis_zh.md、image_analysis_en.md |
| 成员5交接 | reports/handoffs/image_effects_to_model_comparison.md |
| 质量说明 | docs/modules/image_analysis/quality_review.md |
| 测试 | tests/test_image_analysis.py |

## 方法与结果

3003条同猫回答、1132个无序图片对。1016个重复对中64.57%存在分歧；整体回答组合一致率53.05%，按猫bootstrap95%区间约51.03%-55.20%。全局保留A总数置换单侧p=0.0008，按猫保留A总数p=0.0013。

每对1-4回答，4次全票的双侧精确二项p仍为0.125，没有单对p<0.05。200/237只猫的同猫无向图连通，74/237只有向胜负图强连通。支持试验带收缩的图片效应，不证明已经有模型提升或可靠赢家。

逐对表字段：n_responses回答数；n_choose_image_1规范第一图获选次数；response_dyads同对回答的无序组合数；agreeing_dyads其中同图组合；dyad_agreement二者之比，单次回答为空；ci95_low/high为规范第一图概率的逐对精确区间；p_exact_two_sided/p_bh/p_by为原始与调整p值。熵、全票和多数比例仅作小样本描述。

## 限制

保留缺失属性和内容重复，删除额外同内容记录仅作敏感性分析。没有参与者ID，按猫bootstrap不能处理未知跨猫参与者依赖；置换需要零假设下可交换性，逐对区间需要独立同分布回答。回答组合重叠，不是独立试验。

全数据结果只作描述/诊断，不能直接作为验证特征。图片效应需在训练子集内重新估计，明确未知图片回退。人群差异归成员4、模型比较归成员5。

metadata记录输入、实现、共享契约和配置指纹。生成文本统一LF，Git保留数据和结果字节。统计贡献归成员3，旧交接在v0.1-handoff可追溯。
