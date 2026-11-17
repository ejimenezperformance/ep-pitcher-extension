"""Pitcher-season fastball profiles and year-over-year pairs.

Input : data/raw/fastballs_<year>.csv (from pull_data.py)
Output: data/processed/pitcher_seasons.csv, data/processed/pairs.csv
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW, PROC = ROOT / "data" / "raw", ROOT / "data" / "processed"
PROC.mkdir(parents=True, exist_ok=True)

MIN_FB = 300            # fastballs per season to qualify
GAP_DAYS = 30           # max days between appearances that flags an absence (IL / option)
LATE_DAYS = 21          # last appearance this many days before the season's last game

SWING = {"swinging_strike", "swinging_strike_blocked", "foul", "foul_tip",
         "hit_into_play", "foul_bunt", "missed_bunt", "bunt_foul_tip"}
WHIFF = {"swinging_strike", "swinging_strike_blocked", "foul_tip", "missed_bunt"}
CALLED = {"called_strike"}


def season_profiles(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["game_date"] = pd.to_datetime(df["game_date"])
    df["year"] = df["game_date"].dt.year
    df["swing"] = df["description"].isin(SWING)
    df["whiff"] = df["description"].isin(WHIFF)
    df["csw"] = df["description"].isin(WHIFF | CALLED)
    df["called"] = df["description"].isin(CALLED)
    df["swstr"] = df["description"].isin(WHIFF)
    df["in_zone"] = df["zone"].between(1, 9) if "zone" in df else np.nan
    df["z_swing"] = df["in_zone"] & df["swing"]
    df["z_called"] = df["in_zone"] & df["called"]
    df["o_called"] = ~df["in_zone"] & df["called"] & df["zone"].notna()
    # pitch shape in inches; horizontal break signed so + = arm side for both hands
    df["ivb"] = df["pfx_z"] * 12
    df["hb_arm"] = np.where(df["p_throws"] == "R", -df["pfx_x"], df["pfx_x"]) * 12
    df["team"] = np.where(df["inning_topbot"] == "Top", df["home_team"], df["away_team"])
    pa = df["woba_denom"].fillna(0) > 0
    df["x_num"] = np.where(pa, df["estimated_woba_using_speedangle"].fillna(df["woba_value"]), 0.0)
    df["x_den"] = np.where(pa, df["woba_denom"], 0.0)
    df["first_inning"] = df["inning"] == 1
    df["perceived_gain"] = df["effective_speed"] - df["release_speed"]

    season_end = df.groupby("year")["game_date"].max()
    rows = []
    for (pid, yr), g in df.groupby(["pitcher", "year"]):
        games = g.groupby("game_pk").agg(d=("game_date", "first"), first=("first_inning", "any"))
        dates = games["d"].sort_values()
        gaps = dates.diff().dt.days
        rows.append({
            "pitcher": pid, "year": yr, "name": g["player_name"].iloc[0],
            "throws": g["p_throws"].iloc[0], "team": g["team"].mode().iloc[0],
            "n_teams": g["team"].nunique(), "n_fb": len(g), "games": len(games),
            "ext": g["release_extension"].mean(), "velo": g["release_speed"].mean(),
            "eff_velo": g["effective_speed"].mean(),
            "perceived_gain": g["perceived_gain"].mean(),
            "arm_angle": g["arm_angle"].mean() if "arm_angle" in g else np.nan,
            "rel_z": g["release_pos_z"].mean(),
            "swings": int(g["swing"].sum()),
            "whiff_pct": 100 * g["whiff"].sum() / max(g["swing"].sum(), 1),
            "csw_pct": 100 * g["csw"].mean(),
            "called_pct": 100 * g["called"].mean(),   # called strikes per pitch
            "swstr_pct": 100 * g["swstr"].mean(),     # swinging strikes per pitch
            "ivb": g["ivb"].mean(), "hb_arm": g["hb_arm"].mean(),
            "spin": g["release_spin_rate"].mean(),
            "zone_pct": 100 * g["in_zone"].mean(),
            "z_swing_pct": 100 * g["z_swing"].sum() / max(g["in_zone"].sum(), 1),
            "z_called_pct": 100 * g["z_called"].sum() / max(g["in_zone"].sum(), 1),
            "o_called_pct": 100 * g["o_called"].sum() / max((~g["in_zone"] & g["zone"].notna()).sum(), 1),
            "rv100": -100 * g["delta_run_exp"].sum() / len(g),  # + = good for pitcher
            "xwoba": g["x_num"].sum() / g["x_den"].sum() if g["x_den"].sum() else np.nan,
            "starter_share": games["first"].mean(),
            "max_gap_days": float(gaps.max()) if len(gaps) > 1 else np.nan,
            "days_missed_end": (season_end[yr] - dates.max()).days,
            # split-half (odd/even game) extension, for measurement reliability
            "ext_odd": g[g["game_pk"].isin(games.index[::2])]["release_extension"].mean(),
            "ext_even": g[g["game_pk"].isin(games.index[1::2])]["release_extension"].mean(),
        })
    out = pd.DataFrame(rows)
    out["absence_flag"] = (out["max_gap_days"] >= GAP_DAYS) | (out["days_missed_end"] >= LATE_DAYS)
    out["role"] = np.where(out["starter_share"] >= 0.5, "SP", "RP")
    return out


def make_pairs(seasons: pd.DataFrame) -> pd.DataFrame:
    q = seasons[seasons["n_fb"] >= MIN_FB]
    a = q.add_suffix("_y0").rename(columns={"pitcher_y0": "pitcher"})
    b = q.add_suffix("_y1").rename(columns={"pitcher_y1": "pitcher"})
    p = a.merge(b, on="pitcher")
    p = p[p["year_y1"] == p["year_y0"] + 1].copy()
    for m in ["ext", "velo", "eff_velo", "perceived_gain", "arm_angle", "whiff_pct",
              "csw_pct", "called_pct", "swstr_pct", "ivb", "hb_arm", "spin", "zone_pct", "z_swing_pct", "z_called_pct",
              "o_called_pct", "rv100", "xwoba"]:
        p[f"d_{m}"] = p[f"{m}_y1"] - p[f"{m}_y0"]
    p["pair"] = p["year_y0"].astype(str) + "->" + p["year_y1"].astype(str)
    # alternative-explanation flags
    p["flag_absence"] = p["absence_flag_y0"] | p["absence_flag_y1"]
    p["flag_role_change"] = p["role_y0"] != p["role_y1"]
    p["flag_team_change"] = p["team_y0"] != p["team_y1"]
    p["flag_arm_angle"] = p["d_arm_angle"].abs() >= 5
    return p.reset_index(drop=True)


def apply_manual_exclusions(p: pd.DataFrame) -> pd.DataFrame:
    path = ROOT / "data" / "injury_exclusions.csv"
    p["manual_exclude"] = False
    p["manual_note"] = ""
    if path.exists():
        ex = pd.read_csv(path)
        for _, r in ex.iterrows():
            m = (p["name_y0"] == r["pitcher_name"]) & (p["pair"] == r["pair"])
            if r["action"] == "exclude":
                p.loc[m, "manual_exclude"] = True
            p.loc[m, "manual_note"] = f"{r['injury_type']}: {r['reason']}"
    return p


if __name__ == "__main__":
    files = sorted(RAW.glob("fastballs_*.csv"))
    raw = pd.concat([pd.read_csv(f, low_memory=False) for f in files], ignore_index=True)
    raw = raw[raw["game_type"] == "R"]
    seasons = season_profiles(raw)
    seasons.to_csv(PROC / "pitcher_seasons.csv", index=False, encoding="utf-8")
    pairs = apply_manual_exclusions(make_pairs(seasons))
    pairs.to_csv(PROC / "pairs.csv", index=False, encoding="utf-8")
    print(f"{len(seasons):,} pitcher-seasons; {len(pairs):,} year-over-year pairs")
