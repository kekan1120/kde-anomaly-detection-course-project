# 正确性核验记录（sanity checks）

> 本文件由 `04_code/ref_check/checks.py` 自动生成，请勿手工编辑。
> 重新生成：`.venv\Scripts\python.exe 04_code\ref_check/checks.py`

| 项 | 值 |
|---|---|
| 协议版本 | `B-v1.1-near` |
| 检查项数 | 13 |
| 失败项数 | **0** |
| Python | 3.14.6 |
| numpy / scipy / scikit-learn | 2.5.5 / 1.18.1 / 1.9.1 |
| matplotlib / pandas | 3.11.2 / 3.1.1 |

## 总览

| 编号 | 检查项 | 结论 |
|---|---|---|
| C1 | 协议配置自洽性 | ✅ PASS |
| C2 | 同一种子两次生成的 600/1000/1250 行数据逐位一致 | ✅ PASS |
| C3 | 三个 split 的数据指纹互不相同 | ✅ PASS |
| C4 | 各 split 规模、逐簇计数与标签规则 | ✅ PASS |
| C5 | train/validation/test 之间无逐点重合 | ✅ PASS |
| C6 | KDE 公式手算特例 + 手写实现与 sklearn 交叉核验 | ✅ PASS |
| C7 | 手写 LOF（Breunig 定义）与 sklearn novelty 模式交叉核验 | ✅ PASS |
| C8 | 异常得分方向（越大越异常）在全部带宽与邻居数下成立 | ✅ PASS |
| C9 | 阈值校准：验证集超阈样本数恒为 10/1000（经验误报率 1.00%） | ✅ PASS |
| C10 | 指标实现：微型手算样例 + 真实测试集上手算与 sklearn 交叉核验 | ✅ PASS |
| C11 | 分簇误报率可加回总误报率 | ✅ PASS |
| C12 | 无标签泄漏：阈值只来自 validation，与 test 无关 | ✅ PASS |
| C13 | 一维示例：小带宽出现伪峰、大带宽把双峰抹平（prominence 口径） | ✅ PASS |

## 逐项细节

### C1 协议配置自洽性

**结论：PASS**

train/validation 仅含正常样本；test 总数与异常比例自洽；LOF 最大 k=50 < train n=600；标度方式=none；阈值分位数方法=inverted_cdf

实测量：

```json
{
  "protocol_version": "B-v1.1-near",
  "bandwidth_grid": [
    0.1,
    0.2,
    0.35,
    0.5,
    0.8,
    1.2
  ],
  "n_neighbors_grid": [
    10,
    20,
    35,
    50
  ]
}
```

### C2 同一种子两次生成的 600/1000/1250 行数据逐位一致

**结论：PASS**

逐位比较 train:同、validation:同、test:同（float64 完全相等）

### C3 三个 split 的数据指纹互不相同

**结论：PASS**

sha256 前缀 train=bbe5881fa6b3acc6 | validation=ac03679b6fab71e2 | test=98c9456d4e71039f

实测量：

```json
{
  "train": "bbe5881fa6b3acc65340fea280fd28353b2cc9a3d6ff4ab19c97a8a457c5679f",
  "validation": "ac03679b6fab71e2e58688cacb380bb7bd947ecb4261359692a0e11a8f8377b2",
  "test": "98c9456d4e71039f88737c4b6e2ac91eaa1360ea03ce2b370c51dc6ef4ad63ac"
}
```

### C4 各 split 规模、逐簇计数与标签规则

**结论：PASS**

train=600 validation=1000 test=1250；test 异常比例=0.2000；无缺失值；异常标签与 cluster_id=-1 完全对应

实测量：

