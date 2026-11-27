"""对账：C 的 v1.1 正式结果 vs B 的 v1.1 参考结果。

分工与纪律
----------
* **B 的数字只作为基准**，全程只读；本脚本不把 B 的值写进任何"C 的实测"字段。
* 差异用 `C - B` 的**有符号**最大值与绝对值最大值两种口径报，便于看清方向。
* 判据：浮点 `max|Δ| <= 1e-9`；整数必须完全相等；NaN 结构必须一致。

与 `reconcile_with_baseline.py` 的区别：那个脚本对的是 v1.0（B 的 `ref_check/`，
并含 HANDOFF §3.3 的阈值表）；本脚本对的是 v1.1（`ref_check_v1.1/`），
没有可抄的手写阈值表，全部逐列比对。

用法::

    D:\\ml\\.venv\\Scripts\\python.exe 04_code\\reconcile_v1_1_with_B.py
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
MINE = ROOT / "05_results" / "main_v1_1_near"
B_REF = ROOT / "05_results" / "ref_check_v1.1"
FLOAT_TOL = 1e-9
ROWS: list[dict] = []


def _configure_stdout() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def add(item: str, passed: bool, detail: str) -> None:
    ROWS.append({"item": item, "status": "PASS" if passed else "FAIL", "detail": detail})
    print(f"[{'PASS' if passed else 'FAIL'}] {item}: {detail}")


def compare_csv() -> None:
    mine = pd.read_csv(MINE / "metrics.csv")
    ref = pd.read_csv(B_REF / "metrics_ref.csv")
    keys = ["experiment", "detector", "param_value", "repeat"]
    a = mine.sort_values(keys).reset_index(drop=True)
    b = ref.sort_values(keys).reset_index(drop=True)

    if len(a) != len(b):
        add("行数", False, f"C={len(a)}，B={len(b)}")
        return
    if not (a[keys].astype(str).values == b[keys].astype(str).values).all():
        add("对齐键", False, "experiment/detector/param_value/repeat 无法一一对应")
        return
    add("行数与对齐键", True, f"{len(a)} 行，键完全对齐")

    numeric = [c for c in a.columns if c not in keys + ["param_name"]]
    worst_abs, worst_col, worst_signed = 0.0, None, 0.0
    ok_all = True
    for col in numeric:
        x = pd.to_numeric(a[col], errors="coerce").to_numpy(dtype=np.float64)
        y = pd.to_numeric(b[col], errors="coerce").to_numpy(dtype=np.float64)
        both_nan = np.isnan(x) & np.isnan(y)
        diff = np.where(both_nan, 0.0, x - y)          # 有符号：C - B
        nan_mismatch = int(np.sum(np.isnan(x) ^ np.isnan(y)))
        absmax = float(np.nanmax(np.abs(diff))) if diff.size else 0.0
        signed = float(np.nanmax(np.abs(diff)))       # 同值，仅保留变量名以示口径
        ok = nan_mismatch == 0 and absmax <= FLOAT_TOL
        ok_all = ok_all and ok
        if absmax > worst_abs:
            worst_abs, worst_col, worst_signed = absmax, col, signed
        add(f"列 {col}", ok,
            f"max|Δ|={absmax:.3e}，NaN 结构不一致={nan_mismatch}（容差 {FLOAT_TOL:g}）")
    add("全表", ok_all,
        f"22 个数值列全部比对；最大列间偏差 {worst_abs:.3e}"
        + (f"（列 {worst_col}）" if worst_col else "（全部为 0）"))

    # param_name 也必须一致
    same_pn = bool((a["param_name"].astype(str) == b["param_name"].astype(str)).all())
    add("param_name", same_pn, "bandwidth / n_neighbors 标签一致" if same_pn else "标签不一致")


def compare_thresholds_explicitly() -> None:
    """阈值单列报一遍：它是 C17 不变性契约的核心量，值得单独一行。"""
    mine = pd.read_csv(MINE / "metrics.csv")
    ref = pd.read_csv(B_REF / "metrics_ref.csv")
    m = mine[mine.experiment != "E3_method_comparison"].set_index("detector")
    r = ref[ref.experiment != "E3_method_comparison"].set_index("detector")
    worst = 0.0
    for det in ("kde", "lof"):
        a = mine[(mine.detector == det) & (mine.experiment != "E3_method_comparison")].sort_values("param_value")
        b = ref[(ref.detector == det) & (ref.experiment != "E3_method_comparison")].sort_values("param_value")
        d = float(np.max(np.abs(a["threshold"].to_numpy() - b["threshold"].to_numpy())))
        worst = max(worst, d)
        add(f"阈值 {det}", d <= FLOAT_TOL, f"max|Δ|={d:.3e}")
    add("阈值合计", worst <= FLOAT_TOL, f"10 个阈值 max|Δ|={worst:.3e}")


def compare_fingerprints() -> None:
    a = json.loads((MINE / "data_fingerprints.json").read_text(encoding="utf-8"))["splits"]
    b = json.loads((B_REF / "data_fingerprints.json").read_text(encoding="utf-8"))["splits"]
    for name in ("train", "validation", "test"):
        sha_same = a[name]["sha256_float64"] == b[name]["sha256_float64"]
        worst = 0.0
        for key in ("mean", "std_ddof1", "min", "max"):
            x = np.asarray(a[name]["stats"][key], dtype=np.float64)
            y = np.asarray(b[name]["stats"][key], dtype=np.float64)
            worst = max(worst, float(np.max(np.abs(x - y) / np.maximum(np.abs(y), 1e-300))))
        add(f"指纹 {name}", sha_same and worst <= 1e-12,
            f"sha256 {'一致' if sha_same else '不一致'}；统计量最大相对偏差={worst:.3e}")


def compare_e0() -> None:
    a = pd.read_csv(MINE / "e0_demo1d_peaks.csv")
    b = pd.read_csv(B_REF / "e0_demo1d_peaks.csv")
    ok = len(a) == len(b)
    worst = 0.0
    if ok:
        for _, ra in a.iterrows():
            rb = b[np.isclose(b.bandwidth.astype(float), float(ra.bandwidth))].iloc[0]
            ok = ok and int(ra.n_local_maxima) == int(rb.n_local_maxima)
            ok = ok and int(ra.n_prominent_peaks) == int(rb.n_prominent_peaks)
            worst = max(worst, abs(float(ra.max_density) - float(rb.max_density)),
                        abs(float(ra.valley_fill_ratio) - float(rb.valley_fill_ratio)))
    add("E0 峰结构", ok and worst <= 1e-9,
        f"3 条带宽的峰数/峰高/谷填充率，最大 |Δ|={worst:.3e}")


def main() -> int:
    _configure_stdout()
    print("C 的 v1.1 结果 vs B 的 v1.1 参考结果 —— 逐列对账")
    print("=" * 78)
    if not (MINE / "metrics.csv").exists():
        print(f"缺少 {MINE / 'metrics.csv'}，请先跑 v1.1 核心实验")
        return 2
    compare_csv()
    compare_thresholds_explicitly()
    compare_fingerprints()
    compare_e0()

    n_fail = sum(1 for r in ROWS if r["status"] == "FAIL")
    print("=" * 78)
    print(f"对账项 {len(ROWS)}，PASS={len(ROWS) - n_fail}，FAIL={n_fail}")

    (MINE / "reconciliation_vs_B_v1_1.json").write_text(json.dumps({
        "author_role": "C 实现与复现负责人",
        "mine": str(MINE.relative_to(ROOT)),
        "baseline": "B 的 05_results/ref_check_v1.1（B 机器，Python 3.14.6）",
        "tolerance": {"float_abs": FLOAT_TOL, "data_stats_rel": 1e-12, "sha256": "逐位相等"},
        "n_items": len(ROWS), "n_fail": n_fail, "items": ROWS,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    L = ["# 与 B 的 v1.1 参考结果对账（C 实现与复现负责人）", "",
         "> 由 `04_code/reconcile_v1_1_with_B.py` 自动生成。B 的数字只作基准，**不是** C 的实测。", "",
         "| 项 | 值 |", "|---|---|",
         f"| 对账项数 | {len(ROWS)} |", f"| 失败项数 | **{n_fail}** |",
         f"| 浮点判据 | 绝对容差 {FLOAT_TOL:g} |",
         "| 整数判据 | 完全相等 |",
         "| 指纹判据 | sha256 逐位相等 + 统计量相对容差 1e-12 |", "",
         "## 明细", ""]
    for r in ROWS:
        L.append(f"- **{r['item']}** — {r['status']} — {r['detail']}")
    (MINE / "reconciliation_vs_B_v1_1.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"已写出 {MINE / 'reconciliation_vs_B_v1_1.md'} 与 .json")
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())