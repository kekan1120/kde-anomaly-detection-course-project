"""全量实验入口（C 实现与复现负责人）。

用法（在项目根目录执行）::

    D:\\ml\\.venv\\Scripts\\python.exe 04_code\\run_experiment.py                # 核心实验（repeat 0）
    D:\\ml\\.venv\\Scripts\\python.exe 04_code\\run_experiment.py --multiseed   # 追加 P1 多种子（repeat 1..10）
    D:\\ml\\.venv\\Scripts\\python.exe 04_code\\run_experiment.py --smoke       # 小样本冒烟，只验证流程

产物写入 ``05_results/main/``：
``metrics.csv``（主结果长表）、``metrics.json``、``e0_demo1d_peaks.csv``、
``data_fingerprints.json``、``seed_registry.csv``、``run_log.txt``、``figures/``。

数字纪律：本脚本不接受任何「按结果调参」的选项 —— 没有 ``--bandwidth``，没有 ``--k``。
网格只来自 ``config_ref.json``。
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "src"))

from kdelof import calibration, dgp, experiment, peaks, protocol, reporting, scoring  # noqa: E402

ROOT = HERE.parent
RESULTS = ROOT / "05_results" / "main"
FIGDIR = RESULTS / "figures"


def _configure_stdout() -> None:
    """Windows 默认 GBK 控制台会把 '✓'/'±' 之类的字符变成 UnicodeEncodeError。

    这是真实踩到的坑（B 的 ``checks.py`` 在 GBK 控制台下会中途崩溃，见
    ``03_process_logs/member_C.md`` 第 3 回合）。这里把标准输出改成 UTF-8 并对不可编码
    字符降级，保证日志不会因为字符集问题被截断。
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def _table_text(rows: list[str]) -> str:
    return "\n".join(rows)


