# 正确性核验记录（C 实现与复现负责人）

> 由 `04_code/run_checks.py` 自动生成，请勿手工编辑。
> 作用：证明这份实现按协议定义工作，并与 B 的基准逐位/逐项一致。

| 项 | 值 |
|---|---|
| 协议版本 | `B-v1.1-near` |
| 检查项数 | 17 |
| 失败项数 | **0** |
| Python | 3.13.5 |
| numpy / scipy / scikit-learn | 2.5.5 / 1.18.1 / 1.9.1 |
| matplotlib / pandas | 3.11.2 / 3.1.1 |

## 总览

| 编号 | 检查项 | 结论 |
|---|---|---|
| C1 | 协议配置自洽性（网格/默认参数/阈值方法/标度/异常数量） | ✅ PASS |
| C2 | 同一种子两次生成的数据逐位一致，且三划分指纹互不相同 | ✅ PASS |
| C3 | 数据指纹：train/validation 与 v1.0 基准逐位一致；test 指纹按构成变更登记新基线 | ✅ PASS |
| C4 | 各划分规模、逐簇计数、标签规则与异常比例 | ✅ PASS |
| C5 | train/validation/test 两两无逐点重合 | ✅ PASS |
| C6 | KDE：解析特例手算 + 手写实现 vs sklearn（6 条带宽 × 1000 个验证点） | ✅ PASS |
| C7 | LOF：Breunig 原始定义手写实现 vs sklearn novelty 模式 | ✅ PASS |
| C8 | 得分方向「越大越异常」在全部 6 个带宽与 4 个邻居数下成立（人工构造点实测） | ✅ PASS |
| C9 | 阈值校准：10 个配置的验证集超阈数恒为 10/1000；分位数方法对照 | ✅ PASS |
| C10 | 指标实现：玩具手算样例 + 真实测试集上手算 vs sklearn | ✅ PASS |
| C11 | 分簇误报率可加回总误报率（H2 的证据口径没算错） | ✅ PASS |
| C12 | 无泄漏：阈值只来自 validation（换 test 不变、换 validation 必变） | ✅ PASS |
| C13 | E0 一维带宽示意：峰数随带宽单调减少、大带宽退化为单峰、谷被填平（prominence 口径） | ✅ PASS |
| C14 | 缩比配置端到端冒烟：near/far/n_draw 同比例缩放且合计 = n_anomaly | ✅ PASS |
| C15 | 结果表结构契约（列齐全、覆盖预注册网格、无重复行、D 可直接消费） | ✅ PASS |
| C17 | 不变性契约：阈值/val 似然/分簇误报计数与率/正常样本计数/train·validation 指纹逐位不变 | ✅ PASS |
| C18 | 点级嵌套：v1.1 的 125 个 far 点 == v1.0 前 125 个，且两者分数逐位相同 | ✅ PASS |

## 逐项细节

### C1 协议配置自洽性（网格/默认参数/阈值方法/标度/异常数量）

**PASS**

protocol_version=B-v1.1-near；KDE 网格=[0.1, 0.2, 0.35, 0.5, 0.8, 1.2]；LOF 网格=[10, 20, 35, 50]；默认 h*=0.35, k*=20；阈值方法=inverted_cdf @ q=0.99；标度=none。以上全部由 protocol.load_config 的断言强制

实测量：

```json
{
  "protocol_version": "B-v1.1-near"
}
```

### C2 同一种子两次生成的数据逐位一致，且三划分指纹互不相同

**PASS**

逐位一致=train:True、validation:True、test:True；sha256 前缀=train=bbe5881fa6b3acc6 | validation=ac03679b6fab71e2 | test=98c9456d4e71039f

实测量：

```json
{
  "train": "bbe5881fa6b3acc65340fea280fd2835",
  "validation": "ac03679b6fab71e2e58688cacb380bb7",
  "test": "98c9456d4e71039f88737c4b6e2ac91e"
}
```

### C3 数据指纹：train/validation 与 v1.0 基准逐位一致；test 指纹按构成变更登记新基线

**PASS**

train: sha256一致，统计量最大相对偏差=0.000e+00；validation: sha256一致，统计量最大相对偏差=0.000e+00；test: 由「250 far」变为「125 far + 125 near」，指纹必然变（与 v1.0 sha256 不同→符合预期）；新基线 98c9456d4e71039f88737c4b6e2ac91e

实测量：

