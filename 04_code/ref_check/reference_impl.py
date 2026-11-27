"""B 角色独立参考实现 —— 数据与实验设计负责人的对照基准.

本模块不属于正式提交代码（正式代码由 C 实现与复现负责人编写）。它的存在目的有三个：

1. 把 ``04_code/config_ref.json`` 中的预注册协议变成可执行、可核验的唯一事实来源。
2. 为 C 的实现提供逐位可比的基准数值（数据指纹、阈值、指标）。
3. 提供**不依赖 sklearn 的独立计算路径**（手写 KDE 密度、手写 LOF、手算 AUC/AP/混淆矩阵），
   用于交叉核验 C 的库调用是否正确、得分方向是否被搞反、阈值分位数方法是否一致。

所有随机性都来自 config 里登记的独立种子，任一数据流的结果不依赖其它流的随机数消耗顺序。
两个检测器（KernelDensity / LocalOutlierFactor(novelty=True)）都是确定性算法，不消费随机数。

约定
----
* 数组形状: ``X`` 为 ``(n, 2)`` float64;  ``y`` 为 ``(n,)`` int64，0=正常，1=异常。
* ``cluster_id``: 正常点取 0(密集簇) 或 1(稀疏簇)，异常点取 -1。
* ``anomaly_type``: 正常点为 ``"none"``，异常点为 ``"far"`` 或 ``"near"``。
* 异常分数 ``s`` 一律**越大越异常**（KDE 取负对数密度，LOF 取负的 score_samples）。
"""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

# --------------------------------------------------------------------------------------
# 配置
# --------------------------------------------------------------------------------------

_HERE = Path(__file__).resolve().parent
DEFAULT_CONFIG = _HERE.parent / "config_ref.json"


def load_config(path: str | Path | None = None) -> dict:
    """读取并做基本自洽性校验的协议配置。"""
    p = Path(path) if path is not None else DEFAULT_CONFIG
    with open(p, encoding="utf-8") as fh:
        cfg = json.load(fh)

    # 自洽性校验：任何一项不满足都说明配置被改坏了，立即失败而不是静默跑出错误结果。
    splits = cfg["data"]["splits"]
    for name in ("train", "validation"):
        assert splits[name]["n_anomaly"] == 0, f"{name} 必须只含正常样本"
    t = splits["test"]
    total = t["n_dense"] + t["n_sparse"] + t["n_anomaly"]
    assert total == t["total"], f"test 总数不一致: {total} != {t['total']}"
    assert abs(t["n_anomaly"] / total - t["anomaly_ratio"]) < 1e-12, "测试异常比例与配置不符"

    max_k = max(cfg["detectors"]["lof"]["n_neighbors_grid"])
    assert max_k < splits["train"]["total"], "LOF 邻居数必须小于训练样本数"

    assert cfg["data"]["preprocessing"]["scaling"] == "none", "协议规定不做标准化"
    assert cfg["threshold"]["numpy_method"] == "inverted_cdf", "阈值分位数方法必须锁定"
    return cfg


def resolve_seed(cfg: dict, stream: str, repeat: int = 0) -> int:
    """把 (数据流, 重复编号) 解析成具体整数种子。repeat=0 为锁定的核心运行。"""
    base = cfg["seeds"]["streams"][stream]
    if repeat == 0:
        return base
    offset = cfg["seeds"]["extension_repeats"]["seed_offset_per_repeat"]
    return base + offset * repeat


def make_rng(cfg: dict, stream: str, repeat: int = 0) -> np.random.Generator:
    """每个数据流一个独立 Generator（PCG64），互不干扰随机数消耗顺序。"""
    return np.random.Generator(np.random.PCG64(resolve_seed(cfg, stream, repeat)))


# --------------------------------------------------------------------------------------
# 数据生成
# --------------------------------------------------------------------------------------


