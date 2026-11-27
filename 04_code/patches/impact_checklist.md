# near 启用 —— 一页影响清单（待 B 签署）

> 配套：`config_patch_near.json`（字段差异）、`protocol_section12_row_draft.md`（§12 行草稿）。
> 本页只回答两件事：**哪些东西会变**、**哪些东西必须逐位不变**。

## 1. 变更范围

三个字段：`near.enabled false→true`、`near.n_test 0→125`、`far.n_test 250→125`。
其余（样本量、网格、默认参数、阈值规则、指标定义、10 个数据流种子）全部不动。

## 2. 必须逐位不变（可直接写成断言）

| 项 | 为什么必须不变 |
|---|---|
| `train` / `validation` 的 sha256 | 两版共用同一份拟合与校准数据 |
| 10 个阈值（KDE 6 个 + LOF 4 个） | 阈值只由 train+validation 决定，与 test 无关 |
| `val_mean_log_likelihood`（6 条带宽） | 同上，衡量的是密度估计目标 |
| `fp_dense` / `fp_sparse` / `fpr_dense` / `fpr_sparse` | 假阳性只在 500+500 个正常样本上计；分母不变 |
| `test` 的正常侧 500+500 | 正常样本一字不动 |
| E0 峰结构表 | 一维示例与异常类型无关 |
| 列集合与列序 | D 的脚本按列名取值 |

→ 这组等式同时是**「启用 near 没有污染正常侧任何结论」的硬证据**（不变性契约）。

## 3. 会变的核验 / 对账项

| 项 | 变什么 | 处理 |
|---|---|---|
| **C3** 指纹 vs B 基准 | `test` 的 sha256 必变 | 只比 train/validation；test 指纹登记为新基线 |
| **C4** 规模与标签 | 数量仍 1250 / 250，但**类型构成**未被断言 | 新增 C16：`n_anomaly_far=125`、`n_anomaly_compact_void=125`、合计 250、行序正确 |
| **C8** 得分方向 | 仍通过，但不覆盖 near | **不得**把 (0,5) 加进「obvious far」——那等于把待检验结论写进断言；改为只记录不断言的诊断 |
| **C14** 冒烟 | `smoke_config()` 会把 `far.n_test` 写成 `n_anomaly`，near 仍 125 → 合计不等于 `n_anomaly`，**断言必炸** | 先修 `smoke_config`：按各 enabled 类型原比例缩放 |
| **reconcile 数据层** | `test.sha256` 一项必 FAIL | 移出 strict 模式，改为「登记新指纹」 |
| **reconcile 指标层** | `tp/fn/recall/roc_auc/average_precision/n_inversion_pairs_equiv/recall_far` 全变 | 拆成「不变子空间必须逐位相同」+「新指标只做自洽审计（A5/A6/A10/A14）」 |
| **A13** 列集合 | 仍一致（`recall_compact_void` 由 NaN 变真值） | 保留，并断言 NaN 结构按类型翻转 |
| **B 的 cross_audit（12 项）** | 大概率仍全 PASS —— 它不认识 `anomaly_type` | 保留作回归证据，但明确标注「盲审」，不能替代分层审计 |

新增三项：**C16** 分层构成；**C17** 不变性契约（上表逐位相等）；**C18** far 点级嵌套等式
——C18 只在 Q-A 取 B 案（抽 250 再取前 125）时成立；取 A 案则删除 C18，`recall_far` 跨版本不可比。

## 4. 若只做机制诊断（B 尚未签署前的唯一合法形态）

- 输出目录：`05_results/ad_hoc/near_enabled/`，结果文件命名 `metrics_ad_hoc.csv`（不得叫
  `metrics.csv`，避免被误当正式结果）。
- `run_log.txt` **首两行固定**：
  ```
  protocol=NOT LOCKED (awaiting B-v1.1)
  status=ad-hoc
  ```
- 文件头与图标题注明：**「ad-hoc 机制诊断，不得作为论文主结果」**。
- 不进 `05_results/INDEX.md` 的正式版本表；不参与 §4 任何主表/主图。

## 5. 论文口径（若 B 最终签署）

1. 每类异常仅 **125** 个 → 单点变化 = **0.8 个百分点**；不按百分点解读。
2. `recall_compact_void` 是**近似 0/1 的块状量**（整团同分、同进同出），report 写分子/分母
   （如 125/125），不写成 0.998 这类连续小数。
3. **AUC / AP 不得跨版本比较**：新增的正样本分数高于全部正常点，会让 AUC 机械上升
   （预估 KDE 0.999512→0.9997、LOF 0.99904→0.9994），与「检测变好」无关。
4. 新版本标为 post-hoc，与 v1.0（预注册主结果）并列报告；变更前已看过 v1.0 测试结果，
   `test_results_seen_before_change = true`。

## 6. B 的签署结论（2026-11-27）

**已签署，落地为 `B-v1.1-near`。** 实测已核对本清单§2 的全部不变量：

- `train` / `validation` 的 sha256、`test` 的 500+500 正常侧、全部 10 个阈值、
  `val_mean_log_likelihood`、`fp_dense`/`fp_sparse`/`fpr_dense`/`fpr_sparse`/`fpr_overall`/`fp`/`tn`、
  E0 峰结构表、结果表列集合与列序 —— **均逐位不变**（max|Δ| = 0.0e+00）。
- 变化的只有异常侧：`n_anomaly_far` 250→125、`n_anomaly_compact_void` 0→125、
  `tp`/`fn`/`recall`/`precision`/`f1`/`roc_auc`/`average_precision`/`n_inversion_pairs_equiv`。
- Q-A 取 B 案已验证成立：v1.0 的 250 个 far 点前 125 个 == v1.1 的 125 个（逐位）。
- §5.3 的预估已被实测印证：AUC 确实机械上升（KDE h*=0.35：0.999512→0.999644），
  与检测变好无关，因此**不得跳版本比较 AUC/AP**。
- `recall_compact_void` 在全部 10 个配置上均为 **1.0000（125/125）**，印证它是
  整团同分同进同出的块状量，**不构成 KDE/LOF 方法差异**。

## 7. 决策权归属

| 事项 | 归属 |
|---|---|
| 协议版本号与字段增删改（是否升 B-v1.1-near） | **B** |
| 是否启用 near（#15）及其理由 | **A** |
| 实现、核验、复现证据、不变性契约 | **C** |
| 分层报告的写法与图表口径 | **D** |
