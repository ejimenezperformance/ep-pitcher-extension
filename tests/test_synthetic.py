"""Known-answer tests: the model must recover a planted extension effect
in both directions, and find nothing when there is nothing.

Run: python tests/test_synthetic.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from analysis import fit_delta_model, UNIT_FT  # noqa: E402


def synth(true_coef_per_ft: float, n_pitchers=400, seed=1) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for p in range(n_pitchers):
        for y in range(2021, 2021 + rng.integers(1, 5)):
            d_velo = rng.normal(0, 1.0)
            d_ext = 0.15 * d_velo + rng.normal(0, 0.25)       # extension partly tied to velo
            base = rng.normal(22, 5)
            d_whiff = (1.2 * d_velo + true_coef_per_ft * d_ext
                       - 0.3 * (base - 22) + rng.normal(0, 3))
            rows.append({"pitcher": p, "pair": f"{y}->{y+1}", "d_velo": d_velo,
                         "d_ext": d_ext, "whiff_pct_y0": base, "d_whiff_pct": d_whiff})
    return pd.DataFrame(rows)


def check(true_coef):
    m = fit_delta_model(synth(true_coef), "whiff_pct")
    b, (lo, hi) = m.params["d_ext"], m.conf_int().loc["d_ext"]
    ok = lo <= true_coef <= hi
    print(f"planted {true_coef:+.1f} pts/ft -> estimated {b:+.2f} [{lo:+.2f}, {hi:+.2f}] "
          f"(+0.3 ft = {b*UNIT_FT:+.2f}) p={m.pvalues['d_ext']:.3g} {'PASS' if ok else 'FAIL'}")
    return ok, m.pvalues["d_ext"]


if __name__ == "__main__":
    up, p_up = check(+4.0)
    down, p_down = check(-4.0)
    null, p_null = check(0.0)
    results = {"positive effect recovered": up and p_up < 0.05,
               "negative effect recovered": down and p_down < 0.05,
               "null not falsely detected": null and p_null >= 0.05}
    for k, v in results.items():
        print(f"{'PASS' if v else 'FAIL'}  {k}")
    sys.exit(0 if all(results.values()) else 1)
