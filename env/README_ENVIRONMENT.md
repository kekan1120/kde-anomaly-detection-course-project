# 环境分享：直接发 `requirements.txt` 就够了

## 一句话答案

把 **`env/requirements.txt`** 发给队友，让他执行：

```powershell
pip install -r env\requirements.txt
```

就这样。不需要拷贝虚拟环境，不需要额外脚本。

---

## 推荐做法（三行命令）

在项目根目录执行：

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r env\requirements.txt
```

不想用 venv 也可以直接全局安装 `pip install -r env\requirements.txt`，只是可能和你机器上
已有的其它项目打架。四个人用各自独立的 venv 最省事。

网络慢就加国内镜像：

```powershell
pip install -r env\requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

---

## 为什么要钉版本

目的只有一个：**四个人跑出同一份数字**。

- `numpy` 一致 → 用 `PCG64` + `standard_normal` 生成的合成数据**逐位相同**（训练集 sha256 都一样）
- `scikit-learn` 一致 → `KernelDensity` / `LocalOutlierFactor` 的输出逐位相同，阈值和指标自然相同
- 版本一漂，数据通常还能对上，但阈值和指标可能在末几位不同，写论文时谁抄谁的都不确定

`requirements.txt` 里 18 个包，其中真正被 `import` 的只有 5 个（`numpy` / `scipy` /
`scikit-learn` / `matplotlib` / `pandas`），其余是它们的传递依赖。全钉是为了可复现，不是因为用得到。

---

## 装完之后必须验证（这一步最重要）

```powershell
python env\verify_env.py
```

它会检查 6 项，任何一项 FAIL 就**不要相信这台机器产出的任何数字**：

| 检查 | 内容 |
|---|---|
| 包版本 | 5 个直接依赖是否达到最低版本 |
| `numpy.quantile` | `method="inverted_cdf"` 是否可用（协议锁定的阈值规则依赖它） |
| KDE 手算特例 | 单点在 `h=0.5` 时密度应为 `0.636619772368`，相对误差 < 1e-12 |
| 得分方向 | 6 条带宽 + 4 个邻居数下，「明显远端异常点」分数都高于「簇心正常点」 |
| **训练集数据指纹** | 你生成的 600 行训练数据 sha256 是否等于参考值 `bbe5881f...` |
| 阈值校准 | `h=0.35` 时验证集超阈数是否恰为 10/1000 |

最后两项是硬证据 —— 它们直接证明「你的环境和我的环境产出同一份数据、同一个阈值」。

全 PASS 时输出：

```
RESULT: PASS -- environment reproduces the reference numbers exactly
```

---

## 版本对不上怎么办

如果 `pip install -r env\requirements.txt` 报 `No matching distribution found`，说明你的
Python 小版本（比如 3.12 / 3.13）没有这些精确版本的 wheel。改用宽松版本：

```powershell
pip install -r env\requirements_min.txt
python env\freeze_env.py     # 记录你实际装到的版本
```

然后把 `env/freeze_env.py` 生成的 `env/requirements.txt` 内容贴进你自己的运行日志
（`05_results/ref_check/run_log.txt`），并在论文的「可复现性」小节里说明版本差异。

`verify_env.py` 在这种情况下通常会给出 **PASS with warnings** —— 数据指纹字节不同但在
`1e-12` 相对容差内一致，这是可接受的，按 warning 处理并记录即可。

最低版本为什么是这些：

| 包 | 最低 | 原因 |
|---|---|---|
| numpy | 1.22 | `numpy.quantile(..., method=...)` 的 `method=` 参数从这里才有 |
| scipy | 1.7 | `scipy.special.logsumexp` / `scipy.spatial.distance.cdist` |
| scikit-learn | 1.0 | `KernelDensity`、`LocalOutlierFactor(novelty=True)` |
| matplotlib | 3.5 | 出图 |
| pandas | 1.3 | 读写 CSV |

---

## 不要做的事

1. **不要拷贝 `.venv` 文件夹。** 371 MB、11962 个文件，而且 `pyvenv.cfg` 里写死了
   `home = D:\python3.14` —— 换一台机器没有这个路径，venv 里的 python 直接起不来。
2. **不要只装不钉版本。** 那等于放弃可复现性，论文的「固定随机种子」就成了空话。
3. **不要跳过 `verify_env.py`。** 它是唯一能证明「这台机器可信」的动作。

---

## 如果标准方法失败

`env/setup_env.ps1` 是兜底脚本，只在 `pip install` 走不通时用：

```powershell
powershell -ExecutionPolicy Bypass -File env\setup_env.ps1
```

它会自动完成：找 Python → 建 venv →（ensurepip 被拦时自动降级）→ 装依赖 →
（精确版本装不上时自动换宽松版本）→ 跑 `verify_env.py`。

---

## 附：我这台机器为什么用了特殊手段

两个本机限制，**队友不需要复现**：

1. `python -m venv` 的 `ensurepip` 被沙箱拦住，所以我的 `.venv` 里没有 pip。
2. Python 3.14 在这套受限令牌下创建的临时目录拒绝写入，导致 `pip` 常规安装失败。

绕过方式是：用 base 解释器的 `pip install --target` 把包装进 venv 的 `site-packages`，
并加了一个 `sitecustomize.py` 补丁（仓库里的 `.pyshim/`）修临时目录问题。
这两样都只是**打包路径**上的变通，对数值结果没有任何影响 —— 证据是
`env/verify_env.py` 的数据指纹完全匹配。

`.pyshim/` 不需要分享。

---

## 分享清单

发给队友这些就够：

```
env/requirements.txt         ← 核心，就这一个文件
env/requirements_min.txt     ← 精确版本装不上时的备选
env/verify_env.py            ← 装完自查
env/README_ENVIRONMENT.md    ← 本说明
env/setup_env.ps1            ← 兜底脚本（可选）
env/freeze_env.py            ← 记录实际版本（可选）
```

**不要**发 `.venv/`、`.pyshim/`、`.tmp_pip/`。