```json
{
  "worst_rel_dev": 0.0,
  "test_sha256_v1_1": "98c9456d4e71039f88737c4b6e2ac91eaa1360ea03ce2b370c51dc6ef4ad63ac",
  "test_sha256_v1_0": "e00edf67e4bb128d430cf14d430f274fce01125503ce7af07dcbf1ebc154f7df"
}
```

### C4 各划分规模、逐簇计数、标签规则与异常比例

**PASS**

train=600 validation=1000 test=1250；test 异常比例=0.200000；无缺失；Cluster_id=-1 ⇔ y=1

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
    "n_anomaly_compact_void": 0,
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
    "n_anomaly_compact_void": 0,
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
    "n_anomaly_compact_void": 125,
    "n_missing": 0
  }
}
```

### C5 train/validation/test 两两无逐点重合

**PASS**

重合点数 train∩val=0，train∩test=0，val∩test=0

### C6 KDE：解析特例手算 + 手写实现 vs sklearn（6 条带宽 × 1000 个验证点）

**PASS**

手算 p(0)=1/(n·h^d)·(2π)^(-d/2)=0.636619772368；手写相对误差=0.00e+00，sklearn 相对误差=0.00e+00；log 密度最大绝对偏差=1.873e-07（判据 < 1e-5；残差来自 BLAS 与广播求和的结合顺序差异）

实测量：

```json
{
  "analytic": 0.6366197723675814,
  "scratch": 0.6366197723675814,
  "sklearn": 0.6366197723675814,
  "max_abs_dev": 1.8734945328446884e-07
}
```

### C7 LOF：Breunig 原始定义手写实现 vs sklearn novelty 模式

**PASS**

4 个 k × 1000 个验证点上 LOF 数值最大绝对偏差=0.000e+00（最差 k=None），判据 < 1e-9

实测量：

```json
{
  "max_abs_dev": 0.0,
  "worst_k": null
}
```

### C8 得分方向「越大越异常」在全部 6 个带宽与 4 个邻居数下成立（人工构造点实测）

**PASS**

簇心正常点得分上界 -> 环上 r=6 异常点得分下界：kde(0.1):2.34->138.67；kde(0.2):2.53->28.65；kde(0.35):2.71->13.80；kde(0.5):2.83->10.18；kde(0.8):3.07->7.64；kde(1.2):3.44->6.42；lof(10):1.06->2.29；lof(20):0.99->2.37；lof(35):0.99->2.49；lof(50):0.97->2.45

实测量：

```json
{
  "rows": [
    {
      "detector": "kde",
      "param": 0.1,
      "normal_score_max": 2.3421796462926254,
      "anomaly_score_min": 138.6652637981133,
      "ok": true
    },
    {
      "detector": "kde",
      "param": 0.2,
      "normal_score_max": 2.5320645684358074,
      "anomaly_score_min": 28.64692172919063,
      "ok": true
    },
    {
      "detector": "kde",
      "param": 0.35,
      "normal_score_max": 2.7054363729989976,
      "anomaly_score_min": 13.797313555276087,
      "ok": true
    },
    {
      "detector": "kde",
      "param": 0.5,
      "normal_score_max": 2.8276515250750283,
      "anomaly_score_min": 10.184524305963972,
      "ok": true
    },
    {
      "detector": "kde",
      "param": 0.8,
      "normal_score_max": 3.0722720648741015,
      "anomaly_score_min": 7.643570549438999,
      "ok": true
    },
    {
      "detector": "kde",
      "param": 1.2,
      "normal_score_max": 3.437076085174773,
      "anomaly_score_min": 6.418684858892698,
      "ok": true
    },
    {
      "detector": "lof",
      "param": 10.0,
      "normal_score_max": 1.0604260681290958,
      "anomaly_score_min": 2.2904499505200016,
      "ok": true
    },
    {
      "detector": "lof",
      "param": 20.0,
      "normal_score_max": 0.9888321994244279,
      "anomaly_score_min": 2.374535559412664,
      "ok": true
    },
    {
      "detector": "lof",
      "param": 35.0,
      "normal_score_max": 0.9942611721368987,
      "anomaly_score_min": 2.493217467502658,
      "ok": true
    },
    {
      "detector": "lof",
      "param": 50.0,
      "normal_score_max": 0.9668575857457185,
      "anomaly_score_min": 2.449117736793424,
      "ok": true
    }
  ]
}
```

### C9 阈值校准：10 个配置的验证集超阈数恒为 10/1000；分位数方法对照

**PASS**

kde(0.1)=15.7277/超阈10；kde(0.2)=7.8961/超阈10；kde(0.35)=6.1760/超阈10；kde(0.5)=5.7771/超阈10；kde(0.8)=5.2497/超阈10；kde(1.2)=4.8013/超阈10；lof(10)=1.8931/超阈10；lof(20)=2.0223/超阈10；lof(35)=1.9666/超阈10；lof(50)=1.9379/超阈10。方法对照（KDE h=0.35）：inverted_cdf=10，linear=10，higher=9，lower=10，nearest=10，midpoint=10（仅 inverted_cdf 恰为 10，故协议锁定该方法是必要的）

实测量：

```json
{
  "kde:0.1": {
    "threshold": 15.727733455661657,
    "n_exceedance": 10,
    "n_ties_at_threshold": 1
  },
  "kde:0.2": {
    "threshold": 7.896117137391398,
    "n_exceedance": 10,
    "n_ties_at_threshold": 1
  },
  "kde:0.35": {
    "threshold": 6.1760332463781715,
    "n_exceedance": 10,
    "n_ties_at_threshold": 1
  },
  "kde:0.5": {
    "threshold": 5.777107769062261,
    "n_exceedance": 10,
    "n_ties_at_threshold": 1
  },
  "kde:0.8": {
    "threshold": 5.249741535621197,
    "n_exceedance": 10,
    "n_ties_at_threshold": 1
  },
  "kde:1.2": {
    "threshold": 4.801341485167014,
    "n_exceedance": 10,
    "n_ties_at_threshold": 1
  },
  "lof:10": {
    "threshold": 1.893114540986129,
    "n_exceedance": 10,
    "n_ties_at_threshold": 1
  },
  "lof:20": {
    "threshold": 2.022292831724469,
    "n_exceedance": 10,
    "n_ties_at_threshold": 1
  },
  "lof:35": {
    "threshold": 1.9665564127901076,
    "n_exceedance": 10,
    "n_ties_at_threshold": 1
  },
  "lof:50": {
    "threshold": 1.9379304014201812,
    "n_exceedance": 10,
    "n_ties_at_threshold": 1
  },
  "quantile_method_contrast": {
    "inverted_cdf": {
      "threshold": 6.1760332463781715,
      "n_exceedance": 10
    },
    "linear": {
      "threshold": 6.176045196171592,
      "n_exceedance": 10
    },
    "higher": {
      "threshold": 6.177228225720228,
      "n_exceedance": 9
    },
    "lower": {
      "threshold": 6.1760332463781715,
      "n_exceedance": 10
    },
    "nearest": {
      "threshold": 6.1760332463781715,
      "n_exceedance": 10
    },
    "midpoint": {
      "threshold": 6.1766307360492,
      "n_exceedance": 10
    }
  }
}
```

### C10 指标实现：玩具手算样例 + 真实测试集上手算 vs sklearn

**PASS**

玩具样例 AUC=0.7500(应 0.75) AP=0.8333(应 0.8333) 混淆矩阵[[1,1],[1,1]]；真实测试集最大偏差=0.00e+00，混淆矩阵与 sklearn 一致=True

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
  "real_max_dev": 0.0
}
```

