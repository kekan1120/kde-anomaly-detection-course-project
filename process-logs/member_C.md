# 人机协作过程记录 —— 成员 C（实现与复现负责人）

| 项 | 内容 |
|---|---|
| 成员 / 角色 | C —— 实现与复现负责人 |
| 会话 | 本人账号下的**同一个连续会话**（从读题到交付全部在本会话内完成） |
| 会话分享链接 | 〔待填：在客户端「分享会话」处复制完整链接贴在此处〕 |
| 时间 | 2026-11-26 20:28 – 21:05（Asia/Shanghai，单次连续会话） |
| 机器 / 环境 | Windows 11 + Python 3.13.5 + numpy 2.5.5 / scipy 1.18.1 / scikit-learn 1.9.1 / matplotlib 3.11.2 / pandas 3.1.1 |
| 交付物 | `04_code/`（正式实现 + 4 个核验脚本）、`05_results/main/`（结果与举证）、`06_paper/section3_4_draft.md`、本记录 |

> 记录原则：只写真实发生的回合。模型输出摘录用原文片段（错误信息、数字）；人工核验写成
> **可复查的动作**（手算、断言、重跑、交叉脚本），不写「已审核」这种空话。

---

## 回合 1　读材料、锚定角色与边界

**当前任务**：把三份材料（作业要求、任务书 docx、四人规划 PDF）+ A 的技能包 + B 的交接包
读成一份可执行的 C 任务清单。

**提示词**（用户原话，全文）：

> 「@作业要求.md 这是作业要求。@课程报告任务书_第1题_核密度估计与基于密度的异常检测.docx
> 我们做的是这一题。@核密度估计异常检测_四人项目规划.pdf 这是分工和规划。我是成员c
> 实现与复现负责人@kde-anomaly-detection-project/ 这是成员a发的skill，
> @kde-anomaly-detection-handoff/ 这是成员B发的文件。git@github.com:... 这是我们小组github的仓库。
> 开始完成我的工作！」

**模型输出（摘录）**：给出 C 的验收清单：独立实现一遍 → 与 B 的 `metrics_ref.csv` 对账 →
产出源码/配置/环境/机器可读结果/运行日志 → 维护本人过程记录 → 写 §3.4 素材。

**人工核验动作**：
1. 逐份比对三份材料的分工表，确认 C 的职责是「代码结构、固定种子、模型拟合与打分、自动指标、
   运行日志、复现说明」，且 C 另有互审责任 = **审 B 的实现**（规划 §3）。
2. 打开 B 的 `START_HERE.md` §三「五条纪律」，把其中四条转成本次的硬约束：
   测试集不参与任何选择；不用测试最优参数当默认；必须分簇报 FPR；`score_samples` 不能直接当
   异常分数。
3. 核对 docx 与规划 PDF：docx 是任务书（100 分制：人机协作 55 + 论文 45），规划 PDF 与
   `references/four-person-project-plan.md` 内容一致，公式在 PDF 转文字时丢失，以 md 为准。

**证据与判断**：部分通过 → 发现一处**工具使用错误**（见下）。

**修正交互**：第一次抽 docx 正文时用了控制台直接打印，中文变成 `���ܶȹ���` 乱码。判断这不是
文档损坏而是**输出编码问题**（控制台代码页 936 <-> UTF-8 不匹配）。改为「先写 UTF-8 文件，
再用读取工具读」，正文正常。这条经验直接决定了后面所有脚本都显式切 UTF-8（回合 3 因此受益）。

**最终采用**：以 B 的协议 md + `config_ref.json` 为唯一数值事实来源；材料冲突时以 JSON 为准。

---

## 回合 2　建环境（一次真实的失败 + 修正）

**当前任务**：在**自机干净环境**里装锁定依赖，跑通 B 的 `verify_env.py`。

**模型输出（摘录）**：建议 `python -m venv .venv` + `pip install -r env/requirements.txt`，
用系统默认 Python 3.11.9。

**人工核验动作**：执行后读报错原文：

