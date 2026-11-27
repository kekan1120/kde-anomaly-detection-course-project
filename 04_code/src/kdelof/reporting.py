"""结果落盘：CSV / JSON / 运行日志 / 自检图。

纪律
----
* 所有数字只从内存中的 DataFrame 写盘，**不允许**手抄。
* 运行日志必须在结果文件生成前写入 ``protocol_version``（协议 §10 L7）。
* ``figures/`` 里的是 **自检图**，不是论文定稿图：坐标轴为英文、没有样本量与参数标注。
  D 必须从 CSV 重绘正式图（协议 §7 / HANDOFF §3.5）。
"""

from __future__ import annotations

import json
import platform
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd


def environment_info() -> dict:
    """记录实际跑出结果的环境。换机器/换版本必须在此留痕（HANDOFF §2.2）。"""
    import matplotlib
    import scipy
    import sklearn

    return {
        "python": sys.version.split()[0],
        "executable": sys.executable,
        "platform": platform.platform(),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "scikit_learn": sklearn.__version__,
        "matplotlib": matplotlib.__version__,
        "pandas": pd.__version__,
    }


def config_info(cfg: dict) -> dict:
    """运行日志用的配置溯源信息：文件路径 + 字节级 sha256。

    sha256 现场计算（不写死），这样任何人拿到 run_log 都能确认结果对应哪一份配置字节。
    """
    import hashlib

    from . import protocol

    path = protocol.CONFIG_PATH
    return {
        "config_file": str(path),
        "config_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def write_seed_registry(cfg: dict, out_dir: Path) -> pd.DataFrame:
    """种子与数据流登记表（机器可读版，对应协议 §8）。"""
    streams = {
        "train.dense": ("train", "正常·密集簇", "X = mean_dense + 0.5*standard_normal((n,2))"),
        "train.sparse": ("train", "正常·稀疏簇", "X = mean_sparse + 1.0*standard_normal((n,2))"),
        "validation.dense": ("validation", "正常·密集簇", "X = mean_dense + 0.5*standard_normal((n,2))"),
        "validation.sparse": ("validation", "正常·稀疏簇", "X = mean_sparse + 1.0*standard_normal((n,2))"),
        "test.dense": ("test", "正常·密集簇", "X = mean_dense + 0.5*standard_normal((n,2))"),
        "test.sparse": ("test", "正常·稀疏簇", "X = mean_sparse + 1.0*standard_normal((n,2))"),
        "test.anomaly.far": ("test", "异常·远端圆环", "theta=uniform(0,2pi,n); r=uniform(5,7,n); X=[r*cos,r*sin]"),
        "test.anomaly.near": ("test", "异常·空区紧凑簇", "X=[0,5]+0.35*standard_normal((n,2))"),
        "demo1d.dense": ("demo_1d", "一维示意·密集分量", "x = -1.5 + 0.30*standard_normal(n)"),
        "demo1d.sparse": ("demo_1d", "一维示意·稀疏分量", "x = 1.5 + 0.80*standard_normal(n)"),
    }
    split_n = {
        "train": cfg["data"]["splits"]["train"],
        "validation": cfg["data"]["splits"]["validation"],
        "test": cfg["data"]["splits"]["test"],
        "demo_1d": None,
    }
    rows = []
    for stream, (split, role, formula) in streams.items():
        # n_draw：v1.1 起 far 按「先抽 n_draw 组 (theta,r)，再取前 n_test 行」抽样，
        # 随机数消耗量由 n_draw 决定；缺省时等于 n_test（即 v1.0 行为）。
        n_draw, n_draw_note = None, "n/a"
        if split == "demo_1d":
            which = stream.rsplit(".", 1)[-1]
            n = int(cfg["demo_1d"]["components"][which]["n"])
        elif split == "test" and stream.startswith("test.anomaly"):
            key = "far" if stream.endswith("far") else "near"
            spec = cfg["anomaly"]["types"][key]
            n = int(spec["n_test"])
            if "n_draw" in spec:
                n_draw, n_draw_note = int(spec["n_draw"]), "config.anomaly.types.far.n_draw"
            else:
                n_draw, n_draw_note = n, "缺省（= n_test）"
            if key == "near":
                role = "异常·空区紧凑簇" + ("（启用）" if spec["enabled"] else "（未启用）")
        else:
            which = stream.rsplit(".", 1)[-1]
            n = int(split_n[split][f"n_{which}"])
        if n_draw is None:
            n_draw, n_draw_note = n, "n/a（该流不按 n_draw 抽样）"
        rows.append({
            "data_stream": stream,
            "split": split,
            "role": role,
            "n": n,
            "n_draw": n_draw,
            "n_draw_note": n_draw_note,
            "seed_core_repeat0": int(cfg["seeds"]["streams"][stream]),
            "generator": "numpy.random.Generator(numpy.random.PCG64(seed))",
            "sampling_formula": formula,
            "extension_repeat_ids": "1-10",
            "extension_seed_formula": "seed_core + 10000 * repeat",
            "consumes_randomness": "yes",
            "notes": "每个数据流独立 Generator，流之间不共享随机数消耗顺序",
        })
    df = pd.DataFrame(rows)
    df.to_csv(out_dir / "seed_registry.csv", index=False, encoding="utf-8-sig")
    return df


def write_fingerprints(cfg: dict, data: dict, out_dir: Path) -> dict:
    """三个划分的指纹与统计量；C 自查与 B 基准对账都读它。"""
    payload = {
        "protocol_version": cfg["protocol_version"],
        "written_by": "C 实现与复现负责人",
        "note": "sha256 为 X 的 float64 原始字节摘要（同环境逐位判据）；跨环境比对用 stats，相对容差 1e-12",
        "splits": {name: ds.fingerprint() for name, ds in data.items()},
        "demo_1d_n": int(cfg["demo_1d"]["total"]),
    }
    (out_dir / "data_fingerprints.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


# --------------------------------------------------------------------------------------
# 自检图
# --------------------------------------------------------------------------------------


def _plt():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams["font.size"] = 9
    return plt


def plot_data_overview(data: dict, out_dir: Path) -> None:
    plt = _plt()
    fig, axes = plt.subplots(1, 3, figsize=(11.5, 3.6), dpi=150)
    lim = 7.8
    for ax, name in zip(axes, ("train", "validation", "test")):
        ds = data[name]
        for cid, color, label in ((0, "#2b6cb0", "normal/dense"), (1, "#2f855a", "normal/sparse")):
            m = (ds.y == 0) & (ds.cluster_id == cid)
            ax.scatter(ds.X[m, 0], ds.X[m, 1], s=5, c=color, alpha=0.55,
                       label=f"{label} n={int(m.sum())}")
        if (ds.y == 1).any():
            m = ds.y == 1
            ax.scatter(ds.X[m, 0], ds.X[m, 1], s=7, c="#c53030", marker="x", alpha=0.7,
                       label=f"anomaly/far n={int(m.sum())}")
        ax.set_title(f"{name}  n={len(ds)}")
        ax.set_xlim(-lim, lim)
        ax.set_ylim(-lim, lim)
        ax.set_aspect("equal")
        ax.grid(alpha=0.25)
        ax.legend(fontsize=6, loc="upper right", markerscale=1.6)
        ax.set_xlabel("x1")
        ax.set_ylabel("x2")
    fig.suptitle("SELF-CHECK (not final): synthetic DGP, dense N((-2,0),0.25I) + sparse N((2,0),1.0I); far = ring r in [5,7]")
    fig.tight_layout()
    fig.savefig(out_dir / "fig_data_overview.png")
    plt.close(fig)


def plot_e0(cfg: dict, x: np.ndarray, curves: dict, out_dir: Path) -> None:
    plt = _plt()
    fig, ax = plt.subplots(figsize=(7.2, 3.8), dpi=150)
    ax.hist(x, bins=30, density=True, alpha=0.30, color="0.55", edgecolor="none",
            label=f"samples n={len(x)}")
    for (h, p), style in zip(curves.items(), ("-", "--", "-.")):
        ax.plot(np.linspace(cfg["demo_1d"]["plot_grid"]["x_min"],
                            cfg["demo_1d"]["plot_grid"]["x_max"],
                            int(cfg["demo_1d"]["plot_grid"]["n_points"])), p, style, lw=1.8, label=f"h={h:g}")
    ax.set_xlabel("x")
    ax.set_ylabel(r"density $\hat{p}_h(x)$")
    ax.set_title("SELF-CHECK (not final): E0 1D bandwidth illustration, gaussian kernel")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(out_dir / "fig_e0_bandwidth_1d.png")
    plt.close(fig)


def plot_sensitivity(df_main: pd.DataFrame, detector: str, out_dir: Path) -> None:
    plt = _plt()
    sub = df_main[df_main.detector == detector].sort_values("param_value")
    x = sub.param_value.to_numpy()
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.4), dpi=150)

    axes[0].plot(x, sub.roc_auc, "o-", label="ROC-AUC")
    axes[0].plot(x, sub.average_precision, "s--", label="AP (step-wise)")
    axes[0].set_ylim(0, 1.02)
    axes[0].legend(fontsize=7)
    axes[0].set_title("(a) threshold-free")

    axes[1].plot(x, sub.fpr_dense, "o-", label="dense cluster")
    axes[1].plot(x, sub.fpr_sparse, "s--", label="sparse cluster")
    axes[1].plot(x, sub.fpr_overall, "^:", label="overall")
    axes[1].axhline(0.01, color="k", lw=0.8, ls=":", label="target 1%")
    axes[1].legend(fontsize=7)
    axes[1].set_title("(b) FPR by cluster")

    axes[2].plot(x, sub.recall, "o-", label="recall")
    axes[2].plot(x, sub.precision, "s--", label="precision")
    axes[2].plot(x, sub.f1, "^:", label="F1")
    axes[2].set_ylim(0, 1.02)
    axes[2].legend(fontsize=7)
    axes[2].set_title("(c) operating point")

    for ax in axes:
        ax.set_xlabel("bandwidth h" if detector == "kde" else "n_neighbors k")
        ax.grid(alpha=0.25)
    fig.suptitle(f"SELF-CHECK (not final): {detector.upper()} sensitivity, threshold = validation 99th pct, test n=1250")
    fig.tight_layout()
    fig.savefig(out_dir / f"fig_{detector}_sensitivity.png")
    plt.close(fig)


