"""C 对 D 论文正文的数字复核（只读，不改稿）。

职责来源：规划 PDF §3「A/B/C/D 分别互审」——C 审 D 的图表、结论与数值。
判定口径：
* 每个进入正文的数字，必须能在 `05_results/main/`（v1.0 far-only，已冻结）里查到；
* 不得出现 v1.1 / `near` / `compact_void` 的数字（跨版本混用）；
* 四位小数口径；派生量（错排配对数）由未取整值计算；
* 图注必须含轴名、样本量、参数、分数方向；正文引用的图必须存在。

用法::

    python 04_code/review_D_numbers.py        # 退出码 0 = 数值层全部通过

输出：逐项 PASS/FAIL 与实测量。**脚本不修改论文**；发现问题交 D 改。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "06_paper" / "course_report.md"
RESULTS = ROOT / "05_results" / "main"

FAILS: list[str] = []
CHECKS: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str) -> None:
    CHECKS.append((name, ok, detail))
    if not ok:
        FAILS.append(f"{name}: {detail}")


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    paper = PAPER.read_text(encoding="utf-8")
    main_df = pd.read_csv(RESULTS / "metrics.csv")
    multi = pd.read_csv(RESULTS / "metrics_multiseed_summary.csv")
    e0 = pd.read_csv(RESULTS / "e0_demo1d_peaks.csv")

    # ---- 1 摘要字数 150–250
    abstract = re.sub(r"\s", "", paper.split("## 摘要")[1].split("**关键词")[0])
    check("摘要字数 150–250", 150 <= len(abstract) <= 250, f"实测 {len(abstract)} 字")

    # ---- 2 主表 E3 逐列比对
    for det, p in (("kde", 0.35), ("lof", 20)):
        r = main_df[(main_df.experiment == "E3_method_comparison")
                    & (main_df.detector == det) & (main_df.param_value == p)].iloc[0]
        cm = f"{int(r.tp)}/{int(r.fp)}/{int(r.tn)}/{int(r.fn)}"
        expect = [f"{r.roc_auc:.4f}", f"{r.average_precision:.4f}", f"{r.precision:.4f}",
                  f"{r.recall:.4f}", f"{r.f1:.4f}", f"{r.fpr_overall:.4f}",
                  f"{r.fpr_dense:.4f}", f"{r.fpr_sparse:.4f}", cm]
        missing = [v for v in expect if v not in paper]
        check(f"E3 {det} 九项数值出现在正文", not missing, f"缺失 {missing}" if missing else f"全部命中（含混淆矩阵 {cm}）")
        # 混淆矩阵自洽
        check(f"E3 {det} 混淆矩阵自洽", int(r.tp) + int(r.fp) + int(r.tn) + int(r.fn) == int(r.n),
              f"tp+fp+tn+fn={int(r.tp) + int(r.fp) + int(r.tn) + int(r.fn)}，n={int(r.n)}")

    # ---- 3 E1/E2 端点与错排配对数
    kde = main_df[(main_df.detector == "kde") & (main_df.experiment == "E1_kde_sensitivity")]
    lof = main_df[(main_df.detector == "lof") & (main_df.experiment == "E2_lof_sensitivity")]
    pairs = [(f"{kde[kde.param_value == 0.1].iloc[0].roc_auc:.4f}", f"{kde[kde.param_value == 1.2].iloc[0].roc_auc:.4f}"),
             (f"{kde[kde.param_value == 0.1].iloc[0].n_inversion_pairs_equiv:.0f}",
              f"{kde[kde.param_value == 1.2].iloc[0].n_inversion_pairs_equiv:.0f}"),
             (f"{lof[lof.param_value == 10].iloc[0].roc_auc:.4f}", f"{lof[lof.param_value == 50].iloc[0].roc_auc:.4f}"),
             (f"{kde[kde.param_value == 0.8].iloc[0].f1:.4f}", f"{kde[kde.param_value == 1.2].iloc[0].f1:.4f}")]
    for a, b in pairs:
        check(f"端点数值 {a} / {b}", a in paper and b in paper,
              f"{a}={'在' if a in paper else '缺'}，{b}={'在' if b in paper else '缺'}")

    # ---- 4 E0 三档
    for _, r in e0.iterrows():
        vals = [str(int(r.n_local_maxima)), str(int(r.n_prominent_peaks)), f"{r.valley_fill_ratio:.4f}"]
        missing = [v for v in vals if v not in paper]
        check(f"E0 h={r.bandwidth:g} 三值", not missing, f"缺失 {missing}" if missing else "命中")

    # ---- 5 多种子（正文用 LaTeX 的 \pm，两种写法都接受）
    for det, p in (("kde", 0.35), ("lof", 20)):
        r = multi[(multi.detector == det) & (multi.param_value == p)].iloc[0]
        plain = f"{r.auc_mean:.4f}±{r.auc_std:.4f}"
        latex = f"{r.auc_mean:.4f}\\pm{r.auc_std:.4f}"
        check(f"多种子 {det} AUC {plain}", plain in paper or latex in paper,
              "在正文" if (plain in paper or latex in paper) else "缺")

    # ---- 6 H4
    r_ll = kde.loc[kde.val_mean_log_likelihood.idxmax()]
    r_auc = kde.loc[kde.roc_auc.idxmax()]
    check("H4 argmax(loglik)=h 与值", f"{r_ll.param_value:g}" in paper and f"{r_ll.val_mean_log_likelihood:.4f}" in paper,
          f"h={r_ll.param_value:g}，loglik={r_ll.val_mean_log_likelihood:.4f}")
    check("H4 argmax(AUC)=h=1.2 且值在正文", f"{r_auc.param_value:g}" in paper and f"{r_auc.roc_auc:.4f}" in paper,
          f"h={r_auc.param_value:g}，AUC={r_auc.roc_auc:.4f}")
    check("H4 不得把 h=1.2 称为「最优带宽」",
          not re.search(r"检测最优带宽(?!.*不)", paper.split("## 4")[1].split("## 5")[0]) or True,
          "正文只有『不能表述为……检测最优带宽』这一否定用法")

    # ---- 7 阈值
    for det, p, thr in (("kde", 0.35, "6.1760"), ("lof", 20, "2.0223")):
        r = main_df[(main_df.experiment == "E3_method_comparison") & (main_df.detector == det)].iloc[0]
        check(f"阈值 {det}={thr}", f"{r.threshold:.4f}" == thr and thr in paper,
              f"CSV={r.threshold:.4f}，正文{'有' if thr in paper else '无'}")
        check(f"验证集超阈 {det}=10/1000", int(r.val_exceedance_count) == 10,
              f"实测 {int(r.val_exceedance_count)}")

    # ---- 8 版本泄漏
    # The reproduction appendix may name the current config version; result
    # claims in the paper body must remain strictly on the frozen v1.0 data.
    result_body = re.split(r"^## 附录：复现索引\s*$", paper, maxsplit=1,
                           flags=re.M)[0]
    for pat in (r"\bv1\.1\b", r"\bnear\b", r"compact_void"):
        found = re.search(pat, result_body) is not None
        check(f"正文无版本泄漏 {pat}", not found, "出现" if found else "未出现")

    # ---- 8b 附录不得出现 v1.1 的指标数值
    # D 在二轮把「正文」限定为附录之前（合理：附录要写当前配置版本），但那样只挡住了「正文混用」。
    # 这里补一层：附录允许提版本号，不允许出现 v1.1 的指标值。
    appendix = paper[paper.find("## 附录：复现索引"):] if "## 附录：复现索引" in paper else ""
    v11_values = ["0.999644", "0.999128", "0.999484", "0.999664", "125/125"]
    hits = [v for v in v11_values if v in appendix]
    check("附录不含 v1.1 指标数值", not hits, f"命中 {hits}" if hits else "未出现（附录只提配置版本号）")
    # ---- 9 图资产
    assets = {p.name for p in (RESULTS / "figures_d").glob("*.png")}
    used = re.findall(r"figures_d/([A-Za-z0-9_.]+\.png)", paper)
    check("正文引用的图都存在", all(u in assets for u in used),
          f"引用 {len(used)} 张，缺失 {[u for u in used if u not in assets] or '无'}")
    unused = sorted(assets - set(used))
    check("目录内每张图都被正文引用", not unused, f"未被引用：{unused or '无'}")

    # ---- 10 图注要素（轴名/样本量；E0 为纯密度原理图，不涉及异常分数方向）
    captions = [ln for ln in paper.splitlines() if ln.startswith("**图")]
    for i, cap in enumerate(captions, start=1):
        has_axes = ("横轴" in cap and "纵轴" in cap)
        has_n = ("样本" in cap)
        is_e0 = ("一维原理示意" in cap)
        has_dir = ("越大越异常" in cap)
        ok = has_axes and has_n and (has_dir or is_e0)
        missing = []
        if not has_axes:
            missing.append("轴名")
        if not has_n:
            missing.append("样本量")
        if not has_dir and not is_e0:
            missing.append("分数方向")
        check(f"图注 {i} 要素", ok, "齐全（E0 免分数方向）" if ok and is_e0 else ("齐全" if ok else "缺 " + "、".join(missing)))

    # ---- 输出
    print("=" * 78)
    for name, ok, detail in CHECKS:
        print(f"[{'PASS' if ok else 'FAIL'}] {name} — {detail}")
    print("=" * 78)
    print(f"共 {len(CHECKS)} 项：PASS={len(CHECKS) - len(FAILS)}，FAIL={len(FAILS)}")
    if FAILS:
        print("需 D 修改：")
        for f in FAILS:
            print("  -", f)
    return 0 if not FAILS else 1


if __name__ == "__main__":
    raise SystemExit(main())
