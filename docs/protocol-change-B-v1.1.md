# 协议变更提案：B-v1.0 → B-v1.1（A 起草，交 B 确认发布）

> **提案人**：A 林辰旭（组长）　**起草日期**：2026-11-27
> **依据**：decision-log #15（A 拍板开启空区紧凑簇）、#18（论文当前主结果 far-only；near@(0,5) 待 v1.1 签署后补充）、C 的交叉审查结论（boundary / compact@(0,0) 已证伪）
> **状态**：待 **B 确认并在 `config_ref.json` 发布**；A 无权代改，因该文件是「B 锁定、C 只读」的唯一数值事实来源。

## 1. 变更内容（仅 4 个字段，其余全部不动）

| 字段 | 旧值（B-v1.0） | 新值（B-v1.1） | 理由 |
|---|---|---|---|
| `protocol_version` | `B-v1.0-locked` | `B-v1.1-locked` | 新建版本，满足「禁止同版本改字段，须新建 protocol_version 并记录原因」 |
| `protocol_locked_utc` | `TBD-by-team` | 锁定时刻（B 填） | 记录本次变更生效时点 |
| `anomaly.types.near.enabled` | `false` | **`true`** | 开启「空区紧凑簇」，用于检验局部(LOF) vs 全局(KDE)分歧 |
| `anomaly.types.near.n_test` | `0` | **`125`** | near 与 far 各占一半 |
| `anomaly.types.far.n_test` | `250` | **`125`** | 使二者之和仍为 250，测试异常比例保持 20% |

## 2. 不变量（明确不动，防止误改）

- **near 构造**：`center=[0.0, 5.0]`、`cov_diag=[0.1225, 0.1225]`（std=0.35）、`construction="compact_gaussian"`、`seed_key="test.anomaly.near"`（种子 1733）。
- **far 构造**：`construction="ring_uniform"`、`r∈[5,7]`、种子 1723。
- **数据划分**：train 600 / validation 1000 / test 1250。
- **测试集构成**：dense 500 + sparse 500 + anomaly 250，`anomaly_ratio=0.2`。
- **参数网格**：KDE h∈{0.10,0.20,0.35,0.50,0.80,1.20}；LOF k∈{10,20,35,50}。
- **阈值规则**：`numpy.quantile(scores_val, 0.99, method='inverted_cdf')`，`score > threshold` 判异常（严格大于）。
- **指标定义**、**随机种子策略**、**主比较默认参数 h\*=0.35 / k\*=20**：均不变。

## 3. 变更后的影响

- 测试集：1250 = 1000 正常 + 250 异常（**125 far + 125 near**），异常比例仍为 20.0%。
- **主结果须按 `anomaly_type` 分层报告**（far 召回 / near 召回分别给出），不得只报总体召回。
- 论文可新增 near 的分层结果，但**必须更正预期方向**：在 `novelty=True` 且参照集仅含 600 个正常训练样本时，near 点的 k 近邻只能来自正常簇尾部（距离约 2.4–3.2），`lrd(q)≈1/d̄(q)` 由该距离决定、与团内紧密程度无关 → LOF≈2–4，**高于阈值 1.89–2.02，会被判为异常**。原「局部密度很高→LOF 判正常」对应的是**参照集包含该团**的情形（非 novelty 或污染训练集）。因此本变更**不预期**产生「KDE 检出、LOF 漏检」的对照；若需要该对照，应另立 **P2 污染训练集**实验。（详见 `04_code/patches/config_patch_near.json` 的 `mechanism_caveat`）

## 4. 执行步骤

| 步骤 | 责任人 | 动作 |
|---|---|---|
| 1 | **B** | 按 §1 改 `config_ref.json`（或另存 `config_ref_v1.1.json`，由 B 决定），写清变更原因与时戳 |
| 2 | **C** | 重跑 `python 04_code/run_experiment.py --multiseed`，输出到**新目录**（如 `05_results/near_v1.1/`，目录名由 B 定），**不得覆盖 `05_results/main/` 的 v1.0 冻结结果**（否则毁掉 50 项对账与 tag `v1.0-results-frozen`）；`run_log` 记录 `protocol_version=B-v1.1` |
| 3 | **C** | 确认结果按 `anomaly_type` 分层（far / near 召回均有值） |
| 4 | **B** | 用审计脚本复核新结果符合 v1.1 契约 |
| 5 | **D** | 以 v1.1 新结果为准写论文（far/near 分层报告） |

## 5. 验收清单

- [ ] `protocol_version == "B-v1.1-locked"`
- [ ] `near.enabled == true`、`near.n_test == 125`、`far.n_test == 125`
- [ ] 测试集 1250 样本、异常 250、比例 20%（不变）
- [ ] 结果按 `anomaly_type` 分层报告（far / near 召回分别给出）
- [ ] `05_results/main/run_log.txt` 记录 `protocol_version=B-v1.1`
- [ ] B / C / D 三方确认

## 6. 风险与回退

- **风险**：near 开启后若 KDE 与 LOF 在 near 上的差异不显著，论文须**如实报告**，不得因结果不理想回调参数（已锁 v1.1）。
- **回退方案**：若时间不足（截止 2026-12-01 23:41）或 near 结果异常，主结果回退为 v1.0（仅 far），near 作 P1 拓展在局限一节说明「因协议版本未解锁未纳入主结果」——**但回退须在跑 near 之前决定，不能看了 near 结果再回退**。

## 7. 为何现在改（合规与时间）

- **合规**：走「新建 protocol_version」流程，不是同版本改字段；变更在**看 near 结果之前**锁定。注意：v1.0 结果已产出并被用于本决策，故本变更为 **post-hoc protocol amendment（事后修订，非预注册）**——论文中须与 v1.0 预注册主结果并列并标注（详见 `04_code/patches/config_patch_near.json` 的 `change_record`）。
- **成本**：C 的实现（`dgp.py`、`protocol.py`、`reporting.py`）**已支持 near 的生成与分层报告**，只需改配置 + 重跑一次，成本低。
- **收益**：若 B 签署 v1.1，论文可新增 near 的**分层结果**（每类各 125 个，召回近似 0/1 块状量，AUC/AP 不得跨版本比较）；**但该变更不预期产生 KDE/LOF 方法差异**（机制见 §3）——它是「补充分层证据」，不是「验证局部 vs 全局优劣」。签署并在 C 重跑前，论文不得引用任何 near 数字。
