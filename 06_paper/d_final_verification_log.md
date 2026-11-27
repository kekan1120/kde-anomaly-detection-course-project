# D 最终人工核验日志

本表记录 DeepSeek 回合 4 提出的最终核验清单。模型输出只用于确定核验范围；通过状态必须依据原始文件、原始脚本输出、成员本人确认或课程方明确回复填写。未完成项不得写成“已核验”。

## 记录字段

每项至少记录：核验 ID、原始文件路径、字段/行/段落、查看动作、结果、证据路径、日期、核验人、是否本人确认、状态。状态只使用：`待核验`、`部分通过`、`通过`、`不通过`、`需他人确认`。

## A 类：D 亲自打开原始文件核对

| ID | 核验项目 | 原始文件/位置 | 要查看的字段或内容 | 结果与证据 | 核验人/日期 | 状态 |
|---|---|---|---|---|---|---|
| A1 | 论文数字与主结果逐项对应 | `05_results/main/metrics.csv`; `06_paper/course_report.md` §4 | E1/E2/E3 指标、阈值、TP/FP/TN/FN 与论文四位小数 | 待填写 | D / 待填 | 待核验 |
| A2 | train/validation/test 样本量来源 | `05_results/main/run_log.txt`; `config_ref.v1.0.snapshot.json`; `seed_registry.csv` | train、validation、test 样本量及测试异常比例 | 待填写 | D / 待填 | 待核验 |
| A3 | 数据生成参数 | `01_protocol_and_data_dictionary.md`; `05_results/main/config_ref.v1.0.snapshot.json`; `run_log.txt` | 均值、标准差、远端环参数、异常比例、标准化设置 | 待填写 | D / 待填 | 待核验 |
| A4 | 随机种子 | `05_results/main/seed_registry.csv`; v1.0 配置和日志 | train/validation/test、E0、远端环和运行种子 | 待填写 | D / 待填 | 待核验 |
| A5 | 阈值实现与逐配置阈值 | `04_code/src/kdelof/calibration.py`; `05_results/main/run_log.txt`; `metrics.csv` | 分位数实现、严格大于比较、并列处理、各配置 threshold | D 已打开代码、日志和 CSV；阈值及超阈数一致，说明文字已修订 | D / 2026-11-27 | 部分通过 |
| A6 | LOF 分数方向 | `04_code/` LOF 实现; `05_results/main/sanity_checks.md`; API 文档 | 原始输出符号、是否取负、正常点和远端点样例 | D 已打开实现并核对 C8 方向断言；统一越大越异常 | D / 2026-11-27 | 通过 |
| A7 | E0 1D 示意数据 | `05_results/main/e0_demo1d_peaks.csv`; `course_report.md` §4.1 | 各带宽的峰值、谷值/填充率和图中对应数值 | D 已逐行核对论文实际报告的峰数和谷填充率；未将未报告峰高视为冲突 | D / 2026-11-27 | 通过 |
| A8 | 多种子结果实际使用范围 | `05_results/main/metrics_multiseed_summary.csv`; `course_report.md` §4.4 | KDE h=0.35、LOF k=20 的 AUC、AP、稀疏簇 FPR 是否写入正文 | D 已打开汇总 CSV；正文 AUC/稀疏簇 FPR 一致，AP 明确未写入正文 | D / 2026-11-27 | 通过 |
| A9 | 图资产、图号和图注 | `05_results/main/figures_d/`; `course_report.md` §4; `c_review_of_D.md` | 文件是否存在、正文引用、轴名、参数、阈值、分数方向和图号映射 | 待填写 | D / 待填 | 待核验 |
| A10 | 提交包全文搜索 | 最终提交目录及 `course_report.md`、追溯表、互审和阶段 0 文件 | `near`、`compact_void`、`ai_draft`、`v1.1` 及相关数字的上下文 | 待填写 | D / 待填 | 待核验 |

### A 类已执行核验（2026-11-27）

