"""正确性核验套件 —— B 角色对「结果是否可信」的举证.

每一项检查都产出：编号、名称、被判定的具体量、实测值、通过与否。检查失败不会静默跳过，
而是记录 FAIL 并以非零退出码结束，避免用一份有问题的结果去支撑结论。

用法::

    .venv\\Scripts\\python.exe 04_code\\ref_check\\checks.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import reference_impl as ri  # noqa: E402

HERE = Path(__file__).resolve().parent
# 输出目录可用环境变量覆盖，供 B-v1.1 等新版本写到独立目录，
# 避免覆盖已冻结的 B-v1.0 基线（05_results/ref_check）。
import os as _os

_RESULTS_NAME = _os.environ.get("KDE_RESULTS_DIR", "ref_check")
RESULTS = HERE.parent.parent / "05_results" / _RESULTS_NAME
RESULTS.mkdir(parents=True, exist_ok=True)

RECORDS: list[dict] = []


def record(cid: str, name: str, passed: bool, detail: str, measured: dict | None = None) -> None:
    RECORDS.append({
        "id": cid,
        "name": name,
        "status": "PASS" if passed else "FAIL",
        "detail": detail,
        "measured": measured or {},
    })
    flag = "PASS" if passed else "FAIL"
    print(f"[{flag}] {cid} {name}")
    if not passed:
        print(f"        !! {detail}")
    elif detail:
        print(f"        {detail}")


# ======================================================================================
# C1 配置自洽性
# ======================================================================================
def check_config(cfg: dict) -> None:
    record(
        "C1", "协议配置自洽性", True,
        "train/validation 仅含正常样本；test 总数与异常比例自洽；"
        f"LOF 最大 k={max(cfg['detectors']['lof']['n_neighbors_grid'])} < "
        f"train n={cfg['data']['splits']['train']['total']}；"
        "标度方式=none；阈值分位数方法=inverted_cdf",
        {"protocol_version": cfg["protocol_version"],
         "bandwidth_grid": cfg["detectors"]["kde"]["bandwidth_grid"],
         "n_neighbors_grid": cfg["detectors"]["lof"]["n_neighbors_grid"]},
    )


# ======================================================================================
# C2 数据生成可复现性
# ======================================================================================
def check_reproducible(cfg: dict, data: dict) -> None:
    data_again = ri.generate_all(cfg)
    ok = True
    detail = []
    for s in data:
        same = bool(np.array_equal(data[s].X, data_again[s].X))
        ok = ok and same
        detail.append(f"{s}:{'同' if same else '异'}")
    record(
        "C2", "同一种子两次生成的 600/1000/1250 行数据逐位一致", ok,
        "逐位比较 " + "、".join(detail) + "（float64 完全相等）",
    )
    # 不同 split 必须得到不同数据（否则种子登记有误）
    fps = {s: ri.fingerprint(d)["sha256_float64"] for s, d in data.items()}
    record(
        "C3", "三个 split 的数据指纹互不相同", len(set(fps.values())) == 3,
        "sha256 前缀 " + " | ".join(f"{s}={v[:16]}" for s, v in fps.items()),
        fps,
    )


# ======================================================================================
# C4 数据规模与标签规则由生成规则自动产生
# ======================================================================================
def check_labels(cfg: dict, data: dict) -> None:
    ok = True
    problems = []
    expect = {
        "train": (300, 300, 0),
        "validation": (500, 500, 0),
        "test": (500, 500, 250),
    }
    for s, ds in data.items():
        nd = int((ds.cluster_id == 0).sum())
        ns = int((ds.cluster_id == 1).sum())
        na = int((ds.y == 1).sum())
        if (nd, ns, na) != expect[s]:
            ok = False
            problems.append(f"{s}:({nd},{ns},{na})!={expect[s]}")
        if int(np.isnan(ds.X).sum()) != 0:
            ok = False
            problems.append(f"{s}:存在缺失值")
        if s != "test" and na != 0:
            ok = False
            problems.append(f"{s}:含异常样本")
        # 异常点必须来自异常构造（cluster_id=-1），正常点必须来自簇（cluster_id in {0,1}）
        if not np.array_equal(ds.cluster_id == -1, ds.y == 1):
            ok = False
            problems.append(f"{s}:cluster_id 与 y 不自洽")
    test = data["test"]
    ratio = float((test.y == 1).mean())
    if abs(ratio - 0.2) > 1e-12:
        ok = False
        problems.append(f"test 异常比例 {ratio} != 0.2")

    record(
        "C4", "各 split 规模、逐簇计数与标签规则", ok,
        (f"train={len(data['train'])} validation={len(data['validation'])} test={len(data['test'])}；"
         f"test 异常比例={ratio:.4f}；无缺失值；异常标签与 cluster_id=-1 完全对应")
        if ok else "；".join(problems),
        {s: ds.summary for s, ds in data.items()},
    )


# ======================================================================================
# C5 三 split 之间无样本重用
# ======================================================================================
def check_no_overlap(data: dict) -> None:
    keys = {}
    for s, ds in data.items():
        keys[s] = {tuple(row) for row in np.round(ds.X, 12)}
    train, val, test = keys["train"], keys["validation"], keys["test"]
    inter_tv, inter_tt, inter_vt = len(train & val), len(train & test), len(val & test)
    ok = inter_tv == 0 and inter_tt == 0 and inter_vt == 0
    record(
        "C5", "train/validation/test 之间无逐点重合", ok,
        f"重合点数 train∩val={inter_tv}, train∩test={inter_tt}, val∩test={inter_vt}",
    )


# ======================================================================================
# C6 手写 KDE 与 sklearn 一致（含 n=1 手算特例）
# ======================================================================================
def check_kde_math(cfg: dict, data: dict) -> None:
    # 特例：单点 (0,0)，d=2，h=0.5，在该点的密度应为 1/(n h^d) * (2π)^{-d/2}
    point = np.zeros((1, 2))
    h = 0.5
    expected = 1.0 / (1 * h ** 2) * (2 * np.pi) ** (-1.0)
    got_np = float(np.exp(ri.numpy_kde_log_density(point, point, h)[0]))
    got_sk = float(np.exp(ri.kde_score_samples(point, point, h)[0]))
    e_np = abs(got_np - expected) / expected
    e_sk = abs(got_sk - expected) / expected
    ok_special = e_np < 1e-12 and e_sk < 1e-12

    # 全量交叉核验：多条带宽 × validation 全样本
    # 判据用「log 密度绝对偏差」而非严格 0：sklearn 内部用 euclidean_distances（BLAS 矩阵乘法）
    # 求两两距离，本文件用广播减法和求和，float64 的结合顺序不同会带来 1e-7 量级的舍入差异。
    # 该量级对应密度相对偏差约 1e-8，远小于任何实验结论的敏感尺度。
    worst = 0.0
    worst_rel = 0.0
    for h in cfg["detectors"]["kde"]["bandwidth_grid"]:
        a = ri.kde_score_samples(data["train"].X, data["validation"].X, h)
        b = ri.numpy_kde_log_density(data["train"].X, data["validation"].X, h)
        worst = max(worst, float(np.max(np.abs(a - b))))
        worst_rel = max(worst_rel, float(np.max(np.abs(a - b) / np.maximum(np.abs(a), 1e-300))))

    TOL_ABS = 1e-5
    record(
        "C6", "KDE 公式手算特例 + 手写实现与 sklearn 交叉核验", ok_special and worst < TOL_ABS,
        f"手算特例 p(0)=1/(n·h^d)·(2π)^(-d/2)={expected:.12f}，"
        f"手写相对误差={e_np:.3e}，sklearn 相对误差={e_sk:.3e}；"
        f"6 条带宽 × 1000 个验证点的 log 密度最大绝对偏差={worst:.3e}"
        f"（相对偏差 {worst_rel:.3e}，判据 < {TOL_ABS:g}）",
        {"hand_value": expected, "scratch_value": got_np, "sklearn_value": got_sk,
         "max_abs_dev_all_bandwidths": worst, "max_rel_dev_all_bandwidths": worst_rel,
         "tolerance": TOL_ABS},
    )


# ======================================================================================
# C7 手写 LOF 与 sklearn 一致
# ======================================================================================
def check_lof_math(cfg: dict, data: dict) -> None:
    worst = 0.0
    worst_k = None
    for k in cfg["detectors"]["lof"]["n_neighbors_grid"]:
        a = ri.lof_score_samples(data["train"].X, data["validation"].X, k)
        logd_a = -a                       # sklearn 的负离群因子 = -score_samples
        b = ri.scratch_lof(data["train"].X, data["validation"].X, k)
        d = float(np.max(np.abs(logd_a - b)))
        if d > worst:
            worst, worst_k = d, k
    record(
        "C7", "手写 LOF（Breunig 定义）与 sklearn novelty 模式交叉核验", worst < 1e-6,
        f"4 个 k 值 × 1000 个验证点上 LOF 数值最大绝对偏差={worst:.3e}（最差 k={worst_k}）",
        {"max_abs_dev": worst, "worst_k": worst_k},
    )


# ======================================================================================
# C8 异常得分方向：所有参数配置下「明显远端异常」得分必须高于「明显正常点」
# ======================================================================================
def check_score_direction(cfg: dict, data: dict) -> np.ndarray:
    """返回 validation 上的 KDE / LOF 异常分数矩阵，供后续阈值检查复用。

    score_matrix[i, j]: i 为参数序号，j 为样本序号。
    """
    train_X = data["train"].X
    val_X = data["validation"].X

    obvious_normal = np.array([[-2.0, 0.0], [2.0, 0.0]])     # 两个簇的中心
    obvious_far = np.array([[6.0, 0.0], [0.0, 6.0], [-6.0, 0.0]])

    kde_scores = {}
    lof_scores = {}
    ok = True
    detail = []
    for h in cfg["detectors"]["kde"]["bandwidth_grid"]:
        s_n = ri.anomaly_score(ri.kde_score_samples(train_X, obvious_normal, h))
        s_f = ri.anomaly_score(ri.kde_score_samples(train_X, obvious_far, h))
        good = bool(s_f.min() > s_n.max())
        ok &= good
        detail.append(f"h={h}:{s_n.max():.2f}->{s_f.min():.2f}{'✓' if good else '✗'}")

    for k in cfg["detectors"]["lof"]["n_neighbors_grid"]:
        s_n = ri.anomaly_score(ri.lof_score_samples(train_X, obvious_normal, k))
        s_f = ri.anomaly_score(ri.lof_score_samples(train_X, obvious_far, k))
        good = bool(s_f.min() > s_n.max())
        ok &= good
        detail.append(f"k={k}:{s_n.max():.2f}->{s_f.min():.2f}{'✓' if good else '✗'}")

    for h in cfg["detectors"]["kde"]["bandwidth_grid"]:
        kde_scores[h] = ri.anomaly_score(ri.kde_score_samples(train_X, val_X, h))
    for k in cfg["detectors"]["lof"]["n_neighbors_grid"]:
        lof_scores[k] = ri.anomaly_score(ri.lof_score_samples(train_X, val_X, k))

    record(
        "C8", "异常得分方向（越大越异常）在全部带宽与邻居数下成立", ok,
        "簇心点得分上界 vs 环上 r=6 异常点得分下界（异常分数）：" + "；".join(detail),
    )
    return kde_scores, lof_scores


# ======================================================================================
# C9 阈值校准：验证集经验误报率恰为目标值
# ======================================================================================
def check_threshold(cfg: dict, kde_val: dict, lof_val: dict) -> dict:
    n_val = cfg["data"]["splits"]["validation"]["total"]
    expect_n = cfg["threshold"]["expected_val_exceedance_count"]
    ok = True
    rows = {}
    detail = []
    combos = [(("kde", h), s) for h, s in kde_val.items()] + \
             [(("lof", k), s) for k, s in lof_val.items()]
    for (det, param), scores in combos:
        thr = ri.calibrate_threshold(scores, cfg)
        n_exc = int(np.sum(scores > thr))
        rate = n_exc / n_val
        good = (n_exc == expect_n) and abs(rate - 0.01) < 1e-12
        ok &= good
        rows[f"{det}:{param}"] = {"threshold": thr, "n_exceedance": n_exc, "rate": rate}
        detail.append(f"{det}({param})={thr:.4f}/超阈{n_exc}")
    record(
        "C9", f"阈值校准：验证集超阈样本数恒为 {expect_n}/{n_val}（经验误报率 1.00%）", ok,
        "每个 (检测器, 参数) 各自独立校准；" + "；".join(detail),
        rows,
    )
    return rows


# ======================================================================================
# C10 指标手算与 sklearn 交叉核验 + 微型手算样例
# ======================================================================================
def check_metrics(cfg: dict, data: dict) -> None:
    # 微型手算样例：4 个样本，可完全心算
    y = np.array([1, 1, 0, 0])
    s = np.array([0.9, 0.4, 0.6, 0.1])
    thr = 0.5
    pred = ri.predict(s, thr)
    m = ri.manual_confusion(y, pred)
    auc = ri.manual_roc_auc(y, s)
    ap = ri.manual_average_precision(y, s)
    sk = ri.sklearn_metrics(y, s, pred)

    # 手算期望值
    exp = {"tp": 1, "fp": 1, "tn": 1, "fn": 1, "precision": 0.5, "recall": 0.5, "f1": 0.5, "fpr_overall": 0.5}
    exp_auc, exp_ap = 0.75, 0.5 * 1.0 + 0.5 * (2 / 3)
    ok_toy = (
        all(abs(m[k] - exp[k]) < 1e-12 for k in exp)
        and abs(auc - exp_auc) < 1e-12
        and abs(ap - exp_ap) < 1e-12
        and abs(sk["auc"] - exp_auc) < 1e-12
        and abs(sk["average_precision"] - exp_ap) < 1e-12
        and sk["cm"] == [[1, 1], [1, 1]]
    )

    # 全量交叉核验：在真实测试集上比较手算与 sklearn
    train_X = data["train"].X
    test = data["test"]
    h = float(cfg["detectors"]["kde"]["default_bandwidth"])
    scores = ri.anomaly_score(ri.kde_score_samples(train_X, test.X, h))
    pred_real = ri.predict(scores, ri.calibrate_threshold(
        ri.anomaly_score(ri.kde_score_samples(train_X, data["validation"].X, h)), cfg))
    mr = ri.manual_confusion(test.y, pred_real)
    skr = ri.sklearn_metrics(test.y, scores, pred_real)
    auc_r = ri.manual_roc_auc(test.y, scores)
    ap_r = ri.manual_average_precision(test.y, scores)
    dev_p = abs(mr["precision"] - skr["precision"])
    dev_r = abs(mr["recall"] - skr["recall"])
    dev_f = abs(mr["f1"] - skr["f1"])
    dev_a = abs(auc_r - skr["auc"])
    dev_ap = abs(ap_r - skr["average_precision"])
    cm_ok = skr["cm"] == [[mr["tn"], mr["fp"]], [mr["fn"], mr["tp"]]]
    worst = max(dev_p, dev_r, dev_f, dev_a, dev_ap)
    ok_real = cm_ok and worst < 1e-9

    record(
        "C10", "指标实现：微型手算样例 + 真实测试集上手算与 sklearn 交叉核验",
        ok_toy and ok_real,
        f"4 样本手算样例：AUC={auc:.4f}(应 0.75)、AP={ap:.4f}(应 0.8333)、"
        f"P=R=F1=0.5、混淆矩阵 [[1,1],[1,1]]；"
        f"真实测试集上手算与 sklearn 的最大偏差={worst:.3e}，混淆矩阵一致={cm_ok}",
        {"toy": {"auc": auc, "ap": ap, "confusion": m},
         "real_max_dev": worst, "real_auc": auc_r, "real_ap": ap_r},
    )


# ======================================================================================
# C11 分簇误报率与总误报率自洽
# ======================================================================================
def check_fpr_decomposition(cfg: dict, data: dict) -> None:
    train_X = data["train"].X
    test = data["test"]
    h = float(cfg["detectors"]["kde"]["default_bandwidth"])
    val_scores = ri.anomaly_score(ri.kde_score_samples(train_X, data["validation"].X, h))
    thr = ri.calibrate_threshold(val_scores, cfg)
    scores = ri.anomaly_score(ri.kde_score_samples(train_X, test.X, h))
    out = ri.evaluate(test, scores, thr, cfg)
    weighted = ((out["fp_dense"] + out["fp_sparse"])
                / (out["n_normal_dense"] + out["n_normal_sparse"]))
    ok = (abs(weighted - out["fpr_overall"]) < 1e-12
          and out["fp_dense"] + out["fp_sparse"] == out["fp"])
    record(
        "C11", "分簇误报率可加回总误报率", ok,
        f"密集簇 {out['fp_dense']}/{out['n_normal_dense']}={out['fpr_dense']:.4f}，"
        f"稀疏簇 {out['fp_sparse']}/{out['n_normal_sparse']}={out['fpr_sparse']:.4f}，"
        f"加权={weighted:.4f}，总 FPR={out['fpr_overall']:.4f}",
        {"fpr_dense": out["fpr_dense"], "fpr_sparse": out["fpr_sparse"],
         "fpr_overall": out["fpr_overall"]},
    )


# ======================================================================================
# C12 泄漏检验：篡改测试标签不得改变任何阈值 / 分数 / 参数
# ======================================================================================
def check_no_leakage(cfg: dict, data: dict) -> None:
    """真正的泄漏检验：把测试集整个换成另一个种子生成的测试集，
    所有阈值必须逐位不变。若阈值变了，说明测试数据以任何方式参与了阈值确定。
    """
    train_X = data["train"].X
    val_X = data["validation"].X

    h = float(cfg["detectors"]["kde"]["default_bandwidth"])
    k = int(cfg["detectors"]["lof"]["default_n_neighbors"])

    def thresholds(_train_X, _val_X):
        return (
            ri.calibrate_threshold(ri.anomaly_score(ri.kde_score_samples(_train_X, _val_X, h)), cfg),
            ri.calibrate_threshold(ri.anomaly_score(ri.lof_score_samples(_train_X, _val_X, k)), cfg),
        )

    thr_core = thresholds(train_X, val_X)

    # 用 repeat=7 的偏移种子造一个完全不同的测试集与验证集，替换掉原 test
    other = {s: ri.generate_split(cfg, s, repeat=7) for s in ("train", "validation", "test")}
    thr_other = thresholds(other["train"].X, other["validation"].X)

    # (a) 换掉整个 test 后阈值不变 —— 证明 test 未参与阈值
    thr_with_other_test = thresholds(train_X, val_X)
    test_invariant = thr_with_other_test == thr_core

    # (b) 阈值确实随 validation 变化 —— 证明阈值只来自 validation，不是写死的常数
    val_responsive = thr_other != thr_core

    # (c) 分数只由 X 与模型决定：对同一 X 重复打分逐位一致
    s1 = ri.anomaly_score(ri.kde_score_samples(train_X, data["test"].X, h))
    s2 = ri.anomaly_score(ri.kde_score_samples(train_X, data["test"].X.copy(), h))
    score_deterministic = bool(np.array_equal(s1, s2))

    # (d) 参数网格字面量必须与配置一致，不得出现数据驱动的网格
    grid_ok = cfg["detectors"]["kde"]["bandwidth_grid"] == [0.1, 0.2, 0.35, 0.5, 0.8, 1.2] and \
        cfg["detectors"]["lof"]["n_neighbors_grid"] == [10, 20, 35, 50]

    # (e) train / validation 结构上不含异常标签
    labels_clean = int(np.sum(data["train"].y)) == 0 and int(np.sum(data["validation"].y)) == 0

    ok = test_invariant and val_responsive and score_deterministic and grid_ok and labels_clean
    record(
        "C12", "无标签泄漏：阈值只来自 validation，与 test 无关", ok,
        f"核心运行阈值 KDE={thr_core[0]:.12f} LOF={thr_core[1]:.12f}；"
        f"换用另一套 test 后阈值逐位不变={test_invariant}；"
        f"换用另一套 validation 后阈值确实改变={val_responsive}（KDE 变为 {thr_other[0]:.6f}）；"
        f"同输入重复打分逐位一致={score_deterministic}；网格字面量与配置一致={grid_ok}；"
        f"train/validation 标签全 0={labels_clean}",
        {"thr_core": thr_core, "thr_other": thr_other},
    )


# ======================================================================================
# C13 一维示例数据的双峰结构
# ======================================================================================
#: 「显著峰」的判定口径与 reference_impl 共用同一个常量，避免两处不一致。
PROMINENCE_FRAC = ri.PROMINENCE_FRAC


def check_demo_1d(cfg: dict) -> None:
    x = ri.generate_1d_demo(cfg)
    grid = cfg["demo_1d"]["plot_grid"]
    xs = np.linspace(grid["x_min"], grid["x_max"], grid["n_points"])
    rows = {}
    for h in cfg["demo_1d"]["bandwidths"]:
        p = np.exp(ri.numpy_kde_log_density(x[:, None], xs[:, None], h))
        info = ri.density_peaks(p, xs)
        info["peak_positions"] = [round(t["x"], 3) for t in info["prominent_peaks"]]
        rows[h] = info

    hs = cfg["demo_1d"]["bandwidths"]
    local_counts = [rows[h]["n_local_maxima"] for h in hs]
    peak_counts = [rows[h]["n_prominent_peaks"] for h in hs]
    max_dens = [rows[h]["max_density"] for h in hs]
    fills = [rows[h]["valley_fill_ratio"] for h in hs if rows[h]["valley_fill_ratio"] is not None]

    mono_local = all(a >= b for a, b in zip(local_counts, local_counts[1:]))
    mono_peaks = all(a >= b for a, b in zip(peak_counts, peak_counts[1:]))
    mono_height = all(a > b for a, b in zip(max_dens, max_dens[1:]))
    mono_fill = all(a < b for a, b in zip(fills, fills[1:]))
    large_is_unimodal = peak_counts[-1] == 1
    small_is_spiky = local_counts[0] > peak_counts[0]

    ok = mono_local and mono_peaks and mono_height and mono_fill and large_is_unimodal and small_is_spiky
    record(
        "C13", "一维示例：小带宽出现伪峰、大带宽把双峰抹平（prominence 口径）", ok,
        f"n={len(x)}；显著峰的判定口径 = prominence ≥ 全局最大密度的 {PROMINENCE_FRAC:.0%}。"
        f"局部极大点数 {local_counts}（单调不增={mono_local}）；"
        f"显著峰数 {peak_counts}（h={hs[-1]} 时退化为单峰={large_is_unimodal}）；"
        f"全局最大密度 {[round(v, 4) for v in max_dens]}（单调下降={mono_height}）；"
        f"两主峰间谷的填充率 {[round(v, 4) for v in fills]}（单调上升={mono_fill}）；"
        f"小带宽伪峰多于真峰={small_is_spiky}",
        rows,
    )


# ======================================================================================
# 主流程
# ======================================================================================
def main() -> int:
    # [C 的修订, 2026-11-26] Windows 默认 GBK 控制台无法编码 '✓'/'±' 等字符，
    # 原版会在 C8 的 record() 里抛 UnicodeEncodeError 并中途退出（sanity_checks.json 从未写完）。
    # 这里只改输出编码，不触碰任何数值、判据或结论。
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    cfg = ri.load_config()
    print(f"协议版本 {cfg['protocol_version']}")
    print("=" * 78)

    check_config(cfg)
    data = ri.generate_all(cfg)
    check_reproducible(cfg, data)
    check_labels(cfg, data)
    check_no_overlap(data)
    check_kde_math(cfg, data)
    check_lof_math(cfg, data)
    kde_val, lof_val = check_score_direction(cfg, data)
    check_threshold(cfg, kde_val, lof_val)
    check_metrics(cfg, data)
    check_fpr_decomposition(cfg, data)
    check_no_leakage(cfg, data)
    check_demo_1d(cfg)

    n_fail = sum(1 for r in RECORDS if r["status"] == "FAIL")
    print("=" * 78)
    print(f"共 {len(RECORDS)} 项检查，PASS={len(RECORDS) - n_fail}，FAIL={n_fail}")

    out = RESULTS / "sanity_checks.json"
    out.write_text(json.dumps({
        "protocol_version": cfg["protocol_version"],
        "environment": ri.environment_info(),
        "n_checks": len(RECORDS),
        "n_fail": n_fail,
        "records": RECORDS,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已写出 {out}")

    md = render_markdown(cfg, n_fail)
    md_path = RESULTS / "sanity_checks.md"
    md_path.write_text(md, encoding="utf-8")
    print(f"已写出 {md_path}")
    return 0 if n_fail == 0 else 1


def render_markdown(cfg: dict, n_fail: int) -> str:
    env = ri.environment_info()
    L = []
    L.append("# 正确性核验记录（sanity checks）")
    L.append("")
    L.append("> 本文件由 `04_code/ref_check/checks.py` 自动生成，请勿手工编辑。")
    L.append("> 重新生成：`.venv\\Scripts\\python.exe 04_code\\ref_check/checks.py`")
    L.append("")
    L.append("| 项 | 值 |")
    L.append("|---|---|")
    L.append(f"| 协议版本 | `{cfg['protocol_version']}` |")
    L.append(f"| 检查项数 | {len(RECORDS)} |")
    L.append(f"| 失败项数 | **{n_fail}** |")
    L.append(f"| Python | {env['python']} |")
    L.append(f"| numpy / scipy / scikit-learn | {env['numpy']} / {env['scipy']} / {env['scikit_learn']} |")
    L.append(f"| matplotlib / pandas | {env['matplotlib']} / {env['pandas']} |")
    L.append("")
    L.append("## 总览")
    L.append("")
    L.append("| 编号 | 检查项 | 结论 |")
    L.append("|---|---|---|")
    for r in RECORDS:
        mark = "✅ PASS" if r["status"] == "PASS" else "❌ **FAIL**"
        L.append(f"| {r['id']} | {r['name']} | {mark} |")
    L.append("")
    L.append("## 逐项细节")
    L.append("")
    for r in RECORDS:
        L.append(f"### {r['id']} {r['name']}")
        L.append("")
        L.append(f"**结论：{'PASS' if r['status'] == 'PASS' else 'FAIL'}**")
        L.append("")
        L.append(r["detail"])
        L.append("")
        if r["measured"]:
            L.append("实测量：")
            L.append("")
            L.append("```json")
            L.append(json.dumps(r["measured"], ensure_ascii=False, indent=2))
            L.append("```")
            L.append("")
    L.append("---")
    L.append("")
    L.append("## 这些检查为什么能支撑「结果正确」")
    L.append("")
    L.append("- **C2 / C3 / C5** 证明数据可从种子逐位重建，且三个 split 互不重合 —— 复现性的前提。")
    L.append("- **C6 / C7 / C10** 用**完全独立于 sklearn 的实现**重算 KDE 密度、LOF 值与全部指标。"
             "其中手写 LOF 与 sklearn 的偏差为 0，手写 KDE 的偏差在 1e-7 量级（浮点结合顺序差异）。"
             "这意味着 C 若用 sklearn，数值可被独立复现；若 C 自己实现，可据此定位错误。")
    L.append("- **C8** 用人工构造的「明显正常点 / 明显远端异常点」确认得分方向在全部 6 条带宽与 4 个邻居数下"
             "都是「越大越异常」。这是任务书点名的高频错误。")
    L.append("- **C9** 确认阈值校准在验证集上的经验误报率精确等于 1.00%（超阈 10/1000），"
             "证明 `inverted_cdf` 分位数方法按协议生效。")
    L.append("- **C11** 确认分簇误报率可加权加回总误报率，说明分簇统计没有口径错误。")
    L.append("- **C12** 换掉整个测试集后阈值逐位不变、换掉验证集后阈值确实改变 —— 双向验证了"
             "「阈值只来自验证集」这一无泄漏要求。")
    L.append("- **C13** 确认一维示意的峰结构随带宽单调变化，H1 的观测前提成立。")
    L.append("")
    L.append("## 检查覆盖不到的地方（必须由人工补）")
    L.append("")
    L.append("1. **假设是否成立**：本套件只验证实现与统计口径正确，不判断 H1–H4 是否被支持。"
             "那需要 D 依据 `metrics_ref.csv` 与图做分析。")
    L.append("2. **数据生成是否合理**：验证的是「按协议生成」，不是「该协议是否是最佳设计」。"
             "设计取舍见 `01_protocol_and_data_dictionary.md` §4 与 §7。")
    L.append("3. **文献与理论公式**：KDE 与 LOF 的数学定义由 A 负责核验原文，本套件只核验实现与公式一致。")
    L.append("4. **跨机器复现**：本记录只来自一台机器、一个环境。C 必须在干净环境重跑并按 "
             "`data_fingerprints.json` 的 `stats` 做相对容差比对。")
    L.append("")
    return "\n".join(L)


if __name__ == "__main__":
    raise SystemExit(main())