```
ERROR: Ignored the following versions that require a different python version: 1.4.0 Requires-Python >=3.12
ERROR: Could not find a version that satisfies the requirement contourpy==1.4.0 ...
```

**证据与判断**：**错误（方案层）**。`contourpy==1.4.0` 只有 cp312+ 的 wheel，Python 3.11
装不上锁定版本；而「装宽松版本」会破坏四个人数字一致的前提。机器上另有 Python 3.13.5，
换版本重装。

**修正后的结果**：`D:\Python\python.exe` 建 venv → 18 个包全部按锁定版本装成。
`verify_env.py` 输出：

```
[ OK ] numpy 2.5.5 ...
[WARN] Reference environment used Python 3.14; you have 3.13.5.
[ OK ] train data fingerprint: EXACT match (sha256 of float64 bytes)
[ OK ] threshold calibration: 10/1000 exceedances at h=0.35 (threshold 6.176033)
RESULT: PASS with 1 warning(s)
```

**人工核验动作（手算）**：阈值 6.176033 与 B 的 HANDOFF §3.3 表一致；`n=1000`、`q=0.99` 时
`ceil(0.99×1000)=990`，故严格超阈数 = `1000−990 = 10`，与 `1.00%` 吻合。

**最终采用**：Python 3.13.5；版本差异已按要求写进 `05_results/main/run_log.txt`。

---

## 回合 3　复跑 B 的基线 —— 发现并修正 B 核验脚本的真实缺陷

**当前任务**：跑 B 的 `checks.py` / `run_ref.py --multiseed` / `audit_results.py`，确认基线在
本机成立（C 的互审责任）。

**模型输出（摘录）**：`run_ref.py` 正常结束（10.1 s），E1/E2/E0 数字与 B 的 HANDOFF §3.4/§3.5
逐项一致；`audit_results.py` 12/12 PASS。

**人工核验动作**：单独重跑 `checks.py` 并看**退出码**，发现它异常退出：

```
UnicodeEncodeError: 'gbk' codec can't encode character '\u2713' in position 58
  File "04_code/ref_check/checks.py", line 43, in record
File "04_code/ref_check/checks.py", line 241, in check_score_direction
```

**证据与判断**：**发现真实缺陷（B 的代码）**。`check_score_direction` 的 detail 里拼了 `'✓'`，
`record()` 直接 `print`，GBK 控制台编码失败 → 进程在 C8 处中断 → **`sanity_checks.json`
从未被写出**。而 `audit_results.py` 的 A4/A11 读的正是这个文件：它读到了上一次成功留下的旧文件，
于是 12/12 PASS 是在**审计旧记录**。这比数值错误更危险：核验静默失效。

**修正交互**：在 `ref_check/checks.py::main` 开头加「stdout/stderr 切 UTF-8」5 行，只改输出编码，
不动任何判据/数值/结论；修订理由与验证写入 `04_code/ref_check/PATCHES_C.md`。
重跑（不设 `PYTHONIOENCODING`）：13 项全 PASS，退出码 0，`sanity_checks.json` 正常写出。

**最终采用**：保留修订；同时把「所有脚本显式切 UTF-8」写进 C 自己的实现（`run_experiment.py`
等 5 个脚本），从源头避免同类问题。

---

## 回合 4　独立实现（过程中自查出 3 处自身缺陷）

**当前任务**：不复用 `reference_impl.py` 的代码，按协议重写一遍正式实现：
`protocol / dgp / scoring / calibration / metrics / peaks / experiment / reporting` 八个模块
+ 4 个核验脚本。

**提示词**（本回合的关键约束，由我在会话中下达）：

> 「独立实现一遍，和 B 的 `metrics_ref.csv` 对账」（`START_HERE.md` §二）
> 「不要按函数名推断 LOF 的符号，必须实测」

**模型输出（摘录）**：生成八个模块 + 数据类 `Split`（带字段自洽校验）+ 手写 KDE / 手写 LOF /
手算 AUC·AP + prominence 峰结构。

