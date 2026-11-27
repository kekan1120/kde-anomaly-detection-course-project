"""全量参考实验：E0 一维带宽示意 / E1 KDE 敏感性 / E2 LOF 敏感性 / E3 方法对照.

产出（全部写入 ``05_results/ref_check/``）：

* ``metrics_ref.csv``            主结果，长表一格一个数值，D 直接读它画图，不允许手抄
* ``metrics_ref.json``           同上，便于程序读取
* ``data_fingerprints.json``     三个 split 的指纹与统计量，C 用来自查数据是否一致
* ``seed_registry.csv``          种子与数据流登记表（机器可读版，对应协议 §8）
* ``e0_demo1d_peaks.csv``        E0 的峰结构表
* ``run_log.txt``                环境、协议版本、阈值、运行时间
* ``figures/*.png``              自检用参考图（**非论文定稿图**，定稿由 D 从 CSV 重绘）

用法::

    .venv\\Scripts\\python.exe 04_code\\ref_check\\run_ref.py                 # 核心实验（repeat 0）
    .venv\\Scripts\\python.exe 04_code\\ref_check\\run_ref.py --multiseed     # 追加 P1 多种子拓展
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import reference_impl as ri  # noqa: E402

HERE = Path(__file__).resolve().parent
RESULTS = HERE.parent.parent / "05_results" / "ref_check"
FIGDIR = RESULTS / "figures"

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


# ======================================================================================
# 单个 (检测器, 参数) 配置的完整评估
# ======================================================================================
def run_configuration(
    cfg: dict,
    data: dict,
    detector: str,
    param_value: float,
    experiment: str,
    repeat: int = 0,
) -> dict:
    """一个 (检测器, 参数) 配置：train 拟合 → val 校准阈值 → test 一次性评估。"""
    train_X = data["train"].X
    val_X = data["validation"].X
    test = data["test"]

    if detector == "kde":
        raw_val = ri.kde_score_samples(train_X, val_X, param_value)
        raw_test = ri.kde_score_samples(train_X, test.X, param_value)
        val_ll = float(np.mean(raw_val))          # 验证集平均 log 密度，仅作诊断
        param_name = "bandwidth"
    elif detector == "lof":
        raw_val = ri.lof_score_samples(train_X, val_X, int(param_value))
        raw_test = ri.lof_score_samples(train_X, test.X, int(param_value))
        val_ll = float("nan")
        param_name = "n_neighbors"
    else:
        raise ValueError(detector)

    scores_val = ri.anomaly_score(raw_val)        # 统一为「越大越异常」
    scores_test = ri.anomaly_score(raw_test)

    threshold = ri.calibrate_threshold(scores_val, cfg)
    n_exc = int(np.sum(scores_val > threshold))

    m = ri.evaluate(test, scores_test, threshold, cfg)
    row = {
        "experiment": experiment,
        "detector": detector,
        "param_name": param_name,
        "param_value": float(param_value),
        "repeat": repeat,
        "n": m["n"], "n_normal": m["n_normal"], "n_anomaly": m["n_anomaly"],
        "prevalence": m["prevalence"],
        "n_normal_dense": m["n_normal_dense"], "n_normal_sparse": m["n_normal_sparse"],
        "n_anomaly_far": m.get("n_anomaly_far", 0),
        "n_anomaly_compact_void": m.get("n_anomaly_compact_void", 0),
        "threshold": threshold,
        "val_exceedance_count": n_exc,
        "val_exceedance_rate": n_exc / len(scores_val),
        "tp": m["tp"], "fp": m["fp"], "tn": m["tn"], "fn": m["fn"],
        "precision": m["precision"], "recall": m["recall"], "f1": m["f1"],
        "fpr_overall": m["fpr_overall"],
        "fpr_dense": m["fpr_dense"], "fpr_sparse": m["fpr_sparse"],
        "fp_dense": m["fp_dense"], "fp_sparse": m["fp_sparse"],
        "recall_far": m.get("recall_far", float("nan")),
        "recall_compact_void": m.get("recall_compact_void", float("nan")),
        "roc_auc": m["auc"],
        "average_precision": m["average_precision"],
        "n_inversion_pairs_equiv": m["n_inversion_pairs_equiv"],
        "val_mean_log_likelihood": val_ll,
    }
    return row, scores_test, threshold


# ======================================================================================
# E0 一维带宽示意
# ======================================================================================
def run_e0(cfg: dict) -> pd.DataFrame:
    x = ri.generate_1d_demo(cfg)
    grid = cfg["demo_1d"]["plot_grid"]
    xs = np.linspace(grid["x_min"], grid["x_max"], grid["n_points"])

    rows = []
    curves = {}
    for h in cfg["demo_1d"]["bandwidths"]:
        p = np.exp(ri.numpy_kde_log_density(x[:, None], xs[:, None], h))
        curves[h] = p
        info = ri.density_peaks(p, xs)
        rows.append({
            "bandwidth": h,
            "n_local_maxima": info["n_local_maxima"],
            "n_prominent_peaks": info["n_prominent_peaks"],
            "max_density": info["max_density"],
            "valley_fill_ratio": info["valley_fill_ratio"],
            "prominent_peak_positions": " | ".join(f"{t['x']:.3f}" for t in info["prominent_peaks"]),
            "prominent_peak_heights": " | ".join(f"{t['height']:.4f}" for t in info["prominent_peaks"]),
        })
    df = pd.DataFrame(rows)

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7.2, 3.8), dpi=150)
    ax.hist(x, bins=30, density=True, alpha=0.30, color="0.55",
            label=f"samples (n={len(x)})", edgecolor="none")
    for h, style in zip(cfg["demo_1d"]["bandwidths"], ["-", "--", "-."]):
        ax.plot(xs, curves[h], style, lw=1.8, label=f"KDE h={h:g}")
        for t in ri.density_peaks(curves[h], xs)["prominent_peaks"]:
            ax.plot([t["x"]], [t["height"]], "o", ms=4, mfc="none", mec="k")
    ax.set_xlabel("x")
    ax.set_ylabel("density  $\\hat{p}_h(x)$")
    ax.set_title("E0  Bandwidth illustration (1D bimodal sample)\n"
                 "gaussian kernel; open circles = prominent peaks (prominence >= 10% of max)")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(FIGDIR / "fig_e0_bandwidth_1d.png")
    plt.close(fig)
    return df


# ======================================================================================
# 数据总览图
# ======================================================================================
def plot_data_overview(cfg: dict, data: dict) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 3, figsize=(11, 3.6), dpi=150)
    lim = 7.6
    for ax, name in zip(axes, ("train", "validation", "test")):
        ds = data[name]
        normal = ds.y == 0
        ax.scatter(ds.X[normal & (ds.cluster_id == 0), 0], ds.X[normal & (ds.cluster_id == 0), 1],
                   s=5, c="#2b6cb0", alpha=0.55, label=f"normal / dense (n={int((normal & (ds.cluster_id == 0)).sum())})")
        ax.scatter(ds.X[normal & (ds.cluster_id == 1), 0], ds.X[normal & (ds.cluster_id == 1), 1],
                   s=5, c="#2f855a", alpha=0.55, label=f"normal / sparse (n={int((normal & (ds.cluster_id == 1)).sum())})")
        if (ds.y == 1).any():
            ax.scatter(ds.X[ds.y == 1, 0], ds.X[ds.y == 1, 1],
                       s=7, c="#c53030", alpha=0.7, marker="x",
                       label=f"anomaly / far (n={int((ds.y == 1).sum())})")
        ax.set_title(f"{name}   n={len(ds)}", fontsize=9)
        ax.set_xlim(-lim, lim)
        ax.set_ylim(-lim, lim)
        ax.set_aspect("equal")
        ax.grid(alpha=0.25)
        ax.legend(fontsize=6, loc="upper right", markerscale=1.6)
        ax.set_xlabel("x1", fontsize=8)
        ax.set_ylabel("x2", fontsize=8)
        ax.tick_params(labelsize=7)
    fig.suptitle("Synthetic DGP: dense N((-2,0),0.25I) + sparse N((2,0),1.0I); "
                 "far anomalies = uniform ring r in [5,7]", fontsize=8.5)
    fig.tight_layout()
    fig.savefig(FIGDIR / "fig_data_overview.png")
    plt.close(fig)


# ======================================================================================
# E1 / E2 敏感性曲线图
# ======================================================================================
def plot_sensitivity(df: pd.DataFrame, detector: str, param: str, fname: str, title: str) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    sub = df[(df.detector == detector) & (df.experiment == ("E1_kde_sensitivity" if detector == "kde"
                                                            else "E2_lof_sensitivity"))]
    sub = sub.sort_values("param_value")
    x = sub.param_value.to_numpy()

    fig, axes = plt.subplots(1, 3, figsize=(12, 3.5), dpi=150)

    axes[0].plot(x, sub.roc_auc, "o-", label="ROC-AUC")
    axes[0].plot(x, sub.average_precision, "s--", label="Average Precision")
    axes[0].set_ylabel("score (higher = better)")
    axes[0].set_title("(a) Threshold-free detection quality", fontsize=9)
    axes[0].legend(fontsize=8)
    axes[0].set_ylim(0, 1.02)

    axes[1].plot(x, sub.fpr_dense, "o-", label="dense cluster")
    axes[1].plot(x, sub.fpr_sparse, "s--", label="sparse cluster")
    axes[1].plot(x, sub.fpr_overall, "^:", label="overall")
    axes[1].axhline(0.01, color="k", lw=0.8, ls=":", label="target FPR = 1%")
    axes[1].set_ylabel("empirical FPR on test normals")
    axes[1].set_title("(b) False-positive rate by cluster", fontsize=9)
    axes[1].legend(fontsize=7)

    axes[2].plot(x, sub.recall, "o-", label="recall (FAR anomalies)")
    axes[2].plot(x, sub.precision, "s--", label="precision")
    axes[2].plot(x, sub.f1, "^:", label="F1")
    axes[2].set_ylabel("value at calibrated threshold")
    axes[2].set_title("(c) Operating point @ validation 99th pct", fontsize=9)
    axes[2].legend(fontsize=8)
    axes[2].set_ylim(0, 1.02)

    for ax in axes:
        ax.set_xlabel(param)
        ax.grid(alpha=0.25)
        ax.tick_params(labelsize=7)
    fig.suptitle(title, fontsize=9)
    fig.tight_layout()
    fig.savefig(FIGDIR / fname)
    plt.close(fig)


def plot_val_loglik(df: pd.DataFrame) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    sub = df[df.detector == "kde"].sort_values("param_value")
    fig, ax1 = plt.subplots(figsize=(6.4, 3.4), dpi=150)
    ax1.plot(sub.param_value, sub.val_mean_log_likelihood, "o-", color="#2b6cb0",
             label="validation mean log-likelihood (density-estimation objective)")
    ax1.set_xlabel("KDE bandwidth  h")
    ax1.set_ylabel("mean $\\log \\hat{p}_h(x)$ on validation", color="#2b6cb0")
    ax1.tick_params(axis="y", labelcolor="#2b6cb0")
    ax1.grid(alpha=0.25)

    ax2 = ax1.twinx()
    ax2.plot(sub.param_value, sub.roc_auc, "s--", color="#c53030", label="test ROC-AUC")
    ax2.set_ylabel("test ROC-AUC", color="#c53030")
    ax2.tick_params(axis="y", labelcolor="#c53030")

    h_ll = float(sub.loc[sub.val_mean_log_likelihood.idxmax(), "param_value"])
    h_auc = float(sub.loc[sub.roc_auc.idxmax(), "param_value"])
    ax1.axvline(h_ll, color="#2b6cb0", lw=0.8, ls=":")
    ax2.axvline(h_auc, color="#c53030", lw=0.8, ls=":")
    ax1.set_title(f"H4 diagnostic: argmax(loglik)=h={h_ll:g} vs argmax(AUC)=h={h_auc:g}\n"
                  "test-optimal h is POST-HOC description only, never used for selection",
                  fontsize=8.5)
    fig.tight_layout()
    fig.savefig(FIGDIR / "fig_h4_likelihood_vs_detection.png")
    plt.close(fig)


def plot_operating_point(cfg: dict, data: dict) -> None:
    """E3：默认参数下两检测器的测试分数分布与各自校准阈值。"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    h = float(cfg["detectors"]["kde"]["default_bandwidth"])
    k = int(cfg["detectors"]["lof"]["default_n_neighbors"])
    train_X = data["train"].X
    test = data["test"]

    fig, axes = plt.subplots(1, 2, figsize=(10, 3.4), dpi=150)
    for ax, det, param, name in (
        (axes[0], "kde", h, f"KDE  h*={h:g}"),
        (axes[1], "lof", k, f"LOF  k*={k}"),
    ):
        if det == "kde":
            raw_val = ri.kde_score_samples(train_X, data["validation"].X, param)
            raw_test = ri.kde_score_samples(train_X, test.X, param)
        else:
            raw_val = ri.lof_score_samples(train_X, data["validation"].X, param)
            raw_test = ri.lof_score_samples(train_X, test.X, param)
        sv = ri.anomaly_score(raw_val)
        st = ri.anomaly_score(raw_test)
        thr = ri.calibrate_threshold(sv, cfg)
        ax.hist(st[test.y == 0], bins=60, alpha=0.55, color="#2b6cb0", label="test normal", density=True)
        ax.hist(st[test.y == 1], bins=60, alpha=0.55, color="#c53030", label="test anomaly (far)", density=True)
        ax.axvline(thr, color="k", ls="--", lw=1.2, label=f"threshold={thr:.3f}")
        ax.set_yscale("log")
        ax.set_xlabel("anomaly score  s = -score_samples  (higher = more anomalous)")
        ax.set_ylabel("density (log scale)")
        ax.set_title(f"E3  {name}   threshold from validation 99th pct", fontsize=9)
        ax.legend(fontsize=7)
        ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(FIGDIR / "fig_e3_operating_point.png")
    plt.close(fig)


