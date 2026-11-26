"""交叉审计：用 **B 自己的审计脚本** 审 C 的结果文件。

为什么值得单独做这一步
----------------------
「我的结果我能审计通过」说服力有限 —— 审计脚本和实现出自同一双手，口径错误可能被同一个人
重复。让 B 的 ``audit_results.py``（B 写、B 用、C 没改过）去读 C 产出的文件，才算真正的外部
契约检查。它能跑通的前提是：C 的输出**列名、文件名、JSON 记录结构**都与基准兼容。

实现方式：把 C 的结果复制到临时目录并按基准的文件名重命名，然后把 B 的审计模块里的
``RESULTS`` 指向该目录。B 的脚本本身一行不改。

用法::

    D:\\ml\\.venv\\Scripts\\python.exe 04_code\\cross_audit.py
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "ref_check"))

ROOT = HERE.parent
RESULTS = ROOT / "05_results" / "main"
STAGE = RESULTS / "_cross_audit_stage"


def _configure_stdout() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def main() -> int:
    _configure_stdout()

    # ---- 1. 按基准命名搭一个只含文件的临时目录
    if STAGE.exists():
        shutil.rmtree(STAGE)
    STAGE.mkdir(parents=True)

    renames = {
        "metrics.csv": "metrics_ref.csv",
        "metrics_multiseed.csv": "metrics_ref_multiseed.csv",
        "metrics_multiseed_summary.csv": "metrics_ref_multiseed_summary.csv",
        "e0_demo1d_peaks.csv": "e0_demo1d_peaks.csv",
        "sanity_checks.json": "sanity_checks.json",
        "data_fingerprints.json": "data_fingerprints.json",
        "seed_registry.csv": "seed_registry.csv",
    }
    missing = []
    for src_name, dst_name in renames.items():
        src = RESULTS / src_name
        if src.exists():
            shutil.copy2(src, STAGE / dst_name)
        else:
            missing.append(src_name)
    print(f"暂存目录：{STAGE}")
    print(f"缺失文件（可选拓展允许缺失）：{missing or '无'}")

    # ---- 2. 导入 B 的审计模块并改指向（不改它的任何一行代码）
    import audit_results as b_audit            # noqa: E402  (04_code/ref_check/audit_results.py)

    b_audit.RESULTS = STAGE
    print("=" * 78)
    print("用 B 的 audit_results.py 审计 C 的结果文件")
    print("=" * 78)
    rc = b_audit.main()

    # ---- 3. 把 B 脚本产出的记录留档
    produced = STAGE / "audit_results.md"
    if produced.exists():
        body = produced.read_text(encoding="utf-8")
        header = (
            "# 交叉审计：B 的审计脚本 × C 的结果文件\n\n"
            "> 本文件由 `04_code/cross_audit.py` 生成。审计逻辑来自 B 的 "
            "`04_code/ref_check/audit_results.py`（未做任何修改），\n"
            "> 被审计的数据来自 C 的 `05_results/main/`。这条记录用来证明 "
            "C 的输出满足 B 定义的外部契约，\n"
            "> 而不只是「自己审自己」。\n\n"
            f"> 退出码：{rc}（0 = 全部审计项通过）\n\n---\n\n"
        )
        (RESULTS / "audit_by_B_suite.md").write_text(header + body, encoding="utf-8")
        print(f"已写出 {RESULTS / 'audit_by_B_suite.md'}")

    # ---- 4. 清理临时目录（只保留留档文件）
    shutil.rmtree(STAGE, ignore_errors=True)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())