@dataclass
class Dataset:
    """一个数据集的全部字段。`split` 只是标签，算法内部不得按它切换行为。"""

    X: np.ndarray
    y: np.ndarray
    cluster_id: np.ndarray
    anomaly_type: np.ndarray
    split: str
    repeat: int = 0

    def __len__(self) -> int:
        return self.X.shape[0]

    @property
    def summary(self) -> dict:
        out = {"split": self.split, "repeat": self.repeat, "n": len(self)}
        if self.repeat == 0:
            # 反推 repeat 只需看数据集本身；这里只做保险，正常路径不会被用到。
            pass
        out["n_dense"] = int((self.cluster_id == 0).sum())
        out["n_sparse"] = int((self.cluster_id == 1).sum())
        out["n_anomaly"] = int((self.y == 1).sum())
        out["n_anomaly_far"] = int((self.anomaly_type == "far").sum())
        out["n_anomaly_near"] = int((self.anomaly_type == "near").sum())
        out["n_missing"] = int(np.isnan(self.X).sum())
        return out


def sample_cluster(cfg: dict, stream: str, n: int, repeat: int = 0) -> np.ndarray:
    """按 config 的显式对角 Cholesky 写法采样一个二维高斯簇。

    刻意不用 ``multivariate_normal``：``X = mean + scale * standard_normal`` 的语义在任何
    语言/任何 numpy 版本下都一致，才能保证跨实现逐位复现。
    """
    key, which = stream.split(".")
    spec = cfg["data"]["clusters"][which]
    rng = make_rng(cfg, stream, repeat)
    Z = rng.standard_normal((n, int(cfg["data"]["dimension"])))
    return np.asarray(spec["mean"], dtype=np.float64) + float(spec["fixed_scale"]) * Z


def sample_far_anomalies(cfg: dict, n: int, repeat: int = 0) -> np.ndarray:
    """远端异常：绕原点的圆环内均匀采样。

    用参数化构造（theta, r 两次独立 uniform）而不是在方框里做拒绝采样，
    因为拒绝采样的循环次数会影响后续随机数消耗，跨实现无法保证逐位一致。

    **B-v1.1-near 的点级嵌套口径（协议 §3.1，Q-A 裁定取 C 的 B 案）**：实际抽样量恒为
    ``far.n_draw``（250），再取前 ``n`` 行。随机数消耗因此与 ``n_test`` 解耦，任何
    ``n_test <= n_draw`` 的配置都得到 B-v1.0 那 250 个远端异常点的前 ``n_test`` 个，
    使 far 侧判定在版本之间逐位可比。``n_draw`` 缺省时退化为 ``n``（即 B-v1.0 行为不变）。
    """
    spec = cfg["anomaly"]["types"]["far"]
    n_draw = int(spec.get("n_draw", spec["n_test"]))
    assert n <= n_draw, f"n_test={n} 超过 far.n_draw={n_draw}，嵌套口径不成立"
    rng = make_rng(cfg, "test.anomaly.far", repeat)
    theta = rng.uniform(0.0, 2.0 * np.pi, n_draw)
    r = rng.uniform(float(spec["r_min"]), float(spec["r_max"]), n_draw)
    X = np.column_stack([r * np.cos(theta), r * np.sin(theta)])
    return X[:n]


def sample_near_anomalies(cfg: dict, n: int, repeat: int = 0) -> np.ndarray:
    """可选拓展 P1：空区中的紧凑小簇（compact cluster in the void）。

    **为什么这里不是「稀疏簇周围的球壳」**：稀疏簇 sd = 1.0，二维标准高斯在径向上
    ``P(r >= 2.5) = exp(-3.125) = 4.39%``，即 500 个正常稀疏簇点里约有 **22 个**落在 2.5σ
    球壳之外。这些正常点密度更低、异常分数比被标注为「异常」的球壳点还高，标签体系会自相矛盾，
    任何检测器都不可能正确。因此球壳式「局部异常」在本 DGP 下不成立。

    改用**空区紧凑簇**：它离两个正常簇都很远（绝对密度极低，KDE 必然判为异常），但内部点彼此
    很近（局部密度高，LOF 会判为正常）。这正是用来检验「全局密度 vs 局部相对密度」差异的
    经典情形，也对应任务书要求的「指出各自适用的数据形态与失效场景」。
    """
    spec = cfg["anomaly"]["types"]["near"]
    center = np.asarray(spec["center"], dtype=np.float64)
    rng = make_rng(cfg, spec["seed_key"], repeat)
    Z = rng.standard_normal((n, int(cfg["data"]["dimension"])))
    return center + float(spec["fixed_scale"]) * Z