# ======================================================================================
# 种子登记表
# ======================================================================================
def write_seed_registry(cfg: dict) -> pd.DataFrame:
    specs = {
        "train.dense": ("train", "正常·密集簇", cfg["data"]["splits"]["train"]["n_dense"],
                        "X = mean + 0.5*standard_normal((n,2))"),
        "train.sparse": ("train", "正常·稀疏簇", cfg["data"]["splits"]["train"]["n_sparse"],
                         "X = mean + 1.0*standard_normal((n,2))"),
        "validation.dense": ("validation", "正常·密集簇", cfg["data"]["splits"]["validation"]["n_dense"],
                             "X = mean + 0.5*standard_normal((n,2))"),
        "validation.sparse": ("validation", "正常·稀疏簇", cfg["data"]["splits"]["validation"]["n_sparse"],
                              "X = mean + 1.0*standard_normal((n,2))"),
        "test.dense": ("test", "正常·密集簇", cfg["data"]["splits"]["test"]["n_dense"],
                       "X = mean + 0.5*standard_normal((n,2))"),
        "test.sparse": ("test", "正常·稀疏簇", cfg["data"]["splits"]["test"]["n_sparse"],
                        "X = mean + 1.0*standard_normal((n,2))"),
        "test.anomaly.far": ("test", "异常·远端", cfg["anomaly"]["types"]["far"]["n_test"],
                             "theta=uniform(0,2pi,n); r=uniform(5,7,n); X=[r*cos,r*sin]"),
        "test.anomaly.near": ("test", "异常·空区紧凑簇(默认关闭)",
                              cfg["anomaly"]["types"]["near"]["n_test"],
                              "X = [0.0,5.0] + 0.35*standard_normal((n,2))"),
        "demo1d.dense": ("demo_1d", "一维示意·密集分量",
                         cfg["demo_1d"]["components"]["dense"]["n"],
                         "X = -1.5 + 0.30*standard_normal(n)"),
        "demo1d.sparse": ("demo_1d", "一维示意·稀疏分量",
                          cfg["demo_1d"]["components"]["sparse"]["n"],
                          "X = 1.5 + 0.80*standard_normal(n)"),
    }
    rows = []
    for stream, (split, role, n, formula) in specs.items():
        rows.append({
            "data_stream": stream,
            "split": split,
            "role": role,
            "n": n,
            "seed_core_repeat0": cfg["seeds"]["streams"][stream],
            "generator": "numpy.random.Generator(PCG64(seed))",
            "sampling_formula": formula,
            "extension_repeat_ids": "1-10",
            "extension_seed_formula": "seed_core + 10000 * repeat",
            "consumes_randomness": "yes",
            "notes": "每个数据流独立 Generator，流之间不共享随机数消耗顺序",
        })
    df = pd.DataFrame(rows)
    df.to_csv(RESULTS / "seed_registry.csv", index=False, encoding="utf-8-sig")
    return df