```json
{
  "train": {
    "split": "train",
    "repeat": 0,
    "n": 600,
    "n_dense": 300,
    "n_sparse": 300,
    "n_anomaly": 0,
    "n_anomaly_far": 0,
    "n_anomaly_near": 0,
    "n_missing": 0
  },
  "validation": {
    "split": "validation",
    "repeat": 0,
    "n": 1000,
    "n_dense": 500,
    "n_sparse": 500,
    "n_anomaly": 0,
    "n_anomaly_far": 0,
    "n_anomaly_near": 0,
    "n_missing": 0
  },
  "test": {
    "split": "test",
    "repeat": 0,
    "n": 1250,
    "n_dense": 500,
    "n_sparse": 500,
    "n_anomaly": 250,
    "n_anomaly_far": 125,
    "n_anomaly_near": 0,
    "n_missing": 0
  }
}
```

### C5 train/validation/test 之间无逐点重合

**结论：PASS**

重合点数 train∩val=0, train∩test=0, val∩test=0

### C6 KDE 公式手算特例 + 手写实现与 sklearn 交叉核验

**结论：PASS**

手算特例 p(0)=1/(n·h^d)·(2π)^(-d/2)=0.636619772368，手写相对误差=0.000e+00，sklearn 相对误差=0.000e+00；6 条带宽 × 1000 个验证点的 log 密度最大绝对偏差=1.873e-07（相对偏差 1.030e-08，判据 < 1e-05）

实测量：

```json
{
  "hand_value": 0.6366197723675814,
  "scratch_value": 0.6366197723675814,
  "sklearn_value": 0.6366197723675814,
  "max_abs_dev_all_bandwidths": 1.8734945328446884e-07,
  "max_rel_dev_all_bandwidths": 1.0304362172932244e-08,
  "tolerance": 1e-05
}
```

### C7 手写 LOF（Breunig 定义）与 sklearn novelty 模式交叉核验

**结论：PASS**

4 个 k 值 × 1000 个验证点上 LOF 数值最大绝对偏差=0.000e+00（最差 k=None）

实测量：

```json
{
  "max_abs_dev": 0.0,
  "worst_k": null
}
```

### C8 异常得分方向（越大越异常）在全部带宽与邻居数下成立

**结论：PASS**

簇心点得分上界 vs 环上 r=6 异常点得分下界（异常分数）：h=0.1:2.34->138.67✓；h=0.2:2.53->28.65✓；h=0.35:2.71->13.80✓；h=0.5:2.83->10.18✓；h=0.8:3.07->7.64✓；h=1.2:3.44->6.42✓；k=10:1.06->2.29✓；k=20:0.99->2.37✓；k=35:0.99->2.49✓；k=50:0.97->2.45✓

### C9 阈值校准：验证集超阈样本数恒为 10/1000（经验误报率 1.00%）

**结论：PASS**

每个 (检测器, 参数) 各自独立校准；kde(0.1)=15.7277/超阈10；kde(0.2)=7.8961/超阈10；kde(0.35)=6.1760/超阈10；kde(0.5)=5.7771/超阈10；kde(0.8)=5.2497/超阈10；kde(1.2)=4.8013/超阈10；lof(10)=1.8931/超阈10；lof(20)=2.0223/超阈10；lof(35)=1.9666/超阈10；lof(50)=1.9379/超阈10

实测量：

```json
{
  "kde:0.1": {
    "threshold": 15.727733455661657,
    "n_exceedance": 10,
    "rate": 0.01
  },
  "kde:0.2": {
    "threshold": 7.896117137391398,
    "n_exceedance": 10,
    "rate": 0.01
  },
  "kde:0.35": {
    "threshold": 6.1760332463781715,
    "n_exceedance": 10,
    "rate": 0.01
  },
  "kde:0.5": {
    "threshold": 5.777107769062261,
    "n_exceedance": 10,
    "rate": 0.01
  },
  "kde:0.8": {
    "threshold": 5.249741535621197,
    "n_exceedance": 10,
    "rate": 0.01
  },
  "kde:1.2": {
    "threshold": 4.801341485167014,
    "n_exceedance": 10,
    "rate": 0.01
  },
  "lof:10": {
    "threshold": 1.893114540986129,
    "n_exceedance": 10,
    "rate": 0.01
  },
  "lof:20": {
    "threshold": 2.022292831724469,
    "n_exceedance": 10,
    "rate": 0.01
  },
  "lof:35": {
    "threshold": 1.9665564127901076,
    "n_exceedance": 10,
    "rate": 0.01
  },
  "lof:50": {
    "threshold": 1.9379304014201812,
    "n_exceedance": 10,
    "rate": 0.01
  }
}
```

