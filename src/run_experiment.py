# -*- coding: utf-8 -*-
"""
KDE vs LOF 异常检测对照实验（第 1 题 · 实验分支）
实现骨架由 AI 生成，须由 C（沈伊镄）人工核验并复现。

v2 修正：异常改为「远端 + 边界」两类（y 收窄到正常范围），并分类型报告召回，
        避免 v1 中「异常点 y 偏移过大 → 全部 AUROC=1.0、无区分度」的问题。

依赖：numpy, pandas, scikit-learn, matplotlib
运行：python run_experiment.py
输出：results/metrics.csv、results/figures/*.png、results/run_log.txt

关键约定（与协议一致）：
- 异常分数统一「越大越异常」。
  KDE : s = -KernelDensity.score_samples（score_samples 返回 log-density）
  LOF : s = -LocalOutlierFactor(novelty=True).score_samples（score_samples 返回 -LOF）
- 阈值仅用正常验证集分数的 99% 分位数；测试集只在流程锁定后评估一次。
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

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RESULTS = os.path.join(ROOT, "results")
FIGURES = os.path.join(RESULTS, "figures")
os.makedirs(FIGURES, exist_ok=True)

with open(os.path.join(HERE, "config.json"), encoding="utf-8") as f:
    CFG = json.load(f)

# ---------------------------------------------------------------------------
# 数据生成
# ---------------------------------------------------------------------------

def make_two_clusters(n_per_cluster, seed):
    """两个密度不同的正常二维高斯簇。返回 (X, cluster_id)：0=密集, 1=稀疏。"""
    rng = np.random.default_rng(seed)
    d = CFG["data"]
    dense = rng.multivariate_normal(d["dense_center"], d["dense_cov"] * np.eye(2), n_per_cluster)
    sparse = rng.multivariate_normal(d["sparse_center"], d["sparse_cov"] * np.eye(2), n_per_cluster)
    X = np.vstack([dense, sparse])
    cluster = np.array([0] * n_per_cluster + [1] * n_per_cluster, dtype=int)
    return X, cluster


def make_anomalies(n_anom, seed):
    """生成远端(distal)与边界(boundary)两类异常。返回 (X, a_type)：0=distal, 1=boundary。"""
    rng = np.random.default_rng(seed)
    spec = CFG["data"]["anomalies"]

    def sample(box, n):
        xs = rng.uniform(box["x"][0], box["x"][1], n)
        ys = rng.uniform(box["y"][0], box["y"][1], n)
        return np.column_stack([xs, ys])

    n_distal = n_anom // 2
    n_boundary = n_anom - n_distal
    Xd = sample(spec["distal"], n_distal)
    Xb = sample(spec["boundary"], n_boundary)
    X = np.vstack([Xd, Xb])
    a_type = np.array([0] * n_distal + [1] * n_boundary, dtype=int)
    return X, a_type


def make_data(train_seed, val_seed, test_seed):
    """生成 train/val/test。返回 (X_train, X_val, X_test, y_test, c_test, a_test)。"""
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
    a_test = np.concatenate([-np.ones(n_normal, dtype=int), a_test_a])  # -1=正常
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
    s_kde_norm = kde_scores(X_train, X_train[:1], 0.5)[0]
    s_kde_far = kde_scores(X_train, far, 0.5)[0]
    assert s_kde_far > s_kde_norm, "KDE 分数方向错误"
    s_lof_norm = lof_scores(X_train, X_train[:1], 10)[0]
    s_lof_far = lof_scores(X_train, far, 10)[0]
    assert s_lof_far > s_lof_norm, "LOF 分数方向错误"
    print("[smoke] 分数方向通过：远端点得分高于正常训练点")


def evaluate(scores, y_test, threshold=None):
    out = {
        "auroc": roc_auc_score(y_test, scores),
        "ap": average_precision_score(y_test, scores),
    }
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
    for t, name in [(0, "distal"), (1, "boundary")]:
        mask = (a_test == t)
        res[f"recall_{name}"] = float(pred[mask].mean()) if mask.any() else np.nan
    return res


def run_detector(name, X_train, X_val, X_test, y_test, c_test, a_test):
    q = CFG["threshold"]["quantile"]
    grid = CFG["params"]["kde_bandwidths"] if name == "kde" else CFG["params"]["lof_neighbors"]
    rows = []
    for p in grid:
        if name == "kde":
            s_val = kde_scores(X_train, X_val, p)
            s_test = kde_scores(X_train, X_test, p)
        else:
            s_val = lof_scores(X_train, X_val, p)
            s_test = lof_scores(X_train, X_test, p)
        thr = float(np.quantile(s_val, q))
        row = {"detector": name, "param": p, "threshold": thr}
        row.update(evaluate(s_test, y_test, thr))
        row.update(cluster_fpr(s_test, y_test, c_test, thr))
        row.update(type_recall(s_test, y_test, a_test, thr))
        rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# 1D 带宽示意
# ---------------------------------------------------------------------------

def id_bandwidth_demo():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    rng = np.random.default_rng(CFG["seeds"]["train"])
    X = np.concatenate([rng.normal(-2, 0.5, 200), rng.normal(2, 0.5, 200)]).reshape(-1, 1)
    grid = np.linspace(-5, 5, 500).reshape(-1, 1)
    fig, ax = plt.subplots(figsize=(8, 4))
    for h in CFG["params"]["id_bandwidths"]:
        mdl = KernelDensity(kernel="gaussian", bandwidth=h).fit(X)
        dens = np.exp(mdl.score_samples(grid))
        ax.plot(grid.ravel(), dens, label=f"h={h}")
    ax.hist(X.ravel(), bins=40, density=True, alpha=0.25, color="gray")
    ax.set_xlabel("x"); ax.set_ylabel("density")
    ax.set_title("1D bandwidth demo (two peaks)")
    ax.legend()
    fig.savefig(os.path.join(FIGURES, "1d_bandwidth.png"), dpi=150)
    plt.close(fig)


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

    # P1 拓展：多种子重复
    for rep in s["repeat_list"]:
        all_rows += run_one(rep, rep + 100, rep + 200)

    df = pd.DataFrame(all_rows)
    df.to_csv(os.path.join(RESULTS, "metrics.csv"), index=False)

    import sklearn
    with open(os.path.join(RESULTS, "run_log.txt"), "w", encoding="utf-8") as f:
        f.write(f"python={sys.version.split()[0]}\n")
        f.write(f"numpy={np.__version__}\n")
        f.write(f"pandas={pd.__version__}\n")
        f.write(f"scikit-learn={sklearn.__version__}\n")
        f.write(f"platform={platform.platform()}\n")
        f.write(f"config={json.dumps(CFG, ensure_ascii=False)}\n")
        f.write(f"elapsed_s={time.time() - t0:.1f}\n")

    id_bandwidth_demo()
    print(f"[done] {len(df)} 行结果 -> {os.path.join(RESULTS, 'metrics.csv')}")
    cols = ["detector", "param", "auroc", "ap", "f1",
            "recall_distal", "recall_boundary", "fpr_dense", "fpr_sparse"]
    print(df[cols].to_string(index=False))


if __name__ == "__main__":
    main()
