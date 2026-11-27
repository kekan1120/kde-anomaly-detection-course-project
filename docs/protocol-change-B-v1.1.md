# 协议变更提案：B-v1.0 → B-v1.1（A 起草，交 B 确认发布）

> **提案人**：A 林辰旭（组长）　**起草日期**：2026-11-27
> **依据**：decision-log #15（A 拍板开启空区紧凑簇）、#18（论文主结果用 C 的 far + near@(0,5)）、C 的交叉审查结论（boundary / compact@(0,0) 已证伪）
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
- 论文可新增「局部 vs 全局」证据：near 是空区中的紧凑小簇，**KDE 按全局密度判异常、LOF 按局部密度判正常**——是该假设 H3 的关键判别点。

## 4. 执行步骤

| 步骤 | 责任人 | 动作 |
|---|---|---|
| 1 | **B** | 按 §1 改 `config_ref.json`（或另存 `config_ref_v1.1.json`，由 B 决定），写清变更原因与时戳 |
| 2 | **C** | 重跑 `python 04_code/run_experiment.py --multiseed`，输出到 `05_results/main/`，`run_log` 记录 `protocol_version=B-v1.1` |
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

- **合规**：走「新建 protocol_version」流程，不是同版本改字段；且变更在**看 near 结果之前**锁定，不构成测试集泄漏。
- **成本**：C 的实现（`dgp.py`、`protocol.py`、`reporting.py`）**已支持 near 的生成与分层报告**，只需改配置 + 重跑一次，成本低。
- **收益**：让论文从「只有 far 异常」升级为「far + near 两类」，使 H3（局部 vs 全局）有直接检验证据，显著提升论文 45 分部分的论证深度。
