# -*- coding: utf-8 -*-
"""
KDE vs LOF 异常检测对照实验（第 1 题 · 实验分支）
实现骨架由 AI 生成，须由 C（沈伊镄）人工核验并复现。

v3 变更：
- 三类异常：远端(distal) / 边界(boundary) / 空区紧凑簇(compact)
- 补充操作点：主操作点 99% 分位(≈1% FPR)，补充 95% 分位(≈5% FPR)，只加操作点不改设计
- 三张图：参数-AUROC、分簇/分类得分分布、KDE vs LOF 得分对比

依赖：numpy, pandas, scikit-learn, matplotlib
运行：python 04_code/ai_draft/run_experiment.py
输出：05_results/ai_draft/metrics.csv、score_details.csv、figures/*.png、run_log.txt

关键约定：
- 异常分数统一「越大越异常」。
  KDE : s = -KernelDensity.score_samples（log-density 取负）
  LOF : s = -LocalOutlierFactor(novelty=True).score_samples（返回 -LOF，取负）
- 阈值仅用正常验证集分数分位数；测试集只在流程锁定后评估。
"""
import json
import os
import platform
import sys
import time
import numpy as np
import pandas as pd
from sklearn.neighbors import KernelDensity, LocalOutlierFactor
from sklearn.metrics import (roc_auc_score, average_precision_score,
                             precision_score, recall_score, f1_score,
                             confusion_matrix)

HERE = os.path.dirname(os.path.abspath(__file__))          # 04_code/ai_draft
ROOT = os.path.dirname(os.path.dirname(HERE))               # 项目根
RESULTS = os.path.join(ROOT, "05_results", "ai_draft")
FIGURES = os.path.join(RESULTS, "figures")
os.makedirs(FIGURES, exist_ok=True)

with open(os.path.join(HERE, "config.json"), encoding="utf-8") as f:
    CFG = json.load(f)

Q_MAIN = CFG["threshold"]["quantile"]          # 0.99 -> ~1% FPR
Q_SUPP = CFG["threshold"].get("supp_quantile", 0.95)  # 0.95 -> ~5% FPR

# ---------------------------------------------------------------------------
# 数据生成
# ---------------------------------------------------------------------------

def make_two_clusters(n_per_cluster, seed):
    rng = np.random.default_rng(seed)
    d = CFG["data"]
    dense = rng.multivariate_normal(d["dense_center"], d["dense_cov"] * np.eye(2), n_per_cluster)
    sparse = rng.multivariate_normal(d["sparse_center"], d["sparse_cov"] * np.eye(2), n_per_cluster)
    X = np.vstack([dense, sparse])
    cluster = np.array([0] * n_per_cluster + [1] * n_per_cluster, dtype=int)
    return X, cluster


def make_anomalies(n_anom, seed):
    """三类异常：0=distal, 1=boundary, 2=compact。"""
    rng = np.random.default_rng(seed)
    spec = CFG["data"]["anomalies"]

    def sample_box(box, n):
        xs = rng.uniform(box["x"][0], box["x"][1], n)
        ys = rng.uniform(box["y"][0], box["y"][1], n)
        return np.column_stack([xs, ys])

    n_distal = n_anom // 3
    n_boundary = n_anom // 3
    n_compact = n_anom - n_distal - n_boundary
    Xd = sample_box(spec["distal"], n_distal)
    Xb = sample_box(spec["boundary"], n_boundary)
    cc = spec["compact"]
    Xc = rng.multivariate_normal(cc["center"], cc["std"] * np.eye(2), n_compact)
    X = np.vstack([Xd, Xb, Xc])
    a_type = np.array([0] * n_distal + [1] * n_boundary + [2] * n_compact, dtype=int)
    return X, a_type


