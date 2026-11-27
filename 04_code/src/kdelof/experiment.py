"""实验编排 —— 协议 §7 的控制变量表与 §7.2 的拓展。

四条主实验
----------
* **E0** 一维带宽示意：同一组样本、同一网格，只改带宽 ``h ∈ {0.08, 0.30, 0.90}``。
* **E1** KDE 敏感性：只改 ``h ∈ {0.10, 0.20, 0.35, 0.50, 0.80, 1.20}``。
* **E2** LOF 敏感性：只改 ``k ∈ {10, 20, 35, 50}``。
* **E3** 方法对照：默认操作点 ``h*=0.35, k*=20``，直接把 E1/E2 的对应行改标签，
  **不重算**——重算就有机会「不小心」出现两份略有差异的数字。

每个配置的数据流固定为：``train`` 拟合 -> ``validation`` 校准阈值 -> ``test`` 一次性评估。
"""

from __future__ import annotations

import copy
from typing import Any

import numpy as np
import pandas as pd

from . import calibration, dgp, metrics, peaks, scoring

#: 结果表列序。与 B 的基准表同名同序，方便 D 的绘图脚本与审计脚本直接复用、也方便逐列对账。
METRIC_COLUMNS = [
    "experiment", "detector", "param_name", "param_value", "repeat",
    "n", "n_normal", "n_anomaly", "prevalence",
    "n_normal_dense", "n_normal_sparse", "n_anomaly_far", "n_anomaly_compact_void",
    "threshold", "val_exceedance_count", "val_exceedance_rate",
    "tp", "fp", "tn", "fn", "precision", "recall", "f1",
    "fpr_overall", "fpr_dense", "fpr_sparse",
    "fp_dense", "fp_sparse",
    "recall_far", "recall_compact_void",
    "roc_auc", "average_precision", "n_inversion_pairs_equiv", "val_mean_log_likelihood",
]


def _raw_scores(cfg: dict, train_X: np.ndarray, X: np.ndarray, detector: str, param: float) -> np.ndarray:
    """原始 ``score_samples``（越大越正常）。论文里的「密度诊断量」也来自这里。"""
    if detector == "kde":
        return scoring.kde_log_density(train_X, X, float(param))
    if detector == "lof":
        return scoring.lof_neg_outlier_factor(train_X, X, int(param))
    raise ValueError(f"未知检测器: {detector}")


def run_configuration(cfg: dict, data: dict, detector: str, param: float,
                      experiment: str, repeat: int = 0) -> dict:
    """跑一个 (检测器, 参数) 配置，返回结果表的一行。"""
    train_X = data["train"].X
    val_X = data["validation"].X
    test = data["test"]

    raw_val = _raw_scores(cfg, train_X, val_X, detector, param)
    raw_test = _raw_scores(cfg, train_X, test.X, detector, param)

    # 验证集平均对数似然：衡量的是**密度估计目标**，只作 H4 的诊断量，不参与任何选择。
    val_ll = float(np.mean(raw_val)) if detector == "kde" else float("nan")

    scores_val = scoring.to_anomaly_score(raw_val)
    scores_test = scoring.to_anomaly_score(raw_test)

    threshold = calibration.calibrate_threshold(scores_val, cfg["threshold"]["quantile"],
                                                cfg["threshold"]["numpy_method"])
    n_exc = calibration.exceedance(scores_val, threshold)

    m = metrics.evaluate(test, scores_test, threshold, cfg)
    return {
        "experiment": experiment,
        "detector": detector,
        "param_name": "bandwidth" if detector == "kde" else "n_neighbors",
        "param_value": float(param),
        "repeat": repeat,
        "n": m["n"], "n_normal": m["n_normal"], "n_anomaly": m["n_anomaly"],
        "prevalence": m["prevalence"],
        "n_normal_dense": m["n_normal_dense"], "n_normal_sparse": m["n_normal_sparse"],
        "n_anomaly_far": m["n_anomaly_far"],
        "n_anomaly_compact_void": m["n_anomaly_compact_void"],
        "threshold": threshold,
        "val_exceedance_count": n_exc,
        "val_exceedance_rate": n_exc / len(scores_val),
        "tp": m["tp"], "fp": m["fp"], "tn": m["tn"], "fn": m["fn"],
        "precision": m["precision"], "recall": m["recall"], "f1": m["f1"],
        "fpr_overall": m["fpr_overall"],
        "fpr_dense": m["fpr_dense"], "fpr_sparse": m["fpr_sparse"],
        "fp_dense": m["fp_dense"], "fp_sparse": m["fp_sparse"],
        "recall_far": m["recall_far"],
        "recall_compact_void": m["recall_compact_void"],
        "roc_auc": m["roc_auc"],
        "average_precision": m["average_precision"],
        "n_inversion_pairs_equiv": m["n_inversion_pairs_equiv"],
        "val_mean_log_likelihood": val_ll,
    }


# --------------------------------------------------------------------------------------
# E0
# --------------------------------------------------------------------------------------


def run_e0(cfg: dict) -> tuple[pd.DataFrame, dict[float, np.ndarray]]:
    """一维带宽示意：三条曲线 + 峰结构表。"""
    x = dgp.generate_demo_1d(cfg)
    grid = cfg["demo_1d"]["plot_grid"]
    xs = np.linspace(float(grid["x_min"]), float(grid["x_max"]), int(grid["n_points"]))

    rows, curves = [], {}
    for h in cfg["demo_1d"]["bandwidths"]:
        logp = scoring.scratch_kde_log_density(x[:, None], xs[:, None], float(h))
        p = np.exp(logp)
        curves[float(h)] = p
        info = peaks.describe_curve(p, xs)
        rows.append({
            "bandwidth": float(h),
            "n_local_maxima": info["n_local_maxima"],
            "n_prominent_peaks": info["n_prominent_peaks"],
            "max_density": info["max_density"],
            "valley_fill_ratio": info["valley_fill_ratio"],
            "prominent_peak_positions": " | ".join(f"{t['x']:.3f}" for t in info["prominent_peaks"]),
            "prominent_peak_heights": " | ".join(f"{t['height']:.4f}" for t in info["prominent_peaks"]),
            "prominence_frac_rule": peaks.PROMINENCE_FRAC,
        })
    df = pd.DataFrame(rows)
    return df, curves


