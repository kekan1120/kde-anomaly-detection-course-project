# 04_code —— 实现与复现（C 负责人）

本目录是**正式提交代码**。`ref_check/` 是 B 的参考实现，只用于对照，不是提交代码。

## 1. 五分钟跑起来

在项目根目录（`kde-anomaly-detection-course-project/`）执行：

```powershell
# 1) 环境（只需一次）。Python 必须 >= 3.12 —— 见 §5 的版本坑
python -m venv .venv
.venv\Scripts\activate
pip install -r env\requirements.txt
python env\verify_env.py                    # 必须 PASS 才继续

# 2) 快速冒烟（约 2 秒，只验证流程，不产出正式结果）
.venv\Scripts\python.exe 04_code\run_experiment.py --smoke

# 3) 全量实验（约 10 秒）+ P1 多种子（约 20 秒）
.venv\Scripts\python.exe 04_code\run_experiment.py --multiseed

# 4) 核验 / 审计 / 对账（全部应当 PASS）
.venv\Scripts\python.exe 04_code\run_checks.py                  # 15 项正确性
.venv\Scripts\python.exe 04_code\run_audit.py                   # 13 项结果审计
.venv\Scripts\python.exe 04_code\cross_audit.py                 # 用 B 的审计脚本审我的结果
.venv\Scripts\python.exe 04_code\reconcile_with_baseline.py     # 与 B 基准逐项对账
```

Windows 控制台若是 GBK：四个脚本内部已把 stdout 切到 UTF-8，无需手动设 `PYTHONIOENCODING`。

## 2. 目录与模块

```
04_code/
  config_ref.json          B 锁定的预注册配置（C 只读，不修改）
  run_experiment.py        全量实验入口（E0/E1/E2/E3 + P1 多种子）
  run_checks.py            15 项正确性核验 -> 05_results/main/sanity_checks.{json,md}
  run_audit.py             13 项结果审计   -> 05_results/main/audit_results.md
  cross_audit.py           用 B 的 audit_results.py 审 C 的结果 -> audit_by_B_suite.md
  reconcile_with_baseline.py  与 B 基准逐项对账 -> reconciliation_vs_B.md
  src/kdelof/              正式实现（见下表）
  ref_check/               B 的参考实现与审计脚本（对照基准，含 C 的一处编码修订）
```

`env/`（依赖锁定、`verify_env.py`、宽松备选）位于**仓库根目录**，与 B 的交接包布局一致，
所以 `python env\verify_env.py` 必须在**仓库根目录**执行。

| 模块 | 职责 | 对应协议条款 |
|---|---|---|
| `protocol.py` | 读配置并断言自洽（网格/默认参数/阈值方法/标度/异常数量） | §4 §5 §8 §10 |
| `dgp.py` | 数据生成：独立种子、显式对角采样、参数化圆环 | §2 §3 §8 §9 |
| `scoring.py` | sklearn 打分 + 手写 KDE/LOF + 得分方向断言 | §4 §6.1 |
| `calibration.py` | `inverted_cdf` 0.99 阈值、严格大于判定、方法对照 | §5 |
| `metrics.py` | AUC/AP/错排配对数/混淆矩阵/分簇 FPR | §6 |
| `peaks.py` | prominence 口径的峰结构、谷填充率 | §7.1 |
| `experiment.py` | E0–E3、P1 多种子、缩比冒烟配置 | §7 |
| `reporting.py` | CSV/JSON/日志/自检图的落盘 | §7 §10 L7 |

## 3. 输出契约（D 直接消费 `05_results/main/metrics.csv`）

