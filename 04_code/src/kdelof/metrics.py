"""指标计算 —— 协议 §6。

约定
----
* ``y_true``：0 = 正常，1 = 异常。
* ``scores``：异常分数，**越大越异常**。
* 阈值处指标：混淆矩阵 ``[[TN, FP], [FN, TP]]``，precision / recall / F1 / 总 FPR。
* **分簇误报率必须与总 FPR 并列报告**：总 FPR 会把「稀疏正常簇被系统性误报」这一现象
  藏起来（总 1.1% 分解后是密集簇 0/500、稀疏簇 11/500）。
* AP 是 **step-wise** 定义（sklearn ``average_precision_score`` 的阶梯求和），不是 PR
  曲线的梯形积分；报告时必须注明，并同时给出测试集异常比例。

实现策略
--------
本模块默认**手算**（公式直接展开，可逐项核验），并在 ``run_checks.py`` 里与 sklearn 的
``roc_auc_score`` / ``average_precision_score`` / ``confusion_matrix`` 交叉验证。手算与库
计算应当一致到 1e-12：这是「指标口径没搞错」的证据，而不是信任库的声明。
"""

from __future__ import annotations

import numpy as np

from . import calibration


def confusion(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    """混淆矩阵与阈值处指标。分母为 0 时返回 ``nan``（协议 §6.3）。"""
    y_true = np.asarray(y_true).astype(np.int64)
    y_pred = np.asarray(y_pred).astype(np.int64)
    tp = int(np.sum((y_true == 1) & (y_pred == 1)))
    fp = int(np.sum((y_true == 0) & (y_pred == 1)))
    tn = int(np.sum((y_true == 0) & (y_pred == 0)))
    fn = int(np.sum((y_true == 1) & (y_pred == 0)))
    precision = tp / (tp + fp) if (tp + fp) else float("nan")
    recall = tp / (tp + fn) if (tp + fn) else float("nan")
    if np.isfinite(precision) and np.isfinite(recall) and (precision + recall) > 0:
        f1 = 2.0 * precision * recall / (precision + recall)
    else:
        f1 = float("nan")
    fpr = fp / (fp + tn) if (fp + tn) else float("nan")
    return {"tp": tp, "fp": fp, "tn": tn, "fn": fn,
            "precision": precision, "recall": recall, "f1": f1, "fpr_overall": fpr}


def roc_auc(y_true: np.ndarray, scores: np.ndarray) -> float:
    """Mann-Whitney U 形式的 ROC-AUC，并列分数取平均秩。

    ``AUC = U / (n_pos * n_neg)``，其中 ``U = sum(rank_pos) - n_pos(n_pos+1)/2``。
    与 ``sklearn.metrics.roc_auc_score`` 数学等价；这里手算一份是为了能被独立核验。
    """
    from scipy.stats import rankdata

    y_true = np.asarray(y_true).astype(np.int64)
    s = np.asarray(scores, dtype=np.float64)
    pos = y_true == 1
    n_pos, n_neg = int(pos.sum()), int((~pos).sum())
    if n_pos == 0 or n_neg == 0:
        return float("nan")
    ranks = rankdata(s, method="average")
    u = ranks[pos].sum() - n_pos * (n_pos + 1) / 2.0
    return float(u / (n_pos * n_neg))


def average_precision(y_true: np.ndarray, scores: np.ndarray) -> float:
    """阶梯式 AP：``AP = sum_k (R_k - R_{k-1}) * P_k``，在每一个不同的分数值处切一刀。

    注意这不是 PR 曲线的梯形积分（那是 PR-AUC(trapezoid)），两者数值不同。
    """
    y = np.asarray(y_true).astype(np.int64)
    s = np.asarray(scores, dtype=np.float64)
    n_pos = int((y == 1).sum())
    if n_pos == 0:
        return float("nan")

    order = np.argsort(-s, kind="stable")
    s_sorted, y_sorted = s[order], y[order]

    # 只在「分数发生变化」的位置取一个代表点（并列分数不能拆开）
    cut = np.r_[np.where(np.diff(s_sorted) != 0)[0], len(s_sorted) - 1]
    tp = np.cumsum(y_sorted)[cut].astype(np.float64)
    precision = tp / (cut + 1)
    recall = tp / n_pos
    d_recall = np.diff(np.r_[0.0, recall])
    return float(np.sum(d_recall * precision))


def evaluate(split, scores: np.ndarray, threshold: float, cfg: dict) -> dict:
    """在测试集上计算全部约定指标。

    这是**唯一**接触测试标签的函数：标签只在这里出现，不回流到任何参数、阈值或网格。
    """
    scores = np.asarray(scores, dtype=np.float64)
    y_pred = calibration.predict(scores, threshold)
    out = confusion(split.y, y_pred)

    normal = split.y == 0
    out["n"] = len(split)
    out["n_normal"] = int(normal.sum())
    out["n_anomaly"] = int((split.y == 1).sum())
    out["prevalence"] = out["n_anomaly"] / out["n"]

    # ---- 分簇误报率（H2 的唯一直接证据）
    for name, cid in (("dense", 0), ("sparse", 1)):
        mask = normal & (split.cluster_id == cid)
        n_c = int(mask.sum())
        fp_c = int(np.sum(y_pred[mask] == 1))
        out[f"n_normal_{name}"] = n_c
        out[f"fp_{name}"] = fp_c
        out[f"fpr_{name}"] = fp_c / n_c if n_c else float("nan")

    # ---- 分异常类型计数与召回（启用多种类型时才有意义）
    for key in ("far", "near"):
        type_id = str(cfg["anomaly"]["types"][key]["type_id"])
        mask = split.anomaly_type == type_id
        n_t = int(mask.sum())
        out[f"n_anomaly_{type_id}"] = n_t
        out[f"recall_{type_id}"] = (float(np.sum(y_pred[mask] == 1)) / n_t) if n_t else float("nan")

    auc = roc_auc(split.y, scores)
    out["roc_auc"] = auc
    out["average_precision"] = average_precision(split.y, scores)
    # 等价错排配对数：把 AUC 换算成「被错排的 (正常, 异常) 配对个数」。
    # AUC 在本实验里普遍 ≥0.9990，本身几乎没有分辨力；换成配对数后带宽/邻居数的影响才显现。
    out["n_inversion_pairs_equiv"] = (1.0 - auc) * out["n_anomaly"] * out["n_normal"]
    out["threshold"] = float(threshold)
    return out