# --------------------------------------------------------------------------------------
# E1 / E2 / E3
# --------------------------------------------------------------------------------------


def run_core(cfg: dict, data: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """E1 + E2（E3 由两者默认参数行派生）。"""
    rows = []
    for detector, grid, experiment in (
        ("kde", cfg["detectors"]["kde"]["bandwidth_grid"], "E1_kde_sensitivity"),
        ("lof", cfg["detectors"]["lof"]["n_neighbors_grid"], "E2_lof_sensitivity"),
    ):
        for p in grid:
            rows.append(run_configuration(cfg, data, detector, p, experiment))
    df_main = pd.DataFrame(rows)[METRIC_COLUMNS]

    # E3 = E1/E2 中默认参数那一行的并排对照。派生而不重算：两份数字不可能不一致。
    h_star = float(cfg["detectors"]["kde"]["default_bandwidth"])
    k_star = int(cfg["detectors"]["lof"]["default_n_neighbors"])
    mask = (((df_main.detector == "kde") & (df_main.param_value == h_star))
            | ((df_main.detector == "lof") & (df_main.param_value == k_star)))
    e3 = df_main[mask].copy()
    e3["experiment"] = "E3_method_comparison"
    df_all = pd.concat([df_main, e3], ignore_index=True)[METRIC_COLUMNS]
    return df_main, df_all


def run_multiseed(cfg: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """P1 多种子：repeat 1..10（种子列表在看测试结果前已公布）。"""
    rows = []
    for repeat in cfg["seeds"]["extension_repeats"]["repeat_ids"]:
        data_r = dgp.generate_all(cfg, repeat=int(repeat))
        for detector, grid in (
            ("kde", cfg["detectors"]["kde"]["bandwidth_grid"]),
            ("lof", cfg["detectors"]["lof"]["n_neighbors_grid"]),
        ):
            for p in grid:
                rows.append(run_configuration(cfg, data_r, detector, p, "P1_multiseed", repeat=int(repeat)))
    df = pd.DataFrame(rows)[METRIC_COLUMNS]

    summary = (df.groupby(["detector", "param_value"])
                 .agg(n_repeats=("repeat", "nunique"),
                      auc_mean=("roc_auc", "mean"), auc_std=("roc_auc", "std"),
                      ap_mean=("average_precision", "mean"), ap_std=("average_precision", "std"),
                      fpr_sparse_mean=("fpr_sparse", "mean"), fpr_sparse_std=("fpr_sparse", "std"),
                      fpr_dense_mean=("fpr_dense", "mean"), fpr_dense_std=("fpr_dense", "std"),
                      recall_mean=("recall", "mean"))
                 .reset_index())
    return df, summary


# --------------------------------------------------------------------------------------
# 冒烟测试：小规模跑通全流程（不产出正式结果）
# --------------------------------------------------------------------------------------


def smoke_config(cfg: dict, scale: int = 10) -> dict:
    """把样本量按比例缩小的一份**内存副本**，仅用于「先跑少量样本再跑全量」的冒烟测试。

    v1.1 起异常类型不止一个，因此 **near.n_test / far.n_test / far.n_draw 必须按同一比例
    缩放**，否则合计与 `test.n_anomaly` 对不上：旧实现把 `far.n_test` 直接写成 `n_anomaly`，
    只在「只有 far 一种类型」时成立，一旦 near 启用，`build_anomalies` 的合计断言必炸。

    它不写回配置、不产出正式结果，因此不违反「网格与样本量在跑实验前锁定」。
    但阈值超阈数会随 n 变化，所以冒烟只检查流程与形状，不检查超阈数 = 10。
    """
    c = copy.deepcopy(cfg)
    for name in ("train", "validation", "test"):
        s = c["data"]["splits"][name]
        s["n_dense"] //= scale
        s["n_sparse"] //= scale
        s["n_anomaly"] //= scale
        s["total"] = s["n_dense"] + s["n_sparse"] + s["n_anomaly"]

    types = c["anomaly"]["types"]
    enabled = [k for k in ("far", "near") if types[k]["enabled"]]
    target = int(c["data"]["splits"]["test"]["n_anomaly"])
    if enabled:
        alloc = {k: max(1, int(types[k]["n_test"]) // scale) for k in enabled}
        # 整除的零头全部记到第一个类型，保证合计恰好等于 target
        alloc[enabled[0]] += target - sum(alloc.values())
        if alloc[enabled[0]] < 1:
            raise ValueError(f"缩比后 {enabled[0]}.n_test={alloc[enabled[0]]} < 1，请减小 scale")
        if sum(alloc.values()) != target:
            raise ValueError(f"缩比后异常合计 {sum(alloc.values())} != {target}")
        for k in enabled:
            types[k]["n_test"] = int(alloc[k])
            if "n_draw" in types[k]:
                types[k]["n_draw"] = max(int(alloc[k]), int(types[k]["n_draw"]) // scale)
                if types[k]["n_draw"] < types[k]["n_test"]:
                    raise ValueError(f"缩比后 {k}.n_draw < n_test，请减小 scale")
    return c