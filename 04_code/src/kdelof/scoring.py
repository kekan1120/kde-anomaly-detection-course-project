"""检测器打分 —— 协议 §4 / §6.1。

两条打分路径
------------
* **正式路径**（提交代码使用）：``sklearn`` 的 ``KernelDensity`` 与
  ``LocalOutlierFactor(novelty=True)``。
* **手写路径**（独立核验用，不依赖 sklearn 的 KDE/LOF）：直接按定义展开的高斯核 KDE 与
  Breunig 原始定义的 LOF。它的用途是：当 C 的库调用与 B 的基准对不上时，能定位到底是
  「库调用/版本问题」还是「公式或符号问题」。

得分方向
--------
协议 §6.1 规定所有异常分数 ``s`` **越大越异常**。sklearn 的两个 ``score_samples`` 都是
「越大越正常」（分别是 log 密度与负离群因子），因此都要取负。方向**必须实测**，不能按
函数名推断 —— 见 :func:`assert_score_direction`。
"""

from __future__ import annotations

from typing import Iterable

import numpy as np


# --------------------------------------------------------------------------------------
# 正式路径：sklearn
# --------------------------------------------------------------------------------------


def kde_log_density(X_fit: np.ndarray, X_eval: np.ndarray, bandwidth: float) -> np.ndarray:
    """``KernelDensity.score_samples`` = log 密度估计（越大越正常）。只在 train 上 fit。"""
    from sklearn.neighbors import KernelDensity

    model = KernelDensity(kernel="gaussian", bandwidth=float(bandwidth))
    model.fit(np.asarray(X_fit, dtype=np.float64))
    return model.score_samples(np.asarray(X_eval, dtype=np.float64))


def lof_neg_outlier_factor(X_fit: np.ndarray, X_eval: np.ndarray, n_neighbors: int) -> np.ndarray:
    """``LocalOutlierFactor(novelty=True).score_samples`` = negative_outlier_factor（越大越正常）。

    必须 ``novelty=True``：非 novelty 模式只提供训练集上的 ``negative_outlier_factor_``，
    无法给新样本打分（协议 §4.2）。
    """
    from sklearn.neighbors import LocalOutlierFactor

    model = LocalOutlierFactor(n_neighbors=int(n_neighbors), novelty=True, metric="euclidean")
    model.fit(np.asarray(X_fit, dtype=np.float64))
    return model.score_samples(np.asarray(X_eval, dtype=np.float64))


def to_anomaly_score(raw: np.ndarray) -> np.ndarray:
    """统一得分方向：``s = -score_samples``，越大越异常（协议 §6.1）。"""
    return -np.asarray(raw, dtype=np.float64)


# --------------------------------------------------------------------------------------
# 手写路径：独立于 sklearn 的公式实现
# --------------------------------------------------------------------------------------


def scratch_kde_log_density(X_fit: np.ndarray, X_eval: np.ndarray, bandwidth: float) -> np.ndarray:
    r"""按定义展开的高斯核 KDE 对数密度。

    .. math::

        \hat p_h(x) = \frac{1}{n h^d}\sum_{i=1}^{n}
        (2\pi)^{-d/2}\exp\!\left(-\frac{\lVert x-x_i\rVert^2}{2h^2}\right)

    对数域里用 ``logsumexp`` 求和，避免小带宽下密度下溢成 0 再取对数变成 ``-inf``。
    """
    from scipy.special import logsumexp

    X_fit = np.asarray(X_fit, dtype=np.float64)
    X_eval = np.asarray(X_eval, dtype=np.float64)
    h = float(bandwidth)
    n, d = X_fit.shape

    # (m, n, d) 的逐点差：维数 d=2 时内存约 1000*600*2*8B ≈ 9.6 MB，可接受。
    diff = (X_eval[:, None, :] - X_fit[None, :, :]) / h
    log_kernel = -0.5 * np.einsum("ijk,ijk->ij", diff, diff) - 0.5 * d * np.log(2.0 * np.pi)
    return logsumexp(log_kernel, axis=1) - np.log(n) - d * np.log(h)