def generate_split(cfg: dict, split: str, repeat: int = 0) -> Dataset:
    """生成一个 split。正常点与异常的标签完全由生成规则决定，不含任何检测器信息。"""
    spec = cfg["data"]["splits"][split]
    n_dense, n_sparse, n_anom = spec["n_dense"], spec["n_sparse"], spec["n_anomaly"]

    X_parts, cid_parts, y_parts, typ_parts = [], [], [], []

    # 两个正常簇 —— 每个簇一个独立种子，顺序无关。
    X_parts.append(sample_cluster(cfg, f"{split}.dense", n_dense, repeat))
    cid_parts.append(np.zeros(n_dense, dtype=np.int64))
    y_parts.append(np.zeros(n_dense, dtype=np.int64))
    typ_parts.append(np.array(["none"] * n_dense, dtype=object))

    X_parts.append(sample_cluster(cfg, f"{split}.sparse", n_sparse, repeat))
    cid_parts.append(np.ones(n_sparse, dtype=np.int64))
    y_parts.append(np.zeros(n_sparse, dtype=np.int64))
    typ_parts.append(np.array(["none"] * n_sparse, dtype=object))

    # 异常 —— 只有 test 有。类型、数量与构造方式全部来自 config，标签固定为 1。
    if n_anom:
        parts: list[tuple[str, np.ndarray]] = []
        for key in ("far", "near"):
            spec = cfg["anomaly"]["types"][key]
            n_t = int(spec["n_test"]) if spec["enabled"] else 0
            if n_t == 0:
                continue
            construction = spec["construction"]
            if construction == "ring_uniform":
                Xt = sample_far_anomalies(cfg, n_t, repeat)
            elif construction == "compact_gaussian":
                Xt = sample_near_anomalies(cfg, n_t, repeat)
            else:
                raise ValueError(f"未实现的异常构造方式: {construction}")
            parts.append((str(spec["type_id"]), Xt))
        total_anom = sum(len(Xt) for _, Xt in parts)
        assert total_anom == n_anom, (
            f"{split} 的异常数量不一致: 各类型合计 {total_anom} != n_anomaly={n_anom}"
        )
        for type_id, Xt in parts:
            X_parts.append(Xt)
            cid_parts.append(-np.ones(len(Xt), dtype=np.int64))
            y_parts.append(np.ones(len(Xt), dtype=np.int64))
            typ_parts.append(np.array([type_id] * len(Xt), dtype=object))

    return Dataset(
        X=np.vstack(X_parts).astype(np.float64),
        y=np.concatenate(y_parts).astype(np.int64),
        cluster_id=np.concatenate(cid_parts).astype(np.int64),
        anomaly_type=np.concatenate(typ_parts).astype(object),
        split=split,
        repeat=repeat,
    )


def generate_all(cfg: dict, repeat: int = 0) -> dict[str, Dataset]:
    return {s: generate_split(cfg, s, repeat) for s in ("train", "validation", "test")}


def generate_1d_demo(cfg: dict, repeat: int = 0) -> np.ndarray:
    """一维双峰样本，仅用于带宽示意（原理图），不进入二维检测性能汇总。"""
    d = cfg["demo_1d"]
    out = []
    for which in ("dense", "sparse"):
        spec = d["components"][which]
        rng = make_rng(cfg, spec["seed_key"], repeat)
        out.append(float(spec["mean"]) + float(spec["sd"]) * rng.standard_normal(int(spec["n"])))
    x = np.concatenate(out)
    assert x.shape[0] == d["total"], "一维示例样本数不一致"
    return x


# --------------------------------------------------------------------------------------
# 数据指纹：让 C 可以用一行代码确认「我们拿到的是同一份数据」
# --------------------------------------------------------------------------------------


