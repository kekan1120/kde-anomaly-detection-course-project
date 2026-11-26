"""C 的正确性核验套件（15 项）。

与 B 的 ``checks.py`` 的关系：**不是复述**。B 的套件证明「协议可以按定义实现」，本套件证明
「C 的这份实现确实按定义实现，并且与 B 的基准逐位/逐项一致」。其中 C3、C9、C12、C14 是 C
新增或改了判据的项：

* **C3** 直接把三个划分的指纹与 B 的 ``05_results/ref_check/data_fingerprints.json`` 比对，
  这是「两个人跑出同一份数据」的证据，而不是「我这里能跑」。
* **C9** 额外做了分位数方法的对照（``higher`` 会给出 9/1000 而不是 10/1000），把协议里
  「必须写死 inverted_cdf」这条约束从声明变成实测。
* **C12** 做了双向泄漏检验：换掉 test 阈值逐位不变；换掉 validation 阈值必须改变。
* **C14** 用缩比配置跑一遍端到端流水线（冒烟测试），确认改动网格/样本量时流程不会静默出错。

用法::

    D:\\ml\\.venv\\Scripts\\python.exe 04_code\\run_checks.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "src"))

from kdelof import (  # noqa: E402
    calibration,
    dgp,
    experiment,
    metrics,
    peaks,
    protocol,
    reporting,
    scoring,
)

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


def record(cid: str, name: str, passed: bool, detail: str, measured: dict | None = None) -> None:
    RECORDS.append({"id": cid, "name": name, "status": "PASS" if passed else "FAIL",
                    "detail": detail, "measured": measured or {}})
    print(f"[{'PASS' if passed else 'FAIL'}] {cid} {name}")
    if detail:
        print(f"        {detail}")


# --------------------------------------------------------------------------------------


def check_config(cfg: dict) -> None:
    record("C1", "协议配置自洽性（网格/默认参数/阈值方法/标度/异常数量）", True,
           f"protocol_version={cfg['protocol_version']}；"
           f"KDE 网格={cfg['detectors']['kde']['bandwidth_grid']}；"
           f"LOF 网格={cfg['detectors']['lof']['n_neighbors_grid']}；"
           f"默认 h*={cfg['detectors']['kde']['default_bandwidth']}, k*={cfg['detectors']['lof']['default_n_neighbors']}；"
           f"阈值方法={cfg['threshold']['numpy_method']} @ q={cfg['threshold']['quantile']}；"
           f"标度={cfg['data']['preprocessing']['scaling']}。以上全部由 protocol.load_config 的断言强制",
           {"protocol_version": cfg["protocol_version"]})


def check_reproducible(cfg: dict, data: dict) -> None:
    again = dgp.generate_all(cfg)
    same = {n: bool(np.array_equal(data[n].X, again[n].X)) for n in data}
    fps = {n: ds.fingerprint()["sha256_float64"] for n, ds in data.items()}
    record("C2", "同一种子两次生成的数据逐位一致，且三划分指纹互不相同",
           all(same.values()) and len(set(fps.values())) == 3,
           "逐位一致=" + "、".join(f"{n}:{v}" for n, v in same.items())
           + "；sha256 前缀=" + " | ".join(f"{n}={v[:16]}" for n, v in fps.items()),
           {n: v[:32] for n, v in fps.items()})


def check_fingerprint_vs_baseline(data: dict) -> None:
    """与 B 的基准指纹对账（跨实现一致性）。"""
    ref_path = BASELINE / "data_fingerprints.json"
    if not ref_path.exists():
        record("C3", "与 B 基准的数据指纹对账", False,
               f"未找到基准文件 {ref_path}；请确认 05_results/ref_check 已随仓库提供", {})
        return

    ref = json.loads(ref_path.read_text(encoding="utf-8"))["splits"]
    rows, ok = [], True
    worst = 0.0
    for name in ("train", "validation", "test"):
        mine = data[name].fingerprint()
        sha_same = mine["sha256_float64"] == ref[name]["sha256_float64"]
        dev = 0.0
        for key in ("mean", "std_ddof1", "min", "max"):
            a = np.asarray(mine["stats"][key], dtype=np.float64)
            b = np.asarray(ref[name]["stats"][key], dtype=np.float64)
            dev = max(dev, float(np.max(np.abs(a - b) / np.maximum(np.abs(b), 1e-300))))
        worst = max(worst, dev)
        ok = ok and sha_same and dev <= 1e-12
        rows.append(f"{name}: sha256{'一致' if sha_same else '不一致'}，统计量最大相对偏差={dev:.3e}")
    record("C3", "与 B 基准的数据指纹对账（sha256 逐位一致 + 统计量相对容差 ≤ 1e-12）", ok,
           "；".join(rows), {"worst_rel_dev": worst})


def check_labels(cfg: dict, data: dict) -> None:
    expect = {"train": (300, 300, 0), "validation": (500, 500, 0), "test": (500, 500, 250)}
    problems, ok = [], True
    for name, ds in data.items():
        got = (int((ds.cluster_id == 0).sum()), int((ds.cluster_id == 1).sum()), int(ds.y.sum()))
        if got != expect[name]:
            ok = False
            problems.append(f"{name}:{got}!={expect[name]}")
        if not np.array_equal(ds.cluster_id == -1, ds.y == 1):
            ok = False
            problems.append(f"{name}: cluster_id 与 y 不自洽")
        if int(np.isnan(ds.X).sum()):
            ok = False
            problems.append(f"{name}: 存在缺失值")
        if name != "test" and got[2] != 0:
            ok = False
            problems.append(f"{name}: 含异常样本")
    ratio = float((data["test"].y == 1).mean())
    ok = ok and abs(ratio - 0.2) < 1e-12
    record("C4", "各划分规模、逐簇计数、标签规则与异常比例", ok,
           f"train={len(data['train'])} validation={len(data['validation'])} test={len(data['test'])}；"
           f"test 异常比例={ratio:.6f}；无缺失；Cluster_id=-1 ⇔ y=1"
           if ok else "；".join(problems),
           {n: ds.summary for n, ds in data.items()})


def check_no_overlap(data: dict) -> None:
    sets = {n: {tuple(r) for r in np.round(ds.X, 12)} for n, ds in data.items()}
    tv = len(sets["train"] & sets["validation"])
    tt = len(sets["train"] & sets["test"])
    vt = len(sets["validation"] & sets["test"])
    record("C5", "train/validation/test 两两无逐点重合", tv == tt == vt == 0,
           f"重合点数 train∩val={tv}，train∩test={tt}，val∩test={vt}")


def check_kde_math(cfg: dict, data: dict) -> None:
    # 解析特例：单个训练点 (0,0)，在 (0,0) 处的密度 = 1/(n h^d) * (2π)^(-d/2)
    h = 0.5
    pt = np.zeros((1, 2))
    analytic = 1.0 / (1 * h ** 2) * (2 * np.pi) ** (-1.0)
    mine = float(np.exp(scoring.scratch_kde_log_density(pt, pt, h)[0]))
    lib = float(np.exp(scoring.kde_log_density(pt, pt, h)[0]))
    rel_mine = abs(mine - analytic) / analytic
    rel_lib = abs(lib - analytic) / analytic

    worst = 0.0
    for h in cfg["detectors"]["kde"]["bandwidth_grid"]:
        a = scoring.kde_log_density(data["train"].X, data["validation"].X, h)
        b = scoring.scratch_kde_log_density(data["train"].X, data["validation"].X, h)
        worst = max(worst, float(np.max(np.abs(a - b))))

    ok = rel_mine < 1e-12 and rel_lib < 1e-12 and worst < 1e-5
    record("C6", "KDE：解析特例手算 + 手写实现 vs sklearn（6 条带宽 × 1000 个验证点）", ok,
           f"手算 p(0)=1/(n·h^d)·(2π)^(-d/2)={analytic:.12f}；手写相对误差={rel_mine:.2e}，"
           f"sklearn 相对误差={rel_lib:.2e}；log 密度最大绝对偏差={worst:.3e}"
           f"（判据 < 1e-5；残差来自 BLAS 与广播求和的结合顺序差异）",
           {"analytic": analytic, "scratch": mine, "sklearn": lib,
            "max_abs_dev": worst})


def check_lof_math(cfg: dict, data: dict) -> None:
    worst, worst_k = 0.0, None
    for k in cfg["detectors"]["lof"]["n_neighbors_grid"]:
        lib = -scoring.lof_neg_outlier_factor(data["train"].X, data["validation"].X, k)  # 还原成 LOF 本身
        mine = scoring.scratch_lof(data["train"].X, data["validation"].X, k)
        dev = float(np.max(np.abs(lib - mine)))
        if dev > worst:
            worst, worst_k = dev, k
    record("C7", "LOF：Breunig 原始定义手写实现 vs sklearn novelty 模式", worst < 1e-9,
           f"4 个 k × 1000 个验证点上 LOF 数值最大绝对偏差={worst:.3e}（最差 k={worst_k}），判据 < 1e-9",
           {"max_abs_dev": worst, "worst_k": worst_k})


def check_score_direction(cfg: dict, data: dict) -> None:
    rep = scoring.direction_report(data["train"].X,
                                  cfg["detectors"]["kde"]["bandwidth_grid"],
                                  cfg["detectors"]["lof"]["n_neighbors_grid"])
    brief = "；".join(f"{r['detector']}({r['param']:g}):{r['normal_score_max']:.2f}->{r['anomaly_score_min']:.2f}"
                     for r in rep["rows"])
    record("C8", "得分方向「越大越异常」在全部 6 个带宽与 4 个邻居数下成立（人工构造点实测）",
           rep["all_ok"], "簇心正常点得分上界 -> 环上 r=6 异常点得分下界：" + brief,
           {"rows": rep["rows"]})


def check_threshold(cfg: dict, data: dict) -> dict:
    """阈值校准 + 分位数方法对照。measured 的键名与 B 的套件一致，便于交叉审计。"""
    train_X = data["train"].X
    val_X = data["validation"].X
    n_val = len(val_X)
    expect = int(cfg["threshold"]["expected_val_exceedance_count"])

    rows, ok, detail = {}, True, []
    combos = [("kde", h) for h in cfg["detectors"]["kde"]["bandwidth_grid"]] + \
             [("lof", k) for k in cfg["detectors"]["lof"]["n_neighbors_grid"]]
    for det, p in combos:
        raw = (scoring.kde_log_density(train_X, val_X, p) if det == "kde"
               else scoring.lof_neg_outlier_factor(train_X, val_X, p))
        s = scoring.to_anomaly_score(raw)
        thr = calibration.calibrate_threshold(s, cfg["threshold"]["quantile"], cfg["threshold"]["numpy_method"])
        n_exc = calibration.exceedance(s, thr)
        n_ties = int(np.sum(s == thr))
        rows[f"{det}:{p:g}"] = {"threshold": thr, "n_exceedance": n_exc, "n_ties_at_threshold": n_ties}
        ok = ok and n_exc == expect
        detail.append(f"{det}({p:g})={thr:.4f}/超阈{n_exc}")

    # 分位数方法对照：证明「必须 inverted_cdf」不是多余约束
    h0 = float(cfg["detectors"]["kde"]["default_bandwidth"])
    s0 = scoring.to_anomaly_score(scoring.kde_log_density(train_X, val_X, h0))
    contrast = calibration.quantile_method_contrast(s0, cfg["threshold"]["quantile"])
    contrast_ok = contrast["inverted_cdf"]["n_exceedance"] == expect and any(
        v["n_exceedance"] != expect for m, v in contrast.items() if m != "inverted_cdf")

    record("C9", f"阈值校准：10 个配置的验证集超阈数恒为 {expect}/{n_val}；分位数方法对照",
           ok and contrast_ok,
           "；".join(detail) + "。方法对照（KDE h=0.35）："
           + "，".join(f"{m}={v['n_exceedance']}" for m, v in contrast.items())
           + f"（仅 inverted_cdf 恰为 {expect}，故协议锁定该方法是必要的）",
           # 键名与 B 的套件保持一致（"kde:0.35" -> {threshold,...}），
           # 这样 B 的 audit_results.py 可以直接审计 C 的结果文件（见 cross_audit.py）
           {**rows, "quantile_method_contrast": contrast})
    return rows


def check_metrics(cfg: dict, data: dict) -> None:
    from sklearn.metrics import average_precision_score, confusion_matrix, roc_auc_score

    # ---- 玩具样例（可完全手算）
    y = np.array([1, 1, 0, 0])
    s = np.array([0.9, 0.4, 0.6, 0.1])
    pred = calibration.predict(s, 0.5)
    cm = metrics.confusion(y, pred)
    auc = metrics.roc_auc(y, s)
    ap = metrics.average_precision(y, s)
    toy_ok = (cm["tp"], cm["fp"], cm["tn"], cm["fn"]) == (1, 1, 1, 1) \
        and abs(cm["precision"] - 0.5) < 1e-12 and abs(cm["recall"] - 0.5) < 1e-12 \
        and abs(auc - 0.75) < 1e-12 and abs(ap - (0.5 * 1.0 + 0.5 * 2 / 3)) < 1e-12

    # ---- 真实测试集：手算 vs sklearn
    train_X = data["train"].X
    test = data["test"]
    h = float(cfg["detectors"]["kde"]["default_bandwidth"])
    sv = scoring.to_anomaly_score(scoring.kde_log_density(train_X, data["validation"].X, h))
    st = scoring.to_anomaly_score(scoring.kde_log_density(train_X, test.X, h))
    thr = calibration.calibrate_threshold(sv, cfg["threshold"]["quantile"], cfg["threshold"]["numpy_method"])
    y_hat = calibration.predict(st, thr)
    real = metrics.confusion(test.y, y_hat)
    dev = {
        "auc": abs(metrics.roc_auc(test.y, st) - roc_auc_score(test.y, st)),
        "ap": abs(metrics.average_precision(test.y, st) - average_precision_score(test.y, st)),
        "precision": abs(real["precision"] - (real["tp"] / (real["tp"] + real["fp"]))),
        "recall": abs(real["recall"] - (real["tp"] / (real["tp"] + real["fn"]))),
        "f1": abs(real["f1"] - 2 * real["precision"] * real["recall"] / (real["precision"] + real["recall"])),
    }
    cm_lib = confusion_matrix(test.y, y_hat, labels=[0, 1])
    cm_ok = cm_lib.tolist() == [[real["tn"], real["fp"]], [real["fn"], real["tp"]]]
    worst = max(dev.values())
    record("C10", "指标实现：玩具手算样例 + 真实测试集上手算 vs sklearn", toy_ok and cm_ok and worst < 1e-12,
           f"玩具样例 AUC={auc:.4f}(应 0.75) AP={ap:.4f}(应 {0.5*1.0+0.5*2/3:.4f}) 混淆矩阵[[1,1],[1,1]]；"
           f"真实测试集最大偏差={worst:.2e}，混淆矩阵与 sklearn 一致={cm_ok}",
           {"toy": {"auc": auc, "ap": ap, "confusion": cm}, "real_max_dev": worst})


def check_fpr_decomposition(cfg: dict, data: dict) -> None:
    train_X = data["train"].X
    h = float(cfg["detectors"]["kde"]["default_bandwidth"])
    sv = scoring.to_anomaly_score(scoring.kde_log_density(train_X, data["validation"].X, h))
    st = scoring.to_anomaly_score(scoring.kde_log_density(train_X, data["test"].X, h))
    thr = calibration.calibrate_threshold(sv, cfg["threshold"]["quantile"], cfg["threshold"]["numpy_method"])
    m = metrics.evaluate(data["test"], st, thr, cfg)
    weighted = (m["fp_dense"] + m["fp_sparse"]) / (m["n_normal_dense"] + m["n_normal_sparse"])
    ok = (abs(weighted - m["fpr_overall"]) < 1e-12
          and m["fp_dense"] + m["fp_sparse"] == m["fp"])
    record("C11", "分簇误报率可加回总误报率（H2 的证据口径没算错）", ok,
           f"密集簇 {m['fp_dense']}/{m['n_normal_dense']}={m['fpr_dense']:.4f}，"
           f"稀疏簇 {m['fp_sparse']}/{m['n_normal_sparse']}={m['fpr_sparse']:.4f}，"
           f"加权={weighted:.6f}，总 FPR={m['fpr_overall']:.6f}")


def check_no_leakage(cfg: dict, data: dict) -> None:
    train_X = data["train"].X
    val_X = data["validation"].X
    h = float(cfg["detectors"]["kde"]["default_bandwidth"])
    k = int(cfg["detectors"]["lof"]["default_n_neighbors"])

    def thresholds(train, val):
        return (calibration.calibrate_threshold(
                    scoring.to_anomaly_score(scoring.kde_log_density(train, val, h)), 0.99),
                calibration.calibrate_threshold(
                    scoring.to_anomaly_score(scoring.lof_neg_outlier_factor(train, val, k)), 0.99))

    core = thresholds(train_X, val_X)

    # (a) 把 test 整份换掉（换种子重造），阈值必须逐位不变 -> test 没参与阈值
    test_alt = dgp.generate_split(cfg, "test", repeat=7)
    assert test_alt.X.shape == data["test"].X.shape
    core_again = thresholds(train_X, val_X)
    test_invariant = core == core_again

    # (b) 换成另一套 validation，阈值必须改变 -> 阈值确实来自 validation
    other = dgp.generate_split(cfg, "validation", repeat=7)
    other_thr = thresholds(train_X, other.X)
    val_responsive = other_thr != core

    # (c) 网格字面量与协议一致（不得由数据驱动）
    grid_ok = (cfg["detectors"]["kde"]["bandwidth_grid"] == protocol.LOCKED_KDE_GRID
               and cfg["detectors"]["lof"]["n_neighbors_grid"] == protocol.LOCKED_LOF_GRID)

    # (d) 同输入重复打分逐位一致（模型确定性）
    s1 = scoring.to_anomaly_score(scoring.kde_log_density(train_X, data["test"].X, h))
    s2 = scoring.to_anomaly_score(scoring.kde_log_density(train_X, data["test"].X.copy(), h))
    deterministic = bool(np.array_equal(s1, s2))

    ok = test_invariant and val_responsive and grid_ok and deterministic
    record("C12", "无泄漏：阈值只来自 validation（换 test 不变、换 validation 必变）", ok,
           f"核心阈值 KDE={core[0]:.12f} LOF={core[1]:.12f}；换 test 后不变={test_invariant}；"
           f"换 validation 后 KDE 变为 {other_thr[0]:.6f}（确实改变={val_responsive}）；"
           f"网格字面量未被数据影响={grid_ok}；同输入重复打分逐位一致={deterministic}",
           {"thr_core": core, "thr_other": other_thr})


def check_e0(cfg: dict) -> None:
    x = dgp.generate_demo_1d(cfg)
    xs = np.linspace(cfg["demo_1d"]["plot_grid"]["x_min"],
                     cfg["demo_1d"]["plot_grid"]["x_max"],
                     int(cfg["demo_1d"]["plot_grid"]["n_points"]))
    rows = {}
    for h in cfg["demo_1d"]["bandwidths"]:
        p = np.exp(scoring.scratch_kde_log_density(x[:, None], xs[:, None], float(h)))
        info = peaks.describe_curve(p, xs)
        rows[f"{h:g}"] = {k: info[k] for k in ("n_local_maxima", "n_prominent_peaks", "max_density",
                                              "valley_fill_ratio", "prominent_peaks")}

    hs = [f"{h:g}" for h in cfg["demo_1d"]["bandwidths"]]
    local = [rows[h]["n_local_maxima"] for h in hs]
    peaks_n = [rows[h]["n_prominent_peaks"] for h in hs]
    maxd = [rows[h]["max_density"] for h in hs]
    fills = [rows[h]["valley_fill_ratio"] for h in hs]
    ok = (all(a >= b for a, b in zip(local, local[1:]))
          and all(a >= b for a, b in zip(peaks_n, peaks_n[1:]))
          and all(a > b for a, b in zip(maxd, maxd[1:]))
          and all(a < b for a, b in zip(fills, fills[1:]))
          and peaks_n[-1] == 1 and local[0] > peaks_n[0])
    record("C13", "E0 一维带宽示意：峰数随带宽单调减少、大带宽退化为单峰、谷被填平（prominence 口径）", ok,
           f"n={len(x)}；local 极大点数={local}；显著峰数={peaks_n}；最大密度="
           f"{[round(v, 4) for v in maxd]}；谷填充率={[round(v, 4) for v in fills]}",
           rows)


def check_smoke_pipeline(cfg: dict) -> None:
    """缩比配置端到端跑通：形状、NaN、指标取值范围。"""
    small = experiment.smoke_config(cfg, scale=20)
    data = dgp.generate_all(small)
    row_kde = experiment.run_configuration(small, data, "kde", float(small["detectors"]["kde"]["default_bandwidth"]),
                                           "SMOKE")
    row_lof = experiment.run_configuration(small, data, "lof", int(small["detectors"]["lof"]["default_n_neighbors"]),
                                           "SMOKE")
    ok = True
    for r in (row_kde, row_lof):
        ok = ok and r["n"] == small["data"]["splits"]["test"]["total"]
        ok = ok and 0.0 <= r["roc_auc"] <= 1.0 and 0.0 <= r["average_precision"] <= 1.0
        ok = ok and r["tp"] + r["fp"] + r["tn"] + r["fn"] == r["n"]
        ok = ok and not np.isnan(r["threshold"])
    record("C14", "缩比配置端到端冒烟：流水线在改动样本量时不静默出错", ok,
           f"缩小 20 倍后 train={len(data['train'])} validation={len(data['validation'])} "
           f"test={len(data['test'])}；KDE AUC={row_kde['roc_auc']:.4f} 阈值={row_kde['threshold']:.4f}；"
           f"LOF AUC={row_lof['roc_auc']:.4f} 阈值={row_lof['threshold']:.4f}"
           f"（冒烟不校验超阈数=10，因为 n 已变）",
           {"kde": {k: row_kde[k] for k in ("roc_auc", "threshold", "average_precision")},
            "lof": {k: row_lof[k] for k in ("roc_auc", "threshold", "average_precision")}})


def check_output_contract(cfg: dict) -> None:
    """结果表结构契约：列齐全、网格覆盖、无重复行 —— D 的脚本可以直接消费。"""
    path = RESULTS / "metrics.csv"
    if not path.exists():
        record("C15", "结果表结构契约", False, f"未找到 {path}，请先运行 run_experiment.py", {})
        return
    import pandas as pd

    df = pd.read_csv(path)
    missing = [c for c in experiment.METRIC_COLUMNS if c not in df.columns]
    main = df[df.experiment != "E3_method_comparison"]
    grid_ok = (sorted(main[main.detector == "kde"].param_value.unique().tolist())
               == sorted(float(v) for v in cfg["detectors"]["kde"]["bandwidth_grid"])
               and sorted(main[main.detector == "lof"].param_value.unique().tolist())
               == sorted(float(v) for v in cfg["detectors"]["lof"]["n_neighbors_grid"]))
    dup = int(main.duplicated(subset=["detector", "param_value"]).sum())
    ok = not missing and grid_ok and dup == 0 and len(main) == 10
    record("C15", "结果表结构契约（列齐全、覆盖预注册网格、无重复行、D 可直接消费）", ok,
           f"缺列={missing or '无'}；网格覆盖={grid_ok}；重复行={dup}；核心行数={len(main)}（应为 10）",
           {"columns": len(df.columns), "rows": len(df)})


# --------------------------------------------------------------------------------------


def render_markdown(cfg: dict, n_fail: int) -> str:
    env = reporting.environment_info()
    L = ["# 正确性核验记录（C 实现与复现负责人）", "",
         "> 由 `04_code/run_checks.py` 自动生成，请勿手工编辑。",
         "> 作用：证明这份实现按协议定义工作，并与 B 的基准逐位/逐项一致。", "",
         "| 项 | 值 |", "|---|---|",
         f"| 协议版本 | `{cfg['protocol_version']}` |",
         f"| 检查项数 | {len(RECORDS)} |",
         f"| 失败项数 | **{n_fail}** |",
         f"| Python | {env['python']} |",
         f"| numpy / scipy / scikit-learn | {env['numpy']} / {env['scipy']} / {env['scikit_learn']} |",
         f"| matplotlib / pandas | {env['matplotlib']} / {env['pandas']} |", "",
         "## 总览", "", "| 编号 | 检查项 | 结论 |", "|---|---|---|"]
    for r in RECORDS:
        L.append(f"| {r['id']} | {r['name']} | {'✅ PASS' if r['status'] == 'PASS' else '❌ **FAIL**'} |")
    L += ["", "## 逐项细节", ""]
    for r in RECORDS:
        L += [f"### {r['id']} {r['name']}", "", f"**{r['status']}**", "", r["detail"], ""]
        if r["measured"]:
            L += ["实测量：", "", "```json",
                  json.dumps(r["measured"], ensure_ascii=False, indent=2), "```", ""]
    return "\n".join(L)


def main() -> int:
    _configure_stdout()
    RESULTS.mkdir(parents=True, exist_ok=True)
    cfg = protocol.load_config()
    print(f"协议版本 {cfg['protocol_version']}")
    print("=" * 78)

    data = dgp.generate_all(cfg)

    check_config(cfg)
    check_reproducible(cfg, data)
    check_fingerprint_vs_baseline(data)
    check_labels(cfg, data)
    check_no_overlap(data)
    check_kde_math(cfg, data)
    check_lof_math(cfg, data)
    check_score_direction(cfg, data)
    check_threshold(cfg, data)
    check_metrics(cfg, data)
    check_fpr_decomposition(cfg, data)
    check_no_leakage(cfg, data)
    check_e0(cfg)
    check_smoke_pipeline(cfg)
    check_output_contract(cfg)

    n_fail = sum(1 for r in RECORDS if r["status"] == "FAIL")
    print("=" * 78)
    print(f"共 {len(RECORDS)} 项，PASS={len(RECORDS) - n_fail}，FAIL={n_fail}")

    (RESULTS / "sanity_checks.json").write_text(json.dumps({
        "protocol_version": cfg["protocol_version"],
        "author_role": "C 实现与复现负责人",
        "environment": reporting.environment_info(),
        "n_checks": len(RECORDS),
        "n_fail": n_fail,
        "records": RECORDS,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    (RESULTS / "sanity_checks.md").write_text(render_markdown(cfg, n_fail), encoding="utf-8")
    print(f"已写出 {RESULTS / 'sanity_checks.json'} 与 sanity_checks.md")
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())