def main(argv: list[str] | None = None) -> int:
    _configure_stdout()
    ap = argparse.ArgumentParser(description="KDE / LOF 全量实验（C 的正式实现）")
    ap.add_argument("--multiseed", action="store_true", help="追加 P1 多种子拓展 repeat 1..10")
    ap.add_argument("--no-figures", action="store_true", help="跳过绘图")
    ap.add_argument("--smoke", action="store_true", help="小样本冒烟测试（结果写到 05_results/smoke）")
    ap.add_argument("--out", default=None, help="输出目录（默认 05_results/main）")
    args = ap.parse_args(argv)

    t0 = time.time()
    cfg = protocol.load_config()          # 自洽性校验失败会直接抛 ProtocolError
    out_dir = Path(args.out) if args.out else (RESULTS if not args.smoke else ROOT / "05_results" / "smoke")
    fig_dir = out_dir / "figures"
    out_dir.mkdir(parents=True, exist_ok=True)
    fig_dir.mkdir(parents=True, exist_ok=True)

    if args.smoke:
        cfg = experiment.smoke_config(cfg, scale=10)

    log: list[str] = []
    log.append("=" * 78)
    log.append("KDE / LOF 课程项目 —— 正式实验运行日志（C 实现与复现负责人）")
    log.append("=" * 78)
    log.append(f"protocol_version : {cfg['protocol_version']}")
    log.append("接触顺序声明     : 参数网格与默认参数在运行本脚本之前已由 B 锁定；本脚本无任何按结果调参的入口")
    log.append(f"运行开始时间     : {reporting.now_stamp()}")
    for k, v in reporting.environment_info().items():
        log.append(f"{k:<17}: {v}")
    log.append("")

    data = dgp.generate_all(cfg)

    # ---- 一维示例（E0 用的样本）与数据规模
    log.append("数据规模（协议 §2.2 / §9 核对表）：")
    for name, ds in data.items():
        s = ds.summary
        log.append(f"  {name:<11} n={s['n']:>5} dense={s['n_dense']:>4} sparse={s['n_sparse']:>4} "
                   f"anomaly={s['n_anomaly']:>4} far={s['n_anomaly_far']:>4} missing={s['n_missing']}")
    log.append("")

    # ---- 泄漏防控 L1 / L2 / L6：用断言而不是注释
    assert int(np.sum(data["train"].y)) == 0, "L1 违反：train 含异常样本"
    assert int(np.sum(data["validation"].y)) == 0, "L2 违反：validation 含异常样本"
    keys = {n: {tuple(row) for row in np.round(ds.X, 12)} for n, ds in data.items()}
    assert not (keys["train"] & keys["validation"]), "L6 违反：train 与 validation 有重合点"
    assert not (keys["train"] & keys["test"]), "L6 违反：train 与 test 有重合点"
    assert not (keys["validation"] & keys["test"]), "L6 违反：validation 与 test 有重合点"
    log.append("泄漏防控 L1/L2/L5/L6：train 与 validation 标签全 0；标度 none；三划分两两无重合点 ✓")

    # ---- 得分方向（协议 §6.1 要求实测）
    direction = scoring.direction_report(
        data["train"].X,
        cfg["detectors"]["kde"]["bandwidth_grid"],
        cfg["detectors"]["lof"]["n_neighbors_grid"],
    )
    assert direction["all_ok"], "得分方向错误：异常点分数未高于正常点"
    log.append("得分方向实测：全部 6 个带宽 + 4 个邻居数下 min(异常点分数) > max(正常点分数) ✓")
    log.append("")

    # ---- 阈值口径举证：为什么必须是 inverted_cdf
    h0 = float(cfg["detectors"]["kde"]["default_bandwidth"])
    sv = scoring.to_anomaly_score(scoring.kde_log_density(data["train"].X, data["validation"].X, h0))
    contrast = calibration.quantile_method_contrast(sv, cfg["threshold"]["quantile"])
    log.append(f"阈值分位数方法对比（KDE h={h0:g}，validation n={len(sv)}；协议锁定 inverted_cdf，应得 10/1000）：")
    for method, rec in contrast.items():
        flag = "  <- 协议采用" if method == cfg["threshold"]["numpy_method"] else ""
        log.append(f"  {method:<13} threshold={rec['threshold']:.6f}  超阈={rec['n_exceedance']:>3}{flag}")
    log.append("")

    # ---- E0
    x_demo = dgp.generate_demo_1d(cfg)
    e0_df, curves = experiment.run_e0(cfg)
    e0_df.to_csv(out_dir / "e0_demo1d_peaks.csv", index=False, encoding="utf-8-sig")
    log.append("E0 一维带宽示意（显著峰口径：prominence >= 10% 全局最大密度）")
    for _, r in e0_df.iterrows():
        vfr = r["valley_fill_ratio"]
        vfr_s = f"{vfr:.4f}" if vfr is not None and not pd.isna(vfr) else "NA"
        log.append(f"  h={r['bandwidth']:<5g} 局部极大={int(r['n_local_maxima'])} "
                   f"显著峰={int(r['n_prominent_peaks'])} 最大密度={r['max_density']:.4f} "
                   f"谷填充率={vfr_s} 峰位=[{r['prominent_peak_positions']}]")
    log.append("")

    # ---- E1 / E2 / E3
    df_main, df_all = experiment.run_core(cfg, data)
    df_all.to_csv(out_dir / "metrics.csv", index=False, encoding="utf-8-sig")
    (out_dir / "metrics.json").write_text(
        json.dumps(df_all.to_dict(orient="records"), ensure_ascii=False, indent=2,
                   default=lambda o: None), encoding="utf-8")

    log.append("E1 KDE 带宽敏感性（test 一次性评估；阈值来自 validation 99% 分位数）")
    log.append("   h      AUC     错排对   AP      召回    精确率   F1      总FPR   密集簇FPR 稀疏簇FPR 阈值      valLL")
    for _, r in df_main[df_main.detector == "kde"].sort_values("param_value").iterrows():
        log.append(f"  {r.param_value:<5g}  {r.roc_auc:.4f}  {r.n_inversion_pairs_equiv:7.1f}  "
                   f"{r.average_precision:.4f}  {r.recall:.4f}  {r.precision:.4f}  {r.f1:.4f}  "
                   f"{r.fpr_overall:.4f}  {r.fpr_dense:.4f}    {r.fpr_sparse:.4f}    "
                   f"{r.threshold:.4f}  {r.val_mean_log_likelihood:.4f}")
    log.append("")
    log.append("E2 LOF 邻居数敏感性")
    log.append("   k      AUC     错排对   AP      召回    精确率   F1      总FPR   密集簇FPR 稀疏簇FPR 阈值")
    for _, r in df_main[df_main.detector == "lof"].sort_values("param_value").iterrows():
        log.append(f"  {r.param_value:<5g}  {r.roc_auc:.4f}  {r.n_inversion_pairs_equiv:7.1f}  "
                   f"{r.average_precision:.4f}  {r.recall:.4f}  {r.precision:.4f}  {r.f1:.4f}  "
                   f"{r.fpr_overall:.4f}  {r.fpr_dense:.4f}    {r.fpr_sparse:.4f}    {r.threshold:.4f}")
    log.append("")
    log.append("E3 方法对照 @ 默认操作点（h*=0.35, k*=20，均为运行前按 Silverman 参考带宽/网格中位指定）")
    for _, r in df_all[df_all.experiment == "E3_method_comparison"].iterrows():
        log.append(f"  {r.detector:<4} AUC={r.roc_auc:.4f} 错排对={r.n_inversion_pairs_equiv:.1f} "
                   f"AP={r.average_precision:.4f} P={r.precision:.4f} R={r.recall:.4f} F1={r.f1:.4f} "
                   f"FPR={r.fpr_overall:.4f} FPR_dense={r.fpr_dense:.4f} FPR_sparse={r.fpr_sparse:.4f}")
    log.append("")

    # ---- 指纹 / 种子表
    reporting.write_fingerprints(cfg, data, out_dir)
    reporting.write_seed_registry(cfg, out_dir)

    # ---- 图（自检用）
    if not args.no_figures:
        reporting.plot_data_overview(data, fig_dir)
        reporting.plot_e0(cfg, x_demo, curves, fig_dir)
        reporting.plot_sensitivity(df_main, "kde", fig_dir)
        reporting.plot_sensitivity(df_main, "lof", fig_dir)
        h4 = reporting.plot_likelihood_vs_auc(df_main, fig_dir)
        reporting.plot_operating_point(cfg, data, fig_dir)
        log.append(f"自检图已写入 {fig_dir}（非定稿图，D 必须从 CSV 重绘）")
        log.append(f"H4 诊断：argmax_h(validation 平均对数似然) = {h4['argmax_h_val_loglik']:g}，"
                   f"argmax_h(test AUC) = {h4['argmax_h_test_auc']:g}（后者仅作事后描述，不参与选择）")
        log.append("")

    # ---- P1 多种子
    if args.multiseed and not args.smoke:
        log.append("P1 多种子拓展（repeat 1..10，种子偏移 +10000*r，列表在跑测试前已公布）")
        dm, dm_summary = experiment.run_multiseed(cfg)
        dm.to_csv(out_dir / "metrics_multiseed.csv", index=False, encoding="utf-8-sig")
        dm_summary.to_csv(out_dir / "metrics_multiseed_summary.csv", index=False, encoding="utf-8-sig")
        for _, r in dm_summary.iterrows():
            log.append(f"  {r.detector:<4} param={r.param_value:<5g} "
                       f"AUC={r.auc_mean:.4f}±{r.auc_std:.4f} AP={r.ap_mean:.4f}±{r.ap_std:.4f} "
                       f"FPR_sparse={r.fpr_sparse_mean:.4f}±{r.fpr_sparse_std:.4f} "
                       f"FPR_dense={r.fpr_dense_mean:.4f}±{r.fpr_dense_std:.4f}")
        log.append("")

    log.append(f"总运行时间: {time.time() - t0:.1f} s")
    (out_dir / "run_log.txt").write_text("\n".join(log) + "\n", encoding="utf-8")
    print("\n".join(log))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())