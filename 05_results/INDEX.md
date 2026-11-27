# 结果目录索引（版本 ↔ 配置 ↔ 结果 ↔ 论文用途）

> 维护人：C（实现与复现负责人）。本文件是**唯一**的版本对照表，任何"这份 CSV 是哪一版跑的"
> 问题都在这里查。规则：**只增不改**；一个结果目录只对应一个 `protocol_version`；
> **禁止跨版本混用数字**。

## 1. 版本对照

| 版本 | 配置（唯一数值事实来源） | 结果目录 | 冻结提交 | 状态 | 论文用途 |
|---|---|---|---|---|---|
| `B-v1.0-locked` | `04_code/config_ref.json` | `05_results/main/` | `7f4990c`（tag `v1.0-results-frozen`） | **冻结 / 预注册主结果** | §4 主表、主图（E0/E1/E2/E3）、技术路线与局限 |
| `B-v1.0-locked`（参考实现） | 同上 | `05_results/ref_check/` | `7f4990c` | 对账基准（见 §4 说明） | §3.4 可复现性举证、附录对账 |
| ~~`B-v1.1-near`~~ | **无**：仅 `04_code/patches/config_patch_near.json`（待 B 签署） | **无**：B 签署前不得产出任何正式结果 | — | **未授权 / 待签** | 无 |

**v1.1 的状态（重要）**：协议版本权归 B，`config_ref.json` 的 disclaimer 禁止同版本改字段。
因此仓库内**不存在** `config_v1_1_near.json`，也**不会**有条目名为 `main_v1_1_near/` 的正式结果目录。
目前只有三件待签件：`04_code/patches/config_patch_near.json`（三个字段差异 + change_record）、
`04_code/patches/protocol_section12_row_draft.md`（§12 行草稿）、
`04_code/patches/impact_checklist.md`（一页影响清单）。B 签署并给出新版本号后，
才按该版本号建立配置与结果目录，并在本表新增一行。

机制诊断（若在签署前确有必要）只允许落到 `05_results/ad_hoc/near_enabled/`，
`run_log.txt` 首两行固定为 `protocol=NOT LOCKED (awaiting B-v1.1)` 与 `status=ad-hoc`，
结果文件命名 `metrics_ad_hoc.csv`，**不得作为论文主结果**，也不进本表。

## 2. v1.0 关键文件的 sha256（前 16 位）

| 文件 | sha256 | 含义 |
|---|---|---|
| `04_code/config_ref.json` | `A9E7691BDF84906E` | 锁定的预注册配置 |
| `05_results/main/metrics.csv` | `2FD94BD4D437DA98` | 主结果长表（D 的唯一数据源） |
| `05_results/main/metrics_multiseed_summary.csv` | `740EBFA008A2E235` | P1 十种子均值±标准差 |
| `05_results/main/data_fingerprints.json` | `BF5E1A3CDDB933E2` | 三划分指纹（train `bbe5881f…`/validation `ac03679b…`/test `e00edf67…`） |

完整哈希值可用 `Get-FileHash <file> -Algorithm SHA256` 复算；不一致即说明文件被改动过。

## 3. 引用规则（给 D 与 A）

1. **主结论只引 v1.0**：带宽敏感性（H1）、分簇误报率分解（H2）、似然最优 vs 检测最优带宽（H4）
   的数字全部来自 `05_results/main/metrics.csv`。v1.1 不参与这三条。
2. **AUC / AP 不得跨版本比较**。v1.1 只是把 125 个远端异常换成 125 个空区紧凑簇异常，
   正样本构成变了 → AUC/AP 会机械上升（预测见 §5），与"检测变好"无关。
   同一版本内横比 h 或 k 才有效。
3. **`recall_far` 跨版本是否可比，取决于 far 抽样方案**（A/B 两案，待定，见 §5）。
   A 案下完全不可比；B 案下逐点可比但分母从 250 变 125。
4. **分清"实测"与"预测"**：§5 的表格是**跑之前**写下的预测，用来事后对照是否符合机制预期；
   它**不是结果**，任何论文数字都不得引用 §5。

## 4. `05_results/ref_check/` 的身份说明（重要）

该目录是**在本机重跑 B 的参考实现**（`04_code/ref_check/run_ref.py`）得到的等价副本，
其数值与 B 的 `HANDOFF_README.md` §3.3 / §3.4 / §3.5 逐项一致（10 个阈值、E1/E2 全表、E0 峰结构）。
B 的**原始**文件保存在 `kde-anomaly-detection-handoff` 压缩包中。

- 用途：C 的对账基准与回归副本。
- 若 B 后续推送其原始结果：**以其为准**，本目录降级为「回归副本」，不得再作为原始凭证引用。
- 它不属于正式结果，不作为论文数据源。

## 5. 若 B 签署：预测与待定项（跑之前写，跑之后对照）

待定项与影响范围已移到 `04_code/patches/`（`config_patch_near.json` 的 `open_questions_for_B`、
`protocol_section12_row_draft.md` §3、`impact_checklist.md`）。本节只保留**跑前预测**，
用于事后对照机制是否符合预期；**它不是结果**，任何论文数字不得引用本节。

**预测表（v1.1 相对 v1.0，默认操作点 h\*=0.35 / k\*=20）**

| 指标 | 方向 | 理由 |
|---|---|---|
| `fp_dense` / `fp_sparse` | 不变（逐位） | 假阳性只在正常样本上计；阈值来自 train+validation，两版未变 |
| `recall_far` | B 案：逐点相同（分母 125）；A 案：不可预测 | B 案 far 点与 v1.0 同一批、分数逐位相同 |
| `recall_compact_void` | ≈1.0（KDE 与 LOF 都是） | KDE：该处密度比簇心低约 6 个数量级；LOF：LOF≈2–4 > 阈值 1.89–2.02 |
| `roc_auc` | ↑（两检测器） | 新增 125 个分数高于全部正常点的正样本 → 12.5 万对几乎全对 |
| `average_precision` | ↑（两检测器） | 同上，新增正样本落在 PR 曲线最左侧高分段 |

**论文口径（必须写进 §3.3 / §5）**

- 每类异常仅 **125** 个 → 单点变化 = **0.8 个百分点**，不得按百分点解读。
- `recall_compact_void` 是**近似 0/1 的块状量**（整团同分，同进同出），不是连续指标；
  报告时给出分子/分母（如 125/125）而非小数。
- v1.1 是 **post-hoc 协议修订**，不是预注册；变更前已看过 v1.0 测试结果，这一点在
  `change_record.test_results_seen_before_change = true` 中如实记录。

## 6. 变更记录在哪

| 位置 | 内容 | 归属 |
|---|---|---|
| `01_protocol_and_data_dictionary.md` §12 | 协议变更行（草稿在 `04_code/patches/protocol_section12_row_draft.md`） | B（C 起草） |
| `04_code/patches/config_patch_near.json` → `change_record` | 机器可读变更块（**不是配置文件**） | C |
| `docs/decision-log.md` #15 | A 的决策原文 | A |
| 各结果目录的 `run_log.txt` | 运行时打印 `protocol_version` + 配置路径/sha256 + 变更块 | C |

## 7. 标签

| tag | 指向 | 含义 |
|---|---|---|
| `v1.0-results-frozen` | `7f4990c` | v1.0 结果与配置的冻结点；对账/复现以此为准 |
| `v1.1-near-results` | （不得打） | 仅当 B 签署新版本号、跑通并通过不变性契约后才可打；签前禁止 |