def plot_likelihood_vs_auc(df_main: pd.DataFrame, out_dir: Path) -> dict:
    """H4 诊断图：验证集平均对数似然的 argmax vs 测试 AUC 的 argmax。

    后者是**事后描述**，不能用于选参数 —— 图标题里必须写出来。
    """
    plt = _plt()
    sub = df_main[df_main.detector == "kde"].sort_values("param_value")
    h_ll = float(sub.loc[sub.val_mean_log_likelihood.idxmax(), "param_value"])
    h_auc = float(sub.loc[sub.roc_auc.idxmax(), "param_value"])

    fig, ax1 = plt.subplots(figsize=(6.6, 3.5), dpi=150)
    ax1.plot(sub.param_value, sub.val_mean_log_likelihood, "o-", color="#2b6cb0",
             label="validation mean log-likelihood")
    ax1.set_xlabel("KDE bandwidth h")
    ax1.set_ylabel("mean log p_h(x) on validation", color="#2b6cb0")
    ax1.tick_params(axis="y", labelcolor="#2b6cb0")
    ax1.grid(alpha=0.25)
    ax2 = ax1.twinx()
    ax2.plot(sub.param_value, sub.roc_auc, "s--", color="#c53030", label="test ROC-AUC")
    ax2.set_ylabel("test ROC-AUC", color="#c53030")
    ax2.tick_params(axis="y", labelcolor="#c53030")
    ax1.axvline(h_ll, color="#2b6cb0", lw=0.8, ls=":")
    ax2.axvline(h_auc, color="#c53030", lw=0.8, ls=":")
    ax1.set_title(f"SELF-CHECK (not final): argmax loglik h={h_ll:g} vs argmax AUC h={h_auc:g}\n"
                  "test-optimal h is POST-HOC only, never used for selection")
    fig.tight_layout()
    fig.savefig(out_dir / "fig_h4_likelihood_vs_detection.png")
    plt.close(fig)
    return {"argmax_h_val_loglik": h_ll, "argmax_h_test_auc": h_auc}


