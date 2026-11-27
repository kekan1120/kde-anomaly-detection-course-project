# KDE 异常检测课程项目（瓦洛兰特组）

四人机器学习课程项目，研究核密度估计（KDE）带宽对异常检测的影响，并与局部异常因子（LOF）作受控比较。

- 课程：人机协作分组课程报告
- 截止：**2026-12-01 23:41**
- 提交：**两份文件**（人机协作流程记录 + 专题探究论文），超星「分组任务」页组长「开始作答」提交

## 目录结构（已统一）

| 目录 / 文件 | 内容 | 负责人 |
|---|---|---|
| `docs/` | 章程、实验协议、理论说明、术语表、决策日志、四人规划 | A |
| `process-logs/` | 四名成员各自的人机协作过程记录 | 各成员 |
| `04_code/` | 正式实现 + 核验脚本；`04_code/ai_draft/` 为 A 侧 AI 草稿参考 | C（ai_draft 为 A） |
| `05_results/` | `main/` 正式结果（D 唯一数据源）、`ref_check/` B 基准、`ai_draft/` A 草稿结果 | C / B / A |
| `06_paper/` | 论文草稿与素材 | D |
| `07_submission/` | 课程最终交付文件（两份） | A 打包 |
| `env/` | 依赖锁定与环境自查 | C |

> 说明：A 的 AI 草稿代码/结果统一收纳在 `04_code/ai_draft/` 与 `05_results/ai_draft/`，与 C 的正式实现（`04_code/src/`、`05_results/main/`）**物理隔离、不混用**；论文数值以 `05_results/main/` 为准。

## 关键入口

- 项目状态与待办：[PROJECT_STATUS.md](PROJECT_STATUS.md)
- 四人规划与验收标准：[docs/four-person-project-plan.md](docs/four-person-project-plan.md)
- 实验协议：[docs/experiment-protocol.md](docs/experiment-protocol.md)
- 理论说明与假设：[docs/theory-note.md](docs/theory-note.md)、[docs/research-questions-hypotheses.md](docs/research-questions-hypotheses.md)
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

## GitHub

https://github.com/kekan1120/kde-anomaly-detection-course-project