def fingerprint(ds: Dataset) -> dict:
    """给出两种指纹。

    * ``sha256_float64``：``X`` 的 float64 原始字节的 sha256。同一 numpy 版本下应当逐位一致；
      跨版本/跨语言时 ``standard_normal`` 的实现差异可能让它不同，因此不作为唯一判据。
    * ``summary``：均值/标准差/极值/逐簇计数等。任何实现的数值都应落在极小的相对容差内
      （建议 1e-12），这是跨实现的推荐判据。
    """
    X = np.ascontiguousarray(ds.X, dtype=np.float64)
    return {
        "split": ds.split,
        "repeat": ds.repeat,
        "n": len(ds),
        "sha256_float64": hashlib.sha256(X.tobytes()).hexdigest(),
        "summary": ds.summary,
        "stats": {
            "mean": [float(v) for v in X.mean(axis=0)],
            "std_ddof1": [float(v) for v in X.std(axis=0, ddof=1)],
            "min": [float(v) for v in X.min(axis=0)],
            "max": [float(v) for v in X.max(axis=0)],
        },
    }


# --------------------------------------------------------------------------------------
# 检测器：正式路径（sklearn）与独立路径（手写）各一份
# --------------------------------------------------------------------------------------


def kde_score_samples(X_fit: np.ndarray, X_eval: np.ndarray, bandwidth: float) -> np.ndarray:
    """KDE 的 log 密度（越大越正常）。返回原始 score_samples，未取负。"""
    from sklearn.neighbors import KernelDensity

    kde = KernelDensity(kernel="gaussian", bandwidth=float(bandwidth))
    kde.fit(X_fit)
    return kde.score_samples(X_eval)


def lof_score_samples(X_fit: np.ndarray, X_eval: np.ndarray, n_neighbors: int) -> np.ndarray:
    """LOF 的 negative_outlier_factor（越大越正常）。返回原始 score_samples，未取负。

    必须 novelty=True：否则 sklearn 只提供训练集上的 ``negative_outlier_factor_``，
    无法给新样本打分。符号按实测确认，不按函数名推断。
    """
    from sklearn.neighbors import LocalOutlierFactor

    lof = LocalOutlierFactor(n_neighbors=int(n_neighbors), novelty=True, metric="euclidean")
    lof.fit(X_fit)
    return lof.score_samples(X_eval)


def anomaly_score(raw: np.ndarray) -> np.ndarray:
    """统一得分方向：越大越异常。KDE(log 密度) 与 LOF(neg_outlier_factor) 都要取负。"""
    return -np.asarray(raw, dtype=np.float64)


# ---- 独立路径：不依赖 sklearn，用于交叉核验 ---------------------------------------------


def numpy_kde_log_density(X_fit: np.ndarray, X_eval: np.ndarray, bandwidth: float) -> np.ndarray:
    """手写高斯核 KDE 的 log 密度。

        p_h(x) = 1/(n h^d) * sum_i (2*pi)^(-d/2) exp(-||x-x_i||^2 / (2 h^2))

    直接照公式展开，不使用任何库的 KDE。与 sklearn 结果应在 1e-12 量级内一致。
    """
    from scipy.special import logsumexp

    X_fit = np.asarray(X_fit, dtype=np.float64)
    X_eval = np.asarray(X_eval, dtype=np.float64)
    h = float(bandwidth)
    n, d = X_fit.shape
    diff = (X_eval[:, None, :] - X_fit[None, :, :]) / h          # (m, n, d)
    log_kernel = -0.5 * np.sum(diff * diff, axis=2) - 0.5 * d * np.log(2.0 * np.pi)
    return logsumexp(log_kernel, axis=1) - np.log(n) - d * np.log(h)


