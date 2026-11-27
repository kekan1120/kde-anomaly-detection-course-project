# 先读这个

**《核密度估计与基于密度的异常检测》四人课程项目 —— 阶段 1（数据与实验设计）交付包**

B（数据与实验设计负责人）已经把数据生成协议、参数网格、阈值规则、指标定义全部锁定，
并跑通了参考实验、通过了 13 项正确性核验和 12 项结果审计。**现在可以开始写正式实现和论文了。**

---

## 一、三步开始

在**解压后的项目文件夹里**打开 PowerShell，依次执行：

```powershell
# 第 1 步：装环境（只有第一次需要）
python -m venv .venv
.venv\Scripts\activate
pip install -r env\requirements.txt

# 第 2 步：验证环境（必须看到 PASS）
python env\verify_env.py

# 第 3 步：跑通全部实验（约 10 秒，应该全部 PASS）
.venv\Scripts\python.exe 04_code\ref_check\checks.py
.venv\Scripts\python.exe 04_code\ref_check\run_ref.py
.venv\Scripts\python.exe 04_code\ref_check\audit_results.py
```

三步都过了，说明你机器上跑出来的数字和 B 的完全一致，可以放心往下做。

> 第 2 步输出 `RESULT: PASS -- environment reproduces the reference numbers exactly`
> 才代表环境没问题。它比对的是**训练集数据的 sha256**，全 PASS 说明你生成的数据逐位相同。
>
> 装环境遇到问题（pip 报错、Python 版本不对）看 **`env/README_ENVIRONMENT.md`**。

---

## 二、你该读什么

| 角色 | 先读 | 然后 | 你要交付 |
|---|---|---|---|
| **C** 实现与复现 | `01_protocol_and_data_dictionary.md` | `HANDOFF_README.md` §3–§4（基准数值 + 自查清单） | 独立实现一遍，和 B 的 `05_results/ref_check/metrics_ref.csv` 对账 |
| **D** 分析与论文 | `HANDOFF_README.md` §5（结果在讲什么） | `05_results/ref_check/metrics_ref.csv` + `figures/` | 从 CSV 重绘定稿图、写第 4–5 章 |
| **A** 组长兼理论 | `01_protocol_and_data_dictionary.md` §4–§6、§11 | `HANDOFF_README.md` §6（待拍板项） | 核验公式与文献、确认假设范围 |

**所有人都要读：** §三 的五条纪律。

---

## 三、五条纪律（红线，踩了整份实验作废）

1. **测试集不能参与任何选择。** 带宽、邻居数、阈值、异常类型、样本量 —— 一次都不行。
   参数网格在跑实验之前就写死在 `04_code/config_ref.json` 里了，跑出来不好看也要保留。
2. **不要用测试指标最优的参数当主比较的默认参数。** 默认值是 `h*=0.35, k*=20`，
   按 Silverman 参考带宽在跑实验前指定的。
3. **不要只报总误报率。** 总 FPR 1.1% 看起来正常，但分解后是密集簇 0/500、稀疏簇 11/500 ——
   只报总数会把 H2 的全部证据藏起来。
4. **不要把 KDE 的 `score_samples` 直接当异常分数**（它是 log 密度，越大越正常）；
   也不要按函数名推断 LOF 的符号，必须实测。
5. **不要手工从图里读数填进论文。** 所有数字从 `metrics_ref.csv` 程序化生成。
   `figures/` 里的是**自检图,不是定稿图**,D 必须重绘。

---

## 四、文件地图

