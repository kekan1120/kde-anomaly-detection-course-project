# KDE异常检测课程项目

四人机器学习课程项目，研究核密度估计（KDE）带宽对异常检测的影响，并与局部异常因子（LOF）作受控比较。

## 项目状态

**当前阶段：阶段0（立项与开工约束）进行中**

详细状态和未完成事项见 [PROJECT_STATUS.md](PROJECT_STATUS.md)。

## 项目文件

- [四人项目规划与验收标准](docs/four-person-project-plan.md)
- [阶段0项目章程](docs/project-charter.md)
- `process-logs/`：四名成员各自维护的AI协作流程记录
- `configs/`：锁定后的数据、随机种子、参数网格和实验配置
- `src/`：数据生成、模型打分、评价与绘图实现
- `results/`：机器可读结果和图表
- `submission/`：课程要求的最终交付文件

## GitHub仓库

本地项目已连接至 [kekan1120/kde-anomaly-detection-course-project](https://github.com/kekan1120/kde-anomaly-detection-course-project)，仓库为公开可见，默认分支为 `main`。

## 阶段2：实现与复现（成员 C）

| 路径 | 内容 |
|---|---|
| `04_code/` | 正式实现与 4 个核验脚本（跑法见 [04_code/README.md](04_code/README.md)） |
| `04_code/config_ref.json` | B 锁定、C 只读的预注册配置（唯一数值事实来源） |
| `04_code/ref_check/` | B 的参考实现（对照基准）+ C 的交叉审查记录 `PATCHES_C.md` |
| `env/` | 依赖锁定（18 个精确版本）与 `verify_env.py` 环境自查 |
| `05_results/main/` | **正式结果**：`metrics.csv` 是 D 画图制表的唯一数据源 |
| `05_results/ref_check/` | B 的基线结果快照（对账基准） |
| `process-logs/member_C.md` | C 的人机协作过程记录 |
| `06_paper/section3_4_draft.md` | 交给 D 的 §3.4「实验流程与代码实现」素材 |

复现三步：

```powershell
pip install -r env\requirements.txt
python env\verify_env.py                       # 必须 PASS（比对训练集 sha256）
.venv\Scripts\python.exe 04_code\run_experiment.py --multiseed
```

核验四连（全部 PASS 才算复现成立）：

```powershell
.venv\Scripts\python.exe 04_code\run_checks.py              # 15 项正确性核验
.venv\Scripts\python.exe 04_code\run_audit.py               # 13 项结果审计
.venv\Scripts\python.exe 04_code\cross_audit.py             # 用 B 的审计脚本审 C 的结果（12 项）
.venv\Scripts\python.exe 04_code\reconcile_with_baseline.py # 与 B 基准逐项对账（50 项，偏差 0）
```

当前结论：三个划分的数据指纹与 B **sha256 逐位一致**；10 个阈值、12 行主结果 × 22 个数值列、
10 个种子的汇总，与 B 的基准文件**最大绝对偏差 0.000e+00**；换新 venv 重跑同样一致。

> **目录约定提示（待组长统一）**：A 的文档在 `docs/`、过程记录在 `process-logs/`；
> B 与 C 的代码与结果按规划 PDF §8 使用 `04_code/`、`05_results/`。B 的协议文档
> （`01_protocol_and_data_dictionary.md`、`HANDOFF_README.md`）尚未入库，由 B 自己提交。
> 建议阶段 5 打包前由 A 决定是否统一成一套目录结构。