def make_data(train_seed, val_seed, test_seed):
    d = CFG["data"]
    X_train, _ = make_two_clusters(d["n_per_cluster_train"], train_seed)
    X_val, _ = make_two_clusters(d["n_per_cluster_val"], val_seed)
    X_test_n, c_test_n = make_two_clusters(d["n_per_cluster_test"], test_seed)

    n_normal = len(X_test_n)
    ratio = d["test_anomaly_ratio"]
    n_anom = int(round(n_normal * ratio / (1 - ratio)))
    X_test_a, a_test_a = make_anomalies(n_anom, test_seed + 1000)

    X_test = np.vstack([X_test_n, X_test_a])
    y_test = np.concatenate([np.zeros(n_normal), np.ones(n_anom)]).astype(int)
    c_test = np.concatenate([c_test_n, -np.ones(n_anom, dtype=int)])
    a_test = np.concatenate([-np.ones(n_normal, dtype=int), a_test_a])
    return X_train, X_val, X_test, y_test, c_test, a_test


# ---------------------------------------------------------------------------
# 分数与指标
# ---------------------------------------------------------------------------

def kde_scores(X_train, X_eval, h):
    mdl = KernelDensity(kernel="gaussian", bandwidth=h).fit(X_train)
    return -mdl.score_samples(X_eval)


def lof_scores(X_train, X_eval, k):
    mdl = LocalOutlierFactor(n_neighbors=k, novelty=True).fit(X_train)
    return -mdl.score_samples(X_eval)


def smoke_check(X_train):
    far = np.array([[100.0, 100.0]])
    assert kde_scores(X_train, far, 0.5)[0] > kde_scores(X_train, X_train[:1], 0.5)[0], "KDE 分数方向错误"
    assert lof_scores(X_train, far, 10)[0] > lof_scores(X_train, X_train[:1], 10)[0], "LOF 分数方向错误"
    print("[smoke] 分数方向通过：远端点得分高于正常训练点")


def evaluate(scores, y_test, threshold=None):
    out = {"auroc": roc_auc_score(y_test, scores),
           "ap": average_precision_score(y_test, scores)}
    if threshold is not None:
        pred = (scores > threshold).astype(int)
        tn, fp, fn, tp = confusion_matrix(y_test, pred).ravel()
        out.update({
            "precision": precision_score(y_test, pred),
            "recall": recall_score(y_test, pred),
            "f1": f1_score(y_test, pred),
            "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp),
            "fpr_normal": float(fp / (fp + tn)),
        })
    return out


def cluster_fpr(scores, y_test, c_test, threshold):
    pred = (scores > threshold).astype(int)
    res = {}
    for cid, name in [(0, "dense"), (1, "sparse")]:
        mask = (c_test == cid)
        res[f"fpr_{name}"] = float(pred[mask].mean()) if mask.any() else np.nan
    return res


def type_recall(scores, y_test, a_test, threshold):
    pred = (scores > threshold).astype(int)
    res = {}
    for t, name in [(0, "distal"), (1, "boundary"), (2, "compact")]:
        mask = (a_test == t)
        res[f"recall_{name}"] = float(pred[mask].mean()) if mask.any() else np.nan
    return res


def _suffix(d, suf):
    return {f"{k}{suf}": v for k, v in d.items()}


def run_detector(name, X_train, X_val, X_test, y_test, c_test, a_test):
    grid = CFG["params"]["kde_bandwidths"] if name == "kde" else CFG["params"]["lof_neighbors"]
    rows = []
    for p in grid:
        if name == "kde":
            s_val = kde_scores(X_train, X_val, p)
            s_test = kde_scores(X_train, X_test, p)
        else:
            s_val = lof_scores(X_train, X_val, p)
            s_test = lof_scores(X_train, X_test, p)
        thr_main = float(np.quantile(s_val, Q_MAIN))
        thr_supp = float(np.quantile(s_val, Q_SUPP))
        row = {"detector": name, "param": p, "threshold": thr_main}
        row.update(evaluate(s_test, y_test, thr_main))
        row.update(cluster_fpr(s_test, y_test, c_test, thr_main))
        row.update(type_recall(s_test, y_test, a_test, thr_main))
        row["threshold_q95"] = thr_supp
        row.update(_suffix(evaluate(s_test, y_test, thr_supp), "_q95"))
        row.update(_suffix(cluster_fpr(s_test, y_test, c_test, thr_supp), "_q95"))
        row.update(_suffix(type_recall(s_test, y_test, a_test, thr_supp), "_q95"))
        for t, tname in [(0, "distal"), (1, "boundary"), (2, "compact")]:
            m = (a_test == t)
            row[f"score_{tname}"] = float(s_test[m].mean()) if m.any() else np.nan
        rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# 得分明细（供分簇/分类得分分布图）