```
START_HERE.md                       ← 你正在读的
01_protocol_and_data_dictionary.md  ★ 预注册协议：数据生成、划分、参数网格、阈值规则、
                                      指标定义、控制变量表、泄漏清单、假设→观测量映射
HANDOFF_README.md                   ★ 交接说明：基准数值、C 的自查清单、结果解读、待拍板项
env\                                ★ 环境（分享/安装就看这里）
  requirements.txt                    精确版本锁定 —— pip install -r 用这个
  requirements_min.txt                精确版本装不上时的宽松备选
  verify_env.py                       装完自查（含数据指纹比对）
  README_ENVIRONMENT.md               环境安装与排错说明
04_code\
  config_ref.json                   ★ 唯一数值事实来源（不要手抄数字，直接 json.load）
  ref_check\
    reference_impl.py                 独立参考实现（含手写 KDE / 手写 LOF / 手算指标）
    run_ref.py                        全量实验 E0/E1/E2/E3
    checks.py                         13 项正确性核验
    audit_results.py                  12 项结果审计
05_results\ref_check\
  metrics_ref.csv                   ★ 主结果（D 画图与制表的唯一数据源）
  metrics_ref_multiseed_summary.csv   10 个种子的均值±标准差
  e0_demo1d_peaks.csv                 一维带宽示意的峰结构表
  data_fingerprints.json            ★ C 的自查基准（三个 split 的 sha256 与统计量）
  seed_registry.csv                   种子与数据流登记表
  sanity_checks.md                    13 项核验记录（论文举证的现成材料）
  audit_results.md                    12 项审计记录
  run_log.txt                         环境版本、全部阈值、运行时间
  figures\                            6 张自检图（非定稿）
references\
  four-person-project-plan.md         组长写的完整四人规划
```

---

## 五、需要组内拍板的事（`HANDOFF_README.md` §6 有详细说明）

| # | 问题 | B 的建议 |
|---|---|---|
| Q1 | 四人姓名、组长、**课程截止日期**、提交入口与文件格式 | 组长去平台核实 —— **这个阻塞阶段 0,别拖** |
| Q2 | 保留全部 H1–H4,还是合并 H1+H4 只留带宽敏感性主线 | 保留 H1、H2、H4；H3 由 E3 承担 |
| Q3 | 是否启用 P1「空区紧凑簇」异常 | **不要为了拉开方法差距而启用**（实测无效，理由见下） |
| Q4 | 10 种子重复是否写进正文（已跑完） | 写进去,增强「结论有依据」 |
| Q5 | 一维示意的峰判定口径（prominence ≥ 10%）是否认可 | 认可 |
| Q6 | 是否全组统一这套环境 | 是 |

**关于 Q3（这条我更正过）：** 我一开始说「空区紧凑簇能把 KDE 和 LOF 拉开」,并建议启用。
**实测证明这个说法是错的,已撤回。**

原因:协议强制 LOF 用 `novelty=True`（只在训练正常样本上拟合）。此时新点的局部可达密度是
**相对训练集**算的,离训练集很远就一定很低,所以 **LOF 反而会判它异常**。教材里「LOF 对空区紧凑簇
失效」的前提是 LOF 跑在**整个数据集**上,两种语义不同,我混淆了。

实测（`04_code/ref_check/probe_hard_cases.py`,纯坐标探针、不用测试标签）:

| 构造 | KDE 判异率 | LOF 判异率 |
|---|---:|---:|
| 空区紧凑簇 sd 0.35 | 100% | **100%** |
| 空区紧凑簇 sd 0.10 | 100% | **100%** |
| 远端环（现有核心情形） | 99% | 97% |

所以 `compact_void` 保持关闭,**核心实验不动**。

那 AUC 饱和（所有配置 ≥ 0.9990）怎么办?已经解决了,不需要新异常类型:
- 加「等价错排配对数」指标 —— h=0.10 是 256 对、h=1.20 是 34 对,差 7.5 倍
- 分簇报误报率 —— **KDE 稀疏簇 11/500、密集簇 0/500;LOF 是 4/500 与 5/500**

后者才是 H2/H3 的真证据,且已过 10 个种子重复验证。

---

## 六、三点说明

1. **本文档中的路径都相对仓库根目录。** 命令里的 `.venv\Scripts\python.exe` 指你自己建的虚拟环境；
   **所有脚本内部的路径都是相对自身位置解析的**，把仓库放哪儿都能跑，不需要改代码。
2. **仓库里不含 `.venv`，也不需要。** 虚拟环境换台机器就跑不起来
   （`pyvenv.cfg` 里写死了 Python 安装路径），按第一节自己建就行。
3. **`config_ref.json` 是锁定文件，C 只读不改。** 任何数值、网格、种子、阈值规则的改动都必须
   新建 `protocol_version` 并记录原因 —— 见 `01_protocol_and_data_dictionary.md` §12。

---

## 七、人机协作过程记录

任务书要求每个人用**自己账号下的一个连续会话**完成自己负责的部分,并提供会话分享链接。
这个包只是产物,**过程记录得你自己维护**。别到最后补写。
