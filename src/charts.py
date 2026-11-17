"""EP-branded charts. Palette validated for color-vision deficiency
(data blue #2A62A8 / gold #B8862A on off-white; navy #0B1B33 for text only)."""
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RES, FIG = ROOT / "results", ROOT / "figures"
FIG.mkdir(exist_ok=True)

NAVY, GOLD, BLUE, BG, MUTED = "#0B1B33", "#B8862A", "#2A62A8", "#F5F3EC", "#6B7280"
plt.rcParams.update({"font.family": ["Poppins", "DejaVu Sans"], "axes.edgecolor": MUTED,
                     "axes.labelcolor": NAVY, "xtick.color": NAVY, "ytick.color": NAVY,
                     "text.color": NAVY, "figure.facecolor": BG, "axes.facecolor": BG,
                     "font.size": 12, "axes.titlesize": 14, "axes.labelsize": 12})


def style(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(axis="y", color="#D9D6CC", lw=0.8)
    ax.set_axisbelow(True)


def dose_chart():
    d = pd.read_csv(RES / "dose_response.csv")
    fig, ax = plt.subplots(figsize=(8, 4.8))
    colors = [GOLD if v < 0 else BLUE for v in d["resid_csw"]]
    ax.bar(range(len(d)), d["resid_csw"], color=colors, width=0.6)
    ax.errorbar(range(len(d)), d["resid_csw"], yerr=1.96 * d["resid_csw_se"],
                fmt="none", ecolor=NAVY, lw=1.2, capsize=4)
    ax.axhline(0, color=NAVY, lw=1)
    for i, r in d.iterrows():
        y = r["resid_csw"] + (1.96 * r["resid_csw_se"] + 0.15) * (1 if r["resid_csw"] >= 0 else -1)
        ax.text(i, y, f"{r['resid_csw']:+.2f}\nn={int(r['n'])}", ha="center",
                va="bottom" if r["resid_csw"] >= 0 else "top", fontsize=11)
    lo = (d["resid_csw"] - 1.96 * d["resid_csw_se"]).min()
    hi = (d["resid_csw"] + 1.96 * d["resid_csw_se"]).max()
    ax.set_ylim(lo - 0.9, hi + 1.2)
    ax.set_xticks(range(len(d)), [f"{b} ft".replace(">=", "≥ ") for b in d.iloc[:, 0]])
    ax.set_xlabel("Year-over-year change in fastball extension")
    ax.set_ylabel("CSW% change beyond velocity (pts)")
    ax.set_title("More extension came with more fastball strikes (CSW%)",
                 loc="left", fontweight="bold")
    style(ax)
    fig.text(0.01, 0.01, "Emerson Performance | Statcast 2021-2026, FF+SI, min 300 fastballs per season",
             fontsize=9, color=MUTED)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(FIG / "extension_dose_response.png", dpi=200)


def forest_chart():
    m = pd.read_csv(RES / "main_effects.csv")
    names = {"whiff_pct": "Whiff% (pts)", "csw_pct": "CSW% (pts)",
             "rv100": "Run value / 100 (runs)", "xwoba": "xwOBA allowed"}
    fig, axes = plt.subplots(1, len(m), figsize=(11, 4.2))
    for ax, (_, r) in zip(axes, m.iterrows()):
        lo, hi, e = r["boot_lo_0.3ft"], r["boot_hi_0.3ft"], r["effect_per_0.3ft"]
        ax.plot([lo, hi], [0, 0], color=NAVY, lw=2)
        ax.plot(e, 0, "o", ms=9, color=BLUE, mec=BG, mew=2)
        ax.axvline(0, color=MUTED, lw=1)
        ax.axvline(r["practical_threshold"], color=GOLD, lw=1.5, ls="--")
        ax.text(r["practical_threshold"], 0.6, "practical\nthreshold", color=GOLD,
                ha="center", fontsize=10, bbox=dict(fc=BG, ec="none", pad=1))
        ax.text(e, -0.45, f"{e:+.3f}" if r["outcome"] == "xwoba" else f"{e:+.2f}",
                ha="center", fontsize=12, fontweight="bold", bbox=dict(fc=BG, ec="none", pad=1))
        ax.set_ylim(-1, 1.2)
        ax.set_yticks([])
        ax.set_title(f"{names[r['outcome']]}\n{r['label']}", fontsize=11, loc="left")
        for s in ("top", "right", "left"):
            ax.spines[s].set_visible(False)
    fig.suptitle("Effect of +0.3 ft extension, velocity held constant (95% CI)",
                 x=0.01, ha="left", fontweight="bold", fontsize=14)
    fig.tight_layout()
    fig.savefig(FIG / "extension_effects_forest.png", dpi=200)


if __name__ == "__main__":
    dose_chart()
    forest_chart()
    print("figures saved")