- **A1：部分通过。** D 打开并对照 `05_results/main/metrics.csv`、`06_paper/course_report.md`、`05_results/main/e0_demo1d_peaks.csv` 和 `05_results/main/metrics_multiseed_summary.csv`。E1/E2/E3 的样本量、阈值、混淆矩阵、AUC、AP、召回、F1、分簇 FPR、E0 三档峰结构和多种子摘要均与论文四位小数一致；`py -3 04_code/review_D_numbers.py` 输出 34/34 PASS。`metrics_multiseed.csv` 独立复算得到 h=0.35 的稀疏簇 FPR 低于 2% 为 3/10，各带宽为 3–5/10，60/60 次 `fpr_sparse > fpr_dense`。保留一项表述风险：§4.3 的 H4 召回句列出 h=0.35、0.80、1.20，漏列同样达到 1.0000 的 h=0.50；该项不改变实验数字，状态为需局部确认。
- **A2：通过。** `config_ref.v1.0.snapshot.json`、`seed_registry.csv` 和 `run_log.txt` 均显示 train=600、validation=1000、test=1250（正常 1000、far 异常 250），验证集超阈为 10/1000。运行日志同时记录三划分标签、缺失值和无重合检查。
- **A3：通过。** v1.0 快照确认密集簇均值 `(-2,0)`、scale 0.5，稀疏簇均值 `(2,0)`、scale 1.0，far 半径 5–7、n=250、标准化 none；`04_code/src/kdelof/dgp.py` 和 `run_log.txt` 与配置中的生成公式和 v1.0 far-only 口径一致。当前 `01_protocol_and_data_dictionary.md` 的 B-v1.1-near 仅作版本背景，不替代 v1.0 快照。
- **A4：部分通过。** `seed_registry.csv` 和 v1.0 配置中的各数据流种子与论文列出的主种子、E0 种子和 far 种子一致，扩展规则为 repeat 1–10、每次偏移 10000；运行日志记录了多种子运行。论文附录只列核心流的简写种子，未列 sparse 流等完整流键，暂记为“附录完整性需确认”，不影响主结果数值。

**核验依据：** 本次记录来自 D 对仓库原始文件的打开、字段/行对照、代码实现查看、运行日志查看和独立计数；DeepSeek 回合 5 的表格只作为核验范围提示，不作为通过证据。

### A5–A8 已执行核验（2026-11-27）

- **A5：部分通过。** `calibration.py`、`experiment.py`、v1.0 配置和 `metrics.csv` 确认每个 detector×parameter 独立使用 `quantile=0.99`、`method="inverted_cdf"`，预测规则为严格 `score > threshold`，等于阈值判正常；10 个配置的验证集超阈数均为 10/1000。默认 KDE/LOF 阈值与论文一致。保留文档风险：`run_log.txt` 和 C9 JSON 显示 `linear/lower/nearest/midpoint` 也得到 10 个超阈样本，而 C9 文字与 calibration docstring 的“仅 inverted_cdf 恰为 10/linear 会偏”表述过强；该风险不改变主 CSV 数字。
- **A6：通过。** `scoring.py` 的正式 LOF 路径使用 `LocalOutlierFactor(novelty=True, metric="euclidean")`，`experiment.py` 对 validation/test 原始分数统一调用 `to_anomaly_score(raw)=-raw`；`run_log.txt` 和 `sanity_checks.md` C8 记录全部 6 个 KDE 带宽与 4 个 LOF 邻居数方向断言通过。论文“越大越异常”的表述与实现一致。
- **A7：通过（按论文实际报告字段）。** 已打开 `e0_demo1d_peaks.csv`，三档带宽的局部极大数/显著峰数为 `(8,2)`、`(3,2)`、`(2,1)`，谷填充率为 `0.0007/0.1581/0.9140`，与论文一致；峰高和最大密度虽在 CSV 中存在，但论文未报告，未将其当作缺失数字或冲突。
- **A8：通过，成员声明另记。** 已打开 `metrics_multiseed_summary.csv` 和 `metrics_multiseed.csv`；KDE h=0.35 的 AUC/稀疏簇 FPR 为 `0.9998±0.0002`、`0.0258±0.0127`，LOF k=20 为 `0.9995±0.0003`、`0.0110±0.0054`，与 §4.4 一致。AP 在汇总文件中存在但正文未使用。A/C 已确认的具体范围和凭证应保留原始成员确认，不由本日志替代。