# ======================================================================================
# 主流程
# ======================================================================================
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="KDE/LOF 参考实验（B 的对照基准）")
    ap.add_argument("--multiseed", action="store_true", help="追加 P1 多种子拓展 repeat 1..10")
    ap.add_argument("--no-figures", action="store_true", help="跳过绘图")
    args = ap.parse_args(argv)

    t0 = time.time()
    RESULTS.mkdir(parents=True, exist_ok=True)
    FIGDIR.mkdir(parents=True, exist_ok=True)

    cfg = ri.load_config()
    log = []
    log.append("=" * 78)
    log.append("KDE/LOF 参考实验运行日志（B 数据与实验设计负责人）")
    log.append("=" * 78)
    log.append(f"protocol_version : {cfg['protocol_version']}")
    log.append("顺序声明         : 协议与参数网格在运行本脚本之前已锁定（见 01_protocol_and_data_dictionary.md §1）")
    for k, v in ri.environment_info().items():
        log.append(f"{k:<17}: {v}")
    log.append("")

    data = ri.generate_all(cfg)

    # 指纹
    fp = {s: ri.fingerprint(ds) for s, ds in data.items()}
    (RESULTS / "data_fingerprints.json").write_text(
        json.dumps({
            "protocol_version": cfg["protocol_version"],
            "note": "sha256 为 X 的 float64 原始字节摘要；推荐跨实现判据用 stats 的相对容差 1e-12",
            "splits": fp,
            "demo_1d_n": int(cfg["demo_1d"]["total"]),
        }, ensure_ascii=False, indent=2), encoding="utf-8")

    log.append("数据规模：")
    for s, ds in data.items():
        sm = ds.summary
        log.append(f"  {s:<11} n={sm['n']:>5}  dense={sm['n_dense']:>4}  sparse={sm['n_sparse']:>4}  "
                   f"anomaly={sm['n_anomaly']:>4}  missing={sm['n_missing']}")
    log.append("")

    # ---- E0
    e0 = run_e0(cfg)
    e0.to_csv(RESULTS / "e0_demo1d_peaks.csv", index=False, encoding="utf-8-sig")
    log.append("E0 一维带宽示意（显著峰口径：prominence >= 10% 全局最大密度）")
    for _, r in e0.iterrows():
        log.append(f"  h={r['bandwidth']:<5g} 局部极大={int(r['n_local_maxima'])} "
                   f"显著峰={int(r['n_prominent_peaks'])} 峰高={r['max_density']:.4f} "
                   f"谷填充率={r['valley_fill_ratio']:.4f} 峰位=[{r['prominent_peak_positions']}]")
    log.append("")

    # ---- E1 / E2 / E3
    rows = []
    for detector, grid, experiment in (
        ("kde", cfg["detectors"]["kde"]["bandwidth_grid"], "E1_kde_sensitivity"),
        ("lof", cfg["detectors"]["lof"]["n_neighbors_grid"], "E2_lof_sensitivity"),
    ):
        for p in grid:
            row, _, _ = run_configuration(cfg, data, detector, p, experiment)
            rows.append(row)

    df_main = pd.DataFrame(rows)

    # E3 是 E1/E2 中默认参数那一行的并排对照 —— 不重复计算，保证数字完全相同
    e3 = df_main[
        ((df_main.detector == "kde") & (df_main.param_value == cfg["detectors"]["kde"]["default_bandwidth"]))
        | ((df_main.detector == "lof") & (df_main.param_value == cfg["detectors"]["lof"]["default_n_neighbors"]))
    ].copy()
    e3["experiment"] = "E3_method_comparison"
    df = pd.concat([df_main, e3], ignore_index=True)[METRIC_COLUMNS]

    log.append("E1 KDE 带宽敏感性（test 一次性评估；阈值来自 validation 99% 分位数）")
    log.append("   h     AUC      inv_pairs  AP       recall  precision  F1      "
               "FPR(all) FPR(dense) FPR(sparse) thr      valLL")
    for _, r in df_main[df_main.detector == "kde"].sort_values("param_value").iterrows():
        log.append(f"  {r.param_value:<5g} {r.roc_auc:.4f}  {r.n_inversion_pairs_equiv:8.1f}   "
                   f"{r.average_precision:.4f}  {r.recall:.4f}  {r.precision:.4f}    {r.f1:.4f}  "
                   f"{r.fpr_overall:.4f}  {r.fpr_dense:.4f}    {r.fpr_sparse:.4f}     "
                   f"{r.threshold:.4f}  {r.val_mean_log_likelihood:.4f}")
    log.append("")
    log.append("E2 LOF 邻居数敏感性")
    log.append("   k     AUC      inv_pairs  AP       recall  precision  F1      "
               "FPR(all) FPR(dense) FPR(sparse) thr")
    for _, r in df_main[df_main.detector == "lof"].sort_values("param_value").iterrows():
        log.append(f"  {r.param_value:<5g} {r.roc_auc:.4f}  {r.n_inversion_pairs_equiv:8.1f}   "
                   f"{r.average_precision:.4f}  {r.recall:.4f}  {r.precision:.4f}    {r.f1:.4f}  "
                   f"{r.fpr_overall:.4f}  {r.fpr_dense:.4f}    {r.fpr_sparse:.4f}     {r.threshold:.4f}")
    log.append("")
    log.append("E3 方法对照 @ 默认参数（h*=0.35, k*=20，均为运行前指定）")
    for _, r in e3.iterrows():
        log.append(f"  {r.detector:<4} AUC={r.roc_auc:.4f} inj_pairs={r.n_inversion_pairs_equiv:.1f} "
                   f"AP={r.average_precision:.4f} P={r.precision:.4f} R={r.recall:.4f} F1={r.f1:.4f} "
                   f"FPR={r.fpr_overall:.4f} FPR_dense={r.fpr_dense:.4f} FPR_sparse={r.fpr_sparse:.4f}")
    log.append("")

    df.to_csv(RESULTS / "metrics_ref.csv", index=False, encoding="utf-8-sig")
    (RESULTS / "metrics_ref.json").write_text(
        json.dumps(df.to_dict(orient="records"), ensure_ascii=False, indent=2), encoding="utf-8")

    write_seed_registry(cfg)

    # ---- 图
    if not args.no_figures:
        plot_data_overview(cfg, data)
        plot_sensitivity(df, "kde", "bandwidth  h", "fig_e1_kde_sensitivity.png",
                         "E1  KDE bandwidth sensitivity (6 bandwidths, one changed variable)")
        plot_sensitivity(df, "lof", "n_neighbors  k", "fig_e2_lof_sensitivity.png",
                         "E2  LOF n_neighbors sensitivity (4 values, one changed variable)")
        plot_val_loglik(df_main[df_main.detector == "kde"].copy())
        plot_operating_point(cfg, data)
        log.append(f"图已写入 {FIGDIR}")

    # ---- P1 多种子拓展
    if args.multiseed:
        log.append("")
        log.append("P1 多种子拓展（repeat 1..10，种子偏移 +10000*r）")
        rows_multi = []
        for repeat in cfg["seeds"]["extension_repeats"]["repeat_ids"]:
            d_r = ri.generate_all(cfg, repeat=repeat)
            for detector, grid in (("kde", cfg["detectors"]["kde"]["bandwidth_grid"]),
                                   ("lof", cfg["detectors"]["lof"]["n_neighbors_grid"])):
                for p in grid:
                    row, _, _ = run_configuration(cfg, d_r, detector, p,
                                                  "P1_multiseed", repeat=repeat)
                    rows_multi.append(row)
        dm = pd.DataFrame(rows_multi)[METRIC_COLUMNS]
        dm.to_csv(RESULTS / "metrics_ref_multiseed.csv", index=False, encoding="utf-8-sig")

        agg = (dm.groupby(["detector", "param_value"])
                 .agg(n_repeats=("repeat", "nunique"),
                      auc_mean=("roc_auc", "mean"), auc_std=("roc_auc", "std"),
                      ap_mean=("average_precision", "mean"), ap_std=("average_precision", "std"),
                      fpr_sparse_mean=("fpr_sparse", "mean"), fpr_sparse_std=("fpr_sparse", "std"),
                      fpr_dense_mean=("fpr_dense", "mean"), fpr_dense_std=("fpr_dense", "std"),
                      recall_mean=("recall", "mean"))
                 .reset_index())
        agg.to_csv(RESULTS / "metrics_ref_multiseed_summary.csv", index=False, encoding="utf-8-sig")
        for _, r in agg.iterrows():
            log.append(f"  {r.detector:<4} param={r.param_value:<5g} "
                       f"AUC={r.auc_mean:.4f}±{r.auc_std:.4f} "
                       f"AP={r.ap_mean:.4f}±{r.ap_std:.4f} "
                       f"FPR_sparse={r.fpr_sparse_mean:.4f}±{r.fpr_sparse_std:.4f}")

    log.append("")
    log.append(f"总运行时间: {time.time() - t0:.1f} s")
    (RESULTS / "run_log.txt").write_text("\n".join(log) + "\n", encoding="utf-8")
    print("\n".join(log))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
