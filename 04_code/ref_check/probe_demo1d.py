"""临时探针：查看一维示例在各带宽下的峰结构，用于确定 C13 的判定口径。

不属于交付物，可随时删除。
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reference_impl as ri  # noqa: E402


def prominence(p: np.ndarray, i: int) -> float:
    """峰的 prominence：从峰顶向两侧走到第一个更高的点，取两侧最低点中较高者作为基准。"""
    n = len(p)
    v = p[i]
    left_min = v
    l = i
    while l > 0:
        l -= 1
        if p[l] > v:
            break
        left_min = min(left_min, p[l])
    right_min = v
    r = i
    while r < n - 1:
        r += 1
        if p[r] > v:
            break
        right_min = min(right_min, p[r])
    return float(v - max(left_min, right_min))


cfg = ri.load_config()
x = ri.generate_1d_demo(cfg)
g = cfg["demo_1d"]["plot_grid"]
xs = np.linspace(g["x_min"], g["x_max"], g["n_points"])
print(f"1D sample: n={len(x)}, range=[{x.min():.3f}, {x.max():.3f}], "
      f"mean={x.mean():.3f}, sd={x.std(ddof=1):.4f}")

for h in cfg["demo_1d"]["bandwidths"]:
    p = np.exp(ri.numpy_kde_log_density(x[:, None], xs[:, None], h))
    d1 = np.diff(p)
    cand = np.where((d1[:-1] > 0) & (d1[1:] <= 0))[0] + 1
    rows = [(int(i), float(xs[i]), float(p[i]), prominence(p, i) / p.max()) for i in cand]
    rows.sort(key=lambda t: -t[2])
    print(f"\n=== h={h}  global max density={p.max():.4f} ===")
    for i, xv, pv, pr in rows:
        print(f"   idx={i:4d} x={xv:+7.3f} height={pv:.5f} prominence/max={pr:.4f}")
    # 谷：两个最高的显著峰之间的最低密度
    if len(rows) >= 2:
        i1, i2 = rows[0][0], rows[1][0]
        lo, hi = min(i1, i2), max(i1, i2)
        valley = float(p[lo:hi + 1].min())
        print(f"   -> valley between top-2 modes = {valley:.5f} "
              f"({valley / min(rows[0][2], rows[1][2]) * 100:.1f}% of lower mode height)")
