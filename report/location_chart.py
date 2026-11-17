"""Location effects per +0.3 ft (dot + 95% CI)."""
from pathlib import Path
import sys
import matplotlib.pyplot as plt
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from charts import NAVY, GOLD, BLUE, BG, MUTED, style  # noqa: E402
L = pd.read_csv(ROOT / "results/location.csv").set_index("outcome")
rows = [("Fastballs in the zone", "zone_pct"), ("Swings at zone fastballs", "z_swing_pct"),
        ("Called strikes on zone fastballs", "z_called_pct"), ("Called strikes outside the zone", "o_called_pct")]
fig, ax = plt.subplots(figsize=(8, 3.4))
for i, (lab, o) in enumerate(rows):
    y = len(rows) - 1 - i
    r = L.loc[o]
    c = GOLD if r["effect_per_0.3ft"] < 0 else BLUE
    ax.plot([r["boot_lo_0.3ft"], r["boot_hi_0.3ft"]], [y, y], color=NAVY, lw=2)
    ax.plot(r["effect_per_0.3ft"], y, "o", ms=10, color=c, mec=BG, mew=2)
    ax.text(r["boot_hi_0.3ft"] + 0.08, y, f"{r['effect_per_0.3ft']:+.2f}", va="center", fontsize=12, fontweight="bold")
ax.axvline(0, color=MUTED, lw=1)
ax.set_yticks(range(len(rows)), [r[0] for r in rows][::-1])
ax.set_xlim(-2.0, 2.0)
ax.set_xlabel("Points per +0.3 ft of extension (95% CI)")
ax.set_title("More zone fastballs, fewer swings at them", loc="left", fontweight="bold")
style(ax); ax.grid(axis="y", visible=False); ax.grid(axis="x", color="#D9D6CC", lw=0.8)
fig.tight_layout(); fig.savefig(ROOT / "figures/location_effects.png", dpi=200); print("ok")