| 文件 | 内容 | 谁用 |
|---|---|---|
| `metrics.csv` | 主结果长表（E1/E2/E3 共 12 行，一格一个数值） | **D 画图制表的唯一数据源** |
| `metrics.json` | 同上，程序读 | D / A |
| `metrics_multiseed.csv` / `_summary.csv` | P1 多种子逐次结果与均值±标准差 | D 写「结果稳定性」 |
| `e0_demo1d_peaks.csv` | 一维峰结构表（局部极大/显著峰/峰位/谷填充率） | D 画 H1 图，A 核口径 |
| `data_fingerprints.json` | 三划分 sha256 + 统计量 | C 自查、A 核复现声明 |
| `seed_registry.csv` | 种子与数据流登记表 | A / 论文附录 |
| `sanity_checks.md` / `.json` | 15 项正确性核验（含实测量） | 论文「可复现性」举证 |
| `audit_results.md` | 13 项结果审计 | 论文「结果可靠性」举证 |
| `audit_by_B_suite.md` | B 的审计脚本对 C 结果文件的 12 项审计 | 交叉核验举证 |
| `reconciliation_vs_B.md` | 与 B 基准的 50 项逐项对账 | C 的验收主证据 |
| `run_log.txt` | 环境版本、协议版本、阈值、分位数方法对照、运行时间 | 复现说明素材 |
| `figures/` | 6 张**自检图**（英文轴标签，非定稿） | D 必须重绘 |

列序与 B 的 `metrics_ref.csv` 完全一致（审计项 A13 检查），D 的脚本换数据源即可。

## 4. 这份实现被验证到了什么程度

| 证据 | 结果 |
|---|---|
| 与 B 基准的数据指纹 | 三个划分 **sha256 逐位一致**（`bbe5881f…` / `ac03679b…` / `e00edf67…`），统计量相对偏差 **0** |
| 10 个阈值 vs HANDOFF §3.3 | 最大偏差 **0**（6.176033 / 15.727733 / 1.893115 …） |
| 12 行主结果 × 22 个数值列 vs B 的 `metrics_ref.csv` | 最大绝对偏差 **0.000e+00**（容差 1e-9） |
| 多种子汇总 12 列 | 最大绝对偏差 **0.000e+00** |
| E0 峰结构 | 8/3/2 个局部极大、2/2/1 个显著峰、峰位与谷填充率逐项一致 |
| `run_checks.py` | **15/15 PASS** |
| `run_audit.py` | **13/13 PASS** |
| B 的 `audit_results.py` 审 C 的结果 | **12/12 PASS** |
| `reconcile_with_baseline.py` | **50/50 PASS** |

也就是说：**C 的独立实现与 B 的参考实现在全部预注册数值上完全重合，不是「接近」。**

## 5. 环境与已踩到的坑（真实记录）

1. **Python 3.11 装不上锁定依赖**：`contourpy==1.4.0` 要求 Python ≥ 3.12，
   `pip install` 直接 `No matching distribution found`。改用 **Python 3.13.5** 后一次装成。
   参考环境是 3.14.6；`verify_env.py` 对本机只给 WARN（小版本差异），数据指纹仍 **EXACT match**。
2. **GBK 控制台会打断 B 的 `checks.py`**：它打印 `✓`/`±` 时抛 `UnicodeEncodeError`，
   在 C8 中途崩溃，`sanity_checks.json` 从未写出。已向 B 提出并在 `ref_check/checks.py`
   加 3 行输出编码修正（**只改输出编码，不改任何数值/判据**），修订记录见
   `ref_check/PATCHES_C.md`。C 自己的脚本从第一行就切换到 UTF-8。
3. **不要把 `score_samples` 直接当异常分数**：KDE 是 log 密度、LOF 是负离群因子，两者都是
   「越大越正常」，统一取负后才能当异常分数；且必须用人工构造点**实测**方向（C8）。
4. **阈值只能用 `inverted_cdf`**：`higher` 在 validation 上给出 9/1000 而不是 10/1000（C9 实测）。
5. **`.venv` 不进仓库**：虚拟环境的 `pyvenv.cfg` 写死了本机 Python 路径，换机器必坏。

## 6. 边界（C 不负责的部分）

- 参数网格、默认参数、阈值规则、指标定义：B 锁定，C 不改。
- 理论推导、公式与文献核验：A。
- 定稿图与论文正文：D 从 `metrics.csv` 重绘，**不得**从 `figures/` 读图抄数。
- `near`（空区紧凑簇）异常类型仍 `enabled=false`，等 A/D 拍板后再跑 —— 一条配置开关即可，
  但**必须在看结果之前决定**。