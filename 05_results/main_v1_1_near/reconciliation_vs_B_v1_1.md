# 与 B 的 v1.1 参考结果对账（C 实现与复现负责人）

> 由 `04_code/reconcile_v1_1_with_B.py` 自动生成。B 的数字只作基准，**不是** C 的实测。

| 项 | 值 |
|---|---|
| 对账项数 | 39 |
| 失败项数 | **0** |
| 浮点判据 | 绝对容差 1e-09 |
| 整数判据 | 完全相等 |
| 指纹判据 | sha256 逐位相等 + 统计量相对容差 1e-12 |

## 明细

- **行数与对齐键** — PASS — 12 行，键完全对齐
- **列 n** — PASS — max|Δ|=0.000e+00，NaN 结构不一致=0（容差 1e-09）
- **列 n_normal** — PASS — max|Δ|=0.000e+00，NaN 结构不一致=0（容差 1e-09）
- **列 n_anomaly** — PASS — max|Δ|=0.000e+00，NaN 结构不一致=0（容差 1e-09）
- **列 prevalence** — PASS — max|Δ|=0.000e+00，NaN 结构不一致=0（容差 1e-09）
- **列 n_normal_dense** — PASS — max|Δ|=0.000e+00，NaN 结构不一致=0（容差 1e-09）
- **列 n_normal_sparse** — PASS — max|Δ|=0.000e+00，NaN 结构不一致=0（容差 1e-09）
- **列 n_anomaly_far** — PASS — max|Δ|=0.000e+00，NaN 结构不一致=0（容差 1e-09）
- **列 n_anomaly_compact_void** — PASS — max|Δ|=0.000e+00，NaN 结构不一致=0（容差 1e-09）
- **列 threshold** — PASS — max|Δ|=0.000e+00，NaN 结构不一致=0（容差 1e-09）
- **列 val_exceedance_count** — PASS — max|Δ|=0.000e+00，NaN 结构不一致=0（容差 1e-09）
- **列 val_exceedance_rate** — PASS — max|Δ|=0.000e+00，NaN 结构不一致=0（容差 1e-09）
- **列 tp** — PASS — max|Δ|=0.000e+00，NaN 结构不一致=0（容差 1e-09）
- **列 fp** — PASS — max|Δ|=0.000e+00，NaN 结构不一致=0（容差 1e-09）
- **列 tn** — PASS — max|Δ|=0.000e+00，NaN 结构不一致=0（容差 1e-09）
- **列 fn** — PASS — max|Δ|=0.000e+00，NaN 结构不一致=0（容差 1e-09）
- **列 precision** — PASS — max|Δ|=0.000e+00，NaN 结构不一致=0（容差 1e-09）
- **列 recall** — PASS — max|Δ|=0.000e+00，NaN 结构不一致=0（容差 1e-09）
- **列 f1** — PASS — max|Δ|=0.000e+00，NaN 结构不一致=0（容差 1e-09）
- **列 fpr_overall** — PASS — max|Δ|=0.000e+00，NaN 结构不一致=0（容差 1e-09）
- **列 fpr_dense** — PASS — max|Δ|=0.000e+00，NaN 结构不一致=0（容差 1e-09）
- **列 fpr_sparse** — PASS — max|Δ|=0.000e+00，NaN 结构不一致=0（容差 1e-09）
- **列 fp_dense** — PASS — max|Δ|=0.000e+00，NaN 结构不一致=0（容差 1e-09）
- **列 fp_sparse** — PASS — max|Δ|=0.000e+00，NaN 结构不一致=0（容差 1e-09）
- **列 recall_far** — PASS — max|Δ|=0.000e+00，NaN 结构不一致=0（容差 1e-09）
- **列 recall_compact_void** — PASS — max|Δ|=0.000e+00，NaN 结构不一致=0（容差 1e-09）
- **列 roc_auc** — PASS — max|Δ|=0.000e+00，NaN 结构不一致=0（容差 1e-09）
- **列 average_precision** — PASS — max|Δ|=0.000e+00，NaN 结构不一致=0（容差 1e-09）
- **列 n_inversion_pairs_equiv** — PASS — max|Δ|=0.000e+00，NaN 结构不一致=0（容差 1e-09）
- **列 val_mean_log_likelihood** — PASS — max|Δ|=0.000e+00，NaN 结构不一致=0（容差 1e-09）
- **全表** — PASS — 22 个数值列全部比对；最大列间偏差 0.000e+00（列 None）
- **param_name** — PASS — bandwidth / n_neighbors 标签一致
- **阈值 kde** — PASS — max|Δ|=0.000e+00
- **阈值 lof** — PASS — max|Δ|=0.000e+00
- **阈值合计** — PASS — 10 个阈值 max|Δ|=0.000e+00
- **指纹 train** — PASS — sha256 一致；统计量最大相对偏差=0.000e+00
- **指纹 validation** — PASS — sha256 一致；统计量最大相对偏差=0.000e+00
- **指纹 test** — PASS — sha256 一致；统计量最大相对偏差=0.000e+00
- **E0 峰结构** — PASS — 3 条带宽的峰数/峰高/谷填充率，最大 |Δ|=0.000e+00