def plot_operating_point(cfg: dict, data: dict, out_dir: Path) -> None:
    """E3：默认参数下两个检测器的测试分数分布与各自阈值。"""
    from . import calibration, scoring

    plt = _plt()
    train_X = data["train"].X
    test = data["test"]
    h = float(cfg["detectors"]["kde"]["default_bandwidth"])
    k = int(cfg["detectors"]["lof"]["default_n_neighbors"])

    fig, axes = plt.subplots(1, 2, figsize=(10, 3.4), dpi=150)
    for ax, det, param, name in ((axes[0], "kde", h, f"KDE h*={h:g}"),
                                 (axes[1], "lof", k, f"LOF k*={k}")):
        if det == "kde":
            sv = scoring.to_anomaly_score(scoring.kde_log_density(train_X, data["validation"].X, param))
            st = scoring.to_anomaly_score(scoring.kde_log_density(train_X, test.X, param))
        else:
            sv = scoring.to_anomaly_score(scoring.lof_neg_outlier_factor(train_X, data["validation"].X, param))
            st = scoring.to_anomaly_score(scoring.lof_neg_outlier_factor(train_X, test.X, param))
        thr = calibration.calibrate_threshold(sv, cfg["threshold"]["quantile"], cfg["threshold"]["numpy_method"])
        ax.hist(st[test.y == 0], bins=60, alpha=0.55, color="#2b6cb0", density=True, label="test normal")
        ax.hist(st[test.y == 1], bins=60, alpha=0.55, color="#c53030", density=True, label="test anomaly (far)")
        ax.axvline(thr, color="k", ls="--", lw=1.2, label=f"threshold={thr:.3f}")
        ax.set_yscale("log")
        ax.set_xlabel("anomaly score s = -score_samples (higher = more anomalous)")
        ax.set_ylabel("density (log)")
        ax.set_title(f"SELF-CHECK (not final): {name} @ validation 99th pct")
        ax.legend(fontsize=7)
        ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(out_dir / "fig_e3_operating_point.png")
    plt.close(fig)


def now_stamp() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S%z")