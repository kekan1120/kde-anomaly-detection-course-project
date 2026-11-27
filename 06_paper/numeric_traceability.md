# 数字—图表—结论追溯表（D）

> 规则：论文正文数字保留四位小数；所有数值从冻结机器可读文件读取。`05_results/ai_draft/` 和 `05_results/ref_check/` 不得作为主结果来源。

| ID | 论文位置/图表 | 数字或结论 | 来源字段/行 | 参数与数据角色 | 核验状态 |
|---|---|---|---|---|---|
| T-001 | 图2、§4.1 | E0 局部极大点 8/3/2，显著峰 2/2/1，谷填充率 0.0007/0.1581/0.9140 | `e0_demo1d_peaks.csv` 三行 | 独立 1D 示意；h=0.08/0.30/0.90 | D已核验；待 A/C 复核 |
| T-002 | §3.2、图1 | train=600，validation=1000，test=1250，test anomaly=250，比例=0.2000 | train：`run_log.txt`/冻结配置；validation：`val_exceedance_count/rate` 推断并由日志确认；test：`metrics.csv` n/n_normal/n_anomaly/prevalence | train/validation/test；far-only | D已核验；待 A/C 复核 |
| T-003 | §4.1、图3 | KDE h=0.10 AUC=0.9990、recall=0.9680；h=1.20 AUC=0.9999、recall=1.0000 | `metrics.csv` E1_kde_sensitivity 两行 | 测试集最终评估；阈值来自正常验证集 | C 已复核（2026-11-27；32 项脚本 + 逐项对照 CSV） |
| T-004 | §4.1、图3 | KDE h=0.80 F1=0.9804，h=1.20 F1=0.9766 | `metrics.csv` E1 rows, f1 | 测试集；不得写成 h=1.20 全指标最优 | C 已复核（2026-11-27；32 项脚本 + 逐项对照 CSV） |
| T-005 | §4.1、图4 | LOF k=10 AUC=0.9979、recall=0.9520；k=50 AUC=0.9995、recall=0.9960 | `metrics.csv` E2_lof_sensitivity 两行 | novelty=True；测试集 | C 已复核（2026-11-27；32 项脚本 + 逐项对照 CSV） |
| T-006 | §4.2、图5、图6 | KDE h=0.35：AUC/AP/P/R/F1=0.9995/0.9980/0.9579/1.0000/0.9785 | `metrics.csv` E3_method_comparison kde 行 | 默认操作点；测试集 | C 已复核（2026-11-27；32 项脚本 + 逐项对照 CSV） |
| T-007 | §4.2、图5、图6 | LOF k=20：AUC/AP/P/R/F1=0.9990/0.9962/0.9643/0.9720/0.9681 | `metrics.csv` E3_method_comparison lof 行 | 默认操作点；测试集 | C 已复核（2026-11-27；32 项脚本 + 逐项对照 CSV） |
| T-008 | §4.2 | KDE dense/sparse FPR=0.0000/0.0220；LOF=0.0100/0.0080 | `metrics.csv` E3 fpr_dense/fpr_sparse | 正常测试子集；各 500 点 | C 已复核（2026-11-27；32 项脚本 + 逐项对照 CSV） |
| T-009 | §4.3、图7 | 验证平均对数似然最优 h=0.35，值=-2.8790；测试集事后 AUC 最高 h=1.20，值=0.9999 | `metrics.csv` E1 val_mean_log_likelihood/roc_auc | H4；测试 AUC 仅事后描述，不参与选参 | D已核验；C 已复核（2026-11-27；32 项脚本 + 逐项对照 CSV）；待 A 复核 |
| T-010 | §4.4 | KDE h=0.35 多种子 AUC/AP=0.9998±0.0002/0.9990±0.0007 | `metrics_multiseed_summary.csv` kde param=0.35 | 10 repeats；稳健性补充 | C 已复核（2026-11-27；32 项脚本 + 逐项对照 CSV） |
| T-011 | §4.4 | LOF k=20 多种子 AUC/AP=0.9995±0.0003/0.9982±0.0011 | `metrics_multiseed_summary.csv` lof param=20 | 10 repeats；稳健性补充 | C 已复核（2026-11-27；32 项脚本 + 逐项对照 CSV） |
| T-012 | §4.2 | KDE 稀疏簇误报 11/500，密集簇 0/500 | `metrics.csv` E3 fp_sparse/fp_dense 与 n_normal_* | 正常测试子集 | C 已复核（2026-11-27；32 项脚本 + 逐项对照 CSV） |

## 追溯填写约定

- 复核人必须写姓名、日期和动作，例如“从 CSV 重算 F1”“核对 run_log 阈值来源”“重建图表”。
- 若图号在最终排版中变化，保留 T-ID，只更新图号。
- 若任意数字与 CSV 不一致，状态改为“需重跑/不通过”，不得直接改 CSV 或事后改协议。

## 追溯补充字段

| 追溯范围 | 阈值规则与阈值 | 分数方向 | 人工复核人/日期/动作 |
|---|---|---|---|
| T-003--T-005 | 每个 detector/参数由正常验证集 99% 分位数校准，`numpy.quantile(..., method="inverted_cdf")`；逐项对照配置和运行日志 | KDE/LOF 统一为越大越异常；LOF 符号由 API 文档与人工样例确认 | D 陈永喆，2026-11-27；C 已复核（32 项脚本 + 逐项对照 CSV） |
| T-006、T-012 | KDE h=0.35 threshold=6.1760；来自 E3 `threshold` 字段 | 越大越异常 | D 陈永喆，2026-11-27；C 已复核（32 项脚本 + 逐项对照 CSV） |
| T-007 | LOF k=20 threshold=2.0223；来自 E3 `threshold` 字段 | 越大越异常 | D 陈永喆，2026-11-27；C 已复核（32 项脚本 + 逐项对照 CSV） |
| T-008 | 分簇误报率由正常测试子集误报数/簇样本数计算 | 越大越异常 | D 陈永喆，2026-11-27；C 已复核（32 项脚本 + 逐项对照 CSV） |
| T-009 | H4 不使用测试集阈值选参；测试 AUC 只作事后描述 | 越大越异常 | D 陈永喆，2026-11-27；C 已复核（32 项脚本 + 逐项对照 CSV）；待 A 复核 |
| T-010--T-011 | 多种子各重复沿同一验证阈值规则；不属于主 `metrics.csv` | 越大越异常 | D 陈永喆，2026-11-27；C 已复核（32 项脚本 + 逐项对照 CSV） |
| T-001 | 不适用；独立一维原理示意不做异常检测 | 不使用异常分数 | D 陈永喆，2026-11-27；逐项对照 `e0_demo1d_peaks.csv` |
