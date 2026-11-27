# D 材料交接说明

## 已具备：可直接用于 D 工作

| 材料 | 用途 |
|---|---|
| `04_code/config_ref.json` | 确认当前 B-v1.1-near 协议；v1.0 历史主结果仍以冻结 tag 配置为准 |
| `05_results/main/metrics.csv` | v1.0 far-only 预注册主结果、方法对照表、KDE/LOF 敏感性曲线的唯一主结果数字源 |
| `05_results/ref_check_v1.1/metrics_ref.csv` | 不用于本论文正文；待 C 正式 v1.1 结果及组内决定 |
| `05_results/main/metrics_multiseed_summary.csv` | 结果稳定性补充，报告十次重复的均值和标准差 |
| `05_results/main/e0_demo1d_peaks.csv` | H1 一维带宽示意的峰数、显著峰数和谷填充率 |
| `05_results/main/run_log.txt` | 环境版本、样本量、阈值分位数、分数方向、H4 诊断和运行时间 |
| `05_results/main/sanity_checks.md` | 15 项正确性检查的可复现证据 |
| `05_results/main/audit_results.md` | 13 项结果审计证据 |
| `05_results/main/reconciliation_vs_B.md` | C 与 B 基准的 50 项数值对账证据 |
| `docs/theory-note.md` | KDE/LOF 公式、概率密度概念、分数方向和失效场景底稿 |
| `docs/research-questions-hypotheses.md` | Q1--Q3、H1--H4 的预先表述、支持和推翻条件 |
| `docs/paper-citation-guide.md` | 允许引用的结果、图表对应关系和禁止引用项 |
| `04_code/plot_d_results.py` | 从正式 CSV 重建 D 图表，避免手工抄数 |
| `06_paper/course_report.md` | 按 D 写作 brief 整理的 v1.0 far-only 论文正文 |
| `06_paper/numeric_traceability.md` | 数字、图表、结论到 CSV/日志的追溯索引 |
| `07_submission/submission_checklist.md` | 两份交付物的排版、互审、链接和提交检查 |

## 仍需补齐：材料与用途

| 需要谁提供 | 材料 | 用途 | 当前状态 |
|---|---|---|---|
| D 本人 | DeepSeek 同一连续会话分享链接、真实提示词、输出摘录、人工核验和纠错记录 | 满足 55 分人机协作流程记录；证明没有直接采信模型输出 | `process-logs/member_D.md` 已留位，不能由 Codex 代填 |
| A | Silverman、LOF 论文和 scikit-learn 文档的完整书目信息、DOI/稳定 URL、页码、访问日期 | 完成论文参考文献原文核验 | `docs/paper-citation-guide.md` 仅有来源和核验状态 |
| B | B-v1.1 协议签署材料和裁定 | 确认 near 分层的生成与版本边界 | 已完成并入库 |
| C | 已完成 v1.1 的 C3/C14 适配、正式运行与审计；仍需复核 D 图表、正文数值和追溯 ID | 关闭 C→D 交叉复审；不改变当前论文的 v1.0 far-only 主结果 | `05_results/main_v1_1_near/` 已入远端 main |
| A/B/C/D | 各自工作量、封面成员信息和最终文件格式确认 | 论文封面和超星提交 | 章程有初始分工，提交前需全组确认 |
| 组长 A | 最终 Word/PDF 排版、图注编号、超星入口和两份文件提交 | 完成正式交付 | `course_report.md` 已形成初稿 |

## 明确不需要现在提供

- v1.1 的 C 正式结果：已单独保存在 `05_results/main_v1_1_near/`；当前论文按 D brief 只写 v1.0 far-only，不引用 v1.1 数字。
- `05_results/ai_draft/` 的指标：它是 A 的草稿实验，数据设计不同，不能替换主结果。
- `05_results/ref_check/` 的指标：它是基准/回归副本，不是论文主结果。
- 测试集重新调参结果：会破坏冻结协议和测试独立性，不能用于当前论文。