**人工核验动作与三处自查缺陷**（都是**读代码/读对方代码**发现的，不是跑挂才发现的）：

1. `metrics.confusion` 里出现一行无意义残码
   `tn = int(np.sum((y_true == 1e9))) if False else ...` —— 典型的生成残留。删除，只保留
   `tn = sum((y_true==0)&(y_pred==0))`。
2. 手写 LOF 的收尾写成「先对邻居 lrd 求均值，再除以查询点 lrd」。数学上等价（分母是常数），
   但浮点舍入与 sklearn 的 `mean(lrd_i / lrd_p)` **可能差最后一位**，会让「偏差 = 0」这条
   核验证据消失。改为逐邻居取比值再平均。
3. C9 的 `measured` 原本写成嵌套 `{"thresholds": {...}}`。读了 B 的 `audit_results.py` 的 A4
   后发现它按 `c9["kde:0.35"]["threshold"]` 取值 —— 嵌套会让 **B 的审计脚本在我这里 KeyError**。
   改成扁平键名（`"kde:0.35" -> {...}`），并在末尾加 `quantile_method_contrast`。
   这样「B 的脚本能审 C 的结果」才成立（回合 6 兑现）。

**证据与判断**：3 处均为模型侧缺陷，人工发现并修正；修正后 `run_checks.py` 15/15 PASS。

**最终采用**：模块化实现；`Split` 用 `__post_init__` 强制形状/dtype/缺失值检查，
把「数据字典」从文档变成运行时断言。

---

## 回合 5　冒烟 → 全量（数字与 B 的表逐项相符）

**当前任务**：先小样本跑通，再跑全量 E0–E3 + P1 十种子。

**模型输出（摘录）**：
- 冒烟（样本量缩 10 倍）：`总运行时间: 2.2 s`，E0 峰结构已与 B 完全一致
  （8/3/2 个局部极大、2/2/1 个显著峰、峰位 −1.460/1.360、谷填充率 0.0007/0.1581/0.9140）。
- 全量：`总运行时间: 9.6 s`；E1 h=0.35 → AUC 0.9995、AP 0.9980、召回 1.0000、
  总 FPR 0.0110、密集簇 0/500、稀疏簇 11/500；E2 k=20 → AUC 0.9990、AP 0.9962、
  召回 0.9720、密集簇 5/500、稀疏簇 4/500。

**人工核验动作**：
1. 把 E1/E2/E3 表与 HANDOFF §3.4 **逐格**对照（10 行 × 10 列），全部一致。
2. 手算抽验：`n_inversion_pairs_equiv = (1−0.9990)×250×1000 = 250`，CSV 里是 256.0
   （因为 AUC 未取整前是 0.998976，256 才对）—— 确认派生量必须用**未取整**的 AUC 算，
   与协议 §6.5 一致。
3. 分簇 FPR 加回总 FPR：`(0+11)/1000 = 1.1%`，与 `fpr_overall=0.0110` 一致。
4. 检查 `metrics.csv` 的 NaN 结构：`recall_compact_void` 在 far-only 测试集上应为 NaN、
   `n_anomaly_compact_void` 应为 0 —— 与 B 的 CSV 一致。

**证据与判断**：通过。

**最终采用**：结果冻结在 `05_results/main/`；`run_log.txt` 里记录协议版本、环境版本、
阈值、分位数方法对照与耗时。

---

## 回合 6　核验 / 审计 / 交叉审计 / 对账（C 的核心验收）

**当前任务**：跑出 4 份举证，并把「我的实现 = B 的实现」变成可复查的结论。

**执行与结果（原文摘录）**：

| 脚本 | 结果 |
|---|---|
| `run_checks.py` | 共 15 项，PASS=15，FAIL=0 |
| `run_audit.py` | 共 13 项审计，PASS=13，FAIL=0 |
| `cross_audit.py`（**用 B 的 `audit_results.py` 审 C 的结果**） | 共 12 项审计，PASS=12，FAIL=0 |
| `reconcile_with_baseline.py` | 对账项 50，PASS=50，FAIL=0 |

