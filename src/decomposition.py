"""Follow-up tests (v1.2), run after the main analysis. EXPLORATORY: not part of
the pre-registered criteria, so labels here are EXPLORATORY, not CONFIRMED.

1) Where does the CSW% gain come from: called strikes or swinging strikes?
2) Does the CSW% effect survive controlling for changes in pitch shape
   (induced vertical break, arm-side horizontal break, spin rate)?

Input : data/processed/pairs.csv (from build_features.py)
Output: results/decomposition.csv, results/shape_control.csv, results/summary_v2.json
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from statsmodels.stats.multitest import multipletests

from analysis import UNIT_FT, fit_delta_model, cluster_bootstrap_coef

ROOT = Path(__file__).resolve().parents[1]
PROC, RES = ROOT / "data" / "processed", ROOT / "results"


def row(m, outcome, label):
    lo, hi = m.conf_int().loc["d_ext"]
    return {"model": label, "outcome": outcome, "n_pairs": int(m.nobs),
            "effect_per_0.3ft": m.params["d_ext"] * UNIT_FT,
            "ci_lo_0.3ft": lo * UNIT_FT, "ci_hi_0.3ft": hi * UNIT_FT, "p": m.pvalues["d_ext"]}


if __name__ == "__main__":
    pairs = pd.read_csv(PROC / "pairs.csv")
    prim = pairs[~pairs["flag_absence"] & ~pairs["manual_exclude"]].dropna(
        subset=["d_ext", "d_velo", "d_csw_pct", "d_xwoba"]).copy()

    # 1) decomposition of CSW% into called + swinging strikes per pitch
    dec = [row(fit_delta_model(prim, o), o, "velocity control") for o in
           ["csw_pct", "called_pct", "swstr_pct"]]
    dec = pd.DataFrame(dec)
    sub = dec["outcome"] != "csw_pct"
    dec.loc[sub, "q_bh"] = multipletests(dec.loc[sub, "p"], method="fdr_bh")[1]
    for o in ["called_pct", "swstr_pct"]:
        lo, hi = cluster_bootstrap_coef(prim, o)
        dec.loc[dec["outcome"] == o, ["boot_lo_0.3ft", "boot_hi_0.3ft"]] = lo, hi
    dec["share_of_csw_effect"] = dec["effect_per_0.3ft"] / dec.loc[dec["outcome"] == "csw_pct", "effect_per_0.3ft"].iloc[0]
    dec.to_csv(RES / "decomposition.csv", index=False)

    # 2) pitch-shape controls
    shp = prim.dropna(subset=["d_ivb", "d_hb_arm", "d_spin"])
    rows = []
    for o in ["csw_pct", "called_pct", "swstr_pct", "whiff_pct", "xwoba"]:
        rows.append(row(fit_delta_model(shp, o), o, "velocity only"))
        rows.append(row(fit_delta_model(shp, o, " + d_ivb + d_hb_arm + d_spin"), o,
                        "velocity + shape (IVB, HB, spin)"))
    shape = pd.DataFrame(rows)
    shape.to_csv(RES / "shape_control.csv", index=False)

    # 3) location: more pitches in the zone, or more takes of zone pitches? (v1.3)
    loc_out = ["zone_pct", "z_swing_pct", "z_called_pct", "o_called_pct"]
    locdf = prim.dropna(subset=[f"d_{o}" for o in loc_out])
    loc = [row(fit_delta_model(locdf, o), o, "velocity control") for o in loc_out]
    loc = pd.DataFrame(loc)
    loc["q_bh"] = multipletests(loc["p"], method="fdr_bh")[1]
    for o in loc_out:
        lo, hi = cluster_bootstrap_coef(locdf, o)
        loc.loc[loc["outcome"] == o, ["boot_lo_0.3ft", "boot_hi_0.3ft"]] = lo, hi
    loc["baseline_mean"] = [locdf[f"{o}_y0"].mean() for o in loc_out]
    loc.to_csv(RES / "location.csv", index=False)
    print(loc.round(4).to_string())

    corr = shp[["d_ext", "d_ivb", "d_hb_arm", "d_spin", "d_velo"]].corr()["d_ext"].drop("d_ext")
    summary = {
        "n_pairs": int(len(prim)), "n_pairs_shape": int(len(shp)),
        "corr_d_ext_with": corr.to_dict(),
        "mean_called_pct": prim["called_pct_y0"].mean(),
        "mean_swstr_pct": prim["swstr_pct_y0"].mean(),
        "median_fastballs_per_season": float(prim["n_fb_y0"].median()),
    }
    (RES / "summary_v2.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    pd.set_option("display.width", 200)
    print(dec.round(4).to_string())
    print(shape.round(4).to_string())
    print(json.dumps(summary, indent=2))
