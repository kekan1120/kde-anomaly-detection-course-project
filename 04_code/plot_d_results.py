"""Rebuild D's core figures from the frozen v1.0 machine-readable outputs.

Usage (from repository root):
    python 04_code/plot_d_results.py

The script writes to 05_results/main/figures_d so official C figures remain untouched.
图内文字统一为中文（与论文正文/图注语言一致）；数学符号保留 LaTeX 风格标记。
"""
from pathlib import Path
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# 中文字体（Windows 常见字体；找不到时 matplotlib 回退并告警）
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "SimSun", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "05_results" / "main"
OUT = RESULTS / "figures_d"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    metrics = pd.read_csv(RESULTS / "metrics.csv")
    config = json.loads((ROOT / "04_code" / "config_ref.json").read_text(encoding="utf-8"))

    kde = metrics[metrics["experiment"] == "E1_kde_sensitivity"].sort_values("param_value")
    lof = metrics[metrics["experiment"] == "E2_lof_sensitivity"].sort_values("param_value")
    e3 = metrics[metrics["experiment"] == "E3_method_comparison"]

    demo = config["demo_1d"]
    samples = []
    for component in ("dense", "sparse"):
        spec = demo["components"][component]
        seed = config["seeds"]["streams"][spec["seed_key"]]
        rng = np.random.Generator(np.random.PCG64(seed))
        samples.append(spec["mean"] + spec["sd"] * rng.standard_normal(spec["n"]))
    sample = np.concatenate(samples).reshape(-1, 1)
    grid = np.linspace(demo["plot_grid"]["x_min"], demo["plot_grid"]["x_max"], demo["plot_grid"]["n_points"])
    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    for h in demo["bandwidths"]:
        # Direct 1D Gaussian KDE is equivalent to sklearn KernelDensity here and
        # keeps this plotting-only script usable before the project venv is active.
        z = (grid[:, None] - sample[:, 0][None, :]) / h
        density = np.exp(-0.5 * z**2).mean(axis=1) / (h * np.sqrt(2 * np.pi))
        ax.plot(grid, density, label=f"h={h:g}")
    ax.set(xlabel="x", ylabel="估计密度", title="一维 KDE 带宽示意（固定样本）")
    ax.grid(alpha=0.25)
    ax.legend(title="带宽")
    fig.tight_layout()
    fig.savefig(OUT / "d_e0_bandwidth_1d.png", dpi=180)
    plt.close(fig)

    # Reconstruct the v1.0 test geometry from its registered seeds and fixed
    # generation rules. The current config keeps the same normal data streams;
    # the far ring uses n_draw=250 so all v1.0 far points are reproducible.
    data = config["data"]
    test_parts = []
    for name in ("dense", "sparse"):
        spec = data["clusters"][name]
        seed = config["seeds"]["streams"][f"test.{name}"]
        rng = np.random.Generator(np.random.PCG64(seed))
        count = data["splits"]["test"][f"n_{name}"]
        test_parts.append((name, spec["mean"] + spec["fixed_scale"] * rng.standard_normal((count, 2))))
    far = config["anomaly"]["types"]["far"]
    rng = np.random.Generator(np.random.PCG64(config["seeds"]["streams"]["test.anomaly.far"]))
    theta = rng.uniform(0.0, 2 * np.pi, far.get("n_draw", far["n_test"]))
    radius = rng.uniform(far["r_min"], far["r_max"], far.get("n_draw", far["n_test"]))
    far_n = int(e3["n_anomaly_far"].iloc[0])
    far_points = np.column_stack((radius * np.cos(theta), radius * np.sin(theta)))[:far_n]
    fig, ax = plt.subplots(figsize=(6.4, 5.2))
    styles = {"dense": ("tab:blue", "密集簇正常样本"), "sparse": ("tab:green", "稀疏簇正常样本")}
    for name, points in test_parts:
        color, label = styles[name]
        ax.scatter(points[:, 0], points[:, 1], s=12, alpha=0.55, color=color, label=label)
    ax.scatter(far_points[:, 0], far_points[:, 1], s=16, alpha=0.75, color="tab:red", marker="x", label="远端异常")
    ax.set(xlabel="$x_1$", ylabel="$x_2$", title="测试数据总览（v1.0 仅远端异常）")
    ax.set_aspect("equal", adjustable="box")
    ax.grid(alpha=0.2)
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT / "d_data_overview.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    ax.plot(kde["param_value"], kde["roc_auc"], "o-", label="KDE ROC-AUC")
    ax.plot(kde["param_value"], kde["f1"], "s--", label="KDE F1")
    ax.set(xlabel="带宽 h", ylabel="指标值", title="KDE 带宽敏感性（v1.0 仅远端异常）")
    ax.grid(alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT / "d_kde_sensitivity.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    ax.plot(lof["param_value"], lof["roc_auc"], "o-", label="LOF ROC-AUC")
    ax.plot(lof["param_value"], lof["f1"], "s--", label="LOF F1")
    ax.set(xlabel="邻居数 k", ylabel="指标值", title="LOF 邻居数敏感性（v1.0 仅远端异常）")
    ax.grid(alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT / "d_lof_sensitivity.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    labels = [f"{d}\n{p:g}" for d, p in zip(e3["detector"], e3["param_value"])]
    ax.bar(labels, e3["fpr_dense"], label="密集簇误报率")
    ax.bar(labels, e3["fpr_sparse"], bottom=e3["fpr_dense"], label="稀疏簇误报率")
    ax.set(ylabel="正常测试误报率", title="默认操作点（分簇误报率堆叠）")
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT / "d_default_cluster_fpr.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.0, 4.0))
    positions = np.arange(len(e3))
    width = 0.19
    for offset, metric, label in zip((-1.5, -0.5, 0.5, 1.5), ("roc_auc", "average_precision", "recall", "f1"), ("ROC-AUC", "AP", "召回", "F1")):
        ax.bar(positions + offset * width, e3[metric], width, label=label)
    ax.set_xticks(positions, [f"{d}, {p:g}" for d, p in zip(e3["detector"], e3["param_value"])])
    ax.set(ylabel="指标值", title="默认操作点指标对照（仅远端异常测试集）")
    ax.legend(ncols=2)
    ax.grid(axis="y", alpha=0.2)
    fig.tight_layout()
    fig.savefig(OUT / "d_default_metrics_comparison.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    ax.plot(kde["param_value"], kde["val_mean_log_likelihood"], "o-", label="验证集平均对数似然")
    ax2 = ax.twinx()
    ax2.plot(kde["param_value"], kde["roc_auc"], "s--", color="tab:red", label="测试集 ROC-AUC")
    ax.set(xlabel="带宽 h", ylabel="验证集平均对数似然")
    ax2.set_ylabel("测试集 ROC-AUC")
    ax.set_title("似然目标与检测目标的带宽对照")
    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines1 + lines2, labels1 + labels2, loc="lower right")
    fig.tight_layout()
    fig.savefig(OUT / "d_h4_likelihood_vs_auc.png", dpi=180)
    plt.close(fig)

    print(f"Wrote {len(list(OUT.glob('d_*.png')))} figures to {OUT}")


if __name__ == "__main__":
    main()