def scratch_lof(X_fit: np.ndarray, X_query: np.ndarray, k: int) -> np.ndarray:
    r"""Breunig et al. (2000) 原始定义的 LOF。

    定义链：

    * :math:`N_k(p)`：p 的 k 个最近邻（**不含 p 自身**）；
    * :math:`k\text{-}distance(p)`：p 到第 k 近邻的距离；
    * :math:`reach\text{-}dist_k(p,o)=\max\{k\text{-}distance(o),\,d(p,o)\}`；
    * :math:`lrd_k(p)=1/\overline{reach\text{-}dist_k(p,\cdot)}`；
    * :math:`LOF_k(p)=\overline{lrd_k(o)}_{o\in N_k(p)} / lrd_k(p)`。

    只对**不在训练集里**的查询点计算，从而绕开「查询点自身算不算邻居」这一约定歧义
    （sklearn 的 novelty 模式同样把查询点排除在训练邻居之外，两者才可比）。

    ``+1e-10`` 与 sklearn 的 ``_lrd`` 一致，用于避免重复点造成的除零。
    """
    from scipy.spatial.distance import cdist

    X_fit = np.asarray(X_fit, dtype=np.float64)
    X_query = np.asarray(X_query, dtype=np.float64)
    n = X_fit.shape[0]
    if k >= n:
        raise ValueError("k 必须小于训练样本数")

    D_ff = cdist(X_fit, X_fit)
    np.fill_diagonal(D_ff, np.inf)                       # 邻居集合不含自身
    order_ff = np.argsort(D_ff, axis=1, kind="stable")
    idx_ff = order_ff[:, :k]
    kdist = np.take_along_axis(D_ff, idx_ff, axis=1)[:, -1]

    reach_ff = np.maximum(np.take_along_axis(D_ff, idx_ff, axis=1), kdist[idx_ff])
    lrd_fit = 1.0 / (reach_ff.mean(axis=1) + 1e-10)

    D_qf = cdist(X_query, X_fit)
    idx_qf = np.argsort(D_qf, axis=1, kind="stable")[:, :k]
    # 注意：必须 take_along_axis；写成 D_qf[:, idx_qf] 会按二维花式索引展开成 (m, m, k)。
    d_qn = np.take_along_axis(D_qf, idx_qf, axis=1)
    reach_qf = np.maximum(d_qn, kdist[idx_qf])
    lrd_q = 1.0 / (reach_qf.mean(axis=1) + 1e-10)

    # 逐邻居取比值再平均（与 sklearn 的 lrd_ratio 语义一致，不要先平均再相除）
    return (lrd_fit[idx_qf] / lrd_q[:, None]).mean(axis=1)


# --------------------------------------------------------------------------------------
# 得分方向断言（任务书点名的高频错误）
# --------------------------------------------------------------------------------------


def direction_report(
    X_fit: np.ndarray,
    bandwidths: Iterable[float],
    neighbour_counts: Iterable[int],
    obvious_normal: np.ndarray | None = None,
    obvious_far: np.ndarray | None = None,
) -> dict:
    """用人工构造的「明显正常点 / 明显远端异常点」实测两个检测器的得分方向。

    判据：``min(异常点分数) > max(正常点分数)``。正常点取两个簇心，异常点取环上 r=6 的
    三个方向。这个检查**不依赖任何随机样本**，因此它证明的是方向约定，不是数据好坏。
    """
    normal = np.array([[-2.0, 0.0], [2.0, 0.0]]) if obvious_normal is None else obvious_normal
    far = np.array([[6.0, 0.0], [0.0, 6.0], [-6.0, 0.0]]) if obvious_far is None else obvious_far

    rows = []
    for kind, params in (("kde", bandwidths), ("lof", neighbour_counts)):
        for p in params:
            if kind == "kde":
                raw_n = kde_log_density(X_fit, normal, p)
                raw_f = kde_log_density(X_fit, far, p)
            else:
                raw_n = lof_neg_outlier_factor(X_fit, normal, p)
                raw_f = lof_neg_outlier_factor(X_fit, far, p)
            s_n = to_anomaly_score(raw_n)
            s_f = to_anomaly_score(raw_f)
            rows.append({
                "detector": kind,
                "param": float(p),
                "normal_score_max": float(s_n.max()),
                "anomaly_score_min": float(s_f.min()),
                "ok": bool(s_f.min() > s_n.max()),
            })
    return {"rows": rows, "all_ok": all(r["ok"] for r in rows)}


def assert_score_direction(
    X_fit: np.ndarray, bandwidths: Iterable[float], neighbour_counts: Iterable[int]
) -> None:
    """方向不对就直接抛错 —— 宁可不跑，也不能把反向分数算进论文。"""
    rep = direction_report(X_fit, bandwidths, neighbour_counts)
    bad = [r for r in rep["rows"] if not r["ok"]]
    if bad:
        raise AssertionError(f"得分方向错误：异常点分数未高于正常点。前 3 条：{bad[:3]}")