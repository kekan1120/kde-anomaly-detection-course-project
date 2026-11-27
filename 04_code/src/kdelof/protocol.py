"""预注册配置的加载与自洽性校验。

设计立场
--------
配置 ``04_code/config_ref.json`` 由 B（数据与实验设计负责人）锁定，C 只读不改。
本模块把「配置自洽」变成可执行的断言：任何一条不满足就立刻抛 ``ProtocolError``，
而不是带着坏配置跑出一份看起来正常的 CSV。这样做的理由很直接 —— 一份跑得通但
网格被改过的结果，比跑不通危险得多。

对应协议条款：§4 参数网格、§5 阈值规则、§6 指标定义、§8 种子登记、§10 泄漏防控。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CONFIG_PATH = Path(__file__).resolve().parents[2] / "config_ref.json"

#: 协议 §4.1 / §4.2 写死的网格字面量。这里再抄一份，是为了能检出「有人悄悄改了 JSON」。
LOCKED_KDE_GRID = [0.1, 0.2, 0.35, 0.5, 0.8, 1.2]
LOCKED_LOF_GRID = [10, 20, 35, 50]
LOCKED_DEFAULT_H = 0.35
LOCKED_DEFAULT_K = 20
LOCKED_QUANTILE = 0.99
LOCKED_QUANTILE_METHOD = "inverted_cdf"


class ProtocolError(RuntimeError):
    """配置与协议不一致。出现即停止，不允许「先跑通再看」。"""


def _require(cond: bool, msg: str) -> None:
    if not cond:
        raise ProtocolError(msg)


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    """读取配置并校验；返回原始 dict（不做任何数值加工）。"""
    p = Path(path) if path is not None else CONFIG_PATH
    with open(p, encoding="utf-8") as fh:
        cfg = json.load(fh)

    splits = cfg["data"]["splits"]
    data = cfg["data"]

    # ---- §2.2 划分：train / validation 只含正常样本
    for name in ("train", "validation"):
        _require(splits[name]["n_anomaly"] == 0, f"{name} 必须只含正常样本（协议 §2.2）")
        _require(
            splits[name]["n_dense"] + splits[name]["n_sparse"] == splits[name]["total"],
            f"{name} 的逐簇计数与总数不一致",
        )

    # ---- §2.2 测试集：总数与异常比例自洽
    t = splits["test"]
    total = t["n_dense"] + t["n_sparse"] + t["n_anomaly"]
    _require(total == t["total"], f"test 总数不一致: {total} != {t['total']}")
    _require(
        abs(t["n_anomaly"] / total - float(t["anomaly_ratio"])) < 1e-12,
        "test 异常比例与配置声明不符（协议 §2.2）",
    )

    # ---- §4.2 LOF 的 k 必须小于训练样本数
    max_k = max(cfg["detectors"]["lof"]["n_neighbors_grid"])
    _require(max_k < splits["train"]["total"], "LOF 邻居数必须小于训练样本数")

    # ---- §2.3 不做标准化
    _require(data["preprocessing"]["scaling"] == "none", "协议规定不做任何特征变换")

    # ---- §5 阈值分位数方法必须锁定
    _require(
        cfg["threshold"]["numpy_method"] == LOCKED_QUANTILE_METHOD,
        f"阈值分位数方法必须是 {LOCKED_QUANTILE_METHOD}（协议 §5）",
    )
    _require(
        abs(float(cfg["threshold"]["quantile"]) - LOCKED_QUANTILE) < 1e-12,
        "阈值分位数必须是 0.99",
    )
    _require(cfg["threshold"]["prediction_rule"].find("严格大于") >= 0, "判定规则必须是严格大于")

    # ---- §4 网格与默认参数不得漂移
    _require(cfg["detectors"]["kde"]["bandwidth_grid"] == LOCKED_KDE_GRID,
             "KDE 带宽网格与协议锁定值不符")
    _require(cfg["detectors"]["lof"]["n_neighbors_grid"] == LOCKED_LOF_GRID,
             "LOF 邻居数网格与协议锁定值不符")
    _require(float(cfg["detectors"]["kde"]["default_bandwidth"]) == LOCKED_DEFAULT_H,
             "默认带宽必须是 h*=0.35")
    _require(int(cfg["detectors"]["lof"]["default_n_neighbors"]) == LOCKED_DEFAULT_K,
             "默认邻居数必须是 k*=20")

    # ---- §3 异常数量与开关一致：未启用的类型数量必须为 0，合计等于 test 的异常数
    n_enabled = 0
    for key in ("far", "near"):
        spec = cfg["anomaly"]["types"][key]
        if spec["enabled"]:
            n_enabled += int(spec["n_test"])
        else:
            _require(int(spec["n_test"]) == 0,
                     f"异常类型 {key} 未启用，但配置里给了 n_test={spec['n_test']}")
    _require(n_enabled == t["n_anomaly"],
             f"启用的异常类型合计 {n_enabled} 与 test.n_anomaly={t['n_anomaly']} 不一致")

    # ---- §3.1 抽样口径（B-v1.1-near 起）：n_test 不能超过 n_draw。
    # 先按固定的 n_draw 抽 (theta, r) 再取前 n_test 行，故 n_draw 决定随机数消耗量；
    # 该口径使「同一条流、不同 n_test」的两个版本点级嵌套。校验放在这里（协议层），
    # dgp.sample_far_ring 里只留一处防御性断言。
    for key in ("far", "near"):
        spec = cfg["anomaly"]["types"][key]
        if not spec["enabled"]:
            continue
        n_test = int(spec["n_test"])
        n_draw = int(spec.get("n_draw", n_test))
        _require(n_test <= n_draw,
                 f"{key}: n_test={n_test} 不能大于 n_draw={n_draw}（协议 §3.1）")

    # ---- §8 一维示例总数自洽
    demo = cfg["demo_1d"]
    _require(demo["components"]["dense"]["n"] + demo["components"]["sparse"]["n"] == demo["total"],
             "一维示例的样本数合计与 total 不一致")

    return cfg


# --------------------------------------------------------------------------------------
# 种子解析（协议 §8）
# --------------------------------------------------------------------------------------


def resolve_seed(cfg: dict[str, Any], stream: str, repeat: int = 0) -> int:
    """把一个数据流解析成整数种子；``repeat=0`` 是锁定的核心运行。"""
    base = int(cfg["seeds"]["streams"][stream])
    if repeat == 0:
        return base
    offset = int(cfg["seeds"]["extension_repeats"]["seed_offset_per_repeat"])
    return base + offset * repeat


def make_rng(cfg: dict[str, Any], stream: str, repeat: int = 0):
    """每个数据流一个独立 PCG64 Generator —— 流之间不共享随机数消耗顺序（协议 §8）。"""
    import numpy as np

    return np.random.Generator(np.random.PCG64(resolve_seed(cfg, stream, repeat)))


def repeat_ids(cfg: dict[str, Any]) -> list[int]:
    """P1 多种子拓展的 repeat 列表（在看测试结果之前已公布）。"""
    return [int(r) for r in cfg["seeds"]["extension_repeats"]["repeat_ids"]]
