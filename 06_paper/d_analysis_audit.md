# D 结果分析与人工核验记录

> 核验对象：`B-v1.0-locked` / `05_results/main/`。  
> 整理日期：2026-11-27。  
> 说明：本文件记录本轮机器辅助核对路径；D 本人及 C 的独立复核仍待完成，不替代人工核验或 C 的运行审计，也不伪造 DeepSeek 会话记录。

## 1. 数据源与版本

| 项目 | 采用文件 | 结论 |
|---|---|---|
| 主结果 | `05_results/main/metrics.csv` | 唯一正式数字源，v1.0 frozen |
| 配置 | tag `v1.0-results-frozen` 中的 `04_code/config_ref.json` | v1.0 论文口径；工作区配置用于更新后的协议 |
| 运行日志 | `05_results/main/run_log.txt` | train=600，validation=1000，test=1250；test anomaly=250 far |
| 审计 | `05_results/main/audit_results.md` | 13 项 PASS |
| 正确性检查 | `05_results/main/sanity_checks.md` | 15 项 PASS |
| 对账 | `05_results/main/reconciliation_vs_B.md` | 50 项 PASS |
| 草稿/基准 | `05_results/ai_draft/`、`05_results/ref_check/` | 禁止作为论文主结果 |

## 2. 独立核验动作

- 已运行 `py -3 04_code/plot_d_results.py`，脚本从 `05_results/main/` 生成 7 张图；D 正文现已引用全部 7 张。
- 已以程序读取 CSV 并对照正文所列核心结果、十次重复摘要和 E0 峰结构数据；数值映射登记在 `numeric_traceability.md`。
- 已用文本检查确认正文不含禁止的更新版本分层数字或草稿结果引用；摘要字符数为 239，关键词为 5 个。
- 已检查图像输出非空并抽查总览图与默认指标图；最终排版后的全页视觉审查仍由 A 完成。
- 上述属于机器辅助核对；C 已按交叉审阅职责完成正文数字、图表和追溯索引复核（32 项脚本检查，2026-11-27；详见 `c_review_of_D.md`），D 本人已完成内容与引用的人工核验。

## 3. 假设判定

| 假设 | 判定 | 依据 | 限定 |
|---|---|---|---|
| H1 | 支持 | E0 的局部极大点 8→3→2，显著峰 2→2→1，谷填充率 0.0007→0.1581→0.9140 | 仅为固定一维仿真示意 |
| H2 | 支持 | 默认 KDE 稀疏簇 FPR=0.0220，高于密集簇 0；十种子 h=0.35 均值仍为 0.0258 vs 0.0024 | 结论限于全局 99% 阈值和本数据 |
| H3 | 有条件支持 | v1.0 far-only 下 LOF k=20 稀疏 FPR=0.0080 低于 KDE 0.0220，但 recall=0.9720 低于 KDE 1.0000；B-v1.1 参考实现 near 两模型均 125/125 | 不得写成 LOF 总体优于 KDE；near 不是方法差异证据 |
| H4 | 支持 | validation 平均对数似然最优 h=0.35；test AUC 最高 h=1.20 | 后者为事后诊断，不能选参 |

## 4. 风险关闭情况

| 风险 | 处理 |
|---|---|
| 测试泄漏 | 采用 C 的 L1/L2/L3/L4/L5/L6/L7 审计结论；论文明确 train/validation/test 用途 |
| 分数方向写反 | 采用 `-score_samples`，并引用人工构造点方向检查 |
| AP 口径不明 | 说明使用 `sklearn.average_precision_score` 阶梯定义，测试异常比例为 0.2 |
| 稀疏簇误报被总体 FPR 掩盖 | 主结果同时报告 dense/sparse FPR |
| 把测试最优参数冒充事前最优 | H4 段落明确“事后描述，不参与选择” |
| 草稿数字混入 | 明确排除 `05_results/ai_draft/` 和 `05_results/ref_check/` |
| 文献来源 | 当前正文引用 `theory-note.md` §8 列出的来源；仍需 A 最终核对版式与文中支持关系 |

## 5. 待人工完成

- [x] D 本人核验正文数字、方法描述与引用，并在 `process-logs/member_D.md` 填入 DeepSeek 同一会话分享链接和真实回合。
- [x] D 已完成对 A 理论、文献、问题与假设的交叉复核；证据：`d_review_of_A.md`。A 仍需完成最终排版确认。
- [ ] B、C、D 在 `docs/stage0-closure-checklist.md` 完成个人任务和互审签字。
- [x] C 已完成 `run_checks.py` C3/C14 适配并产出正式 v1.1 结果：`05_results/main_v1_1_near/`；提交 `0500653`，正确性检查 17/17、结果审计 13/13、交叉审计 12/12、对账 39/39。该版本不改变 v1.0 far-only 主结果。
- [ ] A/B/C 通读论文，确认图号、成员工作量、提交格式与最终超星入口一致。