### C10 指标实现：微型手算样例 + 真实测试集上手算与 sklearn 交叉核验

**结论：PASS**

4 样本手算样例：AUC=0.7500(应 0.75)、AP=0.8333(应 0.8333)、P=R=F1=0.5、混淆矩阵 [[1,1],[1,1]]；真实测试集上手算与 sklearn 的最大偏差=0.000e+00，混淆矩阵一致=True

实测量：

```json
{
  "toy": {
    "auc": 0.75,
    "ap": 0.8333333333333333,
    "confusion": {
      "tp": 1,
      "fp": 1,
      "tn": 1,
      "fn": 1,
      "precision": 0.5,
      "recall": 0.5,
      "f1": 0.5,
      "fpr_overall": 0.5
    }
  },
  "real_max_dev": 0.0,
  "real_auc": 0.999644,
  "real_ap": 0.998570391539398
}
```

### C11 分簇误报率可加回总误报率

**结论：PASS**

密集簇 0/500=0.0000，稀疏簇 11/500=0.0220，加权=0.0110，总 FPR=0.0110

实测量：

```json
{
  "fpr_dense": 0.0,
  "fpr_sparse": 0.022,
  "fpr_overall": 0.011
}
```

### C12 无标签泄漏：阈值只来自 validation，与 test 无关

**结论：PASS**

核心运行阈值 KDE=6.176033246378 LOF=2.022292831724；换用另一套 test 后阈值逐位不变=True；换用另一套 validation 后阈值确实改变=True（KDE 变为 6.246103）；同输入重复打分逐位一致=True；网格字面量与配置一致=True；train/validation 标签全 0=True

实测量：

```json
{
  "thr_core": [
    6.1760332463781715,
    2.022292831724469
  ],
  "thr_other": [
    6.246103062536947,
    1.7898485012328642
  ]
}
```

### C13 一维示例：小带宽出现伪峰、大带宽把双峰抹平（prominence 口径）

**结论：PASS**

n=200；显著峰的判定口径 = prominence ≥ 全局最大密度的 10%。局部极大点数 [8, 3, 2]（单调不增=True）；显著峰数 [2, 2, 1]（h=0.9 时退化为单峰=True）；全局最大密度 [1.0705, 0.6254, 0.2629]（单调下降=True）；两主峰间谷的填充率 [0.0007, 0.1581, 0.914]（单调上升=True）；小带宽伪峰多于真峰=True

实测量：

