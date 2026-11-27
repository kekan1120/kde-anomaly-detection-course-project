"""v1.1 分层补充图（只出 3 张，不是论文主图）。

为什么单独一个脚本、而不是塞进 `run_experiment.py` 的出图流程：

* v1.0 的自检图与 v1.1 的分层图定位不同 —— 前者是「跑通了没有」，后者是「两类异常各自怎么样」；
* v1.1 属 post-hoc 分层补充，**不进论文主表主图**，所以图也要能单独重画、单独标注；
* 每张图标题都带「v1.1 分层补充（非主结果）」，防止被 D 误取成主结果。

用法::

    D:\\ml\\.venv\\Scripts\\python.exe 04_code\\make_v1_1_figures.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "src"))

from kdelof import calibration, dgp, protocol, scoring  # noqa: E402

ROOT = HERE.parent
MINE = ROOT / "05_results" / "main_v1_1_near"
V10 = ROOT / "05_results" / "main"
FIGDIR = MINE / "figures"
BANNER = "v1.1 分层补充（非主结果）"


def _plt():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # Windows 自带中文字体；Ubuntu 上会回退到 Noto/文泉驿（若有）
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Noto Sans CJK SC",
                                       "WenQuanYi Zen Hei", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["font.size"] = 9
    return plt


def fig_recall_by_type(df: pd.DataFrame) -> Path:
    """① 召回按 anomaly_type 分组：far vs compact_void，两检测器并排。"""
    plt = _plt()
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 3.9), dpi=150, sharey=True)
    for ax, det, label in zip(axes, ("kde", "lof"), ("KDE", "LOF")):
        sub = df[(df.detector == det) & (df.experiment != "E3_method_comparison")].sort_values("param_value")
        x = np.arange(len(sub))
        w = 0.38
        ax.bar(x - w / 2, sub.recall_far, w, label="far（远端圆环）", color="#2b6cb0")
        ax.bar(x + w / 2, sub.recall_compact_void, w, label="compact_void（空区紧凑簇）", color="#c53030")
        ax.set_xticks(x)
        ax.set_xticklabels([f"{v:g}" for v in sub.param_value])
        ax.set_xlabel("带宽 h" if det == "kde" else "邻居数 k")
        ax.set_ylim(0, 1.08)
        ax.grid(axis="y", alpha=0.25)
        ax.set_title(f"{label}：两类异常的召回（各 n=125）", fontsize=9)
        for xi, (rf, rc) in enumerate(zip(sub.recall_far, sub.recall_compact_void)):
            ax.text(xi - w / 2, rf + 0.02, f"{rf:.3f}", ha="center", fontsize=6.5)
            ax.text(xi + w / 2, rc + 0.02, f"{rc:.3f}", ha="center", fontsize=6.5)
    axes[0].set_ylabel("召回率 @ 验证集 99% 分位阈值")
    axes[0].legend(fontsize=7, loc="lower right")
    fig.suptitle(f"{BANNER} ① 召回按异常类型分层：far 召回随参数变化，compact_void 全部 125/125",
                 fontsize=9.5)
    fig.tight_layout()
    p = FIGDIR / "v1_1_fig1_recall_by_anomaly_type.png"
    fig.savefig(p)
    plt.close(fig)
    return p


def fig_score_distributions(cfg: dict) -> Path:
    """② 两检测器在 compact_void 与 far 上的分数分布（含各自阈值线）。"""
    plt = _plt()
    data = dgp.generate_all(cfg)
    train_X, val_X = data["train"].X, data["validation"].X
    test = data["test"]
    h = float(cfg["detectors"]["kde"]["default_bandwidth"])
    k = int(cfg["detectors"]["lof"]["default_n_neighbors"])

    fig, axes = plt.subplots(1, 2, figsize=(11.5, 3.9), dpi=150)
    for ax, det, param, label in ((axes[0], "kde", h, f"KDE  h*={h:g}"),
                                  (axes[1], "lof", k, f"LOF  k*={k}")):
        if det == "kde":
            raw_val = scoring.kde_log_density(train_X, val_X, param)
            raw_test = scoring.kde_log_density(train_X, test.X, param)
        else:
            raw_val = scoring.lof_neg_outlier_factor(train_X, val_X, param)
            raw_test = scoring.lof_neg_outlier_factor(train_X, test.X, param)
        s_val = scoring.to_anomaly_score(raw_val)
        s_test = scoring.to_anomaly_score(raw_test)
        thr = calibration.calibrate_threshold(s_val, 0.99, "inverted_cdf")

        far = s_test[test.anomaly_type == "far"]
        void = s_test[test.anomaly_type == "compact_void"]
        bins = np.linspace(min(s_test.min(), thr) - 0.5, s_test.max() * 1.02, 60)
        ax.hist(far, bins=bins, alpha=0.6, color="#2b6cb0", label=f"far（n={len(far)}）", density=True)
        ax.hist(void, bins=bins, alpha=0.6, color="#c53030", label=f"compact_void（n={len(void)}）", density=True)
        ax.axvline(thr, color="k", ls="--", lw=1.2, label=f"阈值={thr:.3f}")
        ax.set_yscale("log")
        ax.set_xlabel("异常分数 s = -score_samples（越大越异常）")
        ax.set_ylabel("密度（对数轴）")
        ax.set_title(f"{label}：两类异常分数分布", fontsize=9)
        ax.legend(fontsize=7)
        ax.grid(alpha=0.25)
    fig.suptitle(f"{BANNER} ② 分数分布：compact_void 整团落在阈值右侧（KDE 与 LOF 都是）", fontsize=9.5)
    fig.tight_layout()
    p = FIGDIR / "v1_1_fig2_score_distributions.png"
    fig.savefig(p)
    plt.close(fig)
    return p


def fig_v10_vs_v11(df11: pd.DataFrame) -> Path:
    """③ v1.0→v1.1 的 AUC 与错排配对数变化：说明「升是构成变了」。"""
    plt = _plt()
    d10 = pd.read_csv(V10 / "metrics.csv")
    keys = ["experiment", "detector", "param_value"]
    m = d10.merge(df11, on=keys, suffixes=("_10", "_11"))
    m = m[m.experiment != "E3_method_comparison"].copy()
    m["tick"] = m.detector.str.upper() + " " + m.param_value.map(lambda v: f"{v:g}")

    fig, axes = plt.subplots(1, 2, figsize=(12.2, 3.9), dpi=150)
    x = np.arange(len(m))
    w = 0.38
    axes[0].bar(x - w / 2, m.roc_auc_10, w, label="v1.0（250 far）", color="#718096")
    axes[0].bar(x + w / 2, m.roc_auc_11, w, label="v1.1（125 far + 125 near）", color="#2b6cb0")
    axes[0].set_ylim(min(m.roc_auc_10.min(), m.roc_auc_11.min()) - 0.0005, 1.0)
    axes[0].set_ylabel("测试 ROC-AUC")

    axes[1].bar(x - w / 2, m.n_inversion_pairs_equiv_10, w, label="v1.0", color="#718096")
    axes[1].bar(x + w / 2, m.n_inversion_pairs_equiv_11, w, label="v1.1", color="#2b6cb0")
    axes[1].set_ylabel("等价错排配对数（越少越好）")

    for ax in axes:
        ax.set_xticks(x)
        ax.set_xticklabels(m.tick, rotation=30, ha="right", fontsize=7)
        ax.grid(axis="y", alpha=0.25)
        ax.legend(fontsize=7)
    axes[0].set_title("(a) AUC 全部上升 —— 正样本构成变了，不是检测变好", fontsize=9)
    axes[1].set_title("(b) 错排配对数全部下降（near 点贡献 0 个错排）", fontsize=9)
    fig.suptitle(f"{BANNER} ③ v1.0→v1.1 的排序指标变化（分母恒为 250×1000=250k，未变；AUC 不可跨版本比较）",
                 fontsize=9.5)
    fig.tight_layout()
    p = FIGDIR / "v1_1_fig3_auc_inversion_v10_vs_v11.png"
    fig.savefig(p)
    plt.close(fig)
    return p


def main() -> int:
    FIGDIR.mkdir(parents=True, exist_ok=True)
    cfg = protocol.load_config()
    df = pd.read_csv(MINE / "metrics.csv")
    paths = [fig_recall_by_type(df), fig_score_distributions(cfg), fig_v10_vs_v11(df)]
    for p in paths:
        print(f"已写出 {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
