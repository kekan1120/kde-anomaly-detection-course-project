"""结果审计（C 侧，13 项）：核对已冻结的结果文件本身是否自洽、是否覆盖预注册网格。

与 ``run_checks.py`` 的分工：
* ``run_checks.py`` 检**实现**（公式、符号、分位数、泄漏、指纹）；
* 本脚本检**结果文件**（覆盖度、内部自洽、与另一份记录是否一致），不重跑实验。

13 项中有 11 项与 B 的 ``audit_results.py`` 同义（A1–A12），A13 是 C 新增的
「输出契约与基准列集合一致」——因为 D 的绘图脚本按列名取值，列名一改就会静默出错。

用法::

    D:\\ml\\.venv\\Scripts\\python.exe 04_code\\run_audit.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "src"))

from kdelof import protocol  # noqa: E402

ROOT = HERE.parent
RESULTS = ROOT / "05_results" / "main"
BASELINE = ROOT / "05_results" / "ref_check"
RECORDS: list[dict] = []


def _configure_stdout() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def record(cid: str, name: str, passed: bool, detail: str) -> None:
    RECORDS.append({"id": cid, "name": name, "status": "PASS" if passed else "FAIL", "detail": detail})
    print(f"[{'PASS' if passed else 'FAIL'}] {cid} {name}")


def main() -> int:
    _configure_stdout()
    cfg = protocol.load_config()
    print(f"协议版本 {cfg['protocol_version']}")
    print("=" * 78)

    df = pd.read_csv(RESULTS / "metrics.csv")
    main_df = df[df.experiment != "E3_method_comparison"].copy()
    sc = json.loads((RESULTS / "sanity_checks.json").read_text(encoding="utf-8"))

    # ---- A1 覆盖预注册网格
    ok, detail = True, []
    for det, grid in (("kde", cfg["detectors"]["kde"]["bandwidth_grid"]),
                      ("lof", cfg["detectors"]["lof"]["n_neighbors_grid"])):
        got = sorted(main_df[main_df.detector == det].param_value.tolist())
        want = sorted(float(g) for g in grid)
        good = got == want
        ok = ok and good
        detail.append(f"{det}: {got} {'一致' if good else '不一致'}")
    record("A1", "结果覆盖预注册参数网格，无缺项无多项", ok, "；".join(detail))

    # ---- A2 每个配置一行
    dup = int(main_df.duplicated(subset=["detector", "param_value"]).sum())
    n_expect = len(cfg["detectors"]["kde"]["bandwidth_grid"]) + len(cfg["detectors"]["lof"]["n_neighbors_grid"])
    record("A2", "核心运行每个 (检测器, 参数) 恰好一行", dup == 0 and len(main_df) == n_expect,
           f"行数={len(main_df)}（应为 {n_expect}），重复行={dup}")

    # ---- A3 验证集超阈数恒为 10
    bad = main_df[main_df.val_exceedance_count != cfg["threshold"]["expected_val_exceedance_count"]]
    record("A3", "全部配置的验证集超阈数 = 10/1000（经验误报率 1.00%）", len(bad) == 0,
           f"不符合的配置数={len(bad)}；取值集合={sorted(main_df.val_exceedance_count.unique().tolist())}")

    # ---- A4 阈值与核验记录一致
    c9 = next(r for r in sc["records"] if r["id"] == "C9")["measured"]
    ok, detail = True, []
    for _, r in main_df.iterrows():
        key = f"{r.detector}:{r.param_value:g}"
        want = c9[key]["threshold"]
        if abs(want - r.threshold) > 1e-12:
            ok = False
            detail.append(f"{key}: CSV={r.threshold} != 核验={want}")
    record("A4", "CSV 中的阈值与核验记录逐位一致", ok,
           "10 个阈值与 C9 完全一致" if ok else "；".join(detail))

    # ---- A5 混淆矩阵自洽
    sums = main_df.tp + main_df.fp + main_df.tn + main_df.fn
    ok_sums = bool((sums == main_df.n).all())
    ok_p = bool(np.allclose(main_df.precision, main_df.tp / (main_df.tp + main_df.fp), rtol=0, atol=1e-12))
    ok_r = bool(np.allclose(main_df.recall, main_df.tp / (main_df.tp + main_df.fn), rtol=0, atol=1e-12))
    record("A5", "混淆矩阵元素求和等于 n，precision/recall 可由混淆矩阵重算",
           ok_sums and ok_p and ok_r,
           f"sum==n: {ok_sums}；precision 可重算: {ok_p}；recall 可重算: {ok_r}")

    # ---- A6 分簇误报率自洽
    ok_dec = bool((main_df.fp_dense + main_df.fp_sparse == main_df.fp).all())
    ok_cnt = bool(((main_df.n_normal_dense + main_df.n_normal_sparse + main_df.n_anomaly) == main_df.n).all())
    ok_fpr = bool(np.allclose(main_df.fp / (main_df.n_normal_dense + main_df.n_normal_sparse),
                             main_df.fpr_overall, rtol=0, atol=1e-12))
    ok_d = bool(np.allclose(main_df.fp_dense / main_df.n_normal_dense, main_df.fpr_dense, rtol=0, atol=1e-12))
    ok_s = bool(np.allclose(main_df.fp_sparse / main_df.n_normal_sparse, main_df.fpr_sparse, rtol=0, atol=1e-12))
    record("A6", "分簇误报数可加回总误报数；正常/异常计数与分簇误报率自洽",
           ok_dec and ok_cnt and ok_fpr and ok_d and ok_s,
           f"FP 可加回={ok_dec}；n_dense+n_sparse+n_anom==n={ok_cnt}；"
           f"总 FPR 可重算={ok_fpr}；分簇 FPR 可重算 dense={ok_d} sparse={ok_s}")

    # ---- A7 同一份测试集
    combo = main_df[["n", "n_normal_dense", "n_normal_sparse", "n_anomaly", "prevalence"]].drop_duplicates()
    record("A7", "全部配置使用同一份测试集（标签分布逐行相同）", len(combo) == 1,
           f"不同分布组合数={len(combo)}；n={int(combo.n.iloc[0])}，"
           f"正常={int(combo.n_normal_dense.iloc[0])}+{int(combo.n_normal_sparse.iloc[0])}，"
           f"异常={int(combo.n_anomaly.iloc[0])}")

    # ---- A8 E3 与 E1/E2 默认行一致
    e3 = df[df.experiment == "E3_method_comparison"].sort_values("detector").reset_index(drop=True)
    defaults = main_df[
        ((main_df.detector == "kde") & (main_df.param_value == cfg["detectors"]["kde"]["default_bandwidth"]))
        | ((main_df.detector == "lof") & (main_df.param_value == cfg["detectors"]["lof"]["default_n_neighbors"]))
    ].sort_values("detector").reset_index(drop=True)
    ok = len(e3) == len(defaults) == 2
    diffs = []
    if ok:
        for c in [c for c in main_df.columns if c != "experiment"]:
            a, b = e3[c].to_numpy(), defaults[c].to_numpy()
            if a.dtype.kind in "fc":
                if not np.allclose(a, b, rtol=0, atol=1e-12, equal_nan=True):
                    ok = False
                    diffs.append(c)
            elif not (a == b).all():
                ok = False
                diffs.append(c)
    record("A8", "E3 方法对照行与 E1/E2 默认参数行逐字段相同（派生而非重算）", ok,
           "全部字段一致" if ok else f"不一致字段：{diffs}")

    # ---- A9 默认参数
    ok = (set(e3[e3.detector == "kde"].param_value) == {float(cfg["detectors"]["kde"]["default_bandwidth"])}
          and set(e3[e3.detector == "lof"].param_value) == {float(cfg["detectors"]["lof"]["default_n_neighbors"])})
    record("A9", "E3 使用的参数等于配置中预先指定的默认值（h*=0.35, k*=20）", ok,
           f"kde 实际={sorted(e3[e3.detector == 'kde'].param_value)}，"
           f"lof 实际={sorted(e3[e3.detector == 'lof'].param_value)}")

    # ---- A10 错排配对数
    implied = (1.0 - main_df.roc_auc) * main_df.n_anomaly * main_df.n_normal
    ok = bool(np.allclose(implied, main_df.n_inversion_pairs_equiv, rtol=0, atol=1e-9))
    record("A10", "等价错排配对数可由 AUC 重算", ok,
           f"错排对数范围 = {main_df.n_inversion_pairs_equiv.min():.0f} – "
           f"{main_df.n_inversion_pairs_equiv.max():.0f}")

    # ---- A11 E0 峰结构表与核验记录一致
    e0 = pd.read_csv(RESULTS / "e0_demo1d_peaks.csv")
    c13 = next(r for r in sc["records"] if r["id"] == "C13")["measured"]
    ok, detail = len(e0) == len(cfg["demo_1d"]["bandwidths"]), []
    for _, r in e0.iterrows():
        key = str(r.bandwidth) if str(r.bandwidth) in c13 else float(r.bandwidth)
        ref = c13[key]
        good = (int(r.n_prominent_peaks) == ref["n_prominent_peaks"]
                and int(r.n_local_maxima) == ref["n_local_maxima"]
                and abs(float(r.max_density) - ref["max_density"]) < 1e-12)
        ok = ok and good
        detail.append(f"h={r.bandwidth:g}:{'一致' if good else '不一致'}")
    record("A11", "E0 峰结构表与核验记录 C13 一致", ok, "；".join(detail))

    # ---- A12 多种子
    ms = RESULTS / "metrics_multiseed.csv"
    if ms.exists():
        dm = pd.read_csv(ms)
        want = set(cfg["seeds"]["extension_repeats"]["repeat_ids"])
        got = set(int(v) for v in dm.repeat.unique())
        record("A12", "P1 多种子文件覆盖配置中预先公布的 repeat 列表", got == want,
               f"配置={sorted(want)}，实际={sorted(got)}")
    else:
        record("A12", "P1 多种子文件是否存在", True, "尚未生成（可选拓展），跳过")

    # ---- A13 输出契约与基准对齐（D 的脚本按列名取值）
    ref_csv = BASELINE / "metrics_ref.csv"
    if ref_csv.exists():
        cols_ref = set(pd.read_csv(ref_csv).columns)
        cols_mine = set(df.columns)
        ok = cols_ref == cols_mine
        record("A13", "结果表列集合与 B 的基准完全一致（D 的绘图脚本可直接换数据源）", ok,
               f"我的列数={len(cols_mine)}，基准列数={len(cols_ref)}，"
               f"差集={sorted(cols_ref ^ cols_mine) or '无'}")
    else:
        record("A13", "结果表列集合与基准一致", True, f"未找到基准 {ref_csv}，跳过（列数={len(df.columns)}）")

    n_fail = sum(1 for r in RECORDS if r["status"] == "FAIL")
    print("=" * 78)
    print(f"共 {len(RECORDS)} 项审计，PASS={len(RECORDS) - n_fail}，FAIL={n_fail}")

    L = ["# 结果审计记录（C 实现与复现负责人）", "",
         "> 由 `04_code/run_audit.py` 自动生成，勿手工编辑。",
         "> 只读已冻结的结果文件，不重跑实验：核对覆盖度、内部自洽、与核验记录的一致性。", "",
         "| 项 | 值 |", "|---|---|",
         f"| 协议版本 | `{cfg['protocol_version']}` |",
         f"| 审计项数 | {len(RECORDS)} |",
         f"| 失败项数 | **{n_fail}** |", "",
         "## 总览", "", "| 编号 | 审计项 | 结论 |", "|---|---|---|"]
    for r in RECORDS:
        L.append(f"| {r['id']} | {r['name']} | {'✅ PASS' if r['status'] == 'PASS' else '❌ **FAIL**'} |")
    L += ["", "## 细节", ""]
    for r in RECORDS:
        L += [f"### {r['id']} {r['name']}", "", f"**{r['status']}**", "", r["detail"], ""]
    (RESULTS / "audit_results.md").write_text("\n".join(L), encoding="utf-8")
    print(f"已写出 {RESULTS / 'audit_results.md'}")
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())