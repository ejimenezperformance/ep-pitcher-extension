"""Where the CSW% gain came from: called vs swinging strikes (per +0.3 ft)."""
from pathlib import Path
import sys
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from charts import NAVY, GOLD, BLUE, BG, MUTED, style  # noqa: E402

d = pd.read_csv(ROOT / "results/decomposition.csv").set_index("outcome")
main = pd.read_csv(ROOT / "results/main_effects.csv").set_index("outcome")
rows = [("CSW% (total)", d.loc["csw_pct", "effect_per_0.3ft"], main.loc["csw_pct", "boot_lo_0.3ft"], main.loc["csw_pct", "boot_hi_0.3ft"], NAVY),
        ("Called strikes", d.loc["called_pct", "effect_per_0.3ft"], d.loc["called_pct", "boot_lo_0.3ft"], d.loc["called_pct", "boot_hi_0.3ft"], BLUE),
        ("Swinging strikes", d.loc["swstr_pct", "effect_per_0.3ft"], d.loc["swstr_pct", "boot_lo_0.3ft"], d.loc["swstr_pct", "boot_hi_0.3ft"], GOLD)]
fig, ax = plt.subplots(figsize=(8, 3.2))
for i, (lab, e, lo, hi, c) in enumerate(rows):
    y = len(rows) - 1 - i
    ax.barh(y, e, color=c, height=0.5)
    ax.errorbar(e, y, xerr=[[e - lo], [hi - e]], fmt="none", ecolor=NAVY, capsize=4, lw=1.2)
    ax.text(hi + 0.05, y, f"{e:+.2f}", va="center", fontsize=12, fontweight="bold")
ax.set_yticks(range(len(rows)), [r[0] for r in rows][::-1])
ax.axvline(0, color=NAVY, lw=1)
ax.set_xlim(-0.4, 1.7)
ax.set_xlabel("Points per pitch, per +0.3 ft of extension (95% CI)")
ax.set_title("Most of the gain came from called strikes", loc="left", fontweight="bold")
style(ax)
ax.grid(axis="y", visible=False); ax.grid(axis="x", color="#D9D6CC", lw=0.8)
fig.tight_layout()
fig.savefig(ROOT / "figures/csw_decomposition.png", dpi=200)
print("ok")