# ---------------------------------------------------------------------------

def make_score_details():
    s = CFG["seeds"]
    X_train, _, X_test, y_test, c_test, a_test = make_data(s["train"], s["validation"], s["test"])
    frames = []
    for det, p in [("kde", 0.5), ("lof", 35)]:
        sc = kde_scores(X_train, X_test, p) if det == "kde" else lof_scores(X_train, X_test, p)
        group = []
        for i in range(len(X_test)):
            if y_test[i] == 0:
                group.append("dense" if c_test[i] == 0 else "sparse")
            else:
                group.append(["distal", "boundary", "compact"][a_test[i]])
        frames.append(pd.DataFrame({"detector": det, "group": group, "score": sc}))
    return pd.concat(frames, ignore_index=True)


# ---------------------------------------------------------------------------
# 1D 带宽示意
# ---------------------------------------------------------------------------

def plot_1d_bandwidth():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    rng = np.random.default_rng(CFG["seeds"]["train"])
    X = np.concatenate([rng.normal(-2, 0.5, 200), rng.normal(2, 0.5, 200)]).reshape(-1, 1)
    grid = np.linspace(-5, 5, 500).reshape(-1, 1)
    fig, ax = plt.subplots(figsize=(8, 4))
    for h in CFG["params"]["id_bandwidths"]:
        dens = np.exp(KernelDensity(kernel="gaussian", bandwidth=h).fit(X).score_samples(grid))
        ax.plot(grid.ravel(), dens, label=f"h={h}")
    ax.hist(X.ravel(), bins=40, density=True, alpha=0.25, color="gray")
    ax.set_xlabel("x"); ax.set_ylabel("density"); ax.set_title("1D bandwidth demo (two peaks)")
    ax.legend(); fig.savefig(os.path.join(FIGURES, "1d_bandwidth.png"), dpi=150); plt.close(fig)


# ---------------------------------------------------------------------------
# 图 1：参数 - AUROC 曲线（含多种子误差棒）
# ---------------------------------------------------------------------------

def plot_param_auroc(df):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), sharey=True)
    specs = [("kde", "bandwidth h", axes[0]), ("lof", "neighbours k", axes[1])]
    for det, xlabel, ax in specs:
        sub = df[df.detector == det]
        g = sub.groupby("param")["auroc"].agg(["mean", "std"]).reset_index()
        ax.errorbar(g["param"], g["mean"], yerr=g["std"].fillna(0), marker="o", capsize=3, label=det.upper())
        ax.set_xlabel(xlabel); ax.set_ylabel("AUROC"); ax.set_title(f"{det.upper()} sensitivity")
        ax.grid(alpha=0.3)
    fig.suptitle("AUROC vs parameter (mean +- std over seeds)")
    fig.tight_layout()
    fig.savefig(os.path.join(FIGURES, "param_auroc.png"), dpi=150); plt.close(fig)


# ---------------------------------------------------------------------------
# 图 2：分簇/分类得分分布（KDE 与 LOF 各一）
# ---------------------------------------------------------------------------

