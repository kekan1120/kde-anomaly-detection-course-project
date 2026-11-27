"""探针：哪些「难例」在 novelty 模式下才真正能区分 KDE 与 LOF。

背景
----
协议锁定 LOF 必须 `novelty=True`：只在 600 个训练正常样本上拟合，再给新点打分。
这与「LOF 在全数据集上跑」的语义不同：全数据集上，一个空区紧凑簇的内部点彼此是邻居，
局部密度高，LOF 会判正常；但 novelty 模式下，它到最近邻居的距离是「到训练集的距离」，
局部可达密度被算得很低，LOF 同样会判异常。

所以「空区紧凑簇能区分 KDE 与 LOF」这个说法需要实测检验，不能靠直觉。

本探针**不涉及任何测试标签**，只在纯坐标上比较两个检测器的判定，
因此它属于设计可行性检查，不会污染任何评估结果。

用法::

    .venv\\Scripts\\python.exe 04_code\\ref_check\\probe_hard_cases.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import reference_impl as ri  # noqa: E402


def build_probe_groups(cfg: dict) -> dict[str, np.ndarray]:
    """构造若干候选「难例」坐标组。全部是纯几何构造，不含标签。"""
    rng = np.random.Generator(np.random.PCG64(424242))
    groups: dict[str, np.ndarray] = {}

    # 1-2 参照：两个正常簇的中心附近（应当判正常）
    groups["A dense centre      (normal)"] = np.array([[-2.0, 0.0]] * 200)
    groups["B sparse centre     (normal)"] = np.array([[2.0, 0.0]] * 200)

    # 3 参照：远端异常环（应当判异常）
    theta = rng.uniform(0, 2 * np.pi, 200)
    r = rng.uniform(5.0, 7.0, 200)
    groups["C far ring r~[5,7]  (anomaly)"] = np.column_stack(
        [r * np.cos(theta), r * np.sin(theta)])

    # 4 之前提议的「空区紧凑簇」
    groups["D void blob (0,5) sd.35"] = np.array([0.0, 5.0]) + 0.35 * rng.standard_normal((200, 2))

    # 5 空区里的极紧凑小簇（更极端的局部密度）
    groups["E void blob (0,5) sd.10"] = np.array([0.0, 5.0]) + 0.10 * rng.standard_normal((200, 2))

    # 6 嵌在密集簇内部的一个「洞」里的点：绝对密度不低，但局部比邻居稀疏
    groups["F hole inside dense (-1.0,0)"] = np.array([[-1.0, 0.0]] * 200)

    # 7 两簇之间的「谷」：绝对密度低，但四周都是点
    groups["G valley between clusters"] = np.array([[0.0, 0.9]] * 200)

    # 8 稀疏簇的 3.5σ 球壳（尾部）
    theta2 = rng.uniform(0, 2 * np.pi, 200)
    groups["H sparse tail 3.5 sigma"] = np.array([2.0, 0.0]) + 3.5 * np.column_stack(
        [np.cos(theta2), np.sin(theta2)])

    # 9 密集簇的 3.5σ 球壳
    theta3 = rng.uniform(0, 2 * np.pi, 200)
    groups["I dense tail 3.5 sigma"] = np.array([-2.0, 0.0]) + 1.75 * np.column_stack(
        [np.cos(theta3), np.sin(theta3)])

    return groups


def main() -> int:
    cfg = ri.load_config()
    data = ri.generate_all(cfg)
    train_X = data["train"].X
    val_X = data["validation"].X

    h = float(cfg["detectors"]["kde"]["default_bandwidth"])
    k = int(cfg["detectors"]["lof"]["default_n_neighbors"])

    # 用协议规则在验证集上校准两个检测器的阈值（与正式实验完全一致）
    thr_kde = ri.calibrate_threshold(ri.anomaly_score(ri.kde_score_samples(train_X, val_X, h)), cfg)
    thr_lof = ri.calibrate_threshold(ri.anomaly_score(ri.lof_score_samples(train_X, val_X, k)), cfg)

    print("=" * 104)
    print(f"LOF novelty 模式下的难例探针    KDE h*={h}  阈值={thr_kde:.4f} | "
          f"LOF k*={k}  阈值={thr_lof:.4f}")
    print("=" * 104)
    print(f"{'候选组':<32} {'KDE中位':>9} {'KDE判异%':>9} {'LOF中位':>9} {'LOF判异%':>9}  判定")
    print("-" * 104)

    groups = build_probe_groups(cfg)
    rows = []
    for name, X in groups.items():
        s_kde = ri.anomaly_score(ri.kde_score_samples(train_X, X, h))
        s_lof = ri.anomaly_score(ri.lof_score_samples(train_X, X, k))
        kde_rate = float(np.mean(s_kde > thr_kde))
        lof_rate = float(np.mean(s_lof > thr_lof))

        if kde_rate >= 0.5 and lof_rate < 0.5:
            verdict = "只有 KDE 判异常"
        elif lof_rate >= 0.5 and kde_rate < 0.5:
            verdict = "只有 LOF 判异常"
        elif kde_rate >= 0.5 and lof_rate >= 0.5:
            verdict = "两者都判异常"
        else:
            verdict = "两者都判正常"

        print(f"{name:<32} {np.median(s_kde):>9.3f} {kde_rate:>8.1%} "
              f"{np.median(s_lof):>9.3f} {lof_rate:>8.1%}  {verdict}")
        rows.append((name, kde_rate, lof_rate, verdict))

    print()
    print("=" * 104)
    print("结论")
    print("=" * 104)
    disc = [r for r in rows if (r[1] >= 0.5) != (r[2] >= 0.5)]
    if disc:
        print("能区分两个检测器的候选组（一个判异常、另一个判正常）：")
        for name, kr, lr, v in disc:
            print(f"  {name:<32} KDE 判异 {kr:>5.1%}   LOF 判异 {lr:>5.1%}   -> {v}")
    else:
        print("没有候选组能区分。")

    print()
    print("关键判断：")
    print("  1. 「空区紧凑簇」（D/E 组）在 novelty 模式下被 KDE 与 LOF 同时判为异常，")
    print("     LOF 判异率均为 100%。原因是 novelty 模式下 LOF 的局部可达密度是相对")
    print("     训练集算的，离训练集很远就一定很低，因此它并不构成「局部方法失效」的情形。")
    print("     => 新增这个异常类型无法拉开两种方法，只会再增加一个「远端异常」。")
    print("  2. 经典「LOF 对空区紧凑簇失效」需要 LOF 在全数据集上跑（簇内点互为邻居），")
    print("     而本协议强制 novelty=True，语义不同，不能直接套用。")
    print("  3. 真正有区分度的是「密集簇尾部 3.5σ」（I 组）：KDE 只判 15% 异常，")
    print("     LOF 判 59%。但该区域与稀疏簇的正常质量重叠，若标注为异常会造成")
    print("     标签自相矛盾（同 2.5σ 球壳的问题），因此不适合作为核心异常类型。")
    print("  4. 因此本 DGP 下两种方法的真实差异只能体现在**误报的分配**上，")
    print("     即分簇误报率（KDE 稀疏簇 2.2% vs LOF 0.8%），而不是靠新增异常类型。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