### C11 分簇误报率可加回总误报率（H2 的证据口径没算错）

**PASS**

密集簇 0/500=0.0000，稀疏簇 11/500=0.0220，加权=0.011000，总 FPR=0.011000

### C12 无泄漏：阈值只来自 validation（换 test 不变、换 validation 必变）

**PASS**

核心阈值 KDE=6.176033246378 LOF=2.022292831724；换 test 后不变=True；换 validation 后 KDE 变为 6.312323（确实改变=True）；网格字面量未被数据影响=True；同输入重复打分逐位一致=True

实测量：

```json
{
  "thr_core": [
    6.1760332463781715,
    2.022292831724469
  ],
  "thr_other": [
    6.312322588487087,
    2.0003250183150376
  ]
}
```

### C13 E0 一维带宽示意：峰数随带宽单调减少、大带宽退化为单峰、谷被填平（prominence 口径）

**PASS**

n=200；local 极大点数=[8, 3, 2]；显著峰数=[2, 2, 1]；最大密度=[1.0705, 0.6254, 0.2629]；谷填充率=[0.0007, 0.1581, 0.914]

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
    ]
  }
}
```

### C14 缩比配置端到端冒烟：near/far/n_draw 同比例缩放且合计 = n_anomaly

**PASS**

缩小 20 倍后 train=30 validation=50 test=62；far.n_test=6 + near.n_test=6 = 12（应为 12），far.n_draw=12；KDE AUC=1.0000 阈值=12.7010；LOF AUC=0.9950 阈值=1.3067（冒烟不校验超阈数=10，因为 n 已变）

实测量：

```json
{
  "far_n_test": 6,
  "near_n_test": 6,
  "far_n_draw": 12,
  "test_n_anomaly": 12,
  "kde": {
    "roc_auc": 1.0,
    "threshold": 12.700999269609463,
    "average_precision": 1.0
  },
  "lof": {
    "roc_auc": 0.995,
    "threshold": 1.3066911852149048,
    "average_precision": 0.9790695415695415
  }
}
```

### C15 结果表结构契约（列齐全、覆盖预注册网格、无重复行、D 可直接消费）

**PASS**

缺列=无；网格覆盖=True；重复行=0；核心行数=10（应为 10）

实测量：

```json
{
  "columns": 34,
  "rows": 12
}
```

### C17 不变性契约：阈值/val 似然/分簇误报计数与率/正常样本计数/train·validation 指纹逐位不变

**PASS**

12 行主结果逐列比对，最大 |Δ| = 0.000e+00（判据：恒等于 0）；threshold=0；val_mean_log_likelihood=0；fp_dense=0；fp_sparse=0；fpr_dense=0；fpr_sparse=0；n_normal_dense=0；n_normal_sparse=0；train/validation 指纹一致

实测量：

```json
{
  "threshold": {
    "max_abs_diff": 0.0,
    "n_unequal": 0,
    "n_nan_mismatch": 0
  },
  "val_mean_log_likelihood": {
    "max_abs_diff": 0.0,
    "n_unequal": 0,
    "n_nan_mismatch": 0
  },
  "fp_dense": {
    "max_abs_diff": 0.0,
    "n_unequal": 0,
    "n_nan_mismatch": 0
  },
  "fp_sparse": {
    "max_abs_diff": 0.0,
    "n_unequal": 0,
    "n_nan_mismatch": 0
  },
  "fpr_dense": {
    "max_abs_diff": 0.0,
    "n_unequal": 0,
    "n_nan_mismatch": 0
  },
  "fpr_sparse": {
    "max_abs_diff": 0.0,
    "n_unequal": 0,
    "n_nan_mismatch": 0
  },
  "n_normal_dense": {
    "max_abs_diff": 0.0,
    "n_unequal": 0,
    "n_nan_mismatch": 0
  },
  "n_normal_sparse": {
    "max_abs_diff": 0.0,
    "n_unequal": 0,
    "n_nan_mismatch": 0
  },
  "train.sha256": {
    "max_abs_diff": 0.0,
    "n_unequal": 0
  },
  "validation.sha256": {
    "max_abs_diff": 0.0,
    "n_unequal": 0
  }
}
```

### C18 点级嵌套：v1.1 的 125 个 far 点 == v1.0 前 125 个，且两者分数逐位相同

**PASS**

点坐标：不等行数=0/125，max|Δ|=0.000e+00；分数：10 个配置（6 带宽 + 4 邻居数）最大 |Δ|=0.000e+00，不等元素总数=0

实测量：

```json
{
  "points": {
    "n_unequal_rows": 0,
    "max_abs_diff": 0.0
  },
  "scores": {
    "kde_h=0.1": {
      "max_abs_diff": 0.0,
      "n_unequal": 0
    },
    "kde_h=0.2": {
      "max_abs_diff": 0.0,
      "n_unequal": 0
    },
    "kde_h=0.35": {
      "max_abs_diff": 0.0,
      "n_unequal": 0
    },
    "kde_h=0.5": {
      "max_abs_diff": 0.0,
      "n_unequal": 0
    },
    "kde_h=0.8": {
      "max_abs_diff": 0.0,
      "n_unequal": 0
    },
    "kde_h=1.2": {
      "max_abs_diff": 0.0,
      "n_unequal": 0
    },
    "lof_k=10": {
      "max_abs_diff": 0.0,
      "n_unequal": 0
    },
    "lof_k=20": {
      "max_abs_diff": 0.0,
      "n_unequal": 0
    },
    "lof_k=35": {
      "max_abs_diff": 0.0,
      "n_unequal": 0
    },
    "lof_k=50": {
      "max_abs_diff": 0.0,
      "n_unequal": 0
    }
  }
}
```
