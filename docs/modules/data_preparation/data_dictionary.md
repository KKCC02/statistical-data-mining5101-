# 字段说明

观察单位：一条针对两张猫咪图片的选择记录。没有参与者 ID，记录数不是独立人数。
数据来源：原始 README.md、课程提供的 CSV 与 images 文件夹。

## 原始字段

|字段|含义|
|---|---|
|train_row_id / test_row_id|训练/测试记录标识，不作为偏好特征|
|a_cat / b_cat|A/B 侧猫咪标识|
|a_image / b_image|相对于 images/ 的图片路径|
|choice|A 或 B；测试集缺失|
|prob_a|测试提交时预测选择 A 的概率；原始测试集缺失|
|comparison_type|within_cat：同猫不同照片；between_cats：不同猫照片|
|gender|man / woman；自报性别|
|pet_history|current：目前养宠；past：过去养宠；never：从未养宠，家庭层面|
|pet_care|never / occasionally / past_regular / current_regular，个人照顾宠物经历|
|pet_contact|never / rarely / sometimes / often / daily，接触宠物频率|
|future_pet|yes / no / unsure，未来养宠或继续养宠意向|
|mbti_ie|I / E / unknown；unknown 是有效回答，不等于缺失|

## 新增字段

|字段|定义|
|---|---|
|choice_a|选择 A 为 1，B 为 0；测试集为空|
|canonical_image_1 / canonical_image_2|按路径字典序排序后的第一/第二张图片，与左右位置无关|
|image_pair_id|两条排序后的图片路径用 `\|\|` 拼接，A/B 互换仍是同一对|
|cat_pair_id|排序后的猫咪 ID 用 `\|\|` 拼接；同猫比较保留两个相同 ID|
|choice_canonical_1|选择 canonical_image_1 为 1，否则 0；测试集为空|
|winner_cat / loser_cat|由 choice 得出的胜负猫；within_cat 两者相同，不应用于猫咪胜率排名|
|winner_image / loser_image|由 choice 得出的胜负图片|
|human_info_missing|六个人群字段中任意一个缺失|
|human_info_all_missing|六个人群字段全部缺失|
|原字段名_missing|六个人群字段各自的缺失标记|
|content_duplicate_flag|去掉行 ID 后，属于完全相同内容记录组的所有行均标 True，不表示确认录入错误|

注意：choice_a、choice_canonical_1、winner_*、loser_* 都依赖结果，禁止作为模型预测输入。content_duplicate_flag 在训练集中也使用了 choice，仅用于质量检查，不作为预测输入。图片对汇总中的获选次数、比例同样依赖全训练集结果。
CSV 中空单元格表示缺失；原始标识、路径、类别按文本解释；choice_a 与 choice_canonical_1 是可缺失的 0/1 整数；布尔标记保存为 True/False。读取时建议 pandas.read_csv；若需要保留可缺失整数类型，显式指定 dtype={'choice_a':'Int64', 'choice_canonical_1':'Int64'}。CSV 本身不保存类型信息。

训练集的重复标记以全部原始字段（不含 train_row_id，包含 choice）为依据；测试集以其全部原始字段（不含 test_row_id，choice/prob_a 均为空）为依据。因此两者分别表示完整回答内容重复与已知特征重复，不能解释为同一参与者。

## 图片对汇总表

image_pair_summary.csv 每行一个无序图片对，包含图片路径、比较类型、n_responses（回答记录数）、n_choose_image_1/2（两图获选次数）、proportion_choose_image_1（第一图选择比例）、majority_share（多数选项占比）。
majority_share 只是描述性量；单次回答自动得到 1，不能解释为可靠共识。每对仅 1–4 条回答，极端比例有很大不确定性。
此汇总表不保留逐行人群属性，不能替代主表做人群分析。

## 其他输出

- validation_split.csv：train_row_id、image_pair_id、split（train / validation）。
- cat_coverage.csv：between_cats_appearances 是不同猫比较中的出场次数；within_cat_records 是同猫比较记录数，一行只计一次。
- category_distribution.csv 的比例以全部训练记录为分母，包含缺失类别。
- missingness.csv 统计原始训练文件的缺失。
- pair_response_distribution.csv：comparison_type、n_responses（每对回答数）、n_image_pairs（该回答数对应的图片对数量）。
- image_file_check.csv：每张图片的相对路径、字节数、SHA-256 指纹、宽高（像素）、文件格式与解码错误；error 为空表示通过。
- dataset_overview.csv / dataset_summary.json：整体规模、清洗变动数、覆盖情况和已有划分规模。rows_removed 为 0、normalized_train_cells 为 0 表示本次未删行、未修正原始值。
- quality_check_summary.csv：dataset、check、count、action。缺失/重复项非零表示需要报告的信息，不一定是错误；注明 fail if present 的项目非零会停止运行。
