"""Histogram of year-over-year extension change with the measurement threshold."""
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from charts import NAVY, GOLD, BLUE, BG, MUTED, style  # noqa

ROOT = Path(__file__).resolve().parents[1]
p = pd.read_csv(ROOT / "data/processed/primary_sample.csv")
fig, ax = plt.subplots(figsize=(8, 4.2))
bins = np.arange(-0.5, 0.55, 0.05)
ax.hist(p["d_ext"], bins=bins, color=BLUE, edgecolor=BG, linewidth=2)
for x, lab in [(-0.05, "-0.05"), (0.05, "+0.05")]:
    ax.axvline(x, color=GOLD, ls="--", lw=1.5)
ax.text(-0.52, ax.get_ylim()[1] * 0.62, "Gold dashed lines:\nmeasurement noise\n(± 0.05 ft)", color=GOLD, fontsize=11)
ax.axvline(0.3, color=NAVY, lw=1.2)
ax.text(0.31, ax.get_ylim()[1] * 0.55, f"+0.3 ft or more:\n{(p.d_ext >= 0.3).mean()*100:.1f}% of pairs", fontsize=11)
ax.set_xlabel("Year-over-year change in average fastball extension (ft)")
ax.set_ylabel("Pitcher pairs")
ax.set_title("Most pitchers barely change extension year to year", loc="left", fontweight="bold")
style(ax)
fig.tight_layout()
fig.savefig(ROOT / "figures/extension_change_distribution.png", dpi=200)
print("ok")
