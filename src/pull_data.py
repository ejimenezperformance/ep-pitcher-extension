"""Download regular-season fastballs (FF, SI) from Baseball Savant, 2021-2026.

Pulls the Statcast search CSV in 6-day windows (the endpoint caps a response
at 25,000 rows) and keeps only the columns this study needs.

Usage:
    python src/pull_data.py              # all seasons
    python src/pull_data.py 2025 2026    # selected seasons

Output: data/raw/fastballs_<year>.csv  (not committed; see .gitignore)
"""
from __future__ import annotations

import io
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)

SEASONS = {  # approximate regular-season windows; game_type == "R" filters the rest
    2021: ("2021-03-31", "2021-10-04"),
    2022: ("2022-04-06", "2022-10-06"),
    2023: ("2023-03-29", "2023-10-02"),
    2024: ("2024-03-19", "2024-09-30"),
    2025: ("2025-03-17", "2025-09-29"),
    2026: ("2026-03-24", "2026-09-28"),
}

KEEP = [
    "game_date", "game_pk", "game_type", "pitcher", "player_name", "p_throws",
    "pitch_type", "release_speed", "effective_speed", "release_extension",
    "release_pos_z", "arm_angle", "description", "events",
    "estimated_woba_using_speedangle", "woba_value", "woba_denom",
    "delta_run_exp", "inning", "inning_topbot", "home_team", "away_team",
    "at_bat_number", "pitch_number",
]

URL = "https://baseballsavant.mlb.com/statcast_search/csv"


def fetch(start: str, end: str, year: int) -> pd.DataFrame:
    params = {
        "all": "true", "hfPT": "FF|SI|", "hfGT": "R|", "hfSea": f"{year}|",
        "player_type": "pitcher", "game_date_gt": start, "game_date_lt": end,
        "type": "details", "min_pitches": "0", "min_results": "0",
    }
    for attempt in range(4):
        try:
            r = requests.get(URL, params=params, timeout=180)
            r.raise_for_status()
            df = pd.read_csv(io.StringIO(r.content.decode("utf-8-sig")), low_memory=False)
            if len(df) >= 25000:
                print(f"WARNING: {start}..{end} hit the 25k cap; shorten the window")
            return df[[c for c in KEEP if c in df.columns]]
        except Exception as exc:  # network hiccups: retry with backoff
            print(f"retry {start}..{end} ({exc})")
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"failed {start}..{end}")


def windows(start: str, end: str, days: int = 6):
    d0, d1 = date.fromisoformat(start), date.fromisoformat(end)
    while d0 <= d1:
        w1 = min(d0 + timedelta(days=days - 1), d1)
        yield d0.isoformat(), w1.isoformat()
        d0 = w1 + timedelta(days=1)


def pull_season(year: int) -> None:
    out = RAW / f"fastballs_{year}.csv"
    if out.exists():
        print(f"{year}: already downloaded")
        return
    start, end = SEASONS[year]
    with ThreadPoolExecutor(max_workers=4) as ex:
        parts = list(ex.map(lambda w: fetch(w[0], w[1], year), windows(start, end)))
    df = pd.concat(parts, ignore_index=True)
    df = df[df["game_type"] == "R"].drop_duplicates(
        subset=["game_pk", "at_bat_number", "pitch_number"])
    df.to_csv(out, index=False, encoding="utf-8")
    print(f"{year}: {len(df):,} fastballs -> {out.name}")


if __name__ == "__main__":
    years = [int(y) for y in sys.argv[1:]] or list(SEASONS)
    for y in years:
        pull_season(y)
