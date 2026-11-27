# KDE 异常检测课程项目（瓦洛兰特组）

四人机器学习课程项目，研究核密度估计（KDE）带宽对异常检测的影响，并与局部异常因子（LOF）作受控比较。

- 课程：人机协作分组课程报告
- 截止：**2026-12-01 23:41**
- 提交：**两份文件**（人机协作流程记录 + 专题探究论文），超星「分组任务」页组长「开始作答」提交

## 目录结构（已统一）

| 目录 / 文件 | 内容 | 负责人 |
|---|---|---|
| `01_protocol_and_data_dictionary.md` | **权威实验协议**（预注册说明 + 数据字典 + 参数网格 + 阈值规则 + 指标定义 + 控制变量 + 泄漏清单 + 假设→观测量） | B |
| `HANDOFF_README.md` | B 的交接说明：基准数值、C 的自查清单、结果解读、待拍板项 | B |
| `START_HERE.md` | 新人/队友入口：三步开始 + 按角色该读什么 + 五条纪律 | B |
| `docs/` | 章程、实验协议（历史草稿）、理论说明、术语表、决策日志、四人规划、论文引用口径 | A |
| `process-logs/` | 四名成员各自的人机协作过程记录 | 各成员 |
| `04_code/` | 正式实现 + 核验脚本；`04_code/ai_draft/` 为 A 侧 AI 草稿参考；`04_code/ref_check/` 为 B 的参考实现与核验/审计套件 | C（ai_draft 为 A，ref_check 为 B） |
| `05_results/` | `main/` 正式结果（D 唯一数据源）、`ref_check/` B 基准、`ai_draft/` A 草稿结果 | C / B / A |
| `06_paper/` | 论文草稿与素材 | D |
| `07_submission/` | 课程最终交付文件（两份） | A 打包 |
| `env/` | 依赖锁定与环境自查 | C |

> 说明：A 的 AI 草稿代码/结果统一收纳在 `04_code/ai_draft/` 与 `05_results/ai_draft/`，与 C 的正式实现（`04_code/src/`、`05_results/main/`）**物理隔离、不混用**；论文数值以 `05_results/main/` 为准。
> **A 侧草稿的部分设计已被证伪**（boundary 球壳标签矛盾、compact@(0,0) 位于两簇鞍部），详见 `docs/experiment-protocol.md` §10 第 5 条；该草稿作为「设计迭代记录」保留，不进入论文主结果。
> **`docs/experiment-protocol.md` 的 §1–§9 已被 `01_protocol_and_data_dictionary.md` 取代**（三类异常 vs 单一 far 异常、样本量与分位数方法均不同），仅作审计留痕，**不得作为论文依据或复现依据**。

## 关键入口

- 项目状态与待办：[PROJECT_STATUS.md](PROJECT_STATUS.md)
- **权威实验协议（复现与论文都以它为准）**：[01_protocol_and_data_dictionary.md](01_protocol_and_data_dictionary.md)
- **新人从这里开始**：[START_HERE.md](START_HERE.md)
- **交接与基准数值**：[HANDOFF_README.md](HANDOFF_README.md)
- 四人规划与验收标准：[docs/four-person-project-plan.md](docs/four-person-project-plan.md)
- 历史实验协议草稿（**已被取代**）：[docs/experiment-protocol.md](docs/experiment-protocol.md)
- 理论说明与假设：[docs/theory-note.md](docs/theory-note.md)、[docs/research-questions-hypotheses.md](docs/research-questions-hypotheses.md)
- 论文引用口径：[docs/paper-citation-guide.md](docs/paper-citation-guide.md)
- 代码跑法：[04_code/README.md](04_code/README.md)

## 复现（C 正式实现）

```powershell
pip install -r env\requirements.txt
python env\verify_env.py
python 04_code\run_experiment.py --multiseed
```

A 侧 AI 草稿（教学参考，非正式结果）：

```powershell
python 04_code\ai_draft\run_experiment.py
```

## 结果位置

- **正式结果**：`05_results/main/metrics.csv`（D 画图制表的唯一数据源）
- **对账基准**：`05_results/ref_check/metrics_ref.csv`（B）
- **A 侧草稿**：`05_results/ai_draft/`（AI 草稿实验，仅参考，不作为论文定稿数值）

## 版本与验收（C）

- 版本 ↔ 配置 ↔ 结果 对照：[05_results/INDEX.md](05_results/INDEX.md)。v1.0 已冻结于 tag `v1.0-results-frozen`（提交 `7f4990c`）
- v1.0 验收：正确性核验 **15/15**、结果审计 **13/13**、B 脚本交叉审计 **12/12**、与 B 基准对账 **50/50（偏差 0）**
- 配置变更只能由 B 升协议版本。当前 `config_ref.json` = `B-v1.1-near`（已签），
  C 的 v1.1 正式结果在 `05_results/main_v1_1_near/`（核验 17/17、与 B 参考结果对账 39/39，max|Δ|=0）；
  v1.0 仍是预注册主结果，AUC/AP 不得跨版本比较

## GitHub

https://github.com/kekan1120/kde-anomaly-detection-course-project
