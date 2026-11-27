"""Verify that the current interpreter is usable for this project.

Two things are checked:

1. Versions and imports of the scientific stack.
2. A numeric smoke test that proves the environment reproduces the project's
   reference numbers: hand-computed KDE density, score direction, the locked
   quantile method, and the exact data fingerprint of the training split.

Exit code 0 = environment is good. Non-zero = do not trust any result produced
in this environment.

Console output is ASCII on purpose so it renders under any Windows code page.

Usage:

    .venv\\Scripts\\python.exe env\\verify_env.py
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

ENV_DIR = Path(__file__).resolve().parent
ROOT = ENV_DIR.parent
REF_CHECK = ROOT / "04_code" / "ref_check"
CONFIG = ROOT / "04_code" / "config_ref.json"

#: Everything below is the reference machine's fingerprint (see
#: 05_results/ref_check/data_fingerprints.json). If these do not match, the data
#: pipeline is not reproducing and every downstream number is void.
EXPECTED_TRAIN_SHA256 = "bbe5881fa6b3acc65340fea280fd28353b2cc9a3d6ff4ab19c97a8a457c5679f"
EXPECTED_TRAIN_N = 600
EXPECTED_TRAIN_MEAN = (0.06545484003177426, -0.03978977722112398)
STATS_RTOL = 1e-12

FAILS: list[str] = []
WARNS: list[str] = []


def ok(msg: str) -> None:
    print(f"[ OK ] {msg}")


def warn(msg: str) -> None:
    WARNS.append(msg)
    print(f"[WARN] {msg}")


def bad(msg: str) -> None:
    FAILS.append(msg)
    print(f"[FAIL] {msg}")


# --------------------------------------------------------------------------------
# 1. Interpreter
# --------------------------------------------------------------------------------
print("=" * 74)
print("Environment check for the KDE / LOF course project")
print("=" * 74)
print(f"python      : {sys.version.split()[0]}")
print(f"executable  : {sys.executable}")
print(f"platform    : {sys.platform}")
print()

if sys.version_info < (3, 10):
    bad(f"Python {sys.version.split()[0]} is too old; need >= 3.10")
else:
    ok(f"Python {sys.version.split()[0]} (>= 3.10)")

if sys.version_info[:2] != (3, 14):
    warn(
        f"Reference environment used Python 3.14; you have "
        f"{sys.version.split()[0]}. Results should still match within tolerance, "
        f"but record the difference in run_log.txt."
    )

print()

# --------------------------------------------------------------------------------
# 2. Packages
# --------------------------------------------------------------------------------
print("-" * 74)
print("Packages")
print("-" * 74)

REQUIRED = [
    # (module, min_version, why)
    ("numpy", (1, 22), "numpy.quantile(..., method=...) needs >= 1.22"),
    ("scipy", (1, 7), "logsumexp / cdist"),
    ("sklearn", (1, 0), "KernelDensity, LocalOutlierFactor(novelty=True)"),
    ("matplotlib", (3, 5), "figures"),
    ("pandas", (1, 3), "CSV output"),
]

try:
    import importlib.metadata as md
    import importlib.util as iu

    def _ver(mod: str) -> str:
        try:
            return md.version({"sklearn": "scikit-learn"}.get(mod, mod))
        except Exception:
            return "?"

    def _parse(v: str) -> tuple[int, ...]:
        out = []
        for part in v.split(".")[:3]:
            num = ""
            for ch in part:
                if ch.isdigit():
                    num += ch
                else:
                    break
            out.append(int(num) if num else 0)
        return tuple(out)

    for mod, minv, why in REQUIRED:
        if iu.find_spec(mod) is None:
            bad(f"{mod} is NOT installed ({why})")
            continue
        v = _ver(mod)
        if _parse(v) >= minv:
            ok(f"{mod} {v}")
        else:
            bad(f"{mod} {v} is below the required {'.'.join(map(str, minv))} ({why})")
except Exception as exc:  # pragma: no cover
    bad(f"package inspection crashed: {exc!r}")

print()

if FAILS:
    print("-" * 74)
    print("Stopping early: fix the problems above, then run this script again.")
    print(f"FAILED: {len(FAILS)} problem(s)")
    raise SystemExit(1)

# --------------------------------------------------------------------------------
# 3. Numeric smoke test
# --------------------------------------------------------------------------------
print("-" * 74)
print("Numeric smoke test")
print("-" * 74)

import numpy as np  # noqa: E402

# 3a. numpy.quantile(method=...) actually works and gives the locked semantics.
try:
    probe = np.arange(1000, dtype=float)
    q = np.quantile(probe, 0.99, method="inverted_cdf")
    if abs(q - 989.0) < 1e-12:
        ok("numpy.quantile(..., 0.99, method='inverted_cdf') picks the 990th order statistic")
    else:
        bad(f"quantile inverted_cdf returned {q}, expected 989.0")
except TypeError:
    bad("numpy.quantile does not accept method= (numpy too old)")
except Exception as exc:
    bad(f"quantile probe crashed: {exc!r}")

# 3b. Hand-computed KDE density. One point at the origin, d=2, h=0.5:
#     p(0) = 1/(n h^d) * (2*pi)^(-d/2) = 1/(1*0.25) * 1/(2*pi)
HAND_P = 1.0 / (1 * 0.5 ** 2) * (2 * np.pi) ** (-1.0)
try:
    from sklearn.neighbors import KernelDensity

    pts = np.zeros((1, 2))
    kde = KernelDensity(kernel="gaussian", bandwidth=0.5).fit(pts)
    got = float(np.exp(kde.score_samples(pts)[0]))
    rel = abs(got - HAND_P) / HAND_P
    if rel < 1e-12:
        ok(f"KDE hand check: p(0) = {HAND_P:.12f}, relative error {rel:.1e}")
    else:
        bad(f"KDE hand check failed: got {got!r}, expected {HAND_P!r}")
except Exception as exc:
    bad(f"KDE hand check crashed: {exc!r}")

# 3c. Score direction, using the real protocol config.
if not CONFIG.exists():
    bad(f"protocol config not found: {CONFIG}")
else:
    try:
        sys.path.insert(0, str(REF_CHECK))
        import reference_impl as ri  # noqa: E402

        cfg = ri.load_config(CONFIG)
        data = ri.generate_all(cfg)
        train_X = data["train"].X

        obvious_normal = np.array([[-2.0, 0.0], [2.0, 0.0]])
        obvious_far = np.array([[6.0, 0.0], [0.0, 6.0], [-6.0, 0.0]])

        direction_ok = True
        for h in cfg["detectors"]["kde"]["bandwidth_grid"]:
            s_n = -ri.kde_score_samples(train_X, obvious_normal, h)
            s_f = -ri.kde_score_samples(train_X, obvious_far, h)
            direction_ok &= bool(s_f.min() > s_n.max())
        for k in cfg["detectors"]["lof"]["n_neighbors_grid"]:
            s_n = -ri.lof_score_samples(train_X, obvious_normal, k)
            s_f = -ri.lof_score_samples(train_X, obvious_far, k)
            direction_ok &= bool(s_f.min() > s_n.max())
        if direction_ok:
            ok("score direction: far anomalies score higher than cluster centres "
               "for all 6 bandwidths and 4 neighbour counts")
        else:
            bad("score direction is WRONG in this environment")

        # 3d. Data fingerprint -- the single most important check.
        X = np.ascontiguousarray(data["train"].X, dtype=np.float64)
        sha = hashlib.sha256(X.tobytes()).hexdigest()
        if X.shape[0] != EXPECTED_TRAIN_N:
            bad(f"train row count {X.shape[0]} != {EXPECTED_TRAIN_N}")
        elif sha == EXPECTED_TRAIN_SHA256:
            ok("train data fingerprint: EXACT match (sha256 of float64 bytes)")
        else:
            mean = X.mean(axis=0)
            dev = max(abs(mean[0] - EXPECTED_TRAIN_MEAN[0]),
                      abs(mean[1] - EXPECTED_TRAIN_MEAN[1]))
            if dev <= STATS_RTOL * max(1.0, abs(EXPECTED_TRAIN_MEAN[0]),
                                       abs(EXPECTED_TRAIN_MEAN[1])):
                warn(f"train fingerprint differs byte-wise but matches within "
                     f"{STATS_RTOL:g} (max mean deviation {dev:.2e}). "
                     f"A different numpy version is likely the cause; results are "
                     f"still comparable but record it in run_log.txt.")
            else:
                bad(f"train data does NOT match. sha256 {sha[:16]}... expected "
                    f"{EXPECTED_TRAIN_SHA256[:16]}..., mean deviation {dev:.2e}")
    except Exception as exc:
        bad(f"data / direction check crashed: {exc!r}")

# 3e. Threshold calibration semantics on the real validation split.
if CONFIG.exists() and not FAILS:
    try:
        val_thr = ri.calibrate_threshold(
            -ri.kde_score_samples(train_X, data["validation"].X, 0.35), cfg)
        n_exc = int(np.sum(-ri.kde_score_samples(train_X, data["validation"].X, 0.35) > val_thr))
        if n_exc == 10:
            ok(f"threshold calibration: 10/1000 exceedances at h=0.35 (threshold {val_thr:.6f})")
        else:
            bad(f"threshold calibration gave {n_exc}/1000 exceedances, expected 10")
    except Exception as exc:
        bad(f"threshold check crashed: {exc!r}")

# --------------------------------------------------------------------------------
# Summary
# --------------------------------------------------------------------------------
print()
print("=" * 74)
if FAILS:
    print(f"RESULT: FAIL -- {len(FAILS)} problem(s)")
    for f in FAILS:
        print(f"  - {f}")
    print("Do not trust results produced in this environment.")
    raise SystemExit(1)

if WARNS:
    print(f"RESULT: PASS with {len(WARNS)} warning(s) -- record them in run_log.txt")
    for w in WARNS:
        print(f"  - {w}")
else:
    print("RESULT: PASS -- environment reproduces the reference numbers exactly")
print("=" * 74)
raise SystemExit(0)
