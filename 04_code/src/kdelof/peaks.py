"""一维密度曲线的峰结构 —— 协议 §7.1。

口径（写死在协议里，正文图注必须沿用同一口径）
-----------------------------------------------
* **局部极大点**：``p[i-1] < p[i] >= p[i+1]`` 意义上的内部点（与 ``numpy.diff`` 判号等价）。
* **显著峰**：``prominence >= 10% × 全局最大密度`` 的局部极大点。
* **prominence**：从峰顶向两侧走到**第一个更高**的点，取两侧最低点中较高者作基准，峰顶减该基准。
* **两主峰间谷填充率**：两个最高局部极大点之间的最低密度 ÷ 两者中较低的峰高。
  该比值从 0（谷被完全分开）升到 1（谷被填平），是 H1「带宽增大抹平多峰」的直接观测量。

为什么要 prominence 而不是数极大点：小带宽下每条样本都会顶出一个尖，这些尖的 prominence
极小，若一律算成峰，会得到「h 越小峰越多」的假结论。
"""

from __future__ import annotations

import numpy as np

#: 「显著峰」判定阈值，占全局最大密度的比例。协议 §7.1 锁定为 10%。
PROMINENCE_FRAC = 0.10


def local_maxima(p: np.ndarray) -> list[int]:
    """内部局部极大点下标（不含首尾端点）。"""
    p = np.asarray(p, dtype=np.float64)
    d = np.diff(p)
    return [int(i) for i in np.where((d[:-1] > 0) & (d[1:] <= 0))[0] + 1]


def prominence(p: np.ndarray, i: int) -> float:
    """峰 i 的 prominence（地形学定义，见模块文档）。"""
    p = np.asarray(p, dtype=np.float64)
    n = len(p)
    top = float(p[i])

    left_min = top
    j = i
    while j > 0:
        j -= 1
        if p[j] > top:
            break
        left_min = min(left_min, float(p[j]))

    right_min = top
    j = i
    while j < n - 1:
        j += 1
        if p[j] > top:
            break
        right_min = min(right_min, float(p[j]))

    return float(top - max(left_min, right_min))


def valley_fill_ratio(p: np.ndarray) -> float | None:
    """两个最高局部极大点之间的最低密度 ÷ 较低峰高；局部极大点不足 2 个时返回 None。"""
    loc = local_maxima(p)
    if len(loc) < 2:
        return None
    top2 = sorted(loc, key=lambda i: -float(p[i]))[:2]
    lo, hi = sorted(top2)
    valley = float(np.min(p[lo:hi + 1]))
    lower_peak = min(float(p[top2[0]]), float(p[top2[1]]))
    return valley / lower_peak if lower_peak > 0 else None


def describe_curve(p: np.ndarray, xs: np.ndarray, prominence_frac: float = PROMINENCE_FRAC) -> dict:
    """给一条密度曲线出完整峰结构描述（E0 的表格一行）。"""
    p = np.asarray(p, dtype=np.float64)
    xs = np.asarray(xs, dtype=np.float64)
    loc = local_maxima(p)
    pmax = float(p.max())
    prom = {i: prominence(p, i) for i in loc}
    prominent = sorted([i for i in loc if prom[i] >= prominence_frac * pmax], key=lambda i: -float(p[i]))

    return {
        "n_local_maxima": len(loc),
        "n_prominent_peaks": len(prominent),
        "max_density": pmax,
        "valley_fill_ratio": valley_fill_ratio(p),
        "prominent_peaks": [
            {"x": float(xs[i]), "height": float(p[i]), "prominence_ratio": float(prom[i] / pmax)}
            for i in prominent
        ],
        "all_prominences": [
            {"x": float(xs[i]), "prominence_ratio": float(prom[i] / pmax)} for i in loc
        ],
    }