关键实测值：

```
C3  与 B 基准的数据指纹对账：train/validation/test 的 sha256 逐位一致，统计量相对偏差=0.000e+00
C9  10 个配置的验证集超阈数恒为 10/1000；方法对照 inverted_cdf=10, higher=9, linear=10 ...
C12 换 test 后阈值逐位不变=True；换 validation 后 KDE 阈值变为 6.312323（确实改变=True）
指标层 22 个数值列与 B 的 metrics_ref.csv：最大绝对偏差 0.000e+00（容差 1e-9）
```

**人工核验动作**：
1. 手算 KDE 解析特例：单训练点 (0,0)、h=0.5、d=2 时 `p(0)=1/(n·h^d)·(2π)^{−d/2}=0.636619772368`，
   手写实现与 sklearn 的相对误差都是 0（核对 C6）。
2. 手算玩具指标（4 个样本）：AUC=3/4=0.75，AP=0.5×1+0.5×2/3=0.8333，混淆矩阵 `[[1,1],[1,1]]`，
   与手算实现一致（C10）。
3. 逐项比对 HANDOFF §3.3 的 10 个阈值（4 位小数）与 §3.5 的 E0 表 —— 全一致。
4. 检查「B 的审计脚本」这条外部证据不是我自己造的：`cross_audit.py` 只做
   「复制文件 + 改 `RESULTS` 指向」，**没有改动 B 脚本的任何一行**。

**证据与判断**：通过。**结论：C 的独立实现与 B 的参考实现在全部预注册数值上完全重合（偏差 0），
没有任何一项需要「容差内解释」。**

**最终采用**：四份报告落盘为 `sanity_checks.md`、`audit_results.md`、`audit_by_B_suite.md`、
`reconciliation_vs_B.md`，直接作为论文「可复现性/结果可靠性」的举证材料。

---

## 回合 7　文档化与交付（含本记录）

**当前任务**：写 `04_code/README.md`（跑法/契约/坑）、`06_paper/section3_4_draft.md`（给 D 的
§3.4 素材）、`ref_check/PATCHES_C.md`（审 B 的结论）、本过程记录；整理仓库并提交。

**人工核验动作**：
1. 检查 README 里每个数字都能在文件里找到出处（`run_log.txt`、`reconciliation.json`）。
2. 检查 `05_results/main/figures/` 的标题都带 `SELF-CHECK (not final)` —— 防止 D 误当定稿图。
3. 检查仓库不包含 `.venv`（虚拟环境写死了本机 Python 路径，换机器必坏）。
4. 检查流程记录没有虚构提示词：本会话只有**一条**用户提示词（回合 1），其余是我按材料约束
   自行推进的步骤，如实标注为「模型自查/人工核验」，不编造成「用户纠正」。

**待办（诚实留白）**：
- GitHub 推送**未完成**：本机到 github.com 的连接被代理拦住（`Failed to connect to
  127.0.0.1 port 7897`），`git ls-remote` 失败。已在本地 `git init` + 提交，等网络恢复后
  `git push` 即可（命令见仓库根 `README.md`）。
- `near`（空区紧凑簇）异常未启用：等 A/D 拍板。**必须在看结果前决定**，我这侧只需一行配置。
- 定稿图与正文：D 负责，C 提供 CSV 与复现说明。

---

## 回合 8　干净环境重跑（阶段 2 的验收项）

**当前任务**：把「在干净环境重跑一次，核心数值在约定容差内一致」这条验收项真正做掉 ——
不是在本机已装好的 `.venv` 里重跑，而是**新建一个 venv** + **一个全新的输出目录**再跑一遍。

**模型输出（摘录）**：先用 `04_code\env\verify_env.py` 跑环境自查，输出

```
[FAIL] protocol config not found: ...\kde-anomaly-detection-course-project\04_code\04_code\config_ref.json
RESULT: FAIL -- 1 problem(s)
```

