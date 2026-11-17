"""Data-based monitoring thresholds (v1.3).

1) In-season noise: how far does a pitcher's 5-outing average extension wander
   from his own season average when nothing is flagged? -> alert threshold.
2) Health flag: how often do extension losses of different sizes come with a
   long absence (IL / option), compared with the base rate?

Input : data/raw/fastballs_*.csv, data/processed/pairs.csv, pitcher_seasons.csv
Output: results/thresholds.json, results/absence_by_change.csv
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW, PROC, RES = ROOT / "data/raw", ROOT / "data/processed", ROOT / "results"

seasons = pd.read_csv(PROC / "pitcher_seasons.csv")
clean = seasons[(seasons["n_fb"] >= 300) & (~seasons["absence_flag"])][["pitcher", "year"]]

devs = []
for f in sorted(RAW.glob("fastballs_*.csv")):
    d = pd.read_csv(f, low_memory=False, usecols=["pitcher", "game_date", "game_pk", "release_extension"])
    d["year"] = pd.to_datetime(d["game_date"]).dt.year
    d = d.merge(clean, on=["pitcher", "year"])
    g = d.groupby(["pitcher", "year", "game_date"])["release_extension"].mean().reset_index().sort_values("game_date")
    for (p, y), s in g.groupby(["pitcher", "year"]):
        if len(s) < 15:
            continue
        roll = s["release_extension"].rolling(5).mean().dropna()
        devs.append(roll - s["release_extension"].mean())
devs = pd.concat(devs)

pairs = pd.read_csv(PROC / "pairs.csv")
bins = pd.cut(pairs["d_ext"], [-9, -0.3, -0.2, -0.1, 0.1, 9],
              labels=["lost >= 0.3", "lost 0.2-0.3", "lost 0.1-0.2", "stable (+/-0.1)", "gained > 0.1"])
ab = pairs.groupby(bins, observed=True)["flag_absence"].agg(["mean", "size"]).reset_index()
ab.columns = ["change", "absence_rate", "n_pairs"]
ab["absence_rate"] *= 100
ab.to_csv(RES / "absence_by_change.csv", index=False)

out = {
    "n_rolling_windows": int(len(devs)),
    "sd_5outing_dev_ft": float(devs.std()),
    "p95_abs_5outing_dev_ft": float(devs.abs().quantile(0.95)),
    "p99_abs_5outing_dev_ft": float(devs.abs().quantile(0.99)),
    "pct_below_minus_0.10": float((devs <= -0.10).mean() * 100),
    "pct_below_minus_0.20": float((devs <= -0.20).mean() * 100),
    "absence_base_rate_pct": float(pairs["flag_absence"].mean() * 100),
}
(RES / "thresholds.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
print(json.dumps(out, indent=2)); print(ab.round(1).to_string())