**当前待处理：** A5 的方法对照文字是否修订；H4 召回句是否补列 `h=0.50`；附录是否补充完整数据流种子；A/C 确认原文是否归档到 B 类证据。

## B 类：需要 A 或 C 本人确认

| ID | 核验项目 | 依据文件 | 本人需确认的内容 | 证据/回复 | 核验人/日期 | 状态 |
|---|---|---|---|---|---|---|
| B1 | C 初轮/二轮复核范围 | `06_paper/c_review_of_D.md`; `04_code/review_D_numbers.py` 原始输出 | 初轮 32 项、二轮 34 项、退出码和新增检查项 | 待 C 原始输出 | 待填 | 需他人确认 |
| B2 | D→A 文献与互审状态 | `docs/theory-note.md` §8; `06_paper/d_review_of_A.md` | 原文真实性由 A 确认；互审写“已执行，待 A 确认” | 待 A 回复 | 待填 | 需他人确认 |
| B3 | C 阶段 0 签字 | `docs/stage0-closure-checklist.md` §2.3; `c_review_of_D.md` | C 本人确认或撤回代填日期 | 待 C 回复 | 待填 | 需他人确认 |
| B4 | 阶段 0 会话凭证 | `docs/stage0-closure-checklist.md` §4; `docs/session-link-policy.md`; `process-logs/` | 各凭证类型是否符合课程要求且来自本人账号 | 待 A/课程方确认 | 待填 | 需他人确认 |
| B5 | 阶段 0 关闭与 H3 修订顺序 | `stage0-closure-checklist.md`; `course_report.md` §3.1; `docs/decision-log.md` | 关闭日期、H3 修订日期和核准覆盖范围的时间顺序 | 待 A 确认 | 待填 | 需他人确认 |
| B6 | DSH 导出能否替代公网链接 | 课程提交要求、`docs/session-link-policy.md` | 课程入口/助教是否接受导出凭证 | 待 A/课程方回复 | 待填 | 需他人确认 |

## C 类：仅作文档对照，不替代本人确认

| ID | 核验项目 | 依据文件 | 对照内容 | 记录 | 状态 |
|---|---|---|---|---|---|
| C1 | 32/34 项范围差异 | `c_review_of_D.md`; `numeric_traceability.md` | 文档中的初轮、二轮新增项和追溯表旧状态 | 待填写 | 待核验 |
| C2 | T-010/T-011 使用范围 | `course_report.md` §4.4; `numeric_traceability.md` | 正文实际使用 AUC、稀疏簇 FPR 和是否使用多种子 AP | 待填写 | 待核验 |
| C3 | D→A 互审措辞 | `d_review_of_A.md`; `stage0-closure-checklist.md` §2.2 | 是否保留“已执行，待 A 确认” | 待填写 | 待核验 |
| C4 | C 签字记录冲突 | `stage0-closure-checklist.md` §2.3; `c_review_of_D.md` | 文档是否存在代填日期提醒 | 待填写 | 待核验 |
| C5 | near/compact_void/ai_draft 标记 | `d_review_of_A.md`; 阶段 0 条件 4; 论文附录 | 仅作为版本/路径说明，未混入主结果数字 | 待填写 | 待核验 |
| C6 | 图号历史记录 | `c_review_of_D.md` §6; `course_report.md` §4.2; T-006/T-007 | 历史“图5a”和最终图号映射是否一致 | 待填写 | 待核验 |
| C7 | 追溯表状态覆盖范围 | `numeric_traceability.md`; `c_review_of_D.md` | “C 已复核”具体覆盖哪些字段，避免扩大解释 | 待填写 | 待核验 |
| C8 | 阶段 0 凭证类型差异 | `stage0-closure-checklist.md` §4; `session-link-policy.md` | session-id、导出文件、GitHub 链接、分享链接的类型记录 | 待填写 | 待核验 |

## 记录原则

- DeepSeek 输出、追溯表摘要和成员代填内容不能单独构成通过证据。
- 主结果仍限定为 `05_results/main/metrics.csv` 的 v1.0 far-only 数据。
- 在 A/B 类完成前，不修改论文数字、H1–H4 判定或阶段 0 的成员签字状态。
