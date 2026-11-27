"""阈值校准 —— 协议 §5。

规则
----
* 只用 ``validation`` 的**正常样本**异常分数；
* 分位数 0.99，方法写死 ``numpy.quantile(..., method="inverted_cdf")``；
* 判定 ``score > threshold``，**严格大于**；等于阈值判正常；
* 每个 (检测器, 参数配置) **各自独立**校准，两个检测器不共用阈值。

为什么必须是 ``inverted_cdf``
------------------------------
``n=1000`` 时它取第 ``ceil(0.99*1000)=990`` 个次序统计量（0-based 索引 989），于是验证集上
严格超过阈值的样本数恰为 ``1000-990=10``，经验误报率精确等于 **1.00%**。换成其他
``method`` 可能改变阈值和验证集超阈数；本数据上 ``higher`` 给出 9 个超阈样本，
``linear``、``lower``、``nearest``、``midpoint`` 也给出 10。因此协议锁定
``inverted_cdf`` 是为了跨实现统一，而不是因为其他方法在本数据上一定不是 10。
"""

from __future__ import annotations

import numpy as np


def calibrate_threshold(scores_val: np.ndarray, quantile: float = 0.99,
                        method: str = "inverted_cdf") -> float:
    """返回报警阈值（异常分数尺度，越大越异常）。"""
    return float(np.quantile(np.asarray(scores_val, dtype=np.float64), float(quantile), method=method))


def exceedance(scores: np.ndarray, threshold: float) -> int:
    """严格超过阈值的样本数（验证集上应恒为 10）。"""
    return int(np.sum(np.asarray(scores, dtype=np.float64) > float(threshold)))


def predict(scores: np.ndarray, threshold: float) -> np.ndarray:
    """0/1 判定；``score == threshold`` 判为正常（协议 §5 并列处理）。"""
    return (np.asarray(scores, dtype=np.float64) > float(threshold)).astype(np.int64)


def quantile_method_contrast(scores_val: np.ndarray, quantile: float = 0.99) -> dict:
    """对比不同分位数方法在验证集上的超阈数 —— 举证「方法必须锁定」的那一处。

    这条不是协议要求的产物，而是 C 在核验阈值口径时的自查记录：不同 ``method``
    可能改变阈值和超阈数；本数据上 ``higher`` 为 9，其余对照方法为 10。
    协议锁定 ``inverted_cdf`` 是为了跨实现统一。
    """
    out = {}
    for method in ("inverted_cdf", "linear", "higher", "lower", "nearest", "midpoint"):
        try:
            thr = calibrate_threshold(scores_val, quantile, method)
        except (TypeError, ValueError):          # 老 numpy 的 interpolation= 语义
            continue
        out[method] = {"threshold": thr, "n_exceedance": exceedance(scores_val, thr)}
    return out
