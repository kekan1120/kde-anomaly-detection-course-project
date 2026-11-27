# 与 B 基准的对账记录（C 实现与复现负责人）

> 由 `04_code/reconcile_with_baseline.py` 自动生成，勿手工编辑。

| 项 | 值 |
|---|---|
| 对账项数 | 50 |
| 失败项数 | **0** |
| 数据 sha256 判据 | 逐位相等 |
| 数据统计量判据 | 相对容差 1e-12 |
| 指标判据 | 绝对容差 1e-09 |
| E0 判据 | 1e-4（基准表 4 位小数） |

## 总览

| 层 | 项目 | 结论 |
|---|---|---|
| 数据层 | train.sha256 | ✅ PASS |
| 数据层 | train.stats | ✅ PASS |
| 数据层 | validation.sha256 | ✅ PASS |
| 数据层 | validation.stats | ✅ PASS |
| 数据层 | test.sha256 | ✅ PASS |
| 数据层 | test.stats | ✅ PASS |
| 阈值层 | threshold[kde:0.1] | ✅ PASS |
| 阈值层 | threshold[kde:0.2] | ✅ PASS |
| 阈值层 | threshold[kde:0.35] | ✅ PASS |
| 阈值层 | threshold[kde:0.5] | ✅ PASS |
| 阈值层 | threshold[kde:0.8] | ✅ PASS |
| 阈值层 | threshold[kde:1.2] | ✅ PASS |
| 阈值层 | threshold[lof:10] | ✅ PASS |
| 阈值层 | threshold[lof:20] | ✅ PASS |
| 阈值层 | threshold[lof:35] | ✅ PASS |
| 阈值层 | threshold[lof:50] | ✅ PASS |
| 指标层 | n | ✅ PASS |
| 指标层 | n_normal | ✅ PASS |
| 指标层 | n_anomaly | ✅ PASS |
| 指标层 | prevalence | ✅ PASS |
| 指标层 | n_normal_dense | ✅ PASS |
| 指标层 | n_normal_sparse | ✅ PASS |
| 指标层 | n_anomaly_far | ✅ PASS |
| 指标层 | n_anomaly_compact_void | ✅ PASS |
| 指标层 | threshold | ✅ PASS |
| 指标层 | val_exceedance_count | ✅ PASS |
| 指标层 | val_exceedance_rate | ✅ PASS |
| 指标层 | tp | ✅ PASS |
| 指标层 | fp | ✅ PASS |
| 指标层 | tn | ✅ PASS |
| 指标层 | fn | ✅ PASS |
| 指标层 | precision | ✅ PASS |
| 指标层 | recall | ✅ PASS |
| 指标层 | f1 | ✅ PASS |
| 指标层 | fpr_overall | ✅ PASS |
| 指标层 | fpr_dense | ✅ PASS |
| 指标层 | fpr_sparse | ✅ PASS |
| 指标层 | fp_dense | ✅ PASS |
| 指标层 | fp_sparse | ✅ PASS |
| 指标层 | recall_far | ✅ PASS |
| 指标层 | recall_compact_void | ✅ PASS |
| 指标层 | roc_auc | ✅ PASS |
| 指标层 | average_precision | ✅ PASS |
| 指标层 | n_inversion_pairs_equiv | ✅ PASS |
| 指标层 | val_mean_log_likelihood | ✅ PASS |
| 指标层 | param_name | ✅ PASS |
| 多种子层 | 10 个 seeds 的均值/标准差/召回 | ✅ PASS |
| E0 层 | h=0.08 | ✅ PASS |
| E0 层 | h=0.3 | ✅ PASS |
| E0 层 | h=0.9 | ✅ PASS |

## 细节