def scratch_lof(X_fit: np.ndarray, X_query: np.ndarray, k: int) -> np.ndarray:
    """按 Breunig et al. (2000) 定义手写 LOF，不含任何库实现。

    N_k(p) 不含 p 自身；k-distance(p) 为到第 k 近邻（不含自身）的距离；
    reach-dist_k(p,o) = max(k-distance(o), d(p,o))；lrd = 1 / mean(reach-dist)；
    LOF(p) = mean_{o in N_k(p)} lrd(o) / lrd(p)。

    只对**不在训练集内**的查询点计算，从而避免「查询点自身是否算邻居」的约定歧义。
    ``+1e-10`` 与 sklearn 一致，用于避免重复点导致的除零。
    """
    from scipy.spatial.distance import cdist

    X_fit = np.asarray(X_fit, dtype=np.float64)
    X_query = np.asarray(X_query, dtype=np.float64)
    n = X_fit.shape[0]
    assert X_fit.shape != X_query.shape or not np.array_equal(X_fit, X_query), (
        "查询点不应与训练集完全重合；否则自身是否计入邻居会有约定歧义"
    )

    D_ff = cdist(X_fit, X_fit)
    np.fill_diagonal(D_ff, np.inf)                       # 排除自身
    order_ff = np.argsort(D_ff, axis=1, kind="stable")
    idx_ff = order_ff[:, :k]                             # 每个训练点的 k 个近邻
    kdist_fit = D_ff[np.arange(n)[:, None], idx_ff][:, -1]   # 到第 k 近邻的距离

    reach_ff = np.maximum(D_ff[np.arange(n)[:, None], idx_ff], kdist_fit[idx_ff])
    lrd_fit = 1.0 / (reach_ff.mean(axis=1) + 1e-10)

    D_qf = cdist(X_query, X_fit)
    order_qf = np.argsort(D_qf, axis=1, kind="stable")
    idx_qf = order_qf[:, :k]
    # 注意：必须用 take_along_axis，写成 D_qf[:, idx_qf] 会按二维花式索引展开成 (m, m, k)
    d_to_neighbors = np.take_along_axis(D_qf, idx_qf, axis=1)
    reach_qf = np.maximum(d_to_neighbors, kdist_fit[idx_qf])
    lrd_q = 1.0 / (reach_qf.mean(axis=1) + 1e-10)

    return np.mean(lrd_fit[idx_qf] / lrd_q[:, None], axis=1)


# --------------------------------------------------------------------------------------
# 阈值校准
# --------------------------------------------------------------------------------------


def calibrate_threshold(scores_val: np.ndarray, cfg: dict) -> float:
    """用验证集正常样本的异常分数取经验分位数作报警阈值。

    锁定为 ``numpy.quantile(..., 0.99, method='inverted_cdf')``：取第 ``ceil(0.99*n)`` 个
    次序统计量，使验证集上严格超过阈值的样本数恰为 ``n - ceil(0.99*n)``（n=1000 时为 10 个，
    即经验误报率 1.00%）。这是「目标误报率 1%」的精确实现；换成默认的 'linear' 或 'higher'
    会得到不同阈值，跨实现比对时必须统一到本方法。
    """
    q = float(cfg["threshold"]["quantile"])
    method = cfg["threshold"]["numpy_method"]
    return float(np.quantile(np.asarray(scores_val, dtype=np.float64), q, method=method))


def predict(scores: np.ndarray, threshold: float) -> np.ndarray:
    """严格大于判定为异常；等于阈值判为正常（并列处理规则，见协议）。"""
    return (np.asarray(scores, dtype=np.float64) > float(threshold)).astype(np.int64)


# --------------------------------------------------------------------------------------
# 指标：手算一份（可逐项核验），并用 sklearn 复算作为交叉检查
# --------------------------------------------------------------------------------------