```json
{
  "0.08": {
    "n_local_maxima": 8,
    "n_prominent_peaks": 2,
    "max_density": 1.0705264270650237,
    "valley_fill_ratio": 0.0007459547550577733,
    "prominent_peaks": [
      {
        "x": -1.46,
        "height": 1.0705264270650237,
        "prominence_ratio": 1.0
      },
      {
        "x": 1.3600000000000003,
        "height": 0.2740743152139926,
        "prominence_ratio": 0.25582728389635984
      }
    ],
    "prominences": [
      {
        "x": -1.46,
        "prominence_ratio": 1.0
      },
      {
        "x": -0.04999999999999982,
        "prominence_ratio": 0.02011642366345725
      },
      {
        "x": 0.20999999999999996,
        "prominence_ratio": 0.0039011717108214075
      },
      {
        "x": 0.4800000000000004,
        "prominence_ratio": 0.03176345677087333
      },
      {
        "x": 0.9000000000000004,
        "prominence_ratio": 0.02012973919074813
      },
      {
        "x": 1.3600000000000003,
        "prominence_ratio": 0.25582728389635984
      },
      {
        "x": 1.92,
        "prominence_ratio": 0.0637335013081781
      },
      {
        "x": 2.9400000000000004,
        "prominence_ratio": 0.06857097216474489
      }
    ],
    "peak_positions": [
      -1.46,
      1.36
    ]
  },
  "0.3": {
    "n_local_maxima": 3,
    "n_prominent_peaks": 2,
    "max_density": 0.6254107975271286,
    "valley_fill_ratio": 0.15808797510382835,
    "prominent_peaks": [
      {
        "x": -1.46,
        "height": 0.6254107975271286,
        "prominence_ratio": 0.9999999999100994
      },
      {
        "x": 1.42,
        "height": 0.2049173734592694,
        "prominence_ratio": 0.27585452874758687
      }
    ],
    "prominences": [
      {
        "x": -1.46,
        "prominence_ratio": 0.9999999999100994
      },
      {
        "x": 1.42,
        "prominence_ratio": 0.27585452874758687
      },
      {
        "x": 2.8,
        "prominence_ratio": 0.0001658292607631894
      }
    ],
    "peak_positions": [
      -1.46,
      1.42
    ]
  },
  "0.9": {
    "n_local_maxima": 2,
    "n_prominent_peaks": 1,
    "max_density": 0.26290996542046685,
    "valley_fill_ratio": 0.9140445129033304,
    "prominent_peaks": [
      {
        "x": -1.42,
        "height": 0.26290996542046685,
        "prominence_ratio": 0.9932211294288346
      }
    ],
    "prominences": [
      {
        "x": -1.42,
        "prominence_ratio": 0.9932211294288346
      },
      {
        "x": 1.3600000000000003,
        "prominence_ratio": 0.04430460091393894
      }
    ],
    "peak_positions": [
      -1.42
    ]
  }
}
```

---

## 这些检查为什么能支撑「结果正确」

- **C2 / C3 / C5** 证明数据可从种子逐位重建，且三个 split 互不重合 —— 复现性的前提。
- **C6 / C7 / C10** 用**完全独立于 sklearn 的实现**重算 KDE 密度、LOF 值与全部指标。其中手写 LOF 与 sklearn 的偏差为 0，手写 KDE 的偏差在 1e-7 量级（浮点结合顺序差异）。这意味着 C 若用 sklearn，数值可被独立复现；若 C 自己实现，可据此定位错误。
- **C8** 用人工构造的「明显正常点 / 明显远端异常点」确认得分方向在全部 6 条带宽与 4 个邻居数下都是「越大越异常」。这是任务书点名的高频错误。
- **C9** 确认阈值校准在验证集上的经验误报率精确等于 1.00%（超阈 10/1000），证明 `inverted_cdf` 分位数方法按协议生效。
- **C11** 确认分簇误报率可加权加回总误报率，说明分簇统计没有口径错误。
- **C12** 换掉整个测试集后阈值逐位不变、换掉验证集后阈值确实改变 —— 双向验证了「阈值只来自验证集」这一无泄漏要求。
- **C13** 确认一维示意的峰结构随带宽单调变化，H1 的观测前提成立。

## 检查覆盖不到的地方（必须由人工补）

1. **假设是否成立**：本套件只验证实现与统计口径正确，不判断 H1–H4 是否被支持。那需要 D 依据 `metrics_ref.csv` 与图做分析。
2. **数据生成是否合理**：验证的是「按协议生成」，不是「该协议是否是最佳设计」。设计取舍见 `01_protocol_and_data_dictionary.md` §4 与 §7。
3. **文献与理论公式**：KDE 与 LOF 的数学定义由 A 负责核验原文，本套件只核验实现与公式一致。
4. **跨机器复现**：本记录只来自一台机器、一个环境。C 必须在干净环境重跑并按 `data_fingerprints.json` 的 `stats` 做相对容差比对。
