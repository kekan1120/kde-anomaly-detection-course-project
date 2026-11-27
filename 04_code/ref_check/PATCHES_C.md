# C 对 B 参考实现的交叉审查记录

> 审查人：C（实现与复现负责人）。被审对象：`04_code/ref_check/`（B 的参考实现与核验套件）。
> 依据：规划 §3「A、B、C、D 分别互审」——C 审 B 的实现与协议可执行性。

## 修订 1：`checks.py` 在 GBK 控制台中途崩溃（已修）

**现象**（本机 Windows 11 + Python 3.13.5，控制台代码页 936）：

```
UnicodeEncodeError: 'gbk' codec can't encode character '\u2713' in position 58: illegal multibyte sequence
  File "04_code/ref_check/checks.py", line 43, in record
    print(f"        {detail}")
  File "04_code/ref_check/checks.py", line 241, in check_score_direction
    record("C8", ...)
```

**原因**：`check_score_direction` 的 detail 里拼了 `'✓'`，而 `record()` 直接 `print`。
进程在 C8 处异常退出，因此 `sanity_checks.json`、`sanity_checks.md` 根本没有写出 ——
后续 `audit_results.py` 的 A4/A11 只能读到上一次成功留下的旧文件，等于**用旧记录审计新结果**。

**风险等级**：高。它不是数值错误，但会让「核验通过」这件事静默失效：核验脚本退出码是 1，
而如果有人只看 `audit_results.md` 是否 PASS，会误以为核验已通过。

**修订**（`checks.py::main` 开头，仅 5 行，不触碰任何数值、判据、结论）：

```python
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
```

**验证**：不设 `PYTHONIOENCODING` 直接运行 `checks.py`，13 项全部 PASS，退出码 0，
`sanity_checks.json` 正常写出（本机结果见 `05_results/ref_check/sanity_checks.md`）。

**建议 B**：把同样的 3 行加到你自己的脚本与后续的任何 `print` 型核验脚本里；或者干脆把
`✓` 换成 ASCII 的 `ok`。Windows 默认控制台不是 UTF-8，这一点在「四个人各自机器上跑」的
课程项目里一定会遇到。

## 未修订但需要 B/A 知道的两点

1. **`checks.py` 的 C10/C11/C12 会接触测试集**（B 在协议 §1 第 3 点已诚实披露）。
   本文档确认这一点属实：三处都用默认参数在 test 上算过指标。由于网格在接触前已写死，
   不影响参数选择的无偏性；但论文里必须保留这句披露，不能让读者以为「直到最后才碰测试集」。
2. **`run_ref.py --multiseed` 会在 `05_results/ref_check/` 里追加写** `metrics_ref_multiseed*.csv`。
   若两人共用同一份目录会互相覆盖。建议 B 在 README 里点明「每人用独立输出目录」。
   C 的实现已经把输出目录参数化（`--out`，默认 `05_results/main`），互不干扰。