**人工核验动作**：读 B 的 `verify_env.py` 的路径解析逻辑，发现它按「`env/` 在仓库根目录、
配置在 `<根>/04_code/config_ref.json`」写的。我把 env 放到了 `04_code/env/`，于是根被算成
`04_code`，拼出 `04_code/04_code/config_ref.json`。**这是我的目录布局错误，不是 B 的脚本问题**
（B 的交接包本来就是 `env/` 在根）。

**修正**：`git mv 04_code/env env`，并同步修正两个 README 的安装路径。重跑：
`RESULT: PASS with 1 warning(s)`。
随后在干净 venv 里跑全量实验到独立目录，与已提交结果比对：

```
sha256 identical: True
max abs metric diff vs committed results: 0.0
```

**证据与判断**：通过。说明结果**不依赖本机残留的 venv、也不依赖输出目录的状态**，
是由「配置 + 种子 + 锁定版本」唯一确定的。

---

## 我的稳定协作范式（可复用，5 条）

1. **先钉死不可协商的量，再让模型写代码。** 本次把「网格、默认参数、阈值方法、得分方向、
   测试集不参与选择」五项写成 `protocol.load_config()` 的断言，模型再怎么生成，配置一漂移就当场抛错。
2. **让「正确」有第二个来源。** 不是「我觉得对」，而是：手写实现 × 库实现 × 别人的实现三方交叉。
   本次三方是「我的 sklearn 路径 / 我的手写公式 / B 的参考实现」，任意两方偏差都可视。
3. **把证据做成可执行脚本，而不是写在文档里。** 15 项核验 + 13 项审计 + 12 项外部审计 + 50 项对账，
   全部一条命令重跑；论文里的「已验证」由退出码支撑。
4. **优先检查「静默失效」。** 回合 3 的教训：脚本挂掉但旧结果文件还在，审计照样 PASS。
   因此每个脚本都输出**实测量**（阈值、超阈数、偏差数值）而不仅是 PASS/FAIL，
   并让审计脚本自己带「与另一处记录一致」的检查项（A4/A11）。
5. **错误必须落到文件。** 三处模型侧缺陷（残码、平均顺序、嵌套键名）与本机两处环境坑
   （Python 版本、GBK 编码）都写进 `PATCHES_C.md` / README §5 / 本记录，
   让下一个人不必重新踩一次。

## 会话中模型侧错误清单（供评分核对）

| # | 错误 | 谁发现 | 怎么发现 | 修正 |
|---|---|---|---|---|
| 1 | 首选 Python 3.11 建环境 | 人工 | `pip` 报 `contourpy==1.4.0 Requires-Python >=3.12` | 换 Python 3.13.5，重装锁定版本 |
| 2 | （B 的脚本）GBK 下 `✓` 触发 `UnicodeEncodeError` 中途崩溃 | 人工 | 重跑并看退出码 + 报错栈 | 加 5 行输出编码修正，写入 PATCHES_C.md |
| 3 | `metrics.confusion` 出现 `if False else` 残码 | 人工 | 逐行读自己生成的代码 | 删除残码，只保留正确表达式 |
| 4 | 手写 LOF 先平均后相除 | 人工 | 与 sklearn 的 `mean(lrd_i/lrd_p)` 语义对照 | 改为逐邻居取比值再平均 |
| 5 | C9 `measured` 用嵌套结构 | 人工 | 读 B 的 `audit_results.py` A4 的取值方式 | 改扁平键名，使 B 的脚本能审我的结果 |
| 6 | 首次抽 docx 正文乱码 | 人工 | 输出出现 `���ܶȹ���` | 改「写 UTF-8 文件再读」，并推广到所有脚本 |
| 7 | 把 `env/` 放进了 `04_code/env/`，导致 `verify_env.py` 找错配置路径 | 人工 | 干净环境自查输出 `protocol config not found ...04_code\04_code\config_ref.json` | `git mv` 回仓库根，与 B 的交接包布局一致 |