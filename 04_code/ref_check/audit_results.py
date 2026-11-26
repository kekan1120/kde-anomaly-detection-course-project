"""结果审计：用配置清单逐项核对运行结果与预注册网格是否一致.

这是 B 在阶段 3 的监督产物（协议 §7 的「B 工作流和验收」第 1、2 条）：
不重新跑实验，只检查已冻结的 ``metrics_ref.csv`` 内部是否自洽、是否覆盖了预注册网格、
是否与他处记录一致。

用法::

    .venv\\Scripts\\python.exe 04_code\\ref_check\\audit_results.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import reference_impl as ri  # noqa: E402

HERE = Path(__file__).resolve().parent
RESULTS = HERE.parent.parent / "05_results" / "ref_check"

RECORDS: list[dict] = []


def record(cid: str, name: str, passed: bool, detail: str) -> None:
    RECORDS.append({"id": cid, "name": name, "status": "PASS" if passed else "FAIL", "detail": detail})
    print(f"[{'PASS' if passed else 'FAIL'}] {cid} {name}")
    if not passed:
        print(f"        !! {detail}")


def main() -> int:
    cfg = ri.load_config()
    print(f"协议版本 {cfg['protocol_version']}")
    print("=" * 78)

    df = pd.read_csv(RESULTS / "metrics_ref.csv")
    main_df = df[df.experiment != "E3_method_comparison"]

    # ---- A1 覆盖预注册网格，且不多不少
    expected = {
        ("kde", "E1_kde_sensitivity"): cfg["detectors"]["kde"]["bandwidth_grid"],
        ("lof", "E2_lof_sensitivity"): cfg["detectors"]["lof"]["n_neighbors_grid"],
    }
    ok = True
    detail = []
    for (det, exp), grid in expected.items():
        got = sorted(main_df[main_df.detector == det].param_value.tolist())
        want = sorted(float(g) for g in grid)
        good = np.allclose(got, want, atol=0, rtol=0) and len(got) == len(want)
        ok = ok and good
        detail.append(f"{det}: {len(got)} 个取值 {'一致' if good else '不一致'} -> {got}")
    record("A1", "结果覆盖预注册参数网格，无缺项无多项", ok, "；".join(detail))

    # ---- A2 每个配置只出现一次（repeat 0）
    dup = main_df.duplicated(subset=["detector", "param_value"]).sum()
    n_expect = len(cfg["detectors"]["kde"]["bandwidth_grid"]) + len(cfg["detectors"]["lof"]["n_neighbors_grid"])
    record(
        "A2", "核心运行每个 (检测器, 参数) 恰好一行", dup == 0 and len(main_df) == n_expect,
        f"行数={len(main_df)}（应为 {n_expect}），重复行={int(dup)}",
    )

    # ---- A3 阈值校准：全部配置的验证集超阈数 = 10
    bad = main_df[main_df.val_exceedance_count != cfg["threshold"]["expected_val_exceedance_count"]]
    record(
        "A3", "全部配置的验证集超阈数 = 10/1000（经验误报率 1.00%）", len(bad) == 0,
        f"不符合的配置数={len(bad)}；取值范围={main_df.val_exceedance_count.min()}–{main_df.val_exceedance_count.max()}",
    )

    # ---- A4 阈值与 sanity_checks.json 记录一致
    sc = json.loads((RESULTS / "sanity_checks.json").read_text(encoding="utf-8"))
    c9 = next(r for r in sc["records"] if r["id"] == "C9")["measured"]
    ok = True
    detail = []
    for _, r in main_df.iterrows():
        key = f"{r.detector}:{r.param_value:g}"
        want = c9[key]["threshold"]
        if abs(want - r.threshold) > 1e-12:
            ok = False
            detail.append(f"{key}: {r.threshold} != {want}")
    record("A4", "CSV 中的阈值与核验记录逐位一致", ok,
           "10 个阈值全部一致" if ok else "；".join(detail))

    # ---- A5 混淆矩阵自洽
    sums = main_df.tp + main_df.fp + main_df.tn + main_df.fn
    ok_sums = bool(np.all(sums == main_df.n))
    ok_p = bool(np.allclose(main_df.precision, main_df.tp / (main_df.tp + main_df.fp), rtol=0, atol=1e-12))
    ok_r = bool(np.allclose(main_df.recall, main_df.tp / (main_df.tp + main_df.fn), rtol=0, atol=1e-12))
    record("A5", "混淆矩阵元素求和等于 n，precision/recall 可由混淆矩阵重算", ok_sums and ok_p and ok_r,
           f"sum==n: {ok_sums}；precision 可重算: {ok_p}；recall 可重算: {ok_r}")

    # ---- A6 分簇误报率可加回总误报率；正常样本分簇计数自洽
    ok_dec = bool((main_df.fp_dense + main_df.fp_sparse == main_df.fp).all())
    ok_cnt = bool(np.all(
        main_df.n_normal_dense + main_df.n_normal_sparse + main_df.n_anomaly == main_df.n))
    ok_fpr = bool(np.allclose(
        main_df.fp / (main_df.n_normal_dense + main_df.n_normal_sparse), main_df.fpr_overall,
        rtol=0, atol=1e-12))
    ok_rate_d = bool(np.allclose(
        main_df.fp_dense / main_df.n_normal_dense, main_df.fpr_dense, rtol=0, atol=1e-12))
    ok_rate_s = bool(np.allclose(
        main_df.fp_sparse / main_df.n_normal_sparse, main_df.fpr_sparse, rtol=0, atol=1e-12))
    record("A6", "分簇误报数可加回总误报数；正常/异常计数与分簇误报率自洽",
           ok_dec and ok_cnt and ok_fpr and ok_rate_d and ok_rate_s,
           f"FP 可加回: {ok_dec}；n_dense+n_sparse+n_anom==n: {ok_cnt}；FPR 可重算: {ok_fpr}；"
           f"分簇 FPR 可重算: dense={ok_rate_d} sparse={ok_rate_s}")

    # ---- A7 测试集标签分布在全部行中完全相同（同一份测试集）
    combo = main_df[["n", "n_normal_dense", "n_normal_sparse", "n_anomaly", "prevalence"]].drop_duplicates()
    record("A7", "全部配置使用同一份测试集（标签分布逐行相同）", len(combo) == 1,
           f"不同的分布组合数={len(combo)}；n={int(combo.n.iloc[0])}, "
           f"正常={int(combo.n_normal_dense.iloc[0])}+{int(combo.n_normal_sparse.iloc[0])}, "
           f"异常={int(combo.n_anomaly.iloc[0])}")

    # ---- A8 E3 与 E1/E2 默认参数行逐字段相同
    e3 = df[df.experiment == "E3_method_comparison"].sort_values("detector").reset_index(drop=True)
    defaults = main_df[
        ((main_df.detector == "kde") & (main_df.param_value == cfg["detectors"]["kde"]["default_bandwidth"]))
        | ((main_df.detector == "lof") & (main_df.param_value == cfg["detectors"]["lof"]["default_n_neighbors"]))
    ].sort_values("detector").reset_index(drop=True)
    metric_cols = [c for c in main_df.columns if c not in ("experiment",)]
    ok = len(e3) == len(defaults) == 2
    diffs = []
    if ok:
        for c in metric_cols:
            a, b = e3[c].to_numpy(), defaults[c].to_numpy()
            if a.dtype.kind in "fc":
                if not np.allclose(a, b, rtol=0, atol=1e-12, equal_nan=True):
                    ok = False
                    diffs.append(c)
            elif not (a == b).all():
                ok = False
                diffs.append(c)
    record("A8", "E3 方法对照行与 E1/E2 默认参数行逐字段相同（未重复计算、未手工抄数）", ok,
           "全部字段一致" if ok else f"不一致字段：{diffs}")

    # ---- A9 默认参数确实是配置里预先指定的值
    ok = (set(e3[e3.detector == "kde"].param_value) == {float(cfg["detectors"]["kde"]["default_bandwidth"])}
          and set(e3[e3.detector == "lof"].param_value) == {float(cfg["detectors"]["lof"]["default_n_neighbors"])})
    record("A9", "E3 使用的参数等于配置中预先指定的默认值（h*=0.35, k*=20）", ok,
           f"kde 实际={sorted(e3[e3.detector == 'kde'].param_value)}, "
           f"lof 实际={sorted(e3[e3.detector == 'lof'].param_value)}")

    # ---- A10 错排配对数与 AUC 自洽
    implied = (1.0 - main_df.roc_auc) * main_df.n_anomaly * main_df.n_normal
    ok = bool(np.allclose(implied, main_df.n_inversion_pairs_equiv, rtol=0, atol=1e-9))
    record("A10", "等价错排配对数可由 AUC 重算", ok,
           f"各配置错排对数范围 = {main_df.n_inversion_pairs_equiv.min():.0f} – "
           f"{main_df.n_inversion_pairs_equiv.max():.0f}")

    # ---- A11 E0 峰结构表与核验记录一致
    e0 = pd.read_csv(RESULTS / "e0_demo1d_peaks.csv")
    c13 = next(r for r in sc["records"] if r["id"] == "C13")["measured"]
    ok = len(e0) == len(cfg["demo_1d"]["bandwidths"])
    detail = []
    for _, r in e0.iterrows():
        ref = c13[str(r.bandwidth)] if str(r.bandwidth) in c13 else c13[float(r.bandwidth)]
        good = (int(r.n_prominent_peaks) == ref["n_prominent_peaks"]
                and int(r.n_local_maxima) == ref["n_local_maxima"]
                and abs(float(r.max_density) - ref["max_density"]) < 1e-12)
        ok = ok and good
        detail.append(f"h={r.bandwidth:g}:{'一致' if good else '不一致'}")
    record("A11", "E0 峰结构表与核验记录 C13 一致", ok, "；".join(detail))

    # ---- A12 多种子文件存在且种子列表与配置一致（若已生成）
    ms = RESULTS / "metrics_ref_multiseed.csv"
    if ms.exists():
        dm = pd.read_csv(ms)
        want = set(cfg["seeds"]["extension_repeats"]["repeat_ids"])
        got = set(int(v) for v in dm.repeat.unique())
        ok = got == want
        record("A12", "P1 多种子文件覆盖配置中预先公布的 repeat 列表", ok,
               f"配置={sorted(want)}，实际={sorted(got)}")
    else:
        record("A12", "P1 多种子文件是否存在", True, "尚未生成（可选拓展），跳过")

    n_fail = sum(1 for r in RECORDS if r["status"] == "FAIL")
    print("=" * 78)
    print(f"共 {len(RECORDS)} 项审计，PASS={len(RECORDS) - n_fail}，FAIL={n_fail}")

    (RESULTS / "audit_results.md").write_text(render_markdown(cfg, n_fail), encoding="utf-8")
    print(f"已写出 {RESULTS / 'audit_results.md'}")
    return 0 if n_fail == 0 else 1


def render_markdown(cfg: dict, n_fail: int) -> str:
    L = [
        "# 结果审计记录（B 的阶段 3 监督产物）",
        "",
        "> 由 `04_code/ref_check/audit_results.py` 自动生成，勿手工编辑。",
        "> 作用：不重跑实验，只核验已冻结的 `metrics_ref.csv` 是否覆盖预注册网格、内部是否自洽、"
        "是否与其他记录一致。",
        "",
        f"| 项 | 值 |",
        f"|---|---|",
        f"| 协议版本 | `{cfg['protocol_version']}` |",
        f"| 审计项数 | {len(RECORDS)} |",
        f"| 失败项数 | **{n_fail}** |",
        "",
        "## 总览",
        "",
        "| 编号 | 审计项 | 结论 |",
        "|---|---|---|",
    ]
    for r in RECORDS:
        L.append(f"| {r['id']} | {r['name']} | {'✅ PASS' if r['status'] == 'PASS' else '❌ **FAIL**'} |")
    L += ["", "## 细节", ""]
    for r in RECORDS:
        L += [f"### {r['id']} {r['name']}", "", f"**{r['status']}**", "", r["detail"], ""]
    return "\n".join(L)


if __name__ == "__main__":
    raise SystemExit(main())