- **数据层 / train.sha256** — PASS — bbe5881fa6b3acc65340fea280fd2835 vs bbe5881fa6b3acc65340fea280fd2835
- **数据层 / train.stats** — PASS — 相对容差判据 1e-12，实测最大相对偏差 0.000e+00
- **数据层 / validation.sha256** — PASS — ac03679b6fab71e2e58688cacb380bb7 vs ac03679b6fab71e2e58688cacb380bb7
- **数据层 / validation.stats** — PASS — 相对容差判据 1e-12，实测最大相对偏差 0.000e+00
- **数据层 / test.sha256** — PASS — e00edf67e4bb128d430cf14d430f274f vs e00edf67e4bb128d430cf14d430f274f
- **数据层 / test.stats** — PASS — 相对容差判据 1e-12，实测最大相对偏差 0.000e+00
- **阈值层 / threshold[kde:0.1]** — PASS — C=15.727733，HANDOFF §3.3=15.727733，偏差=4.56e-07
- **阈值层 / threshold[kde:0.2]** — PASS — C=7.896117，HANDOFF §3.3=7.896117，偏差=1.37e-07
- **阈值层 / threshold[kde:0.35]** — PASS — C=6.176033，HANDOFF §3.3=6.176033，偏差=2.46e-07
- **阈值层 / threshold[kde:0.5]** — PASS — C=5.777108，HANDOFF §3.3=5.777108，偏差=2.31e-07
- **阈值层 / threshold[kde:0.8]** — PASS — C=5.249742，HANDOFF §3.3=5.249742，偏差=4.64e-07
- **阈值层 / threshold[kde:1.2]** — PASS — C=4.801341，HANDOFF §3.3=4.801341，偏差=4.85e-07
- **阈值层 / threshold[lof:10]** — PASS — C=1.893115，HANDOFF §3.3=1.893115，偏差=4.59e-07
- **阈值层 / threshold[lof:20]** — PASS — C=2.022293，HANDOFF §3.3=2.022293，偏差=1.68e-07
- **阈值层 / threshold[lof:35]** — PASS — C=1.966556，HANDOFF §3.3=1.966556，偏差=4.13e-07
- **阈值层 / threshold[lof:50]** — PASS — C=1.937930，HANDOFF §3.3=1.937930，偏差=4.01e-07
- **指标层 / n** — PASS — 最大绝对偏差=0.000e+00，NaN 结构不一致点=0（容差 1e-09）
- **指标层 / n_normal** — PASS — 最大绝对偏差=0.000e+00，NaN 结构不一致点=0（容差 1e-09）
- **指标层 / n_anomaly** — PASS — 最大绝对偏差=0.000e+00，NaN 结构不一致点=0（容差 1e-09）
- **指标层 / prevalence** — PASS — 最大绝对偏差=0.000e+00，NaN 结构不一致点=0（容差 1e-09）
- **指标层 / n_normal_dense** — PASS — 最大绝对偏差=0.000e+00，NaN 结构不一致点=0（容差 1e-09）
- **指标层 / n_normal_sparse** — PASS — 最大绝对偏差=0.000e+00，NaN 结构不一致点=0（容差 1e-09）
- **指标层 / n_anomaly_far** — PASS — 最大绝对偏差=0.000e+00，NaN 结构不一致点=0（容差 1e-09）
- **指标层 / n_anomaly_compact_void** — PASS — 最大绝对偏差=0.000e+00，NaN 结构不一致点=0（容差 1e-09）
- **指标层 / threshold** — PASS — 最大绝对偏差=0.000e+00，NaN 结构不一致点=0（容差 1e-09）
- **指标层 / val_exceedance_count** — PASS — 最大绝对偏差=0.000e+00，NaN 结构不一致点=0（容差 1e-09）
- **指标层 / val_exceedance_rate** — PASS — 最大绝对偏差=0.000e+00，NaN 结构不一致点=0（容差 1e-09）
- **指标层 / tp** — PASS — 最大绝对偏差=0.000e+00，NaN 结构不一致点=0（容差 1e-09）
- **指标层 / fp** — PASS — 最大绝对偏差=0.000e+00，NaN 结构不一致点=0（容差 1e-09）
- **指标层 / tn** — PASS — 最大绝对偏差=0.000e+00，NaN 结构不一致点=0（容差 1e-09）
- **指标层 / fn** — PASS — 最大绝对偏差=0.000e+00，NaN 结构不一致点=0（容差 1e-09）
- **指标层 / precision** — PASS — 最大绝对偏差=0.000e+00，NaN 结构不一致点=0（容差 1e-09）
- **指标层 / recall** — PASS — 最大绝对偏差=0.000e+00，NaN 结构不一致点=0（容差 1e-09）
- **指标层 / f1** — PASS — 最大绝对偏差=0.000e+00，NaN 结构不一致点=0（容差 1e-09）
- **指标层 / fpr_overall** — PASS — 最大绝对偏差=0.000e+00，NaN 结构不一致点=0（容差 1e-09）
- **指标层 / fpr_dense** — PASS — 最大绝对偏差=0.000e+00，NaN 结构不一致点=0（容差 1e-09）
- **指标层 / fpr_sparse** — PASS — 最大绝对偏差=0.000e+00，NaN 结构不一致点=0（容差 1e-09）
- **指标层 / fp_dense** — PASS — 最大绝对偏差=0.000e+00，NaN 结构不一致点=0（容差 1e-09）
- **指标层 / fp_sparse** — PASS — 最大绝对偏差=0.000e+00，NaN 结构不一致点=0（容差 1e-09）
- **指标层 / recall_far** — PASS — 最大绝对偏差=0.000e+00，NaN 结构不一致点=0（容差 1e-09）
- **指标层 / recall_compact_void** — PASS — 最大绝对偏差=0.000e+00，NaN 结构不一致点=0（容差 1e-09）
- **指标层 / roc_auc** — PASS — 最大绝对偏差=0.000e+00，NaN 结构不一致点=0（容差 1e-09）
- **指标层 / average_precision** — PASS — 最大绝对偏差=0.000e+00，NaN 结构不一致点=0（容差 1e-09）
- **指标层 / n_inversion_pairs_equiv** — PASS — 最大绝对偏差=0.000e+00，NaN 结构不一致点=0（容差 1e-09）
- **指标层 / val_mean_log_likelihood** — PASS — 最大绝对偏差=0.000e+00，NaN 结构不一致点=0（容差 1e-09）
- **指标层 / param_name** — PASS — bandwidth / n_neighbors 标签一致
- **多种子层 / 10 个 seeds 的均值/标准差/召回** — PASS — 共 12 列，最大绝对偏差=0.000e+00（容差 1e-09）
- **E0 层 / h=0.08** — PASS — C: 局部极大=8/显著峰=2/最大密度=1.0705/谷填充率=0.0007；基准: 8/2/1.0705/0.0007
- **E0 层 / h=0.3** — PASS — C: 局部极大=3/显著峰=2/最大密度=0.6254/谷填充率=0.1581；基准: 3/2/0.6254/0.1581
- **E0 层 / h=0.9** — PASS — C: 局部极大=2/显著峰=1/最大密度=0.2629/谷填充率=0.9140；基准: 2/1/0.2629/0.9140
