"""Case study chart: Grant Taylor four-seam extension by outing, 2025-2026."""
from pathlib import Path
import sys

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from charts import NAVY, GOLD, BLUE, BG, MUTED, style  # noqa: E402

NAME = "Taylor, Grant"
frames = [pd.read_csv(ROOT / f"data/raw/fastballs_{y}.csv", low_memory=False) for y in (2025, 2026)]
t = pd.concat([f[(f["player_name"] == NAME) & (f["pitch_type"] == "FF")] for f in frames])
t["game_date"] = pd.to_datetime(t["game_date"])
g = t.groupby("game_date")["release_extension"].mean().reset_index()
g["year"] = g["game_date"].dt.year
g["i"] = range(len(g))
g["roll5"] = g["release_extension"].rolling(5, min_periods=3).mean()
base = g.loc[g["year"] == 2025, "release_extension"].mean()

fig, ax = plt.subplots(figsize=(8, 4.2))
for yr, c in ((2025, BLUE), (2026, GOLD)):
    s = g[g["year"] == yr]
    ax.scatter(s["i"], s["release_extension"], s=14, color=c, alpha=0.45, edgecolor="none")
ax.plot(g["i"], g["roll5"], color=NAVY, lw=2)
ax.axhline(base, color=BLUE, ls="--", lw=1.4)
ax.text(1, 7.66, f"2025 baseline {base:.2f} ft (dashed)", color=BLUE, fontsize=11)
gi = g.loc[g["game_date"] >= "2025-09-10", "i"].min()
ax.annotate("Groin strain\nSep 10, 2025", xy=(gi, g.loc[g["i"] == gi, "release_extension"].iloc[0]), xytext=(gi - 16, 6.86),
            fontsize=10, color=NAVY, arrowprops=dict(arrowstyle="->", color=NAVY, lw=1))
print("strain outing", gi, g.loc[g["i"] == gi, "game_date"].iloc[0].date())
split = g.loc[g["year"] == 2026, "i"].min() - 0.5
ax.axvline(split, color=MUTED, lw=1)
ax.text(split - 1, 6.72, "2025", ha="right", fontsize=11, color=BLUE)
ax.text(split + 1, 6.72, "2026", ha="left", fontsize=11, color=GOLD)
ax.text(g["i"].max(), 7.66, "Navy line: 5-outing average", ha="right", fontsize=11, color=NAVY)
ax.set_ylim(6.65, 7.75)
ax.set_xlabel("Outings, in order (four-seam fastballs only)")
ax.set_ylabel("Extension (ft)")
ax.set_title("Grant Taylor: four-seam extension by outing", loc="left", fontweight="bold")
style(ax)
fig.tight_layout()
fig.savefig(ROOT / "figures/case_taylor_extension.png", dpi=200)
print("ok", round(base, 3))