def manual_confusion(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    y_true = np.asarray(y_true).astype(np.int64)
    y_pred = np.asarray(y_pred).astype(np.int64)
    tp = int(np.sum((y_true == 1) & (y_pred == 1)))
    fp = int(np.sum((y_true == 0) & (y_pred == 1)))
    tn = int(np.sum((y_true == 0) & (y_pred == 0)))
    fn = int(np.sum((y_true == 1) & (y_pred == 0)))
    precision = tp / (tp + fp) if (tp + fp) else float("nan")
    recall = tp / (tp + fn) if (tp + fn) else float("nan")
    f1 = (2 * precision * recall / (precision + recall)
          if np.isfinite(precision) and np.isfinite(recall) and (precision + recall) else float("nan"))
    fpr = fp / (fp + tn) if (fp + tn) else float("nan")
    return {
        "tp": tp, "fp": fp, "tn": tn, "fn": fn,
        "precision": precision, "recall": recall, "f1": f1, "fpr_overall": fpr,
    }


def manual_roc_auc(y_true: np.ndarray, scores: np.ndarray) -> float:
    """用 Mann-Whitney U 恒等式手算 AUC：AUC = U / (n_pos * n_neg)，并列分数取平均秩。"""
    y_true = np.asarray(y_true).astype(np.int64)
    s = np.asarray(scores, dtype=np.float64)
    pos, neg = y_true == 1, y_true == 0
    n_pos, n_neg = int(pos.sum()), int(neg.sum())
    if n_pos == 0 or n_neg == 0:
        return float("nan")

    order = np.argsort(s, kind="stable")
    ranks = np.empty_like(s, dtype=np.float64)
    sorted_s = s[order]
    i = 0
    n = len(s)
    while i < n:
        j = i
        while j + 1 < n and sorted_s[j + 1] == sorted_s[i]:
            j += 1
        ranks[order[i:j + 1]] = (i + j) / 2.0 + 1.0     # 平均秩，1-based
        i = j + 1
    u = ranks[pos].sum() - n_pos * (n_pos + 1) / 2.0
    return float(u / (n_pos * n_neg))


def manual_average_precision(y_true: np.ndarray, scores: np.ndarray) -> float:
    """手算 step-wise AP：AP = sum_k (R_k - R_{k-1}) * P_k，阈值遍历全部不同的分数值。

    与 sklearn.metrics.average_precision_score 的阶梯定义一致；不等同于 PR 曲线梯形积分。
    """
    y_true = np.asarray(y_true).astype(np.int64)
    s = np.asarray(scores, dtype=np.float64)
    n_pos = int((y_true == 1).sum())
    if n_pos == 0:
        return float("nan")

    order = np.argsort(-s, kind="stable")               # 分数从高到低
    s_sorted = s[order]
    y_sorted = y_true[order]

    # 在每个「不同的分数值」处切一刀，等价于 sklearn 的阶梯式 PR 曲线
    distinct = np.where(np.diff(s_sorted) != 0)[0]
    cut = np.r_[distinct, len(s_sorted) - 1]

    tp = np.cumsum(y_sorted)[cut]
    n_pred = (cut + 1).astype(np.float64)
    precision = tp / n_pred
    recall = tp / n_pos
    d_recall = np.diff(np.r_[0.0, recall])
    return float(np.sum(d_recall * precision))


def evaluate(ds: Dataset, scores: np.ndarray, threshold: float, cfg: dict | None = None) -> dict:
    """在测试集上计算全部约定指标。这是唯一接触测试标签的函数。"""
    y_pred = predict(scores, threshold)
    m = manual_confusion(ds.y, y_pred)

    normal = ds.y == 0
    out = dict(m)
    out["n"] = len(ds)
    out["n_normal"] = int(normal.sum())
    out["n_anomaly"] = int((ds.y == 1).sum())
    out["prevalence"] = out["n_anomaly"] / len(ds)

    # 分簇误报率 —— H2 的唯一直接证据，必须与总 FPR 并列报告
    for name, cid in (("dense", 0), ("sparse", 1)):
        mask = normal & (ds.cluster_id == cid)
        n_c = int(mask.sum())
        fp_c = int(np.sum(y_pred[mask] == 1))
        out[f"n_normal_{name}"] = n_c
        out[f"fp_{name}"] = fp_c
        out[f"fpr_{name}"] = fp_c / n_c if n_c else float("nan")

    # 分异常类型召回率（启用多种异常类型时才有意义）
    type_ids = [cfg["anomaly"]["types"][k]["type_id"] for k in ("far", "near")] if cfg else ["far", "near"]
    for typ in type_ids:
        mask = ds.anomaly_type == typ
        n_t = int(mask.sum())
        if n_t:
            out[f"n_anomaly_{typ}"] = n_t
            out[f"recall_{typ}"] = float(np.sum(y_pred[mask] == 1)) / n_t

    auc = manual_roc_auc(ds.y, scores)
    out["auc"] = auc
    out["average_precision"] = manual_average_precision(ds.y, scores)
    # 排序错误对数：AUC 在接近 1 时会失去分辨力，这个量把它换算成「有意义的整数对数量」。
    # (1 - AUC) * n_pos * n_neg 恰等于被错排的 (正常, 异常) 配对数（并列按半对计）。
    out["n_inversion_pairs_equiv"] = (1.0 - auc) * out["n_anomaly"] * out["n_normal"]
    out["threshold"] = float(threshold)
    out["exceedance_rate_full"] = float(np.mean(y_pred))
    return out


# --------------------------------------------------------------------------------------
# sklearn 复算，用于交叉核验手算指标
# --------------------------------------------------------------------------------------


def sklearn_metrics(y_true: np.ndarray, scores: np.ndarray, y_pred: np.ndarray) -> dict:
    from sklearn.metrics import (
        average_precision_score,
        confusion_matrix,
        f1_score,
        precision_score,
        recall_score,
        roc_auc_score,
    )

    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    return {
        "cm": cm.tolist(),
        "precision": float(precision_score(y_true, y_pred, zero_division=np.nan)),
        "recall": float(recall_score(y_true, y_pred, zero_division=np.nan)),
        "f1": float(f1_score(y_true, y_pred, zero_division=np.nan)),
        "auc": float(roc_auc_score(y_true, scores)),
        "average_precision": float(average_precision_score(y_true, scores)),
    }


# --------------------------------------------------------------------------------------
# 峰结构分析：E0 一维带宽示意的统一口径（协议 §7.1）
# --------------------------------------------------------------------------------------

#: 「显著峰」判定口径：prominence 不低于全局最大密度的 10%。
#: checks.py 与 run_ref.py 必须共用同一个常量，否则论文图注与核验记录会自相矛盾。
PROMINENCE_FRAC = 0.10


def prominence(p: np.ndarray, i: int) -> float:
    """峰的 prominence：从峰顶向两侧走到第一个更高点，取两侧最低点中较高者作基准后的落差。

    这是判断「一个局部极大是否真的构成一个峰」的标准量。小带宽下每条样本都会顶出一个尖，
    这些尖的 prominence 很小，不应被当作真正的众数。
    """
    n = len(p)
    v = float(p[i])
    left_min = v
    l = i
    while l > 0:
        l -= 1
        if p[l] > v:
            break
        left_min = min(left_min, float(p[l]))
    right_min = v
    r = i
    while r < n - 1:
        r += 1
        if p[r] > v:
            break
        right_min = min(right_min, float(p[r]))
    return float(v - max(left_min, right_min))


def density_peaks(p: np.ndarray, xs: np.ndarray, prominence_frac: float = PROMINENCE_FRAC) -> dict:
    """给出一条密度曲线上的峰结构描述。

    返回 ``n_local_maxima``（全部局部极大点数）、``n_prominent_peaks``（显著峰数）、
    ``prominent_peaks``（显著峰的 x 与高度）、``valley_fill_ratio``（两个最高局部极大点之间的
    最低密度除以较低峰高度）以及 ``prominences``（每个局部极大点的 prominence/全局最大）。
    """
    p = np.asarray(p, dtype=np.float64)
    xs = np.asarray(xs, dtype=np.float64)
    d1 = np.diff(p)
    local = [int(i) for i in np.where((d1[:-1] > 0) & (d1[1:] <= 0))[0] + 1]
    pmax = float(p.max())
    prom = {i: prominence(p, i) for i in local}
    prominent = [i for i in local if prom[i] >= prominence_frac * pmax]
    prominent.sort(key=lambda i: -p[i])

    valley = None
    if len(local) >= 2:
        top2 = sorted(local, key=lambda i: -p[i])[:2]
        lo, hi = min(top2), max(top2)
        valley = float(p[lo:hi + 1].min()) / min(float(p[top2[0]]), float(p[top2[1]]))

    return {
        "n_local_maxima": len(local),
        "n_prominent_peaks": len(prominent),
        "max_density": pmax,
        "valley_fill_ratio": valley,
        "prominent_peaks": [
            {"x": float(xs[i]), "height": float(p[i]),
             "prominence_ratio": float(prom[i] / pmax)} for i in prominent
        ],
        "prominences": [
            {"x": float(xs[i]), "prominence_ratio": float(prom[i] / pmax)} for i in local
        ],
    }


# --------------------------------------------------------------------------------------
# 环境信息 / 运行日志
# --------------------------------------------------------------------------------------


def environment_info() -> dict:
    import matplotlib
    import pandas as pd
    import scipy
    import sklearn

    return {
        "python": sys.version.split()[0],
        "executable": sys.executable,
        "platform": sys.platform,
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "scikit_learn": sklearn.__version__,
        "matplotlib": matplotlib.__version__,
        "pandas": pd.__version__,
    }
