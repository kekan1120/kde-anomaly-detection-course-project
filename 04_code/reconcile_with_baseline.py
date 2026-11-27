"""对账：C 的结果 vs B 的参考结果（逐列、逐项）。

这是 C 的核心验收动作（规划 PDF 阶段 2：「至少一次由 C 以外成员在干净运行中复现核心结果，
核心数值在预先约定的容差内一致」的镜像：C 在**独立实现**上复现 B 的基准）。

对账分四层，每层用不同的判据：

1. **数据层**：三个划分的 sha256 与统计量 —— 要求 sha256 逐位一致，统计量相对容差 1e-12。
2. **阈值层**：10 个 (检测器, 参数) 阈值与 `HANDOFF_README.md` §3.3 的 4 位小数表比对。
3. **指标层**：`metrics.csv` 与 B 的 `metrics_ref.csv` 逐列比对，浮点绝对容差 1e-9、
   整数必须完全相等 —— 两边的 AUC/AP 是各自的独立实现（C 用 scipy 平均秩 + 阶梯求和，
   B 用手写循环），1e-9 已是极严的判据。
4. **多种子层**：`metrics_multiseed_summary.csv` 与 B 的同名汇总逐列比对。

用法::

    D:\\ml\\.venv\\Scripts\\python.exe 04_code/reconcile_with_baseline.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "src"))

ROOT = HERE.parent
MINE = ROOT / "05_results" / "main"
BASELINE = ROOT / "05_results" / "ref_check"

#: HANDOFF_README.md §3.3 的阈值表（B 在另一台机器、Python 3.14 上跑出的结果，用于独立核对）。
BASELINE_THRESHOLDS_4DP = {
    "kde:0.1": 15.727733,
    "kde:0.2": 7.896117,
    "kde:0.35": 6.176033,
    "kde:0.5": 5.777108,
    "kde:0.8": 5.249742,
    "kde:1.2": 4.801341,
    "lof:10": 1.893115,
    "lof:20": 2.022293,
    "lof:35": 1.966556,
    "lof:50": 1.937930,
}

#: HANDOFF_README.md §3.5 的 E0 峰结构表（局部极大点数, 显著峰数, 最大密度, 谷填充率）。
BASELINE_E0 = {
    0.08: {"n_local_maxima": 8, "n_prominent_peaks": 2, "max_density": 1.0705, "valley_fill_ratio": 0.0007},
    0.30: {"n_local_maxima": 3, "n_prominent_peaks": 2, "max_density": 0.6254, "valley_fill_ratio": 0.1581},
    0.90: {"n_local_maxima": 2, "n_prominent_peaks": 1, "max_density": 0.2629, "valley_fill_ratio": 0.9140},
}

FLOAT_TOL = 1e-9
STATS_TOL = 1e-12
ROWS: list[dict] = []


def _configure_stdout() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def add(section: str, item: str, passed: bool, detail: str) -> None:
    ROWS.append({"section": section, "item": item, "status": "PASS" if passed else "FAIL", "detail": detail})
    print(f"[{'PASS' if passed else 'FAIL'}] {section} / {item}: {detail}")


# --------------------------------------------------------------------------------------


def compare_data_fingerprints() -> None:
    mine = json.loads((MINE / "data_fingerprints.json").read_text(encoding="utf-8"))["splits"]
    ref = json.loads((BASELINE / "data_fingerprints.json").read_text(encoding="utf-8"))["splits"]
    for name in ("train", "validation", "test"):
        sha_ok = mine[name]["sha256_float64"] == ref[name]["sha256_float64"]
        worst = 0.0
        for key in ("mean", "std_ddof1", "min", "max"):
            a = np.asarray(mine[name]["stats"][key], dtype=np.float64)
            b = np.asarray(ref[name]["stats"][key], dtype=np.float64)
            worst = max(worst, float(np.max(np.abs(a - b) / np.maximum(np.abs(b), 1e-300))))
        add("数据层", f"{name}.sha256", sha_ok,
            f"{mine[name]['sha256_float64'][:32]} vs {ref[name]['sha256_float64'][:32]}")
        add("数据层", f"{name}.stats", worst <= STATS_TOL,
            f"相对容差判据 {STATS_TOL:g}，实测最大相对偏差 {worst:.3e}")


def compare_thresholds() -> None:
    df = pd.read_csv(MINE / "metrics.csv")
    main = df[df.experiment != "E3_method_comparison"]
    worst = 0.0
    for _, r in main.iterrows():
        key = f"{r.detector}:{r.param_value:g}"
        want = BASELINE_THRESHOLDS_4DP[key]
        # 基准表只有 4 位小数，故按 5e-7 判据（= 4 位小数舍入的半个单位）
        dev = abs(float(r.threshold) - want)
        worst = max(worst, dev)
        add("阈值层", f"threshold[{key}]", dev <= 5e-7,
            f"C={r.threshold:.6f}，HANDOFF §3.3={want:.6f}，偏差={dev:.2e}")
    print(f"    -> 阈值最大偏差 {worst:.2e}（判据 5e-7，即基准表 4 位小数的舍入单位）")


def compare_metrics() -> None:
    mine = pd.read_csv(MINE / "metrics.csv")
    ref = pd.read_csv(BASELINE / "metrics_ref.csv")
    keys = ["experiment", "detector", "param_value", "repeat"]
    m = mine.sort_values(keys).reset_index(drop=True)
    r = ref.sort_values(keys).reset_index(drop=True)
    if len(m) != len(r):
        add("指标层", "行数", False, f"C={len(m)} 行，基准={len(r)} 行")
        return
    if not (m[keys].astype(str).values == r[keys].astype(str).values).all():
        add("指标层", "对齐键", False, "行对齐失败：experiment/detector/param_value/repeat 不一致")
        return

    numeric = [c for c in mine.columns if c not in keys + ["param_name"]]
    for col in numeric:
        a = pd.to_numeric(m[col], errors="coerce").to_numpy(dtype=np.float64)
        b = pd.to_numeric(r[col], errors="coerce").to_numpy(dtype=np.float64)
        both_nan = np.isnan(a) & np.isnan(b)
        dev = np.where(both_nan, 0.0, np.abs(a - b))
        nan_mismatch = int(np.sum(np.isnan(a) ^ np.isnan(b)))
        worst = float(np.nanmax(dev)) if len(dev) else 0.0
        ok = nan_mismatch == 0 and worst <= FLOAT_TOL
        add("指标层", col, ok,
            f"最大绝对偏差={worst:.3e}，NaN 结构不一致点={nan_mismatch}（容差 {FLOAT_TOL:g}）")
    param_name_same = bool((m["param_name"].astype(str) == r["param_name"].astype(str)).all())
    add("指标层", "param_name", param_name_same, "bandwidth / n_neighbors 标签一致" if param_name_same else "标签不一致")


def compare_multiseed() -> None:
    mine_path = MINE / "metrics_multiseed_summary.csv"
    ref_path = BASELINE / "metrics_ref_multiseed_summary.csv"
    if not (mine_path.exists() and ref_path.exists()):
        add("多种子层", "文件存在性", False, f"C={mine_path.exists()}，基准={ref_path.exists()}")
        return
    m = pd.read_csv(mine_path).sort_values(["detector", "param_value"]).reset_index(drop=True)
    r = pd.read_csv(ref_path).sort_values(["detector", "param_value"]).reset_index(drop=True)
    cols = [c for c in r.columns if c in m.columns]
    ok = len(m) == len(r)
    worst = 0.0
    for c in cols:
        if c in ("detector", "param_value"):
            ok = ok and bool((m[c].astype(str) == r[c].astype(str)).all())
        else:
            a, b = m[c].to_numpy(dtype=np.float64), r[c].to_numpy(dtype=np.float64)
            dev = float(np.max(np.abs(a - b)))
            worst = max(worst, dev)
            ok = ok and dev <= FLOAT_TOL
    add("多种子层", "10 个 seeds 的均值/标准差/召回", ok,
        f"共 {len(cols)} 列，最大绝对偏差={worst:.3e}（容差 {FLOAT_TOL:g}）")


def compare_e0() -> None:
    df = pd.read_csv(MINE / "e0_demo1d_peaks.csv")
    for _, row in df.iterrows():
        h = round(float(row.bandwidth), 2)
        ref = BASELINE_E0.get(h) or BASELINE_E0.get(float(row.bandwidth))
        if ref is None:
            add("E0 层", f"h={row.bandwidth:g}", False, "基准表里没有这个带宽")
            continue
        ok = (int(row.n_local_maxima) == ref["n_local_maxima"]
              and int(row.n_prominent_peaks) == ref["n_prominent_peaks"]
              and abs(float(row.max_density) - ref["max_density"]) < 1e-4
              and abs(float(row.valley_fill_ratio) - ref["valley_fill_ratio"]) < 1e-4)
        add("E0 层", f"h={row.bandwidth:g}", ok,
            f"C: 局部极大={int(row.n_local_maxima)}/显著峰={int(row.n_prominent_peaks)}/"
            f"最大密度={row.max_density:.4f}/谷填充率={row.valley_fill_ratio:.4f}；"
            f"基准: {ref['n_local_maxima']}/{ref['n_prominent_peaks']}/"
            f"{ref['max_density']:.4f}/{ref['valley_fill_ratio']:.4f}")


def main() -> int:
    _configure_stdout()
    print("C 的结果 vs B 的基准 —— 逐项对账")
    print("=" * 78)
    compare_data_fingerprints()
    compare_thresholds()
    compare_metrics()
    compare_multiseed()
    compare_e0()

    n_fail = sum(1 for r in ROWS if r["status"] == "FAIL")
    print("=" * 78)
    print(f"对账项 {len(ROWS)}，PASS={len(ROWS) - n_fail}，FAIL={n_fail}")

    (MINE / "reconciliation.json").write_text(json.dumps({
        "author_role": "C 实现与复现负责人",
        "baseline": "B 的 05_results/ref_check（另一台机器，Python 3.14.6）",
        "tolerances": {"data_sha256": "逐位相等", "data_stats": STATS_TOL,
                       "metrics_float": FLOAT_TOL, "e0": 1e-4},
        "n_items": len(ROWS), "n_fail": n_fail, "items": ROWS,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    L = ["# 与 B 基准的对账记录（C 实现与复现负责人）", "",
         "> 由 `04_code/reconcile_with_baseline.py` 自动生成，勿手工编辑。", "",
         f"| 项 | 值 |", "|---|---|",
         f"| 对账项数 | {len(ROWS)} |", f"| 失败项数 | **{n_fail}** |",
         f"| 数据 sha256 判据 | 逐位相等 |",
         f"| 数据统计量判据 | 相对容差 {STATS_TOL:g} |",
         f"| 指标判据 | 绝对容差 {FLOAT_TOL:g} |",
         f"| E0 判据 | 1e-4（基准表 4 位小数） |", "",
         "## 总览", "", "| 层 | 项目 | 结论 |", "|---|---|---|"]
    for r in ROWS:
        L.append(f"| {r['section']} | {r['item']} | {'✅ PASS' if r['status'] == 'PASS' else '❌ **FAIL**'} |")
    L += ["", "## 细节", ""]
    for r in ROWS:
        L.append(f"- **{r['section']} / {r['item']}** — {r['status']} — {r['detail']}")
    (MINE / "reconciliation_vs_B.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"已写出 {MINE / 'reconciliation_vs_B.md'} 与 reconciliation.json")
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())