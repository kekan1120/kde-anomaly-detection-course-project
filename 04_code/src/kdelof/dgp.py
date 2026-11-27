"""数据生成（DGP）—— 协议 §2 / §3 / §8 / §9。

复现要求
--------
* 每个数据流一个**独立** ``Generator(PCG64(seed))``，流之间不共享随机数消耗顺序。
* 二维高斯簇一律写成 ``mean + fixed_scale * standard_normal((n, 2))``，不用
  ``multivariate_normal``：前者的语义在任意 numpy 版本下都是同一个数，后者内部可能
  走 Cholesky 或特征分解，跨版本未必逐位一致。
* 远端异常用参数化圆环（先 theta 再一次 r），不做拒绝采样：拒绝采样的循环次数会改变
  后续随机数消耗量，跨实现无法保证逐位一致。

行顺序约定（协议 §9）：``[密集簇, 稀疏簇, far 异常, near 异常]`` 依次 ``vstack``。
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from . import protocol

SPLITS = ("train", "validation", "test")


@dataclass
class Split:
    """一个数据划分的全部字段。

    ``split`` 只是名字标签：算法内部**不得**按它切换行为，否则就是把划分信息带进模型。
    """

    X: np.ndarray
    y: np.ndarray
    cluster_id: np.ndarray
    anomaly_type: np.ndarray
    split: str
    repeat: int = 0
    _summary: dict[str, Any] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        self.X = np.ascontiguousarray(self.X, dtype=np.float64)
        self.y = np.asarray(self.y, dtype=np.int64)
        self.cluster_id = np.asarray(self.cluster_id, dtype=np.int64)
        self.anomaly_type = np.asarray(self.anomaly_type, dtype=object)
        n = self.X.shape[0]
        if self.X.ndim != 2:
            raise ValueError(f"{self.split}: X 必须是二维数组")
        if not (len(self.y) == len(self.cluster_id) == len(self.anomaly_type) == n):
            raise ValueError(f"{self.split}: 各字段行数不一致")
        if np.isnan(self.X).any():
            raise ValueError(f"{self.split}: 出现缺失值，协议不允许")

    def __len__(self) -> int:
        return int(self.X.shape[0])

    @property
    def n_normal(self) -> int:
        return int((self.y == 0).sum())

    @property
    def n_anomaly(self) -> int:
        return int((self.y == 1).sum())

    @property
    def summary(self) -> dict[str, Any]:
        """规模与逐簇计数（协议 §9 的核对表）。"""
        if self._summary:
            return self._summary
        out = {
            "split": self.split,
            "repeat": self.repeat,
            "n": len(self),
            "n_dense": int((self.cluster_id == 0).sum()),
            "n_sparse": int((self.cluster_id == 1).sum()),
            "n_anomaly": int((self.y == 1).sum()),
            "n_anomaly_far": int((self.anomaly_type == "far").sum()),
            "n_anomaly_compact_void": int((self.anomaly_type == "compact_void").sum()),
            "n_missing": int(np.isnan(self.X).sum()),
        }
        self._summary = out
        return out

    def fingerprint(self) -> dict[str, Any]:
        """数据指纹：sha256（同环境逐位判据）+ 统计量（跨环境判据）。

        协议要求跨实现比对优先用 ``stats``（相对容差 1e-12），因为 ``standard_normal``
        的实现细节可能随版本变化，而均值/标准差/极值不该变。
        """
        X = np.ascontiguousarray(self.X, dtype=np.float64)
        return {
            "split": self.split,
            "repeat": self.repeat,
            "n": len(self),
            "sha256_float64": hashlib.sha256(X.tobytes()).hexdigest(),
            "summary": self.summary,
            "stats": {
                "mean": [float(v) for v in X.mean(axis=0)],
                "std_ddof1": [float(v) for v in X.std(axis=0, ddof=1)],
                "min": [float(v) for v in X.min(axis=0)],
                "max": [float(v) for v in X.max(axis=0)],
            },
        }


# --------------------------------------------------------------------------------------
# 三个数据流
# --------------------------------------------------------------------------------------


def sample_gaussian_cluster(cfg: dict[str, Any], stream: str, n: int, repeat: int = 0) -> np.ndarray:
    """二维高斯簇：``X = mean + fixed_scale * Z``（协议 §2.1）。"""
    which = stream.rsplit(".", 1)[-1]
    spec = cfg["data"]["clusters"][which]
    rng = protocol.make_rng(cfg, stream, repeat)
    Z = rng.standard_normal((int(n), int(cfg["data"]["dimension"])))
    return np.asarray(spec["mean"], dtype=np.float64) + float(spec["fixed_scale"]) * Z


def sample_far_ring(cfg: dict[str, Any], n_test: int, repeat: int = 0) -> np.ndarray:
    """远端异常：绕原点的圆环上均匀采样（协议 §3.1；B-v1.1-near 起支持 ``n_draw``）。

    抽样口径（Q-A 裁定取「真嵌套」）：先按**固定的** ``n_draw`` 依次抽
    ``theta ~ U(0, 2π, n_draw)`` 与 ``r ~ U(r_min, r_max, n_draw)``，再取前 ``n_test`` 行。
    ``n_draw`` 不随 ``n_test`` 变化，因此任何 ``n_test <= n_draw`` 的配置都得到同一批点的
    前 ``n_test`` 个（点级嵌套），且**随机数消耗量与 n_test 无关**。

    ``n_draw`` 缺省时等于 ``n_test`` —— 这样 B-v1.0（无该字段、n_test=250）的行为逐位不变。

    抽取顺序写死为「先 theta 一次，再 r 一次」。调换这两次调用不会报错，只会让指纹对不上。
    """
    spec = cfg["anomaly"]["types"]["far"]
    n_test = int(n_test)
    n_draw = int(spec.get("n_draw", n_test))
    if n_test > n_draw:
        raise ValueError(
            f"far: n_test={n_test} 不能大于 n_draw={n_draw}"
            "（协议 §3.1：先抽 n_draw 组 (theta, r)，再取前 n_test 行）"
        )
    rng = protocol.make_rng(cfg, "test.anomaly.far", repeat)
    theta = rng.uniform(0.0, 2.0 * np.pi, n_draw)
    radius = rng.uniform(float(spec["r_min"]), float(spec["r_max"]), n_draw)
    X = np.column_stack([radius * np.cos(theta), radius * np.sin(theta)])
    return X[:n_test]


def sample_compact_void(cfg: dict[str, Any], n: int, repeat: int = 0) -> np.ndarray:
    """可选 P1：空区里的紧凑小簇（协议 §3.2）。

    空区中的紧凑小簇：离两个正常簇都很远，但内部点彼此很近。

    注意：本协议强制 LOF 使用 ``novelty=True``（只在训练正常样本上拟合），新点的局部可达密度
    是相对**训练集**计算的，离训练集很远就一定很低，因此 **KDE 与 LOF 都会判它异常**；
    它不是「全局密度 vs 局部相对密度」的方法差异判别点（B 已于 2026-11-27 签署的
    `near.design_note` 中改写为同一结论，设计阶段探针实测判异率均 100%）。
    """
    spec = cfg["anomaly"]["types"]["near"]
    rng = protocol.make_rng(cfg, spec["seed_key"], repeat)
    Z = rng.standard_normal((int(n), int(cfg["data"]["dimension"])))
    return np.asarray(spec["center"], dtype=np.float64) + float(spec["fixed_scale"]) * Z


def build_anomalies(cfg: dict[str, Any], n_expected: int, repeat: int = 0) -> list[tuple[str, np.ndarray]]:
    """按配置构造启用的异常类型，返回 ``[(type_id, X), ...]``。

    标签恒为 1，由生成位置决定，**不由任何检测器输出决定**（协议 §3）。
    """
    out: list[tuple[str, np.ndarray]] = []
    for key in ("far", "near"):
        spec = cfg["anomaly"]["types"][key]
        n_t = int(spec["n_test"]) if spec["enabled"] else 0
        if n_t == 0:
            continue
        construction = spec["construction"]
        if construction == "ring_uniform":
            X = sample_far_ring(cfg, n_t, repeat)
        elif construction == "compact_gaussian":
            X = sample_compact_void(cfg, n_t, repeat)
        else:
            raise ValueError(f"未实现的异常构造方式: {construction}")
        out.append((str(spec["type_id"]), X))
    total = sum(len(X) for _, X in out)
    if total != n_expected:
        raise ValueError(f"异常类型合计 {total} != 期望 {n_expected}（协议 §3 / 配置自洽性）")
    return out


def generate_split(cfg: dict[str, Any], split: str, repeat: int = 0) -> Split:
    """生成一个划分。正常点与异常点的标签完全由生成规则自动产生。"""
    spec = cfg["data"]["splits"][split]
    n_dense, n_sparse, n_anom = int(spec["n_dense"]), int(spec["n_sparse"]), int(spec["n_anomaly"])

    X_parts: list[np.ndarray] = []
    y_parts: list[np.ndarray] = []
    cid_parts: list[np.ndarray] = []
    typ_parts: list[np.ndarray] = []

    for name, n_c, cid in (("dense", n_dense, 0), ("sparse", n_sparse, 1)):
        if n_c == 0:
            continue
        X_parts.append(sample_gaussian_cluster(cfg, f"{split}.{name}", n_c, repeat))
        y_parts.append(np.zeros(n_c, dtype=np.int64))
        cid_parts.append(np.full(n_c, cid, dtype=np.int64))
        typ_parts.append(np.full(n_c, "none", dtype=object))

    if n_anom:
        for type_id, Xt in build_anomalies(cfg, n_anom, repeat):
            X_parts.append(Xt)
            y_parts.append(np.ones(len(Xt), dtype=np.int64))
            cid_parts.append(np.full(len(Xt), -1, dtype=np.int64))
            typ_parts.append(np.full(len(Xt), type_id, dtype=object))

    return Split(
        X=np.vstack(X_parts),
        y=np.concatenate(y_parts),
        cluster_id=np.concatenate(cid_parts),
        anomaly_type=np.concatenate(typ_parts),
        split=split,
        repeat=repeat,
    )


def generate_all(cfg: dict[str, Any], repeat: int = 0) -> dict[str, Split]:
    """生成 train / validation / test 三个划分。"""
    return {s: generate_split(cfg, s, repeat) for s in SPLITS}


def generate_demo_1d(cfg: dict[str, Any], repeat: int = 0) -> np.ndarray:
    """一维双峰示例（协议 §9 末段），只用于带宽原理图，不进入二维检测性能汇总。"""
    spec = cfg["demo_1d"]
    parts: list[np.ndarray] = []
    for which in ("dense", "sparse"):
        c = spec["components"][which]
        rng = protocol.make_rng(cfg, c["seed_key"], repeat)
        parts.append(float(c["mean"]) + float(c["sd"]) * rng.standard_normal(int(c["n"])))
    x = np.concatenate(parts).astype(np.float64)
    if x.shape[0] != int(spec["total"]):
        raise ValueError("一维示例样本数与配置不一致")
    return x