def plot_score_distribution(details):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    groups = ["dense", "sparse", "distal", "boundary", "compact"]
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), sharey=True)
    for ax, det in zip(axes, ["kde", "lof"]):
        sub = details[details.detector == det]
        data = [sub[sub.group == g]["score"].values for g in groups]
        ax.boxplot(data, tick_labels=groups, showfliers=False)
        ax.set_title(f"{det.upper()} score by group")
        ax.set_ylabel("anomaly score (higher = more anomalous)")
        ax.grid(alpha=0.3, axis="y")
        ax.tick_params(axis="x", rotation=20)
    fig.suptitle("Score distribution: normal clusters vs anomaly types")
    fig.tight_layout()
    fig.savefig(os.path.join(FIGURES, "score_distribution.png"), dpi=150); plt.close(fig)


# ---------------------------------------------------------------------------
# 图 3：KDE vs LOF 各类异常得分对比
# ---------------------------------------------------------------------------

def plot_kde_vs_lof(df):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    types = ["distal", "boundary", "compact"]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    width = 0.35
    x = np.arange(len(types))
    for i, det in enumerate(["kde", "lof"]):
        sub = df[df.detector == det]
        vals = [sub[f"score_{t}"].mean() for t in types]
        errs = [sub[f"score_{t}"].std() for t in types]
        ax.bar(x + (i - 0.5) * width, vals, width, yerr=errs, capsize=3, label=det.upper())
    ax.set_xticks(x); ax.set_xticklabels(types)
    ax.set_ylabel("mean anomaly score (higher = more anomalous)")
    ax.set_title("KDE vs LOF: mean score by anomaly type")
    ax.legend(); ax.grid(alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(os.path.join(FIGURES, "kde_vs_lof_scores.png"), dpi=150); plt.close(fig)


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def run_one(train_seed, val_seed, test_seed):
    X_train, X_val, X_test, y_test, c_test, a_test = make_data(train_seed, val_seed, test_seed)
    smoke_check(X_train)
    rows = []
    rows += run_detector("kde", X_train, X_val, X_test, y_test, c_test, a_test)
    rows += run_detector("lof", X_train, X_val, X_test, y_test, c_test, a_test)
    for r in rows:
        r["seed"] = f"{train_seed}/{val_seed}/{test_seed}"
    return rows


def main():
    t0 = time.time()
    s = CFG["seeds"]
    all_rows = run_one(s["train"], s["validation"], s["test"])
    for rep in s["repeat_list"]:
        all_rows += run_one(rep, rep + 100, rep + 200)

    df = pd.DataFrame(all_rows)
    df.to_csv(os.path.join(RESULTS, "metrics.csv"), index=False)

    details = make_score_details()
    details.to_csv(os.path.join(RESULTS, "score_details.csv"), index=False)

    import sklearn
    with open(os.path.join(RESULTS, "run_log.txt"), "w", encoding="utf-8") as f:
        f.write(f"python={sys.version.split()[0]}\n")
        f.write(f"numpy={np.__version__}\n")
        f.write(f"pandas={pd.__version__}\n")
        f.write(f"scikit-learn={sklearn.__version__}\n")
        f.write(f"platform={platform.platform()}\n")
        f.write(f"config={json.dumps(CFG, ensure_ascii=False)}\n")
        f.write(f"elapsed_s={time.time() - t0:.1f}\n")

    plot_1d_bandwidth()
    plot_param_auroc(df)
    plot_score_distribution(details)
    plot_kde_vs_lof(df)

    print(f"[done] {len(df)} 行结果 -> {os.path.join(RESULTS, 'metrics.csv')}")
    print("主操作点(99%)与补充操作点(95%)对比 — compact 召回：")
    g = df.groupby("detector").agg(
        rc_1pct=("recall_compact", "mean"), rc_5pct=("recall_compact_q95", "mean"),
        rb_1pct=("recall_boundary", "mean"), rb_5pct=("recall_boundary_q95", "mean"),
        auroc=("auroc", "mean"), fs=("fpr_sparse", "mean")).round(3)
    print(g.to_string())


if __name__ == "__main__":
    main()
